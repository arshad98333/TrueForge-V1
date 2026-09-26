import { Sandbox, CommandExitError } from 'e2b';
import path from 'node:path';

const ROOT = '/home/user/.trueforge';
const MAX_OUTPUT = 65536;

function safePath(value) {
  const normalized = path.posix.normalize(value);
  if (!normalized.startsWith(ROOT + '/')) throw new Error('Sandbox path is outside the workspace');
  return normalized;
}

// TrueForge 0.2.1 SandboxProvider contract. MCP executes on the host; no credentials
// or Code Mode transport are installed in this isolated calculation sandbox.
export class E2BSandboxProvider {
  type = 'e2b';
  static cache = new Map();

  constructor({ apiKey, tenantName, template = 'base', timeoutMs = 20000,
    lifetimeMs = 1800000, sdk = Sandbox }) {
    if (!apiKey || !tenantName) throw new Error('E2B configuration is incomplete');
    this.apiKey = apiKey;
    this.tenantName = tenantName;
    this.template = template;
    this.timeoutMs = Math.min(timeoutMs, 20000);
    this.lifetimeMs = Math.min(lifetimeMs, 3600000);
    this.sdk = sdk;
  }

  async buildImage() {
    // E2B runs its published template; there is no release-image build to queue.
    // This is template selection, not a claim that credentials/execution were tested.
    return { status: 'ready', reason: null, metadata: { template: this.template } };
  }
  async getImageBuildStatus() { return this.buildImage(); }

  async createSandbox() {
    try {
      const sandbox = await this.sdk.create(this.template, {
        apiKey: this.apiKey, timeoutMs: this.lifetimeMs, requestTimeoutMs: 60000,
        allowInternetAccess: false, network: { allowPublicTraffic: false },
        metadata: { application: 'roaming-resolver', tenant: this.tenantName },
      });
      E2BSandboxProvider.cache.set(this.tenantName + ':' + sandbox.sandboxId, sandbox);
      return { sandboxId: sandbox.sandboxId };
    } catch {
      throw new Error('E2B provisioning failed; verify credentials, template, and quota');
    }
  }

  async getSandbox(sandboxId) {
    const key = this.tenantName + ':' + sandboxId;
    let sandbox = E2BSandboxProvider.cache.get(key);
    if (!sandbox) {
      sandbox = await this.sdk.connect(sandboxId, {
        apiKey: this.apiKey, timeoutMs: this.lifetimeMs, requestTimeoutMs: 20000,
      });
      const info = await sandbox.getInfo();
      if (info.metadata?.tenant !== this.tenantName ||
          info.metadata?.application !== 'roaming-resolver') {
        throw new Error('E2B sandbox ownership mismatch');
      }
      E2BSandboxProvider.cache.set(key, sandbox);
    }
    return sandbox;
  }

  async exec({ sandboxId, command, cwd, env = {}, timeoutSeconds }) {
    let handle;
    let overflow = false;
    let bytes = 0;
    const count = async (chunk) => {
      bytes += Buffer.byteLength(chunk);
      if (bytes > MAX_OUTPUT) {
        overflow = true;
        if (handle) {
          await handle.kill().catch(() => {});
          await handle.disconnect().catch(() => {});
        }
        throw new Error('Sandbox output exceeded 64 KiB');
      }
    };
    try {
      if (Object.keys(env).some(k => /KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL/i.test(k))) {
        throw new Error('Credentials must not enter the calculation sandbox');
      }
      const sandbox = await this.getSandbox(sandboxId);
      handle = await sandbox.commands.run(command, {
        background: true, cwd: cwd ?? '/home/user', envs: env,
        timeoutMs: Math.min(timeoutSeconds ? timeoutSeconds * 1000 : this.timeoutMs, 20000),
        requestTimeoutMs: 25000, onStdout: count, onStderr: count,
      });
      if (overflow) await handle.kill().catch(() => {});
      let result;
      try { result = await handle.wait(); }
      catch (error) {
        if (!(error instanceof CommandExitError)) throw error;
        result = error;
      }
      const output = result.stdout + result.stderr;
      if (overflow || Buffer.byteLength(output) > MAX_OUTPUT) throw new Error('Output limit');
      return { success: true, response: { exitCode: result.exitCode, result: output } };
    } catch {
      if (handle) await handle.kill().catch(() => {});
      return { success: false, error: overflow ? 'Sandbox output exceeded 64 KiB' :
        'E2B execution failed or timed out; no automatic retry' };
    } finally {
      if (handle) await handle.disconnect().catch(() => {});
    }
  }

  getAdditionalInstructions() {
    return 'E2B isolated calculation sandbox. Internet and Code Mode are disabled. ' +
      'Call MCP tools directly. Use only the exact prepared native exec command.';
  }
  getToolResultDumpDir() { return ROOT + '/results'; }
  getGitCredentialsPath() { return ROOT + '/git-credentials'; }
  getFileUploadsDir() { return ROOT + '/uploads'; }
  getSkillsDir() { return ROOT + '/skills'; }
  getSkillDownloaderPath() { return ROOT + '/download-skills.py'; }

  async downloadFile({ sandboxId, path: filename }) {
    const sandbox = await this.getSandbox(sandboxId);
    const remote = safePath(filename);
    const info = await sandbox.files.getInfo(remote);
    if (info.size > MAX_OUTPUT || info.type === 'dir') throw new Error('File is not a small artifact');
    const bytes = await sandbox.files.read(remote, { format: 'bytes' });
    if (bytes.length > MAX_OUTPUT) throw new Error('Artifact exceeds 64 KiB');
    return Buffer.from(bytes);
  }
  async uploadFile({ sandboxId, remotePath, content }) {
    if (content.length > MAX_OUTPUT) throw new Error('Artifact exceeds 64 KiB');
    const remote = safePath(remotePath);
    const sandbox = await this.getSandbox(sandboxId);
    await sandbox.files.write(remote, content);
  }
  createCodeModeTransport() {
    return {
      getClientInstall: () => ({
        remotePath: ROOT + '/mcp-client.py',
        content: '#!/usr/bin/env python3\nraise SystemExit("Code Mode disabled; call native MCP tools")\n',
      }),
      start: async () => ({ env: {} }),
      stop: async () => {},
    };
  }
}

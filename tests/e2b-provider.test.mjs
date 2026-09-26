import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { E2BSandboxProvider } from '../runtime/e2b-provider.mjs';
import { extendSkillMounter, extendTrueForge } from '../runtime/trueforge-e2b-hook.mjs';

function fakeProvider() {
  const calls = [];
  const sandbox = {
    sandboxId: 'test-' + Math.random(),
    getInfo: async () => ({ metadata: { tenant: 'test', application: 'roaming-resolver' } }),
    commands: { run: async (command, options) => {
      calls.push({ command, options });
      return { wait: async () => ({ stdout: 'ok', stderr: '', exitCode: 0 }),
        kill: async () => true, disconnect: async () => {} };
    } },
  };
  const sdk = { create: async (template, options) => {
    calls.push({ template, options }); return sandbox;
  }, connect: async () => sandbox };
  return { provider: new E2BSandboxProvider({ apiKey: 'fake-test-key', tenantName: 'test', sdk }),
    calls, sandbox };
}

test('pinned TrueForge extension exposes honest E2B type and refuses drift', () => {
  const source = readFileSync(new URL('../node_modules/@truefoundry/trueforge/dist/main.js', import.meta.url), 'utf8');
  const patched = extendTrueForge(source);
  assert.match(patched, /type: z12.literal\("e2b"\)/);
  assert.match(patched, /case "e2b":\n    case "daytona":/);
  assert.throws(() => extendTrueForge(source + '\n'), /Unsupported TrueForge/);
});
test('empty agent skills skip the optional pydantic downloader bootstrap', () => {
  const source = readFileSync(new URL('../node_modules/@truefoundry/trueforge-core/dist/core/sandbox/skills/SkillMounter.mjs', import.meta.url), 'utf8');
  const patched = extendSkillMounter(source);
  assert.match(patched, /if \(this\.skills\.length === 0\) return null/);
  assert.throws(() => extendSkillMounter(source + '\n'), /Unsupported TrueForge SkillMounter/);
});
test('creation disables internet/public traffic and forwards no env secrets', async () => {
  const { provider, calls } = fakeProvider();
  await provider.createSandbox();
  assert.equal(calls[0].options.allowInternetAccess, false);
  assert.equal(calls[0].options.network.allowPublicTraffic, false);
  assert.equal(calls[0].options.envs, undefined);
});
test('native exec contract enforces 20s even if caller requests more', async () => {
  const { provider, calls } = fakeProvider();
  const { sandboxId } = await provider.createSandbox();
  const result = await provider.exec({ sandboxId, command: 'python3 --version', timeoutSeconds: 999 });
  assert.deepEqual(result, { success: true, response: { exitCode: 0, result: 'ok' } });
  assert.equal(calls[1].options.timeoutMs, 20000);
});
test('credentials, oversized output and cross-tenant reconnect fail closed', async () => {
  const { provider, sandbox } = fakeProvider();
  const { sandboxId } = await provider.createSandbox();
  assert.equal((await provider.exec({ sandboxId, command: 'x', env: { API_KEY: 'fake' } })).success, false);
  sandbox.commands.run = async () => ({
    wait: async () => ({ stdout: 'x'.repeat(65537), stderr: '', exitCode: 0 }),
    kill: async () => true, disconnect: async () => {},
  });
  assert.equal((await provider.exec({ sandboxId, command: 'x' })).success, false);
  sandbox.getInfo = async () => ({ metadata: { tenant: 'other' } });
  assert.equal((await provider.exec({ sandboxId: 'not-cached', command: 'x' })).success, false);
});
test('Code Mode has no RPC channel; artifact paths cannot escape workspace', async () => {
  const { provider } = fakeProvider();
  const transport = provider.createCodeModeTransport();
  assert.deepEqual(await transport.start(), { env: {} });
  await assert.rejects(provider.uploadFile({ sandboxId: 'unused', remotePath: '/etc/passwd', content: Buffer.from('x') }), /outside/);
});

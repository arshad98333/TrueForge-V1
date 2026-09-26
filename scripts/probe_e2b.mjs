import { mkdirSync, writeFileSync } from 'node:fs';
import { Sandbox } from 'e2b';
import { E2BSandboxProvider } from '../runtime/e2b-provider.mjs';

process.loadEnvFile('.env');
const apiKey = process.env.E2B_API_KEY || process.env.E2B_SANDBOX;
const provider = new E2BSandboxProvider({ apiKey, tenantName: 'resolver-preflight',
  template: process.env.E2B_TEMPLATE || 'base', lifetimeMs: 120000 });
let sandboxId;
try {
  ({ sandboxId } = await provider.createSandbox());
  const result = await provider.exec({ sandboxId,
    command: 'env -i PATH=/usr/local/bin:/usr/bin:/bin timeout 20s python3 -I -S -c \'import json, os, resource; print(json.dumps({"python": True, "credentials_absent": not any("KEY" in k or "TOKEN" in k for k in os.environ)}))\'' });
  if (!result.success || result.response.exitCode !== 0) throw new Error('E2B exec failed');
  const report = { checked_at: new Date().toISOString(), provider: 'e2b',
    sdk_version: '2.51.0', provisioning: 'passed', execution: JSON.parse(result.response.result),
    native_trueforge_execution: 'not tested by this provider probe' };
  mkdirSync('.runtime', { recursive: true });
  writeFileSync('.runtime/e2b-probe.json', JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
} catch {
  console.error('E2B probe failed. Verify connectivity, API key, template, and account quota.');
  process.exitCode = 1;
} finally {
  if (sandboxId) {
    try { await Sandbox.kill(sandboxId, { apiKey }); console.log('Probe sandbox removed.'); }
    catch { console.error('Probe sandbox cleanup failed; it expires after two minutes.'); }
  }
}

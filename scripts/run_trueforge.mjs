import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { installE2BHook } from '../runtime/trueforge-e2b-hook.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
process.chdir(root);
mkdirSync('.runtime', { recursive: true });
process.env.SQLITE_PATH = path.join(root, '.runtime', 'trueforge.sqlite');
process.env.HOST = '127.0.0.1';
process.env.ACCESS_LOGS = 'false';
process.env.OUTBOUND_URL_ALLOWED_HOSTS = '["127.0.0.1"]';
installE2BHook();
await import('../node_modules/@truefoundry/trueforge/dist/cli.js');

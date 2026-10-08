import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const cwd = fileURLToPath(new URL('../', import.meta.url));
for (const args of [
  ['node_modules/typescript/bin/tsc', '-p', 'tsconfig.json'],
  ['--test', '--test-concurrency=1', 'test/protocol.test.mjs', 'test/http-backend.test.mjs'],
]) {
  const result = spawnSync(process.execPath, args, { cwd, stdio: 'inherit', windowsHide: true });
  if (result.error || result.status !== 0) process.exit(result.status || 1);
}

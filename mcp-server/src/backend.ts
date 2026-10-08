import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process';
import { fileURLToPath } from 'node:url';

export class Backend {
  private child: ChildProcessWithoutNullStreams;
  private buffer = '';
  private sequence = 0;
  private pending = new Map<number, { resolve: (x: unknown) => void; reject: (e: Error) => void }>();
  constructor() {
    const env: Record<string, string> = {};
    for (const key of ['PATH', 'Path', 'SystemRoot', 'WINDIR', 'TEMP', 'TMP', 'PYTHONHOME',
      'SERVICE_DESK_MODE', 'SERVICE_DESK_BINDINGS', 'SERVICE_DESK_API_TOKEN', 'SERVICE_DESK_TEST_FIXTURES']) {
      if (process.env[key]) env[key] = process.env[key]!;
    }
    this.child = spawn(process.env.SERVICE_DESK_PYTHON ?? 'python', ['-B', '-m', 'service_desk.bridge'], {
      cwd: fileURLToPath(new URL('../../backend/', import.meta.url)), env, windowsHide: true,
      stdio: ['pipe', 'pipe', 'pipe'],
    });
    this.child.stdout.setEncoding('utf8');
    this.child.stderr.resume(); // Never forward Python exception/config details to MCP.
    this.child.on('error', () => this.fail());
    this.child.on('exit', () => this.fail());
    this.child.stdin.on('error', () => this.fail());
    this.child.stdout.on('data', (chunk: string) => {
      this.buffer += chunk;
      if (Buffer.byteLength(this.buffer) > 65536) { this.close(); return; }
      let newline: number;
      while ((newline = this.buffer.indexOf('\n')) >= 0) {
        const line = this.buffer.slice(0, newline); this.buffer = this.buffer.slice(newline + 1);
        try {
          const result = JSON.parse(line);
          const pending = this.pending.get(result.id);
          if (pending) {
            this.pending.delete(result.id);
            if (result.ok) pending.resolve(result.data);
            else pending.reject(new Error(typeof result.error === 'string' ? result.error : 'backend_error'));
          }
        } catch { this.close(); }
      }
    });
  }
  private fail() {
    for (const item of this.pending.values()) item.reject(new Error('backend_unavailable'));
    this.pending.clear();
  }
  async call(command: string, args: Record<string, unknown>, signal?: AbortSignal): Promise<unknown> {
    if (signal?.aborted) throw new Error('cancelled');
    if (this.pending.size >= 16 || this.child.exitCode !== null) throw new Error('backend_unavailable');
    const id = ++this.sequence;
    return new Promise((resolve, reject) => {
      const finish = (error?: Error, data?: unknown) => {
        clearTimeout(timer); signal?.removeEventListener('abort', abort); this.pending.delete(id);
        if (error) reject(error); else resolve(data);
      };
      const abort = () => finish(new Error('cancelled_outcome_unknown'));
      const timer = setTimeout(() => finish(new Error('timeout_outcome_unknown')), 5000);
      signal?.addEventListener('abort', abort, { once: true });
      this.pending.set(id, { resolve: x => finish(undefined, x), reject: e => finish(e) });
      const line = JSON.stringify({ id, command, args });
      if (Buffer.byteLength(line) > 16384) { finish(new Error('input_limit')); return; }
      this.child.stdin.write(line + '\n', error => { if (error) finish(new Error('backend_unavailable')); });
    });
  }
  close() { this.child.kill(); this.fail(); }
}

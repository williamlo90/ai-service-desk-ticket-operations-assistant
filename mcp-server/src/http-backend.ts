// Loopback integration only. Token belongs to one operator-configured identity.
export class HttpBackend {
  private origin: string;
  private token: string;
  private active = 0;
  private shutdown = new AbortController();
  constructor(origin: string, token: string) {
    const url = new URL(origin);
    if (url.protocol !== 'http:' || url.hostname !== '127.0.0.1' || !url.port ||
      url.username || url.password || url.pathname !== '/' || url.search || url.hash ||
      !/^[\x21-\x7e]{32,512}$/.test(token)) throw new Error('Invalid local API configuration');
    this.origin = url.origin; this.token = token;
  }
  async call(command: string, args: Record<string, unknown>, signal?: AbortSignal): Promise<unknown> {
    if (signal?.aborted || this.shutdown.signal.aborted) throw new Error('cancelled');
    if (!new Set(['search','create','context','prepare','execute','verify','close','reopen']).has(command))
      throw new Error('invalid_arguments');
    if (this.active >= 16) throw new Error('backend_unavailable');
    const body = JSON.stringify(args);
    if (Buffer.byteLength(body) > 16384) throw new Error('input_limit');
    const timeout = AbortSignal.timeout(5000);
    const combined = AbortSignal.any([timeout, this.shutdown.signal, ...(signal ? [signal] : [])]);
    this.active++;
    try {
      const response = await fetch(`${this.origin}/v1/tools/${command}`, { method: 'POST',
        redirect: 'error', signal: combined, headers: { Authorization: `Bearer ${this.token}`,
          'Content-Type': 'application/json' }, body });
      const reader = response.body?.getReader();
      if (!reader) throw new Error('backend_unavailable');
      const chunks: Uint8Array[] = []; let size = 0;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        size += value.byteLength;
        if (size > 60000) { await reader.cancel(); throw new Error('output_limit'); }
        chunks.push(value);
      }
      const result = JSON.parse(Buffer.concat(chunks).toString('utf8'));
      if (!response.ok) throw new Error(typeof result.error === 'string' ? result.error : 'request_rejected');
      if (typeof result !== 'object' || result === null || Object.keys(result).join() !== 'result')
        throw new Error('request_rejected');
      return result.result;
    } catch (error) {
      if (signal?.aborted || this.shutdown.signal.aborted) throw new Error('cancelled_outcome_unknown');
      if (timeout.aborted) throw new Error('timeout_outcome_unknown');
      // No transport details or URL/credential-bearing errors cross the boundary.
      if (error instanceof TypeError || error instanceof SyntaxError) throw new Error('reconciliation_required');
      throw error;
    } finally { this.active--; }
  }
  close() { this.shutdown.abort(); }
}

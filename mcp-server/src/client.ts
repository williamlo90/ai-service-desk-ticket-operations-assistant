import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { fileURLToPath } from 'node:url';

// Reference client inherits only deliberately configured local identity, never .env.
const env: Record<string, string> = {};
for (const key of ['PATH','Path','SystemRoot','WINDIR','TEMP','TMP','SERVICE_DESK_PYTHON',
  'SERVICE_DESK_MODE','SERVICE_DESK_BINDINGS','SERVICE_DESK_API_TOKEN']) {
  if (process.env[key]) env[key] = process.env[key]!;
}
const client = new Client({ name: 'service-desk-reference-client', version: '0.1.0' });
const transport = new StdioClientTransport({ command: process.execPath,
  args: [fileURLToPath(new URL('./server.js', import.meta.url))], env, stderr: 'pipe', maxBufferSize: 65536 });
try {
  await client.connect(transport);
  const tools = await client.listTools();
  console.log(JSON.stringify({ tools: tools.tools.map(tool => tool.name) }));
  const result = await client.callTool({ name: 'ticket.search', arguments: { query: '', offset: 0, limit: 5 } });
  console.log(JSON.stringify(result));
} finally { await client.close(); }

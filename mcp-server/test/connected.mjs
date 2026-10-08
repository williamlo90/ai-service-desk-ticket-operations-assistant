// Invoked by the disposable PostgreSQL harness. Config is stdin, never logged.
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
let raw = ''; for await (const chunk of process.stdin) raw += chunk;
const config = JSON.parse(raw); raw = '';
const env = { SERVICE_DESK_MODE: config.mode ?? 'synthetic', SERVICE_DESK_API_URL: config.origin,
  SERVICE_DESK_API_TOKEN: config.staff };
for (const key of ['PATH','Path','SystemRoot','WINDIR','TEMP','TMP']) if (process.env[key]) env[key] = process.env[key];
const client = new Client({ name: 'connected-contract', version: '1.0.0' });
const transport = new StdioClientTransport({ command: process.execPath,
  args: [fileURLToPath(new URL('../dist/server.js', import.meta.url))], env, stderr: 'pipe' });
transport.stderr?.resume();
async function call(name, args) {
  const reply = await client.callTool({ name: `ticket.${name}`, arguments: args });
  assert.ok(!JSON.stringify(reply).includes(config.staff));
  return reply;
}
function data(reply) { assert.ok(!reply.isError); return reply.structuredContent.result; }
try {
  await client.connect(transport);
  const list = await client.listTools(); assert.equal(list.tools.length, 8);
  if (config.stage === 'approved') {
    const context = data(await call('get_context', { case_id: config.case_id }));
    assert.equal(context.case.source.key, 'IT-1');
    assert.equal(context.case.category, 'access_request');
    const receipt = data(await call('apply_approved_update', {
      case_id: config.case_id, expected_version: context.case.version }));
    assert.ok(['accepted','succeeded'].includes(receipt.action.status));
    assert.equal(data(await call('verify_outcome', { case_id: config.case_id })).evidence.matches, true);
    assert.equal(data(await call('close', { case_id: config.case_id })).status, 'closed');
    console.log(JSON.stringify({ status: 'closed', operation_id: receipt.action.id }));
  } else if (config.stage === 'pending') {
    const context = data(await call('get_context', { case_id: config.case_id }));
    assert.equal(context.case.source.key, 'IT-1');
    assert.equal(context.case.status, 'open');
    assert.equal(context.case.action, null);
    console.log(JSON.stringify({ status: 'passed' }));
  } else if (config.stage === 'create') {
    const state = data(await call('create_synthetic', { text: config.incident ? 'demo-api unavailable' : 'Grant reports read access' }));
    const args = { case_id: state.case_id, expected_version: 1 };
    const prepared = data(await call('propose_update', args));
    assert.equal((await call('apply_approved_update', args)).isError, true);
    // Test supervisor uses the separate human-approval API, never the MCP process.
    const approved = await fetch(`${config.origin}/v1/approvals`, { method: 'POST',
      headers: { Authorization: `Bearer ${config.supervisor}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...args, payload_hash: prepared.proposal.payload_hash }) });
    assert.equal(approved.status, 200);
    const receipt = data(await call('apply_approved_update', args));
    assert.equal(receipt.action.status, 'accepted');
    if (config.incident) {
      for (let i = 0; i < 3; i++) {
        if (i) await new Promise(resolve => setTimeout(resolve, 10100));
        assert.equal(data(await call('verify_outcome', { case_id: state.case_id })).evidence.matches, i === 2);
        if (i < 2) assert.equal((await call('close', { case_id: state.case_id })).isError, true);
      }
    } else {
      assert.equal(data(await call('verify_outcome', { case_id: state.case_id })).evidence.matches, true);
    }
    assert.equal(data(await call('close', { case_id: state.case_id })).status, 'closed');
    console.log(JSON.stringify({ case_id: state.case_id, operation_id: receipt.action.id }));
  } else {
    const context = data(await call('get_context', { case_id: config.case_id }));
    assert.equal(context.case.status, 'closed');
    const replay = data(await call('apply_approved_update', { case_id: config.case_id, expected_version: 1 }));
    assert.equal(replay.action.id, config.operation_id);
    if (config.stage === 'reopen') {
      const reopened = data(await call('reopen', { case_id: config.case_id }));
      assert.equal(reopened.status, 'reopened'); assert.equal(reopened.version, 2);
    }
    console.log(JSON.stringify({ status: 'passed' }));
  }
} catch { process.stderr.write('Connected MCP check failed.\n'); process.exitCode = 1; }
finally { await client.close(); }

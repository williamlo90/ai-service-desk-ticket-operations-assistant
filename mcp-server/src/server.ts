import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import type { RequestHandlerExtra } from '@modelcontextprotocol/sdk/shared/protocol.js';
import type { ServerRequest, ServerNotification } from '@modelcontextprotocol/sdk/types.js';
import { Backend } from './backend.js';

if (process.env.SERVICE_DESK_MODE !== 'synthetic' || !process.env.SERVICE_DESK_API_TOKEN || !process.env.SERVICE_DESK_BINDINGS) {
  process.stderr.write('Explicit synthetic mode and identity configuration required.\n');
  process.exit(1);
}
const backend = new Backend();
const server = new McpServer({ name: 'service-desk-local', version: '0.1.0' });
const id = z.string().uuid();
const expected = z.number().int().positive();
const proposal = z.object({ tenant_id: z.string(), case_id: id, case_version: expected,
  payload_hash: z.string().regex(/^[a-f0-9]{64}$/), policy_version: z.string(), requester_id: z.string(),
  payload: z.union([
    z.object({ action: z.literal('grant_read_access'), tenant: z.string(), requester: z.string(), resource: z.literal('reports'), access: z.literal('read-only') }).strict(),
    z.object({ action: z.literal('restart_service'), tenant: z.string(), requester: z.string(), service: z.literal('demo-api') }).strict(),
    z.object({ action: z.literal('link_tickets'), tenant: z.string(), requester: z.string(), source: z.literal('SD-2'), related: z.literal('SD-1') }).strict(),
  ]) }).strict();
const evidence = z.object({ matches: z.boolean(), at: z.string(), reference: z.string() }).strict();
const actionStatus = z.enum(['requested','accepted','running','succeeded','failed','unknown']);
const state = z.object({ case_id: id, tenant: z.string(), version: expected,
  status: z.enum(['open','closed','reopened']), category: z.enum(['access_request','service_incident','repeated_ticket','unsupported']),
  proposal: proposal.nullable(), action: z.object({ id, status: actionStatus, dispatched_at: z.string(),
    sequence: z.number().int().nonnegative(), healthy_checks: z.array(z.string()) }).strict().nullable(),
  verified: evidence.nullable() }).strict();
const outputs = {
  search: z.object({ items: z.array(state).max(20), next_offset: z.number().int().nonnegative().nullable() }).strict(),
  create: state,
  context: z.object({ case: state, context: z.union([
    z.object({ policy: z.string(), action: z.string(), sources: z.array(z.string()), synthetic: z.literal(true) }).strict(),
    z.object({ decision: z.literal('escalate'), sources: z.array(z.string()).max(0) }).strict(),
  ]) }).strict(),
  prepare: z.object({ case_id: id, version: expected, proposal, approval_required: z.literal(true) }).strict(),
  verify: z.object({ case_id: id, status: actionStatus, evidence }).strict(),
  execute: state, close: state, reopen: state,
};
const tools = [
  ['ticket.search', 'search', 'Search authorized local synthetic cases; use next_offset for pagination.',
    z.object({ query: z.string().max(200), offset: z.number().int().nonnegative(), limit: z.number().int().min(1).max(20) }).strict(), true],
  ['ticket.create_synthetic', 'create', 'Create a synthetic case only; never creates a Jira ticket.',
    z.object({ text: z.string().min(1).max(4000) }).strict(), false],
  ['ticket.get_context', 'context', 'Read same-tenant case and scoped SOP references.', z.object({ case_id: id }).strict(), true],
  ['ticket.propose_update', 'prepare', 'Prepare a proposal; separate human supervisor approval is required.',
    z.object({ case_id: id, expected_version: expected }).strict(), false],
  ['ticket.apply_approved_update', 'execute', 'Execute only a stored, current supervisor approval. Replays never resubmit.',
    z.object({ case_id: id, expected_version: expected }).strict(), false],
  ['ticket.verify_outcome', 'verify', 'Read the authoritative synthetic target and record evidence; acknowledgement is not success.',
    z.object({ case_id: id }).strict(), false],
  ['ticket.close', 'close', 'Close only after a fresh verified outcome; linking tickets alone cannot resolve an incident.',
    z.object({ case_id: id }).strict(), false],
  ['ticket.reopen', 'reopen', 'Reopen only after trusted target read-back invalidates a closed result.',
    z.object({ case_id: id }).strict(), false],
] as const;
for (const [name, command, description, inputSchema, readOnly] of tools) {
  server.registerTool(name, { description, inputSchema,
    outputSchema: z.object({ result: outputs[command] }).strict(),
    annotations: { readOnlyHint: readOnly, destructiveHint: false, openWorldHint: false } }, async (args: Record<string, unknown>, extra: RequestHandlerExtra<ServerRequest, ServerNotification>) => {
    try {
      const data = outputs[command].parse(await backend.call(command, args, extra.signal));
      const structuredContent = { result: data };
      const text = JSON.stringify(structuredContent);
      if (Buffer.byteLength(text) > 60000) throw new Error('output_limit');
      return { structuredContent, content: [{ type: 'text' as const, text }] };
    } catch (error) {
      const allowed = new Set(['forbidden','unauthorized','not_found','approval_required','version_conflict',
        'reconciliation_required','expired_approval','stale_approval','outcome_not_verified',
        'adverse_evidence_required','case_not_closed','request_rejected','invalid_arguments',
        'backend_unavailable','cancelled','cancelled_outcome_unknown','timeout_outcome_unknown',
        'input_limit','output_limit','clarification','escalate','action_already_started',
        'relation_does_not_resolve_incident','proposal_required','case_not_open','stale_policy']);
      const code = error instanceof Error && allowed.has(error.message) ? error.message : 'request_rejected';
      return { isError: true, content: [{ type: 'text' as const, text: JSON.stringify({ error: code }) }] };
    }
  });
}
const transport = new StdioServerTransport();
transport.onclose = () => backend.close();
process.on('exit', () => backend.close());
process.on('SIGTERM', () => { backend.close(); process.exit(0); });
process.stdin.on('end', () => { backend.close(); process.exit(0); });
await server.connect(transport);

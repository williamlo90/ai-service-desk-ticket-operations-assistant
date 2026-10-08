const $ = id => document.getElementById(id);
const token = $('token'), caseInput = $('case'), approve = $('approve'), load = $('load'), message = $('message');
let snapshot = null, generation = 0;
const linkedCase = new URLSearchParams(window.location.search).get('case');
if (linkedCase && /^[a-f0-9-]{36}$/.test(linkedCase)) caseInput.value = linkedCase;
function next(title, reason) { $('next-title').textContent = title; $('next-reason').textContent = reason; }
function clearSnapshot() { snapshot = null; approve.disabled = true; }
function invalidate() {
  generation++; clearSnapshot(); $('case-detail').hidden = true; $('empty').hidden = false;
  $('proposal').textContent = ''; $('fields').replaceChildren(); $('status').textContent = 'No case selected';
  message.textContent = ''; next('Load a proposal to continue', 'The action and its current state will appear above.');
}
token.addEventListener('input', invalidate); caseInput.addEventListener('input', invalidate);
window.addEventListener('pagehide', () => { token.value = ''; invalidate(); });
async function request(path, args, credential) {
  const response = await fetch(path, { method: 'POST', redirect: 'error', cache: 'no-store',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${credential}` },
    body: JSON.stringify(args), signal: AbortSignal.timeout(5000) });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Request rejected');
  return data.result;
}
function row(label, value) {
  const dt = document.createElement('dt'), dd = document.createElement('dd');
  dt.textContent = label; dd.textContent = typeof value === 'object' ? JSON.stringify(value) : String(value);
  $('fields').append(dt, dd);
}
function render(result) {
  const c = result.case; $('empty').hidden = true; $('case-detail').hidden = false;
  $('category').textContent = c.category.replaceAll('_', ' ');
  $('case-title').textContent = c.source?.summary || ({access_request:'Review access to a resource',service_incident:'Restore a service',repeated_ticket:'Connect related tickets'}[c.category] || 'Review the request');
  $('case-meta').textContent = `Tenant ${c.tenant} · Version ${c.version} · ${c.case_id}`;
  $('status').textContent = c.status === 'closed' && c.verified ? 'Verified & closed' : c.action ? 'Action ' + c.action.status : c.status === 'open' && c.proposal ? 'Proposal available' : c.status;
  $('fields').replaceChildren();
  if (c.proposal) {
    for (const [key,value] of Object.entries(c.proposal.payload)) row(key.replaceAll('_',' '),value);
    row('Policy', c.proposal.policy_version);
  } else row('Proposal', 'No action has been prepared.');
  row('Verification', c.verified ? 'Target outcome verified' : 'Not yet verified');
  if (c.action) row('Operation status', c.action.status);
  $('proposal').textContent = JSON.stringify({case:c, sources:result.context?.sources || []},null,2);
  if (c.status === 'closed' && c.verified) next('Resolution verified', 'The case is closed. Review the evidence before considering any follow-up.');
  else if (c.action) next('Check the execution outcome', 'An action has already started. Wait for target verification or operator reconciliation; do not submit another action.');
  else if (c.status === 'open' && c.proposal) {
    snapshot = {case_id:c.case_id, expected_version:c.version, payload_hash:c.proposal.payload_hash}; approve.disabled = false;
    next('Review and approve the proposal', 'Check the requested action and policy above. Approval is bound to this exact proposal version.');
  } else next('Prepare the missing information', 'An eligible proposal is required before approval. Return to triage to clarify or prepare the request.');
}
load.addEventListener('click', async () => {
  invalidate(); const current = generation; load.disabled = true; message.textContent = 'Loading case...';
  try {
    const result = await request('/v1/tools/context', {case_id:caseInput.value.trim()}, token.value);
    if (generation !== current) return;
    render(result); message.textContent = 'Case loaded. Review the current evidence.';
  } catch (error) { if (generation === current) message.textContent = 'Unable to load case: ' + error.message; }
  finally { load.disabled = false; }
});
approve.addEventListener('click', async () => {
  if (!snapshot) return;
  const reviewed = snapshot, current = generation, credential = token.value; clearSnapshot(); load.disabled = true;
  message.textContent = 'Recording approval...';
  try {
    await request('/v1/approvals', reviewed, credential);
    if (generation !== current) return;
    $('status').textContent = 'Approval recorded'; next('Wait for execution and verification', 'Approval is recorded. The separate worker can now process the action. Reload to check its outcome.');
    message.textContent = 'Approved. Execution is a separate step.';
  } catch (error) { if (generation === current) message.textContent = `Approval not confirmed. Reload before retrying. ${error.message}`; }
  finally { load.disabled = false; }
});

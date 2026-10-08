const token = document.querySelector('#token');
const caseInput = document.querySelector('#case');
const approve = document.querySelector('#approve');
const load = document.querySelector('#load');
const message = document.querySelector('#message');
const proposal = document.querySelector('#proposal');
let snapshot = null;
const linkedCase = new URLSearchParams(window.location.search).get('case');
if (linkedCase && /^[a-f0-9-]{36}$/.test(linkedCase)) caseInput.value = linkedCase;
function clearSnapshot() { snapshot = null; approve.disabled = true; }
token.addEventListener('input', clearSnapshot);
caseInput.addEventListener('input', clearSnapshot);
window.addEventListener('pagehide', () => { token.value = ''; clearSnapshot(); });
async function request(path, args) {
  const response = await fetch(path, { method: 'POST', redirect: 'error', cache: 'no-store',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token.value}` },
    body: JSON.stringify(args), signal: AbortSignal.timeout(5000) });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Request rejected');
  return data.result;
}
load.addEventListener('click', async () => {
  clearSnapshot(); load.disabled = true; message.textContent = 'Loading…';
  const requestedCase = caseInput.value.trim(); const requestedToken = token.value;
  try {
    const result = await request('/v1/tools/context', { case_id: requestedCase });
    if (caseInput.value.trim() !== requestedCase || token.value !== requestedToken) return;
    const c = result.case;
    if (!c.proposal || c.action || c.status !== 'open') throw new Error('No pending proposal available.');
    snapshot = { case_id: c.case_id, expected_version: c.version, payload_hash: c.proposal.payload_hash };
    proposal.textContent = JSON.stringify({ source: c.source, tenant: c.tenant, version: c.version,
      policy: c.proposal.policy_version, requested_action: c.proposal.payload, sources: result.context.sources }, null, 2);
    approve.disabled = false; message.textContent = 'Review the action above.';
  } catch (error) { message.textContent = error.message; }
  finally { load.disabled = false; }
});
approve.addEventListener('click', async () => {
  if (!snapshot) return;
  const reviewed = snapshot; clearSnapshot(); load.disabled = true;
  try { await request('/v1/approvals', reviewed); message.textContent = 'Approved. Execution is a separate step.'; }
  catch (error) { message.textContent = `Approval not confirmed. Reload before retrying. ${error.message}`; }
  finally { load.disabled = false; }
});

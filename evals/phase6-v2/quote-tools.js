/* A source quote is selected/copied, never silently rewritten from a paraphrase. */
(function () {
  function exactQuote(source, selection) {
    if (typeof source !== 'string' || typeof selection !== 'string') return null;
    const quote = selection.trim();
    return quote.length >= 12 && quote.length <= 1000 && source.includes(quote) ? quote : null;
  }
  function suggestedStep(category, missing) {
    if (category === 'unsupported') return 'route_out_of_scope';
    if (!['access_request','service_incident','repeated_ticket'].includes(category)) return '';
    return missing.length ? 'clarify' : 'prepare_for_approval';
  }
  function recommendation(category, missing) {
    const fields = {requester_identity:'requester identity', resource:'application or resource',
      entitlement:'requested access', service_name:'service name', symptoms:'symptoms or error message',
      source_ticket_id:'source ticket ID', related_ticket_id:'related ticket ID'};
    if (!Array.isArray(missing) || missing.some(code => !Object.hasOwn(fields, code)) ||
        !['access_request','service_incident','repeated_ticket','unsupported'].includes(category)) {
      return {step:'', title:'Review the request manually', reason:'The triage data is not valid enough to recommend a next step.'};
    }
    const step = suggestedStep(category, missing);
    if (step === 'clarify') return {step, title:'Ask for clarification',
      reason:'Still needed: '+missing.map(code => fields[code]).join(', ')+'. Gather this information before preparing an action.'};
    if (step === 'prepare_for_approval') return {step, title:'Prepare for approval',
      reason:'The required triage fields appear complete. Review the evidence and prepare a plan; execution still requires human approval.'};
    return {step, title:'Route to another team',
      reason:'This request appears to be outside the service desk scope. Check the category, then route it to the appropriate team.'};
  }
  const questions = Object.freeze({requester_identity:'Who needs access?', resource:'Which application or resource is involved?', entitlement:'What level of access is requested?', service_name:'Which service is affected?', symptoms:'What symptoms or error messages are present?', source_ticket_id:'What is the source ticket ID?', related_ticket_id:'Which ticket should be linked?'});
  const api = {exactQuote, suggestedStep, recommendation, questions};
  globalThis.QuoteTools = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();

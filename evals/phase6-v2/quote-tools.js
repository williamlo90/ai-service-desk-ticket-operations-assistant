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
    const fields = {requester_identity:'identitas pengguna', resource:'aplikasi atau resource',
      entitlement:'hak akses yang diminta', service_name:'nama layanan', symptoms:'gejala atau pesan error',
      source_ticket_id:'nomor tiket sumber', related_ticket_id:'nomor tiket terkait'};
    if (!Array.isArray(missing) || missing.some(code => !Object.hasOwn(fields, code)) ||
        !['access_request','service_incident','repeated_ticket','unsupported'].includes(category)) {
      return {step:'', title:'Tinjau tiket secara manual', reason:'Data triage belum valid untuk menentukan langkah berikutnya.'};
    }
    const step = suggestedStep(category, missing);
    if (step === 'clarify') return {step, title:'Minta klarifikasi',
      reason:'Masih diperlukan: '+missing.map(code => fields[code]).join(', ')+'. Lengkapi informasi ini sebelum menyiapkan tindakan.'};
    if (step === 'prepare_for_approval') return {step, title:'Siapkan rencana untuk approval',
      reason:'Field triage yang diperlukan sudah lengkap menurut saran ini. Tinjau bukti dan siapkan rencana; pelaksanaan tetap memerlukan approval manusia.'};
    return {step, title:'Arahkan keluar scope',
      reason:'Menurut hasil triage, permintaan ini berada di luar layanan service desk. Periksa kategorinya, lalu arahkan ke tim atau layanan yang sesuai.'};
  }
  const api = {exactQuote, suggestedStep, recommendation};
  globalThis.QuoteTools = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();

import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { HttpBackend } from '../dist/http-backend.js';

test('HTTP adapter refuses non-loopback destinations, credentials in URL and unknown commands', async () => {
  for (const url of ['https://example.org','http://localhost:5679','http://user:secret@127.0.0.1:5679',
    'http://127.0.0.1:5679/foreign','http://127.0.0.1:5679/?override=true'])
    assert.throws(() => new HttpBackend(url,'s'.repeat(40)));
  const backend = new HttpBackend('http://127.0.0.1:5679','s'.repeat(40));
  await assert.rejects(backend.call('approve',{}),/invalid_arguments/);
  backend.close();
  await assert.rejects(backend.call('search',{}),/cancelled/);
});

test('HTTP adapter rejects redirects and limits upstream output', async t => {
  let followups = 0;
  const server = createServer((req,res) => {
    if (req.url === '/v1/tools/search') {
      res.writeHead(302,{Location:'/redirect-target'}); res.end();
    } else if (req.url === '/v1/tools/context') {
      res.writeHead(200,{'Content-Type':'application/json'});
      res.end(JSON.stringify({result:'x'.repeat(60001)}));
    } else { followups++; res.end('{}'); }
  });
  await new Promise(resolve => server.listen(0,'127.0.0.1',resolve));
  t.after(() => new Promise(resolve => { server.closeAllConnections(); server.close(resolve); }));
  const backend = new HttpBackend(`http://127.0.0.1:${server.address().port}`,'s'.repeat(40));
  t.after(() => backend.close());
  await assert.rejects(backend.call('search',{}),/reconciliation_required/);
  assert.equal(followups,0);
  await assert.rejects(backend.call('context',{}),/output_limit/);
});

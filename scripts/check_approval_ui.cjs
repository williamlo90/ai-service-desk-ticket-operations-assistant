// Dependency-free behavioral checks for the real browser controller.
const {readFileSync}=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const {test}=require('node:test');
const source=readFileSync('backend/service_desk/web/approval.js','utf8');
function fixture(){
  const nodes=new Map(),events={},calls=[],pending=[];
  const node=()=>({value:'',textContent:'',hidden:false,disabled:false,children:[],listeners:{},addEventListener(e,f){this.listeners[e]=f;},append(...n){this.children.push(...n);},replaceChildren(){this.children=[];}});
  const get=id=>{if(!nodes.has(id))nodes.set(id,node());return nodes.get(id);};
  vm.runInNewContext(source,{document:{getElementById:get,createElement:node},window:{location:{search:''},addEventListener:(e,f)=>events[e]=f},URLSearchParams,AbortSignal,fetch:(path,options)=>{calls.push({path,options});return new Promise(resolve=>pending.push(result=>resolve({ok:true,json:async()=>({result})})));}});
  get('token').value='fixture';get('case').value='11111111-1111-1111-1111-111111111111';
  return {get,events,calls,pending};
}
const context=(changes={})=>({case:{case_id:'11111111-1111-1111-1111-111111111111',version:1,tenant:'demo',category:'access_request',status:'open',verified:false,proposal:{payload:{resource:'reports'},payload_hash:'a'.repeat(64),policy_version:'v1'},action:null,...changes},context:{sources:[]}});
async function load(f,c=context()){const done=f.get('load').listeners.click();f.pending.shift()(c);await done;}
test('untrusted ticket values render as text, approval binds the reviewed hash',async()=>{const f=fixture();await load(f,context({source:{summary:'<img src=x onerror=alert(1)>'}}));assert.equal(f.get('case-title').textContent,'<img src=x onerror=alert(1)>');const done=f.get('approve').listeners.click();assert.equal(f.calls[1].path,'/v1/approvals');assert.equal(JSON.parse(f.calls[1].options.body).payload_hash,'a'.repeat(64));f.pending.shift()({});await done;assert.equal(f.get('approve').disabled,true);assert.equal(f.calls.length,2);});
test('editing credentials while load is in flight invalidates its result',async()=>{const f=fixture();const done=f.get('load').listeners.click();f.get('token').listeners.input();f.pending.shift()(context());await done;assert.equal(f.get('approve').disabled,true);assert.equal(f.get('case-detail').hidden,true);});
test('changing a case clears review, even when changed back to the same ID',async()=>{const f=fixture();await load(f);f.get('case').listeners.input();assert.equal(f.get('approve').disabled,true);assert.equal(f.get('proposal').textContent,'');});
test('closed verified case is readable but cannot be approved',async()=>{const f=fixture();await load(f,context({status:'closed',verified:true,action:{status:'succeeded'}}));assert.equal(f.get('case-detail').hidden,false);assert.equal(f.get('approve').disabled,true);assert.equal(f.get('next-title').textContent,'Resolution verified');});
test('unknown execution cannot enable another approval',async()=>{const f=fixture();await load(f,context({action:{status:'unknown'}}));assert.equal(f.get('approve').disabled,true);assert.equal(f.get('next-title').textContent,'Check the execution outcome');});
test('page exit erases the token and evidence',async()=>{const f=fixture();await load(f);f.events.pagehide();assert.equal(f.get('token').value,'');assert.equal(f.get('proposal').textContent,'');assert.equal(f.get('approve').disabled,true);});
test('late approval response does not overwrite another case selection',async()=>{const f=fixture();await load(f);const done=f.get('approve').listeners.click();f.get('case').listeners.input();f.pending.shift()({});await done;assert.equal(f.get('status').textContent,'No case selected');assert.equal(f.get('message').textContent,'');});

"""MCP/HTTP/SQL path with real local Keycloak, using explicit fixture approvals."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
from queue import Queue,Empty
from threading import Thread
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import json,secrets,subprocess,sys
from setup_target_sandbox import ROOT,PRIVATE
from connected_checks import ConnectedCheckFailed


def check_lab_connected(database):
    from service_desk.lab_targets import LabTargets
    credentials=json.loads((PRIVATE/'bootstrap.json').read_text())
    folder=ROOT/'local/lab-connected'/secrets.token_hex(6);folder.mkdir(parents=True)
    target=LabTargets(folder/'target.sqlite',credentials['tenants'])
    tokens={tenant:{role:secrets.token_hex(32) for role in ('staff','supervisor')} for tenant in ('alpha','beta')}
    expiry=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
    bindings={value:{'actor_id':'technical-fixture-'+role+'-'+tenant,'tenant_id':tenant,
        'role':'specialist' if role=='staff' else 'supervisor','expires_at':expiry}
        for tenant,roles in tokens.items() for role,value in roles.items()}
    config={'mode':'lab','database':database,'port':0,'bindings':bindings,
        'target_path':str(folder/'target.sqlite'),'lab_tenants':credentials['tenants']}
    process=None;checks=[];cleanup=True
    def require(ok,label):
        if not ok:raise ConnectedCheckFailed('lab_'+label)
    def stop():
        nonlocal process
        if process:
            if process.poll() is None:process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
            process.stdout.close();process=None
    def start():
        nonlocal process
        process=subprocess.Popen([sys.executable,'-B','-m','service_desk.runtime_api'],cwd=ROOT/'backend',
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
        process.stdin.write(json.dumps(config)+'\n');process.stdin.close()
        q=Queue();Thread(target=lambda:q.put(process.stdout.readline()),daemon=True).start()
        try:line=q.get(timeout=20)
        except Empty:raise ConnectedCheckFailed('lab_start_timeout') from None
        return json.loads(line)['origin']
    def mcp(origin,tenant,stage,case=None):
        p=subprocess.run(['node',str(ROOT/'mcp-server/test/connected.mjs')],text=True,capture_output=True,timeout=60,
            input=json.dumps({'mode':'lab','origin':origin,**tokens[tenant],'stage':stage,**(case or {})}))
        require(p.returncode==0,'mcp_'+tenant+'_'+stage)
        require(all(t not in p.stdout+p.stderr for roles in tokens.values() for t in roles.values()),'tokens_redacted')
        return json.loads(p.stdout)
    def member(tenant):
        c=credentials['tenants'][tenant]
        return target.keycloak+'/admin/realms/'+c['realm']+'/users/'+c['user_id']+'/groups',c
    for tenant in tokens:
        url,c=member(tenant)
        require(not any(g['id']==c['group_id'] for g in target.http(url,token=target.token(c))),'initial_membership')
    try:
        origin=start()
        with urlopen(origin+'/healthz',timeout=5) as r:require(json.load(r)['mode']=='lab','mode_label')
        cases={}
        for tenant in tokens:
            cases[tenant]=mcp(origin,tenant,'create')
            url,c=member(tenant)
            require(any(g['id']==c['group_id'] for g in target.http(url,token=target.token(c))),tenant+'_independent_readback')
            other='beta' if tenant=='alpha' else 'alpha'
            req=Request(origin+'/v1/tools/context',data=json.dumps({'case_id':cases[tenant]['case_id']}).encode(),
                headers={'Content-Type':'application/json','Authorization':'Bearer '+tokens[other]['staff']})
            try:urlopen(req,timeout=5)
            except HTTPError as exc:require(exc.code==404,'case_tenant_denial')
            else:raise ConnectedCheckFailed('lab_cross_tenant_case_visible')
        checks.append('two-tenant MCP -> HTTP -> PostgreSQL -> Keycloak membership -> verified closure with fixture supervisor approval')
        stop();origin=start()
        for tenant in tokens:mcp(origin,tenant,'resume',cases[tenant])
        checks.append('API restart and fresh MCP connections preserve operation IDs and closed cases')
        for tenant in tokens:
            url,c=member(tenant);target.http(url+'/'+c['group_id'],'DELETE',token=target.token(c))
            mcp(origin,tenant,'reopen',cases[tenant])
        checks.append('actual Keycloak membership revocation reopens each tenant case without granting access again')
        incidents={};generations={}
        for tenant in tokens:
            c=credentials['tenants'][tenant]
            url=target.demo+'/v1/'+tenant+'/service'
            before=target.http(url,token=c['control_token'])['generation']
            incidents[tenant]=mcp(origin,tenant,'create',{'incident':True})
            generations[tenant]=target.http(url,token=c['control_token'])['generation']
            require(before!=generations[tenant],tenant+'_actual_service_restart')
        checks.append('two-tenant demo child restarts via MCP/API/SQL; closure denied until three healthy observations separated by real ten-second intervals')
        stop();origin=start()
        for tenant in tokens:
            mcp(origin,tenant,'resume',incidents[tenant])
            c=credentials['tenants'][tenant]
            require(target.http(target.demo+'/v1/'+tenant+'/service',token=c['control_token'])['generation']==generations[tenant],tenant+'_no_duplicate_restart')
        checks.append('API restart and incident replay preserve each actual service generation without a second restart')
    finally:
        stop()
        for tenant in tokens:
            try:
                url,c=member(tenant)
                if any(g['id']==c['group_id'] for g in target.http(url,token=target.token(c))):
                    target.http(url+'/'+c['group_id'],'DELETE',token=target.token(c))
                cleanup=cleanup and not any(g['id']==c['group_id'] for g in target.http(url,token=target.token(c)))
            except Exception:cleanup=False
        require(cleanup,'membership_restore')
    report={'status':'passed','checks':checks,'original_membership_restored':cleanup,
        'approvals':'technical fixture identities, not William or a human acceptance session',
        'project_dotenv_read':False,'credentials_printed':False,'jira_calls':0,
        'limitations':['Local access and service restart journeys only; Jira ticket-link full path pending',
            'Temporary runtime and database; no persistent operator deployment or human approval acceptance']}
    (ROOT/'docs/phase-5/lab-connected-check.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

"""Create the user-selected local targets; secrets stay in a private directory.

No project .env access. No existing application containers or workflows changed.
"""
from datetime import datetime,timezone
from pathlib import Path
import json,os,secrets,subprocess,sys,time
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from urllib.parse import urlencode

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=Path.home()/'.codex/private/service-desk-targets'
BASE='http://127.0.0.1:8085'
PYTHON_IMAGE='python@sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9'


def command(args,data=None,timeout=120):
    p=subprocess.run(args,input=data,text=True,capture_output=True,timeout=timeout)
    if p.returncode:raise RuntimeError('sandbox_command_failed')
    return p.stdout


def request(path,method='GET',data=None,token=None,form=False,base=BASE):
    headers={}
    if token:headers['Authorization']='Bearer '+token
    raw=None
    if data is not None:
        raw=urlencode(data).encode() if form else json.dumps(data).encode()
        headers['Content-Type']='application/x-www-form-urlencoded' if form else 'application/json'
    with urlopen(Request(base+path,data=raw,method=method,headers=headers),timeout=15) as response:
        body=response.read(1048576)
        return json.loads(body) if body else None


def main(demo_only=False):
    if not demo_only:
        expected='sha256:43ebe9d4e97c2e5483b7637edf474e6adc1bbf4832a7396686cf90259c396d42'
        actual=command(['docker','image','inspect','quay.io/keycloak/keycloak:26.8.0','--format','{{.Id}}']).strip()
        if actual!=expected:raise RuntimeError('keycloak_image_digest_mismatch')
    PRIVATE.mkdir(parents=True,exist_ok=True)
    if os.name=='nt':
        identity=command(['whoami']).strip()
        command(['icacls',str(PRIVATE),'/inheritance:r','/grant:r',identity+':(OI)(CI)F','/grant:r','SYSTEM:(OI)(CI)F'])
    config_file=PRIVATE/'bootstrap.json'
    if config_file.exists():config=json.loads(config_file.read_text())
    else:
        config={'admin_username':'service-desk-bootstrap','admin_password':secrets.token_urlsafe(36),
            'tenants':{t:{'realm':'sd-lab-'+t,'client_id':'service-desk-worker',
                'client_secret':secrets.token_urlsafe(36),'control_token':secrets.token_urlsafe(36)} for t in ('alpha','beta')}}
        config_file.write_text(json.dumps(config,indent=2)+'\n');config_file.chmod(0o600)
    command(['docker','volume','create','service-desk-targets_secrets'])
    init="""import json,sys,os
from pathlib import Path
c=json.load(sys.stdin)
values={'keycloak_admin':c['admin_password'],**{'control_'+t:v['control_token'] for t,v in c['tenants'].items()}}
for name,value in values.items():
 p=Path('/secrets')/name;p.write_text(value);os.chmod(p,0o600);os.chown(p,1000,1000)
"""
    command(['docker','run','--rm','-i','--user','0:0','-v','service-desk-targets_secrets:/secrets',PYTHON_IMAGE,'python','-c',init],json.dumps(config))
    # The empty explicit env file prevents Compose auto-loading the Jira .env.
    compose=['docker','compose','--env-file',str(ROOT/'deploy/compose.empty.env'),'-f',str(ROOT/'deploy/targets.compose.yaml')]
    command(compose+['up','-d','--build']+(['demo'] if demo_only else []),timeout=180)
    if demo_only:
        for _ in range(30):
            try:
                request('/healthz',base='http://127.0.0.1:8086');break
            except (URLError,TimeoutError,ConnectionError):time.sleep(1)
        for tenant,c in config['tenants'].items():
            assert request('/v1/'+tenant+'/service',token=c['control_token'],base='http://127.0.0.1:8086')['healthy']
        print('Demo target ready for alpha/beta; Keycloak setup still pending. Credentials remain private.',flush=True)
        return
    print('Isolated target containers started; waiting for Keycloak readiness.',flush=True)
    end=time.monotonic()+180
    while True:
        try:
            request('/realms/master/.well-known/openid-configuration');break
        except (URLError,TimeoutError,ConnectionError):
            if time.monotonic()>=end:raise RuntimeError('keycloak_readiness_timeout')
            time.sleep(2)
    token=request('/realms/master/protocol/openid-connect/token','POST',{
        'grant_type':'password','client_id':'admin-cli','username':config['admin_username'],
        'password':config['admin_password']},form=True)['access_token']
    def admin(path,method='GET',data=None):return request('/admin/realms'+path,method,data,token)
    for tenant,c in config['tenants'].items():
        realm=c['realm'];prefix='/'+realm
        try:admin(prefix)
        except HTTPError as exc:
            if exc.code!=404:raise
            admin('','POST',{'realm':realm,'enabled':True,'registrationAllowed':False,
                'resetPasswordAllowed':False,'sslRequired':'none','eventsEnabled':True,
                'adminEventsEnabled':True,'adminEventsDetailsEnabled':False})
        clients=admin(prefix+'/clients?clientId='+c['client_id'])
        if not clients:
            admin(prefix+'/clients','POST',{'clientId':c['client_id'],'enabled':True,
                'protocol':'openid-connect','publicClient':False,'secret':c['client_secret'],
                'serviceAccountsEnabled':True,'standardFlowEnabled':False,'directAccessGrantsEnabled':False})
            clients=admin(prefix+'/clients?clientId='+c['client_id'])
        client=clients[0]['id'];account=admin(prefix+'/clients/'+client+'/service-account-user')['id']
        manager=admin(prefix+'/clients?clientId=realm-management')[0]['id']
        roles=[admin(prefix+'/clients/'+manager+'/roles/'+role) for role in ('manage-users','view-users','query-users')]
        admin(prefix+'/users/'+account+'/role-mappings/clients/'+manager,'POST',roles)
        groups=admin(prefix+'/groups?search=reports-reader&exact=true')
        if not groups:
            admin(prefix+'/groups','POST',{'name':'reports-reader'});groups=admin(prefix+'/groups?search=reports-reader&exact=true')
        username='requester-'+('a' if tenant=='alpha' else 'b')
        users=admin(prefix+'/users?username='+username+'&exact=true')
        if not users:
            admin(prefix+'/users','POST',{'username':username,'enabled':True,'firstName':'Lab',
                'lastName':'Requester','emailVerified':True})
            users=admin(prefix+'/users?username='+username+'&exact=true')
        c.update(user_id=users[0]['id'],group_id=groups[0]['id'],requester=username)
        # Validate each realm-scoped integration identity without changing membership.
        scoped=request('/realms/'+realm+'/protocol/openid-connect/token','POST',{
            'grant_type':'client_credentials','client_id':c['client_id'],'client_secret':c['client_secret']},form=True)['access_token']
        request('/admin/realms/'+realm+'/users/'+c['user_id'],token=scoped)
        print('Configured '+realm+' requester, reports-reader group and scoped service identity.',flush=True)
    # Both realms must exist before a denial proves isolation.
    for tenant,c in config['tenants'].items():
        scoped=request('/realms/'+c['realm']+'/protocol/openid-connect/token','POST',{
            'grant_type':'client_credentials','client_id':c['client_id'],'client_secret':c['client_secret']},form=True)['access_token']
        other='sd-lab-'+('beta' if tenant=='alpha' else 'alpha')
        try:request('/admin/realms/'+other+'/users',token=scoped)
        except HTTPError as exc:
            if exc.code!=403:raise
        else:raise RuntimeError('cross_realm_access_unexpected')
    config_file.write_text(json.dumps(config,indent=2)+'\n');config_file.chmod(0o600)
    request('/healthz',base='http://127.0.0.1:8086')
    for tenant,c in config['tenants'].items():
        assert request('/v1/'+tenant+'/service',token=c['control_token'],base='http://127.0.0.1:8086')['healthy']
    digest=command(['docker','image','inspect','quay.io/keycloak/keycloak:26.8.0','--format','{{.Id}}']).strip()
    report={'checked_at':datetime.now(timezone.utc).isoformat(),'status':'ready_for_acceptance',
        'keycloak_url':'http://localhost:8085','demo_url':'http://localhost:8086','keycloak_image':digest,
        'realms':['sd-lab-alpha','sd-lab-beta'],'scoped_identity_read_checks':2,'cross_realm_denials':2,
        'demo_health_checks':2,'project_dotenv_read':False,'credentials_printed':False,
        'private_credentials_location':str(config_file),'operational_approver':'William',
        'credential_custodian':'William','membership_changes':0,
        'limitations':['Local development-mode Keycloak with persistent H2 volume, not production deployment',
            'Integration identity can manage users in its own lab realm; adapter must enforce exact user/group allowlist',
            'No live Jira write, business approval or end-to-end acceptance performed by setup']}
    (ROOT/'docs/phase-5/target-sandbox-setup.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Sandbox setup verified; credentials saved privately and not displayed.',flush=True)


if __name__=='__main__':
    try:main(demo_only='--demo-only' in sys.argv[1:])
    except Exception as exc:
        # HTTP exceptions may include response context; report only safe category.
        print('Sandbox setup stopped: '+type(exc).__name__+(' HTTP '+str(exc.code) if isinstance(exc,HTTPError) else '')+'. Credentials were not printed.');sys.exit(1)

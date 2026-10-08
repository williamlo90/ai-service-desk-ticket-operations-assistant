"""Rotate lab bearer identities while the operator service is stopped. No .env."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json,secrets,socket,sys
from operator_lab import CONFIG,PRIVATE,ROOT,save


def rotated(config,now):
    if now.tzinfo is None:raise ValueError('aware_clock_required')
    result=deepcopy(config);bindings={}
    for tenant in ('alpha','beta'):
        for role in ('staff','supervisor'):
            old=config['tokens'][tenant][role]
            identity=config['bindings'][old]
            if identity['tenant_id']!=tenant or identity['role']!=('specialist' if role=='staff' else role):
                raise ValueError('binding_mismatch')
            token=secrets.token_hex(32)
            result['tokens'][tenant][role]=token
            bindings[token]={**identity,'expires_at':(now+timedelta(hours=24)).isoformat()}
    if len(config['bindings'])!=4:raise ValueError('unexpected_identity_count')
    result['bindings']=bindings
    return result


def main():
    if sys.argv[1:]!=['--rotate']:raise ValueError('explicit_rotate_required')
    folder=ROOT/'local/operator-lab'
    if not (folder/'stop-service').exists():raise ValueError('stop_operator_service_first')
    status=json.loads((folder/'service-status.json').read_text())
    if (datetime.now(timezone.utc)-datetime.fromisoformat(status['checked_at'])).total_seconds()<15:
        raise ValueError('wait_for_stopped_heartbeat')
    try:
        with socket.create_connection(('127.0.0.1',5681),timeout=1):pass
    except OSError:pass
    else:raise ValueError('api_still_listening')
    updated=rotated(json.loads(CONFIG.read_text()),datetime.now(timezone.utc))
    save(CONFIG,updated)
    for tenant in ('alpha','beta'):
        path=PRIVATE/('william-'+tenant+'-approval-token.txt')
        temp=path.with_suffix('.tmp')
        temp.write_text(updated['tokens'][tenant]['supervisor'],encoding='utf-8');temp.replace(path)
    print('Lab identities rotated for 24 hours. Approval tokens saved privately. Start the operator service and check health.')
    return 0


if __name__=='__main__':
    try:sys.exit(main())
    except Exception as exc:
        allowed={'explicit_rotate_required','stop_operator_service_first','wait_for_stopped_heartbeat','api_still_listening','binding_mismatch','unexpected_identity_count'}
        print('Identity renewal stopped: '+(str(exc) if str(exc) in allowed else type(exc).__name__));sys.exit(1)

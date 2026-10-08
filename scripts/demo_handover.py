"""Offline synthetic demo; never reads credentials or opens business connections."""
from pathlib import Path
import json,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from service_desk.contracts import Actor,Role
from service_desk.journeys import JourneyService,JourneyBlocked
from service_desk.store import MemoryStateStore
from service_desk.durable_target import DurableSyntheticTarget
from service_desk.recovery import RecoveryController
from service_desk.clarification import next_step


def main():
    folder=ROOT/'local/demo';folder.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=folder) as directory:
        assert Path(directory).resolve().is_relative_to(folder.resolve())
        class LostReceipt(DurableSyntheticTarget):
            def submit(self,*args):super().submit(*args);raise TimeoutError()
        target=LostReceipt(Path(directory)/'effects.sqlite')
        service=JourneyService(MemoryStateStore(),target)
        staff=Actor('demo-specialist','alpha',Role.SPECIALIST)
        lead=Actor('demo-fixture-supervisor','alpha',Role.SUPERVISOR)
        case=service.create(staff,'Grant reports read access');key=case['id']
        service.prepare(staff,key,1)
        denied=False
        try:service.execute(staff,key,1)
        except JourneyBlocked:denied=True
        assert denied and len(target.ledger())==0
        service.approve(lead,key,1)
        pending=service.execute(staff,key,1)
        assert pending['status']=='open' and pending['action']['status']=='unknown'
        result=RecoveryController(service).tick(staff,key)
        assert result['reason']=='closed' and len(target.ledger())==1
        service.execute(staff,key,1)
        assert len(target.ledger())==1
        report={'status':'passed','mode':'offline synthetic demo; fixture approval, not William',
                'unapproved_action_blocked':True,'lost_receipt_stays_open_until_verified':True,
                'verified_reconciliation_closed':True,'effects_after_replay':1,
                'missing_service_name_recommendation':next_step('service_incident',['service_name']),
                'credential_reads':0,'external_calls':0}
    if '--report' in sys.argv:
        (ROOT/'docs/phase-8/demo.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()

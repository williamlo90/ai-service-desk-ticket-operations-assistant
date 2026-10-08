"""Executable skills shared by assistant and automation callers."""
from .contracts import require_staff
from .policy import triage,context


class SkillRejected(Exception):pass


class SkillRunner:
    def __init__(self,service):self.service=service

    def run(self,name,actor,arguments,caller='interactive'):
        require_staff(actor,actor.tenant_id)
        if caller not in ('interactive','automation'):raise SkillRejected('invalid_caller')
        fields={'triage_ticket':{'text'},'prepare_resolution':{'case_id','expected_version'},
                'verify_resolution':{'case_id'},'summarize_operations':set()}
        if name not in fields or type(arguments) is not dict or set(arguments)!=fields[name]:
            raise SkillRejected('invalid_arguments')
        if 'case_id' in arguments and (not isinstance(arguments['case_id'],str) or len(arguments['case_id'])!=36):
            raise SkillRejected('invalid_arguments')
        if 'expected_version' in arguments and (type(arguments['expected_version']) is not int or arguments['expected_version']<1):
            raise SkillRejected('invalid_arguments')
        if name=='triage_ticket':
            result=triage(arguments['text'])
            result['sources']=context(actor,actor.tenant_id,result['category']).get('sources',[])
        elif name=='prepare_resolution':
            state=self.service.prepare(actor,arguments['case_id'],arguments['expected_version'])
            result={'case_id':state['id'],'version':state['version'],'proposal':state['proposal'],'approval_required':True}
        elif name=='verify_resolution':
            state=self.service.verify(actor,arguments['case_id'])
            result={'case_id':state['id'],'status':state['action']['status'],'evidence':state['verified']}
        else:result=self.service.summary(actor)
        return {'skill':name,'schema_version':1,'result':result}

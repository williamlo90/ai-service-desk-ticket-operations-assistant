"""Recompute pilot dimensions without changing recorded answers or the rubric."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from business_pilot import ROOT, OUTPUT, tasks


def analyze(observations, reference):
    expected={t['id']:t for t in reference}
    if len(expected)!=len(reference) or len(observations)!=len(reference):
        raise ValueError('incomplete_reference_or_pilot')
    if {r['case_id'] for r in observations}!=set(expected):raise ValueError('case_mismatch')
    rows=[]
    for order,row in enumerate(observations,1):
        task=expected[row['case_id']];answer=row['answer']
        if row['order']!=order or row['condition']!=task['condition'] or row['pair_id']!=task['pair']:
            raise ValueError('identity_mismatch')
        for field in ('active_seconds','interruption_seconds','elapsed_seconds','waiting_seconds'):
            if type(row[field]) not in (int,float) or not 0<=row[field]<86400:
                raise ValueError('invalid_time')
        if abs(row['elapsed_seconds']-row['active_seconds']-row['interruption_seconds'])>.01:
            raise ValueError('inconsistent_time')
        next_step=('route_out_of_scope' if task['expected_category']=='unsupported' else
                   'clarify' if task['expected_missing'] else 'prepare_for_approval')
        checks={'category':answer['category']==task['expected_category'],
                'missing_fields':set(answer['missing'])==set(task['expected_missing']),
                'verbatim_evidence':answer['evidence'] in task['text'],
                'next_step':answer['next_step']==next_step}
        correct=all(checks.values())
        if correct!=row['correct_automatic_rubric']:raise ValueError('stored_grade_mismatch')
        advice=task['advice']
        corrections=(int(answer['category']!=advice['category'])+
                     int(set(answer['missing'])!=set(advice['missing']))) if advice else None
        if corrections!=row['changed_category_or_missing_fields']:raise ValueError('correction_mismatch')
        rows.append({'case_id':row['case_id'],'pair_id':row['pair_id'],'condition':row['condition'],
                     'active_seconds':row['active_seconds'],'checks':checks,'all_correct':correct,
                     'changed_category_or_missing_fields':corrections})
    conditions={}
    for condition in ('manual','assisted'):
        subset=[r for r in rows if r['condition']==condition]
        if not subset:raise ValueError('missing_condition')
        conditions[condition]={'tasks':len(subset),'active_seconds_total':round(sum(r['active_seconds'] for r in subset),3),
             'descriptive_mean_active_seconds':round(mean(r['active_seconds'] for r in subset),3),
             'correct':sum(r['all_correct'] for r in subset),
             'dimensions':{key:sum(r['checks'][key] for r in subset) for key in subset[0]['checks']}}
    eligible=[]
    for pair in sorted({r['pair_id'] for r in rows}):
        members={r['condition']:r for r in rows if r['pair_id']==pair}
        if len(members)!=2:raise ValueError('unpaired_case')
        if all(r['all_correct'] for r in members.values()):
            eligible.append({'pair_id':pair,'manual_active_seconds':members['manual']['active_seconds'],
                             'assisted_active_seconds':members['assisted']['active_seconds']})
    return {'observations':len(rows),'conditions':conditions,'rows':rows,'eligible_correct_pairs':eligible,
            'efficiency_comparison':'not_estimable' if not eligible else 'descriptive_paired_only',
            'roi':None,'recorded_active_seconds_total':round(sum(r['active_seconds'] for r in rows),3),
            'changed_category_or_missing_fields_total':sum(r['changed_category_or_missing_fields'] or 0 for r in rows)}


def main():
    raw=OUTPUT.read_bytes();record=json.loads(raw)
    report={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'status':'pilot_completed',
            'study':record['study'],'participant_count':1,'raw_observations_sha256':hashlib.sha256(raw).hexdigest(),
            'reference_sha256':hashlib.sha256(json.dumps(tasks(),sort_keys=True).encode()).hexdigest(),
            'analysis':analyze(record['observations'],tasks()),'limitations':record['limitations'],
            'review_type':'mechanical rubric recomputation plus implementation-agent interpretation; not independent human sign-off'}
    (ROOT/'docs/phase-6/business-pilot-results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report['analysis'].items() if k!='rows'}))


if __name__=='__main__':main()

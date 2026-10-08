"""Pure, denominator-preserving scoring for synthetic advisory extraction."""
import hashlib
import json
import math
from .ai import Source, validate, AIError


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
                                    separators=(',', ':')).encode()).hexdigest()


def score(case, result):
    """Failures remain in every case-level denominator. No LLM-as-judge."""
    checks = dict(schema=False, category=False, ticket_evidence=False,
                  required_clarification=False)
    if 'expected_missing' in case:
        checks['clarification_slots']=False
    if result is None:
        return checks
    sources = [Source('ticket', case['tenant'], case['text'])]
    try:
        data = validate(result['data'], sources)
    except (AIError, KeyError, TypeError):
        return checks
    checks['schema'] = True
    checks['category'] = data['category'] == case['expected_category']
    # Non-vacuous evidence: a quote must overlap a pre-labelled relevant span.
    checks['ticket_evidence'] = any(
        len(fact['quote']) >= 12 and any(
            span in fact['quote'] or fact['quote'] in span
            for span in case['evidence_spans']) for fact in data['facts'])
    # This checks clarification presence only; semantic adequacy needs human review.
    checks['required_clarification'] = not case['needs_clarification'] or bool(data['missing'])
    if 'expected_missing' in case:
        checks['clarification_slots']=set(data['missing'])==set(case['expected_missing'])
    return checks


def summarize(cases, rows):
    if not cases or len({c['id'] for c in cases}) != len(cases):
        raise ValueError('invalid_dataset')
    by_id = {row['id']: row for row in rows}
    if len(by_id) != len(rows) or not set(by_id).issubset({c['id'] for c in cases}):
        raise ValueError('invalid_rows')
    metrics = {name: {'passed': 0, 'total': len(cases)} for name in
               ('schema', 'category', 'ticket_evidence', 'required_clarification', 'all_checks')}
    if any('expected_missing' in case for case in cases):
        if not all('expected_missing' in case for case in cases):raise ValueError('mixed_rubric')
        metrics['clarification_slots']={'passed':0,'total':len(cases)}
    timings = []
    for case in cases:
        row = by_id.get(case['id'], {})
        checks = score(case, row.get('result'))
        checks['all_checks'] = all(checks.values())
        for name, passed in checks.items():
            metrics[name]['passed'] += int(passed)
        if row.get('result'):
            timings.append(row['result']['elapsed_ms'])
    for metric in metrics.values():
        metric['rate'] = metric['passed'] / metric['total']
    timings.sort()
    return {'metrics': metrics, 'attempted': len(rows), 'unattempted': len(cases)-len(rows),
            'successful_response_latency_ms': {
                'samples': len(timings),
                'p50': timings[math.ceil(.5*len(timings))-1] if timings else None,
                'p95': timings[math.ceil(.95*len(timings))-1] if timings else None},
            'quality_gate': (metrics['schema']['rate'] == 1
                             and metrics['category']['rate'] >= .9
                             and metrics['ticket_evidence']['rate'] >= .9
                             and metrics['required_clarification']['rate'] == 1
                             and metrics.get('clarification_slots',{'rate':1})['rate'] >= .9)}

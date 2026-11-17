"""Audit the actual authored course against its declared release requirements."""
import csv
from collections import Counter
import json
from pathlib import Path
import re
import jsonschema
from runner.api.content import Content
from runner.api.models import CheckResult, Question, Validator, LessonMetadata, ChallengeContract
from runner.regions import SUPPORTED_REGIONS

ROOT=Path(__file__).resolve().parents[1]
content=Content(ROOT)
domains=content.domains()
assert len(domains)==8,'Eight complete domains are required'
assert sum(len(d['exercises']) for d in domains)==11
assert sum(len(d['checkpoints']) for d in domains)==24
bank=content.questions()
assert len(bank)==120
allocation=Counter(q.domain_id for q in bank.values())
assert [allocation[f'{n:02}'] for n in range(1,9)]==[8,12,18,30,12,14,10,16]
coverage=Counter(objective for q in bank.values() for objective in q.objectives)
expected={f'{d}{chr(97+i)}' for d,count in enumerate([3,4,7,8,4,4,3,4],1) for i in range(count)}
assert set(coverage)==expected and min(coverage.values())>=2
rows=list(csv.DictReader((ROOT/'objective-coverage.csv').open()))
assert len(rows)==37 and {row['objective_id'] for row in rows}==expected
for row in rows:
    name,anchor=row['lesson_anchor'].split('#')
    assert f'id="{anchor}"' in (ROOT/name).read_text(),row['objective_id']
    domain_id=row['objective_id'][0].zfill(2)
    checkpoints=content.checkpoints(domain_id)
    assert row['checkpoint_ids'] and row['bank_question_ids']
    for qid in row['checkpoint_ids'].split(';'):
        assert row['objective_id'] in checkpoints[qid].objectives
    for qid in row['bank_question_ids'].split(';'):
        assert row['objective_id'] in bank[qid].objectives
    assert (ROOT/row['lab_validator']).is_file()
prompts=[]
checkpoint_objectives=set()
for domain in domains:
    directory=content.directory(domain['id'])
    lesson=(directory/'lesson.mdx').read_text()
    assert '2023 vs 2026' in lesson and '3-Year Catch-Up' in lesson
    assert len(lesson.split())>=400,domain['id']
    validator=content.validator(domain['id'])
    assert validator.domain_id==domain['id']
    for variant in ['starter','solution']:
        assert (directory/variant/'main.tf').is_file()
        assert (directory/variant/'.terraform.lock.hcl').is_file()
    assert len(domain['checkpoints'])==3
    for question in content.checkpoints(domain['id']).values():
        prompts.append(question.prompt)
        checkpoint_objectives.update(question.objectives)
    assert domain['cost']['target_usd']>0 and domain['cost']['free_tier_guaranteed'] is False
    assert set(domain['cost']['regions'])==({'us-east-1','eu-west-2'} if domain['id']=='02' else set(SUPPORTED_REGIONS))
    assert (directory/'challenge.md').stat().st_size>500
prompts += [q.prompt for q in bank.values()]
assert len(prompts)==len(set(prompts))==144,'Checkpoint and bank prompts must be independently authored'
assert checkpoint_objectives==expected,'All objectives need checkpoint coverage'
mock=json.loads((ROOT/'exam-bank/mock-blueprint.json').read_text())
a,b=mock['sets']['A'],mock['sets']['B']
assert len(a)==len(b)==57 and not set(a)&set(b)
assert set(a+b)<=set(bank)
assert {objective for qid in a for objective in bank[qid].objectives}==expected
assert {objective for qid in b for objective in bank[qid].objectives}==expected
assert mock['duration_seconds']==3600
for name,model in [('validator',Validator),('question',Question),('result',CheckResult),('lesson',LessonMetadata),('challenge',ChallengeContract)]:
    stored=json.loads((ROOT/f'schemas/{name}.schema.json').read_text())
    assert stored==model.model_json_schema(),f'Regenerate stale schema {name}'
    jsonschema.Draft202012Validator.check_schema(stored)
    if name=='validator':
        for domain in domains:
            jsonschema.validate(content.validator(domain['id']).model_dump(),stored)
    if name in {'lesson','challenge'}:
        for domain in domains:
            filename='domain.json' if name=='lesson' else 'challenge.json'
            jsonschema.validate(json.loads((content.directory(domain['id'])/filename).read_text()),stored)
assert not any((content.directory('08')/variant/'cloud.tf').exists() for variant in ['starter','solution'])
supplement=ROOT/'curriculum/troubleshooting'
assert (supplement/'lesson.mdx').is_file() and (supplement/'workshop.mdx').is_file()
cases=json.loads((supplement/'scenarios.json').read_text())
assert len(cases)==7 and len({case['id'] for case in cases})==7
for case in cases:
    assert len(case['questions'])==3 and case['brief'] and case['diagnostic']
    for question in case['questions']:
        assert len(question['options'])>=3
        assert question['correct'] in {option['id'] for option in question['options']}
        assert all(option['label'] and option['reason'] for option in question['options'])
for variant in ['repository','solution']:
    assert (supplement/variant/'main.tf').is_file() and (supplement/variant/'modules/service/main.tf').is_file()
print('PASS: eight domains, 11 exercises, 24 checkpoints, 120 questions, all 37 objectives, current schemas, no HCP dependency, and the debugging supplement with seven diagnostic cases.')

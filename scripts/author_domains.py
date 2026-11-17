import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOMAINS = [{
    "id":"01", "title":"Infrastructure as code", "subtitle":"Think in desired state, not imperative steps.",
    "minutes":65, "lab_minutes":25, "objectives":["1a","1b","1c"],
    "lab_id":"lab-01-iac-baseline", "difficulty":"Refresh", "icon":"layers",
    "delta":{"before":"Create a bucket, enable versioning, then add metadata with separate CLI commands.",
             "after":"Declare the resources, review their dependency graph, apply a saved plan, and prove convergence."},
    "exercises":[
        {"id":"architecture-triage","title":"Architecture Triage","description":"Separate provider topology from application tiers.",
         "cases":[
            {"prompt":"AWS compute and Google Cloud storage in one configuration","choices":["Multi-cloud","Multi-tier","Single-provider alias"],"correct":"Multi-cloud","explanation":"Two cloud providers make this multi-cloud; tiers are not specified."},
            {"prompt":"A web tier and database tier, both in AWS","choices":["Multi-cloud","Multi-tier","Hybrid"],"correct":"Multi-tier","explanation":"Application tiers do not imply multiple clouds."},
            {"prompt":"A private virtualization cluster and AWS networking","choices":["Single-region","Hybrid","Only SaaS"],"correct":"Hybrid","explanation":"Private and public environments form a hybrid topology."}]},
        {"id":"idempotency-simulator","title":"Idempotency Simulator","description":"Predict the next refreshed plan.",
         "cases":[
            {"prompt":"State and AWS match the bucket configuration after apply.","choices":["No changes","+ create","-/+ replace"],"correct":"No changes","explanation":"The system already matches desired state."},
            {"prompt":"Versioning was disabled in the console; HCL still requests Enabled.","choices":["No changes","~ update versioning","Delete the HCL"],"correct":"~ update versioning","explanation":"A normal plan proposes restoring the declared setting."},
            {"prompt":"A tracked SSM parameter was deleted outside Terraform.","choices":["+ create","No changes","Edit configuration automatically"],"correct":"+ create","explanation":"The declaration still requests an object that is now absent."}]}],
    "checkpoint_bank_ids":["d01-001","d01-004","d01-006"],
    "expected_starter_failures":["declarative_versioning","bucket_versioning","exact_metadata"],
    "resource_types":["aws_s3_bucket","aws_s3_bucket_versioning","aws_ssm_parameter"],
    "cost":{"target_usd":0.01,"currency":"USD","regions":["eu-west-1","us-east-1","eu-west-2"],"pricing_date":"2026-11-14","assumptions":"Short session; no object uploads; standard SSM only; gross usage before credits.","free_tier_guaranteed":False}
}]


def write():
    from domain_catalog import DOMAINS, CHECKPOINTS
    for domain in DOMAINS:
        metadata=copy.deepcopy(domain)
        metadata['checkpoints']=[]
        metadata.pop('checkpoint_bank_ids',None)
        for index,(objective,prompt,answers,correct) in enumerate(CHECKPOINTS[int(domain['id'])],1):
            question={'id':f"cp{domain['id']}-{index}",'domain_id':domain['id'],'objectives':objective if isinstance(objective,list) else [objective],
                'type':'boolean' if [a[0] for a in answers]==['True','False'] else 'single','prompt':prompt,
                'choices':{letter:pair[0] for letter,pair in zip('abcdef',answers)},
                'rationale':{letter:pair[1] for letter,pair in zip('abcdef',answers)},'correct':[correct],
                'difficulty':'application','source_url':'https://developer.hashicorp.com/terraform/tutorials/certification-004/associate-review-004',
                'terraform_version':'1.12.2','reviewed':'2026-11-14'}
            metadata['checkpoints'].append(question)
        destination=ROOT/'curriculum'/f"domain-{domain['id']}"
        destination.mkdir(exist_ok=True,parents=True)
        (destination/'domain.json').write_text(json.dumps(metadata,indent=2)+'\n')
        challenge={'schema_version':1,'domain_id':metadata['id'],'lab_id':metadata['lab_id'],'estimated_minutes':metadata['lab_minutes'],
            'prerequisites':['Terraform 1.12.2','Verified AWS profile or access-key connection'],
            'resource_types':metadata['resource_types'],'cost':metadata['cost'],'instructions_file':'challenge.md',
            'teardown_gate':'state_and_owned_inventory_and_prior_apply_validation'}
        (destination/'challenge.json').write_text(json.dumps(challenge,indent=2)+'\n')


if __name__=='__main__':
    write()

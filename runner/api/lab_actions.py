from datetime import datetime, timezone
import json
import subprocess
import uuid
from .terraform import state_resources, terraform_json


def lab_action(operation, attempt, directory, jobs):
    if operation == "setup-import":
        if attempt["domain_id"] != "07":
            raise ValueError("Import fixtures belong to domain 07")
        return setup_import(attempt, jobs)
    env = jobs.credentials.environment(attempt["account"])
    state = jobs.validator.state(directory, env)
    jobs.inventory.capture(attempt, state)
    from .resources import PRIMARY
    expected={r['values']['id'] for r in state_resources(state) if r.get('mode')=='managed' and r['type'] in PRIMARY}
    jobs.inventory.verify_owned(attempt,expected)
    if operation == "capture-baseline":
        if attempt["baseline"] != "{}":
            return {"baseline": json.loads(attempt["baseline"]), "message":"The original baseline is already saved"}
        baseline = {resource["address"]: resource["values"]["id"] for resource in state_resources(state) if resource.get("mode") == "managed" and resource["type"] in {"aws_security_group","aws_ssm_parameter","aws_s3_bucket","aws_iam_policy"}}
        if not baseline:
            raise ValueError("No resource IDs are available to capture")
        jobs.db.execute("UPDATE attempts SET baseline=? WHERE id=?", (json.dumps(baseline),attempt["id"]))
        return {"baseline":baseline}
    if operation == "simulate-drift":
        if attempt["domain_id"] == "03":
            resource = next((r for r in jobs.inventory.rows(attempt["id"]) if r["address"] == "aws_security_group.app"), None)
            if not resource:
                raise ValueError("Create the lab security group before simulating drift")
            ec2=jobs.credentials.client('ec2',attempt['region'])
            permissions=ec2.describe_security_groups(GroupIds=[resource['resource_id']])['SecurityGroups'][0].get('IpPermissions',[])
            present=any(rule.get('IpProtocol')=='tcp' and rule.get('FromPort')==8443 and rule.get('ToPort')==8443 and any(ip.get('CidrIp')=='10.43.0.0/16' for ip in rule.get('IpRanges',[])) for rule in permissions)
            if not present:
                ec2.authorize_security_group_ingress(GroupId=resource['resource_id'],IpPermissions=[{
                    'IpProtocol':'tcp','FromPort':8443,'ToPort':8443,
                    'IpRanges':[{'CidrIp':'10.43.0.0/16','Description':'Controlled tfprep drift'}]}])
            return {'changed':'Private TCP 8443 ingress rule on the owned security group','rule_already_present':present}
        if attempt["domain_id"] == "06":
            resource = next((r for r in jobs.inventory.rows(attempt["id"]) if r["address"] in {"aws_ssm_parameter.legacy","aws_ssm_parameter.metadata"}), None)
            if not resource:
                raise ValueError("Create the lab parameter before simulating drift")
            client = jobs.credentials.client("ssm",attempt["region"])
            client.put_parameter(Name=resource["resource_id"],Value="out-of-band",Type="String",Overwrite=True)
            client.add_tags_to_resource(ResourceType="Parameter",ResourceId=resource["resource_id"],Tags=[{"Key":"Stage","Value":"drift"}])
            return {"changed":"Value and Stage tag on the owned parameter"}
        raise ValueError("Drift simulation is available only for domains 03 and 06")
    if operation == "reconcile-locks":
        if attempt["domain_id"] != "06":
            raise ValueError("Native S3 lock testing belongs to domain 06")
        return verify_lock_contention(attempt,directory,jobs,env)
    raise ValueError("Unknown lab action")


def setup_import(attempt,jobs):
    expected_tags={"Project":"tf-004-prep","ManagedBy":"terraform","Learner":"local","Lab":"07","Attempt":attempt["id"]}
    tag_list=[{"Key":key,"Value":value} for key,value in expected_tags.items()]
    bucket=f"tf004-{attempt['account']}-{attempt['id']}-import"
    policy_name=f"tf004-{attempt['id']}-import"
    policy_arn=f"arn:aws:iam::{attempt['account']}:policy/{policy_name}"
    # A previous setup may have stopped after creating only one fixture. Discover
    # fully tagged objects first, then create only the missing, exact identities.
    jobs.inventory.reconcile(attempt)
    existing=set()
    for row in jobs.inventory.rows(attempt['id']):
        observed=jobs.inventory.inspect(row)
        if observed['exists']:
            if any(observed['tags'].get(key)!=value for key,value in expected_tags.items()):
                raise ValueError('Existing import fixture ownership does not match; inspect recovery inventory')
            existing.add(row['resource_id'])
    if bucket not in existing:
        s3=jobs.credentials.client("s3",attempt["region"])
        parameters={"Bucket":bucket}
        if attempt["region"] != "us-east-1":
            parameters["CreateBucketConfiguration"]={"LocationConstraint":attempt["region"]}
        s3.create_bucket(**parameters)
        jobs.inventory.register(attempt,"aws_s3_bucket.imported","aws_s3_bucket",bucket,attempt["region"],f"arn:aws:s3:::{bucket}",expected_tags)
        s3.put_bucket_tagging(Bucket=bucket,Tagging={"TagSet":tag_list})
    if policy_arn not in existing:
        policy={"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["s3:GetBucketLocation"],"Resource":f"arn:aws:s3:::{bucket}"}]}
        jobs.credentials.client("iam","us-east-1").create_policy(PolicyName=policy_name,Description="Disposable Terraform import exercise",PolicyDocument=json.dumps(policy),Tags=tag_list)
        jobs.inventory.register(attempt,"aws_iam_policy.imported","aws_iam_policy",policy_arn,"global",policy_arn,expected_tags)
    jobs.inventory.verify_owned(attempt)
    baseline={"aws_s3_bucket.imported":bucket,"aws_iam_policy.imported":policy_arn}
    jobs.db.execute("UPDATE attempts SET baseline=? WHERE id=?",(json.dumps(baseline),attempt["id"]))
    return {"bucket_name":bucket,"policy_arn":policy_arn,"baseline":baseline}


def migrate_backend(operation,attempt,directory,jobs):
    if attempt["domain_id"] != "06":
        raise ValueError("Backend migration belongs to domain 06")
    managed=directory/'course-backend.tf'
    marker='# Managed by tfprep backend exercise\n'
    if managed.exists() and not managed.read_text().startswith(marker):
        raise ValueError("course-backend.tf already contains learner-owned content; rename it before continuing")
    if operation == 'migrate-remote':
        bootstrap=directory/'bootstrap'
        state=jobs.validator.state(bootstrap,jobs.credentials.environment(attempt['account']))
        bucket=state.get('values',{}).get('outputs',{}).get('bucket_name',{}).get('value')
        expected=f"tf004-{attempt['account']}-{attempt['id']}-state"
        if bucket != expected:
            raise ValueError("The owned bootstrap bucket is not ready")
        managed.write_text(marker+'terraform {\n  backend "s3" {\n    use_lockfile = true\n    encrypt = true\n  }\n}\n')
        config=directory/'course-backend.hcl'
        config.write_text(f'bucket = "{bucket}"\nkey = "tfprep/{attempt["id"]}/terraform.tfstate"\nregion = "{attempt["region"]}"\n')
        return directory,['init','-input=false','-migrate-state','-force-copy','-lockfile=readonly','-backend-config=course-backend.hcl']
    state=jobs.validator.state(directory,jobs.credentials.environment(attempt['account']))
    if any(r.get('mode')=='managed' for r in state_resources(state)):
        raise ValueError("Destroy the workload before migrating its empty state back to local")
    snapshot=terraform_json(jobs.settings,directory,['state','pull'],jobs.credentials.environment(attempt['account']))
    jobs.empty_migrations[attempt['id']]=snapshot
    managed.write_text(marker+'terraform {\n  backend "local" {}\n}\n')
    return directory,['init','-input=false','-migrate-state','-force-copy','-lockfile=readonly']


def verify_lock_contention(attempt,directory,jobs,env):
    metadata=directory/'.terraform/terraform.tfstate'
    backend=json.loads(metadata.read_text()).get('backend',{})
    config=backend.get('config',{})
    if backend.get('type')!='s3' or config.get('use_lockfile') is not True or config.get('encrypt') is not True:
        raise ValueError("Migrate to an encrypted S3 backend with use_lockfile=true first")
    bucket,key=config['bucket'],config['key']
    expected_bucket=f"tf004-{attempt['account']}-{attempt['id']}-state"
    if bucket!=expected_bucket or key!=f"tfprep/{attempt['id']}/terraform.tfstate":
        raise ValueError("Backend identity does not match the owned lab bootstrap")
    s3=jobs.credentials.client('s3',attempt['region'])
    s3.head_object(Bucket=bucket,Key=key)
    lock_id=str(uuid.uuid4())
    lock={'ID':lock_id,'Operation':'OperationTypePlan','Info':'Controlled tfprep contention probe','Who':'tfprep','Version':'1.12.2','Created':datetime.now(timezone.utc).isoformat(),'Path':bucket+'/'+key}
    lock_key=key+'.tflock'
    created=s3.put_object(Bucket=bucket,Key=lock_key,Body=json.dumps(lock).encode(),IfNoneMatch='*',ContentType='application/json')
    try:
        result=subprocess.run([jobs.settings.terraform,'plan','-input=false','-no-color','-lock-timeout=1s'],cwd=directory,env=env,capture_output=True,text=True,timeout=30)
        combined=result.stdout+result.stderr
        if result.returncode!=1 or 'Error acquiring the state lock' not in combined or lock_id not in combined:
            raise ValueError("Terraform did not report contention against the controlled S3 lock")
    finally:
        current=s3.get_object(Bucket=bucket,Key=lock_key)
        if json.loads(current['Body'].read()).get('ID')==lock_id:
            s3.delete_object(Bucket=bucket,Key=lock_key,IfMatch=current['ETag'])
    return {'backend':'s3','lockfile':lock_key,'terraform_contention_observed':True,'owned_probe_lock_released':True,'state_object_exists':True}

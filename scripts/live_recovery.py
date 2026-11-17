"""Exercise cleanup failures on exact owned attempts; requires the native runner.

The additional AWS objects are two disposable domain-01 stacks and one domain-07
fixture pair. No other account resources are selected or changed.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

import boto3

from live_course import LiveCourse,ROOT
from runner.api.config import Settings


def interrupt(course,operation,signal_text):
    aid=course.attempt['id']
    job=course.request('POST',f'/attempts/{aid}/run',{'operation':operation})
    canceled=False
    deadline=time.monotonic()+180
    while job['status'] in {'queued','running'}:
        if not canceled and signal_text in job['log']:
            course.request('POST','/jobs/'+job['id']+'/cancel');canceled=True
        if time.monotonic()>deadline:
            course.request('POST','/jobs/'+job['id']+'/cancel')
            raise RuntimeError('Recovery interruption observation exceeded its deadline')
        time.sleep(.04)
        job=course.request('GET','/jobs/'+job['id'])
    assert canceled and job['status']=='canceled',f'{operation} finished before the interruption was observed; recovery proof is incomplete'
    return {'operation':operation,'status':job['status'],'cloud_operation_observed':True,'job_id':job['id']}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--profile',required=True)
    parser.add_argument('--url',default='http://127.0.0.1:8080')
    args=parser.parse_args()
    session=boto3.Session(profile_name=args.profile,region_name='us-east-1')
    s3=session.client('s3')
    courses=[]
    report={'account':session.client('sts').get_caller_identity()['Account'],'checks':{},'attempts':[]}
    def new(domain):
        course=LiveCourse(args.profile,'us-east-1',args.url)
        assert course.identity['account']==report['account']
        course.attempt=course.request('POST','/attempts',{'domain_id':domain})
        courses.append(course);report['attempts'].append(course.attempt['id'])
        return course
    def detail(course):return course.request('GET','/attempts/'+course.attempt['id'])
    try:
        control=new('01');control.reference('01');control.workflow();control.job('plan');control.job(endpoint='validate')
        control_ids={r['resource_id'] for r in detail(control)['resources']}
        target=new('01');target.reference('01')
        for op in ['init','fmt','validate','plan']:target.job(op)
        report['checks']['interrupted_apply']=interrupt(target,'apply','Creation complete')
        target.job(endpoint='reaper?execute=true')
        target.job('destroy')
        # Reapply the same attempt to test cleanup after a fully graded deployment.
        target.job('plan');target.job('apply');target.job('plan');target.job(endpoint='validate')
        bucket=next(r['resource_id'] for r in detail(target)['resources'] if r['type']=='aws_s3_bucket')
        tags=s3.get_bucket_tagging(Bucket=bucket)['TagSet']
        assert {t['Key']:t['Value'] for t in tags}['Attempt']==target.attempt['id']
        for value in [b'first disposable version',b'second disposable version']:
            s3.put_object(Bucket=bucket,Key='cleanup-proof.txt',Body=value)
        s3.delete_object(Bucket=bucket,Key='cleanup-proof.txt')
        versions=s3.list_object_versions(Bucket=bucket)
        assert len(versions.get('Versions',[]))==2 and versions.get('DeleteMarkers')
        s3.put_bucket_tagging(Bucket=bucket,Tagging={'TagSet':[t for t in tags if t['Key']!='Project']})
        directory=Path(target.attempt['workspace'])
        expected=Settings.load().workspaces/f"01-{target.attempt['id']}"
        if directory.resolve()!=expected.resolve():raise RuntimeError('State surgery requires this native runner workspace')
        frozen=session.get_credentials().get_frozen_credentials()
        env={key:value for key,value in os.environ.items() if key in {'PATH','HOME','LANG','TMPDIR','SSL_CERT_FILE','SSL_CERT_DIR'}}
        env.update(AWS_ACCESS_KEY_ID=frozen.access_key,AWS_SECRET_ACCESS_KEY=frozen.secret_key,AWS_SESSION_TOKEN=frozen.token or '',AWS_REGION='us-east-1',AWS_EC2_METADATA_DISABLED='true')
        removed=subprocess.run([Settings.load().terraform,'state','rm','aws_s3_bucket.course','aws_s3_bucket_versioning.course'],cwd=directory,env=env,capture_output=True,text=True,timeout=60)
        if removed.returncode:raise RuntimeError('Disposable state association removal failed')
        preview=target.job(endpoint='reaper')['result']
        assert not preview['executed'] and s3.head_bucket(Bucket=bucket)
        target.job('destroy')
        incomplete=target.job(endpoint='teardown-check',expect_success=False)
        assert not incomplete['result']['complete'] and incomplete['result']['remaining_cloud']
        target.job(endpoint='reaper?execute=true')
        assert target.job(endpoint='teardown-check')['result']['complete']
        report['checks'].update(missing_tag_recovered_from_verified_inventory=True,state_rm_did_not_award_false_completion=True,s3_versions_and_delete_markers_removed=True,reaper_defaults_to_dry_run=True)
        for row in detail(control)['resources']:
            if row['type']=='aws_s3_bucket':s3.head_bucket(Bucket=row['resource_id'])
            if row['type']=='aws_ssm_parameter':session.client('ssm').get_parameter(Name=row['resource_id'])
        assert {r['resource_id'] for r in detail(control)['resources']}==control_ids
        report['checks']['other_attempt_survived_unchanged']=True
        report['checks']['interrupted_destroy']=interrupt(control,'destroy','Destroying...')
        control.job('destroy');assert control.job(endpoint='teardown-check')['result']['complete']
        imports=new('07');imports.job('setup-import')
        assert len(detail(imports)['resources'])==2
        imports.job(endpoint='reaper?execute=true')
        assert all(row['status']=='absent' for row in detail(imports)['resources'])
        report['checks']['unimported_setup_objects_recovered']=True
        report['passed']=True
    finally:
        # Finish all owned attempts even if an interruption assertion raced completion.
        cleanup=[]
        for course in courses:
            if detail(course)['status']=='complete':continue
            try:
                course.job('destroy',expect_success=False)
                recovered=course.job(endpoint='reaper?execute=true')
                cleanup.append({'attempt':course.attempt['id'],'remaining':recovered['result']['remaining']})
            except Exception as exc:cleanup.append({'attempt':course.attempt['id'],'attention_required':str(exc)})
        report['failure_cleanup']=cleanup
        output=ROOT/'docs/evidence/live-recovery.json'
        output.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()

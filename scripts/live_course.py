"""Live release checks; only the explicitly supplied profile/account is used."""
import argparse
import json
from pathlib import Path
import time
import httpx

ROOT=Path(__file__).resolve().parents[1]


class LiveCourse:
    def __init__(self,profile,region,url,credential_method='profile'):
        self.client=httpx.Client(base_url=url.rstrip('/')+'/api',headers={'X-Tfprep':'1'},timeout=45)
        payload={'mode':'profile','profile':profile,'region':region}
        if credential_method=='keys':
            import boto3
            frozen=boto3.Session(profile_name=profile).get_credentials().get_frozen_credentials()
            payload={'mode':'keys','region':region,'access_key_id':frozen.access_key,'secret_access_key':frozen.secret_key}
            if frozen.token:payload['session_token']=frozen.token
        self.identity=self.request('POST','/connection',payload)
        payload.clear()
        self.region=region
        self.evidence={'account':self.identity['account'],'region':region,'connection_method':credential_method,'terraform':'1.12.2','aws_provider':'5.92.0','jobs':[],'started':time.time()}
        self.attempt=None

    def request(self,method,path,data=None):
        response=self.client.request(method,path,json=data)
        if response.status_code>=400:
            raise RuntimeError(f'{path}: {response.text}')
        return response.json()

    def job(self,operation=None,endpoint='run',expect_success=True,**options):
        aid=self.attempt['id']
        job=self.request('POST',f'/attempts/{aid}/{endpoint}',{'operation':operation,**options} if endpoint=='run' else None)
        deadline=time.monotonic()+1000
        while job['status'] in {'queued','running'} and time.monotonic()<deadline:
            time.sleep(.8)
            job=self.request('GET','/jobs/'+job['id'])
        if job['status'] in {'queued','running'}:
            self.request('POST','/jobs/'+job['id']+'/cancel')
            raise RuntimeError('Live operation exceeded its observation deadline; cancellation requested')
        print(f"[{self.region} / {self.attempt['domain_id']}] {operation or endpoint}: {job['status']} ({job['exit_code']})",flush=True)
        self.evidence['jobs'].append({key:job[key] for key in ['id','operation','params','status','exit_code','config_hash','plan_hash','result']})
        if expect_success and job['status']!='succeeded':
            raise RuntimeError(job['log'] or json.dumps(job['result'],indent=2))
        return job

    def reference(self,domain):
        for path in (ROOT/f'curriculum/domain-{domain}/solution').rglob('*.tf'):
            relative=str(path.relative_to(ROOT/f'curriculum/domain-{domain}/solution'))
            self.request('PUT',f"/attempts/{self.attempt['id']}/files",{'path':relative,'content':path.read_text()})

    def workflow(self):
        for op in ['init','fmt','validate','plan','apply']:
            self.job(op)

    def cleanup(self,domain):
        self.job('destroy')
        if domain=='06':
            self.job('migrate-local')
            self.job(endpoint='reaper?execute=true')
            self.job('bootstrap-destroy')
        deadline=time.monotonic()+150
        while True:
            job=self.job(endpoint='teardown-check',expect_success=False)
            if job['status']=='succeeded' and job['result'].get('complete'):
                return job
            if job['status']=='failed' and not (job.get('result') or {}).get('remaining_cloud'):
                raise RuntimeError(job['log'] or json.dumps(job['result']))
            if time.monotonic()>deadline:
                raise RuntimeError('Cloud cleanup did not reach verified absence: '+json.dumps(job['result']))
            time.sleep(3)

    def run(self,domain):
        self.attempt=self.request('POST','/attempts',{'domain_id':domain})
        self.evidence.update({'domain_id':domain,'attempt_id':self.attempt['id']})
        print('START',domain,self.region,self.attempt['id'],flush=True)
        try:
            if domain=='06':
                self.workflow()
                self.job('capture-baseline')
                for op in ['bootstrap-init','bootstrap-plan','bootstrap-apply','migrate-remote']:
                    self.job(op)
                self.reference(domain)
                for op in ['plan','apply','simulate-drift']:
                    self.job(op)
                self.job('plan',refresh_only=True)
                self.job('apply')
                self.job('plan')
                self.job('apply')
                self.job('reconcile-locks')
            elif domain=='07':
                self.job('setup-import')
                self.job('init')
                generated=self.job('generate-config',expect_success=False,debug=True)
                if not generated.get('result',{}).get('generated_config'):
                    raise RuntimeError('Terraform did not generate the import configuration')
                self.request('PUT',f"/attempts/{self.attempt['id']}/files",{'path':'generated.tf','content':'# Refined declarations are now in main.tf.\n'})
                self.reference(domain)
                for op in ['fmt','validate','plan','apply']:
                    self.job(op,debug=op=='plan')
            else:
                if domain=='04':
                    self.job('init')
                    failed=self.job('plan',expect_success=False)
                    if failed['status']!='failed' or 'SSH must not be open' not in failed['log']:
                        raise RuntimeError('The invalid public-SSH contract was not rejected as expected')
                    self.evidence['negative_contract_rejected']=True
                self.reference(domain)
                self.workflow()
                if domain=='02':
                    self.job('provider-lock')
                if domain=='03':
                    self.job('capture-baseline')
                    self.job('simulate-drift')
                    self.job('plan',replace='aws_security_group.app')
                    self.job('apply')
            self.job('plan')
            graded=self.job(endpoint='validate')
            assert graded['result']['apply_verified'] and graded['result']['percentage']==50
            self.cleanup(domain)
            self.evidence['complete']=True
            return self.evidence
        except BaseException as exc:
            self.evidence['error']=str(exc)
            try:
                self.job('destroy',expect_success=False)
                if domain=='06':
                    self.job('migrate-local',expect_success=False)
                self.job(endpoint='reaper?execute=true',expect_success=False)
                if domain=='06':
                    self.job('bootstrap-destroy',expect_success=False)
                self.evidence['failure_cleanup']=self.job(endpoint='teardown-check',expect_success=False)['result']
            except Exception as cleanup_error:
                self.evidence['cleanup_attention_required']=str(cleanup_error)
            raise
        finally:
            self.evidence['finished']=time.time()
            directory=ROOT/'docs/evidence';directory.mkdir(exist_ok=True,parents=True)
            path=directory/f"live-domain{domain}-{self.region}-{self.attempt['id']}.json"
            path.write_text(json.dumps(self.evidence,indent=2)+'\n')
            print('EVIDENCE',path.name,flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--profile',required=True)
    parser.add_argument('--domains',default='01,02,03,04,05,06,07,08')
    parser.add_argument('--regions',default='us-east-1,eu-west-1,eu-west-2')
    parser.add_argument('--url',default='http://127.0.0.1:8080')
    parser.add_argument('--credential-method',choices=['profile','keys'],default='profile',help='Keys mode resolves the supplied profile into temporary credentials in memory; no keys appear in shell arguments or evidence.')
    args=parser.parse_args()
    multi_provider_verified=False
    for region in args.regions.split(','):
        for domain in args.domains.split(','):
            domain=domain.zfill(2)
            if domain=='02':
                if multi_provider_verified:
                    continue
                multi_provider_verified=True
            LiveCourse(args.profile,region,args.url,args.credential_method).run(domain)


if __name__=='__main__':
    main()

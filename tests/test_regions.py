import json
from pathlib import Path
import shutil
import subprocess
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from runner.api.credentials import Credentials
from runner.api.main import create_app
from runner.api.resources import ResourceInventory
from runner.api.terraform import parsed_hcl,select_nodes
from runner.cli.main import app as cli
from runner.regions import SUPPORTED_REGIONS


@pytest.mark.parametrize('region',SUPPORTED_REGIONS)
@pytest.mark.parametrize('mode',['profile','keys'])
def test_supported_region_reaches_credentials_attempt_and_backend_inputs(settings,aws_session,region,mode):
    application=create_app(settings,lambda db:Credentials(db,Mock(return_value=aws_session)))
    headers={'X-Tfprep':'1'}
    payload={'mode':mode,'region':region}
    payload.update({'profile':'course-sandbox'} if mode=='profile' else {'access_key_id':'key-canary','secret_access_key':'secret-canary'})
    with TestClient(application) as client:
        connected=client.post('/api/connection',headers=headers,json=payload)
        assert connected.status_code==200 and connected.json()['region']==region
        attempt=client.post('/api/attempts',headers=headers,json={'domain_id':'06'}).json()
        assert attempt['region']==region
        directory=Path(attempt['workspace'])
        for relative in ['tfprep.auto.tfvars.json','bootstrap/tfprep.auto.tfvars.json']:
            assert json.loads((directory/relative).read_text())['region']==region
        env=application.state.services['credentials'].environment()
        assert env['AWS_REGION']==env['AWS_DEFAULT_REGION']==region
        # Selecting another primary region must not move an existing attempt.
        payload['region']='us-east-1' if region!='us-east-1' else 'eu-west-1'
        assert client.post('/api/connection',headers=headers,json=payload).status_code==200
        assert client.get('/api/attempts/'+attempt['id']).json()['region']==region


def test_cli_accepts_ireland_and_api_rejects_unlisted_regions(settings,aws_session,monkeypatch):
    application=create_app(settings,lambda db:Credentials(db,Mock(return_value=aws_session)))
    with TestClient(application) as client:
        def request(method,url,**kwargs):
            return client.request(method,'/api'+url.split('/api',1)[1],json=kwargs.get('json'),headers=kwargs.get('headers'))
        monkeypatch.setattr('runner.cli.main.httpx.request',request)
        result=CliRunner().invoke(cli,['setup','--profile','course-sandbox','--region','eu-west-1'])
        assert result.exit_code==0,result.output
        assert json.loads(result.output)['region']=='eu-west-1'
        denied=client.post('/api/connection',headers={'X-Tfprep':'1'},json={'mode':'profile','profile':'course-sandbox','region':'ap-southeast-2'})
        assert denied.status_code==422


def test_every_lab_region_constraint_accepts_all_three_regions_in_real_terraform(settings,tmp_path):
    files=[path for path in (settings.root/'curriculum').rglob('variables.tf') if '.terraform' not in path.parts]
    constraints={select_nodes(parsed_hcl(path.parent),'variable.region.validation.condition')[0] for path in files}
    assert len(files)==19 and len(constraints)==1
    directory=tmp_path/'region-inputs';directory.mkdir()
    shutil.copy(files[0],directory/'variables.tf')
    init=subprocess.run([settings.terraform,'init','-backend=false','-input=false'],cwd=directory,capture_output=True,text=True,timeout=20)
    assert init.returncode==0,init.stderr
    for region in [*SUPPORTED_REGIONS,'ap-southeast-2']:
        result=subprocess.run([settings.terraform,'plan','-input=false','-no-color','-var=region='+region,'-var=account_id=123456789012','-var=attempt_id=0123456789abcdef'],cwd=directory,capture_output=True,text=True,timeout=20)
        assert result.returncode==(0 if region in SUPPORTED_REGIONS else 1),result.stdout+result.stderr


def test_provider_alias_lab_keeps_its_actual_pair_when_primary_is_ireland(settings,db,credentials):
    attempt={'id':'0123456789abcdef','domain_id':'02','account':'123456789012','region':'eu-west-1'}
    db.execute('INSERT INTO attempts(id,domain_id,account,region,created) VALUES (?,?,?,?,?)',(*attempt.values(),0))
    inventory=ResourceInventory(db,credentials)
    state={'values':{'root_module':{'resources':[
        {'address':'aws_ssm_parameter.us','type':'aws_ssm_parameter','mode':'managed','values':{'id':'us-name','tags_all':{}}},
        {'address':'aws_ssm_parameter.uk','type':'aws_ssm_parameter','mode':'managed','values':{'id':'uk-name','tags_all':{'RegionRole':'uk'}}},
    ]}}}
    inventory.capture(attempt,state)
    assert {row['resource_id']:row['region'] for row in inventory.rows(attempt['id'])}=={'us-name':'us-east-1','uk-name':'eu-west-2'}
    for variant in ['starter','solution']:
        providers=parsed_hcl(settings.root/f'curriculum/domain-02/{variant}')
        assert set(select_nodes(providers,'provider.aws.region'))=={'us-east-1','eu-west-2'}

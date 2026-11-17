import json
from unittest.mock import Mock

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from runner.api.credentials import Credentials
from runner.api.main import create_app
from runner.cli.main import app


def test_cli_and_browser_share_connection_attempt_and_progress_services(settings,aws_session,monkeypatch):
    application=create_app(settings,lambda db:Credentials(db,Mock(return_value=aws_session)))
    runner=CliRunner()
    with TestClient(application) as client:
        def request(method,url,**kwargs):
            return client.request(method,'/api'+url.split('/api',1)[1],json=kwargs.get('json'),headers=kwargs.get('headers'))
        monkeypatch.setattr('runner.cli.main.httpx.request',request)
        connected=runner.invoke(app,['setup','--keys'],input='cli-key-canary\ncli-secret-canary\ncli-token-canary\n')
        assert connected.exit_code==0,connected.output
        assert 'cli-secret-canary' not in connected.output and 'cli-token-canary' not in connected.output
        assert client.get('/api/connection').json()['mode']=='keys'
        started=runner.invoke(app,['start','01'])
        assert started.exit_code==0,started.output
        attempt=json.loads(started.output)
        assert client.get('/api/attempts/'+attempt['id']).json()['id']==attempt['id']
        status=runner.invoke(app,['status'])
        assert json.loads(status.output)==client.get('/api/progress').json()
        # An approved operation submitted by the CLI is the same durable job seen in the UI.
        validator=application.state.services['jobs'].validator
        validator.validate=Mock(return_value={'checks':[{'status':'pass'}],'apply_verified':True,'percentage':50})
        graded=runner.invoke(app,['validate','01','--attempt',attempt['id']])
        assert graded.exit_code==0,graded.output
        api_job=client.get('/api/attempts/'+attempt['id']).json()['jobs'][0]
        assert api_job['operation']=='validate-lab' and api_job['status']=='succeeded'
        assert json.loads(api_job['result'])['percentage']==50
        assert 'cli-secret-canary' not in json.dumps(api_job)
        doctor=runner.invoke(app,['doctor'])
        assert doctor.exit_code==0,doctor.output
        diagnostics=json.loads(doctor.output)
        assert diagnostics['schema_version']==3 and diagnostics['workspaces_writable']
        assert diagnostics['aws']['identity_verified']
        assert len(diagnostics['read_permission_checks'])==8
        formatted=runner.invoke(app,['run','01','--attempt',attempt['id'],'--','fmt'])
        assert formatted.exit_code==0,formatted.output
        assert client.get('/api/attempts/'+attempt['id']).json()['jobs'][0]['operation']=='fmt'
        exam=runner.invoke(app,['exam','--mock','A','--questions','20'])
        assert exam.exit_code==0 and '/exam/' in exam.output
        session_id=exam.output.strip().rsplit('/',1)[1]
        assert len(client.get('/api/exams/'+session_id).json()['questions'])==20
        cleanup=runner.invoke(app,['teardown-check','01','--attempt',attempt['id']])
        assert cleanup.exit_code==1 and 'failed' in cleanup.output
        assert client.get('/api/attempts/'+attempt['id']).json()['status']!='complete'
        assert runner.invoke(app,['disconnect']).exit_code==0
        assert client.get('/api/connection').json()['connected'] is False

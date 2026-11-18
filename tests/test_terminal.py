import json
from pathlib import Path
import time
import sys
import threading
from unittest.mock import Mock

from fastapi.testclient import TestClient
import pytest

from runner.api.credentials import Credentials
from runner.api.main import create_app
from runner.api.models import Check
from runner.api.terminal import parse_command
from runner.api.jobs import Jobs
from runner.api.content import Content


@pytest.mark.parametrize('command,domain,operation', [
    ('terraform init', '01', 'init'), ('terraform fmt -check -recursive', '03', 'fmt'),
    ('terraform validate -json', '04', 'validate'), ('terraform plan -out tfplan -detailed-exitcode', '02', 'plan'),
    ('terraform plan -replace=aws_security_group.app -out=tfplan', '03', 'plan'),
    ('terraform plan -refresh-only -out=tfplan', '06', 'plan'), ('terraform apply tfplan', '01', 'apply'),
    ('terraform show -json tfplan', '01', 'show'), ('terraform state pull', '06', 'state-pull'),
    ('''terraform state show 'module.app_tier["dev"].aws_vpc.app' ''', '05', 'state-show'),
    ('terraform state mv terraform_data.old terraform_data.new', '06', 'state-mv'),
    ('terraform state rm terraform_data.old', '06', 'state-rm'),
    ('terraform providers lock -platform=linux_arm64 -platform=linux_amd64 -platform=darwin_arm64', '02', 'provider-lock'),
    ('terraform -chdir=bootstrap plan -out=tfplan', '06', 'bootstrap-plan'),
    ('terraform plan -generate-config-out=generated.tf', '07', 'generate-config'),
    ('TF_LOG_PROVIDER=DEBUG terraform plan -out=tfplan', '07', 'plan'),
    ('lab grade', '01', 'validate-lab'), ('lab check-cleanup', '01', 'teardown-check'),
    ('lab migrate-remote', '06', 'migrate-remote'), ('lab setup-import', '07', 'setup-import'),
    ('terraform plan -help', '01', 'terminal-help'),
])
def test_terminal_accepts_course_workflows(command, domain, operation):
    parsed = parse_command(command, domain)
    assert parsed.operation == operation
    assert parsed.params['terminal_command'] == command.strip()


@pytest.mark.parametrize('command', [
    'terraform init; touch /tmp/escape', 'terraform plan && terraform apply tfplan',
    'terraform plan | cat', 'terraform plan > output.txt', 'terraform plan\nterraform destroy',
    'terraform plan $(cat /root/.aws/credentials)', 'terraform plan `id`',
    'AWS_PROFILE=other terraform plan', 'bash', 'aws s3 rb s3://foreign',
    'terraform -chdir=../../other destroy', 'terraform apply -auto-approve',
    'terraform plan -out=../../tfplan', 'terraform plan -var=attempt_id=foreign',
    'terraform state pull -state=/private/other', 'terraform state mv -state-out=other old new',
    'terraform import aws_s3_bucket.foreign existing-bucket', 'terraform show /root/.aws/credentials',
])
def test_terminal_rejects_shell_escapes_and_untracked_operations(command):
    with pytest.raises(ValueError):
        parse_command(command, '01')


def test_terminal_distinguishes_preview_saved_plans_and_confirmation():
    preview = parse_command('terraform plan', '01')
    assert not preview.params['save_plan'] and not preview.params['detailed_exitcode']
    saved = parse_command('terraform plan -out=tfplan -detailed-exitcode', '01')
    assert saved.params['save_plan'] and saved.params['detailed_exitcode']
    assert parse_command('terraform destroy', '01').confirmation
    assert not parse_command('terraform destroy -auto-approve', '01').confirmation
    assert parse_command('lab recover --execute', '01').confirmation
    with pytest.raises(ValueError):
        parse_command('terraform -chdir=bootstrap init', '01')
    with pytest.raises(ValueError):
        parse_command('lab setup-import', '01')


def test_terminal_interrupt_allows_process_to_finish_and_keeps_final_output(settings, db, credentials, tmp_path):
    db.execute('INSERT INTO attempts(id,domain_id,account,region,created) VALUES (?,?,?,?,?)', ('interrupt', '01', '123456789012', 'us-east-1', 0))
    db.execute('INSERT INTO jobs(id,attempt_id,operation,params,status,created) VALUES (?,?,?,?,?,?)', ('interrupt-job', 'interrupt', 'plan', '{}', 'running', 0))
    jobs = Jobs(settings, db, credentials, Content(settings.root), Mock())
    code = '''import signal,pathlib,time,sys
def finish(*args):
    pathlib.Path('interrupted-cleanly').write_text('state-flushed')
    print('Finished graceful interrupt',flush=True)
    sys.exit(0)
signal.signal(signal.SIGINT,finish)
print('Ready',flush=True)
while True: time.sleep(.05)
'''
    timer = threading.Timer(.3, lambda: jobs.cancel('interrupt-job'))
    timer.start()
    try:
        with pytest.raises(InterruptedError):
            jobs.run_process('interrupt-job', [sys.executable, '-c', code], tmp_path, credentials.environment())
        assert (tmp_path / 'interrupted-cleanly').read_text() == 'state-flushed'
        assert 'Finished graceful interrupt' in jobs.get('interrupt-job')['log']
    finally:
        timer.cancel(); jobs.pool.shutdown()


def test_typed_commands_execute_real_terraform_and_preserve_grading_guards(settings, aws_session, monkeypatch):
    application = create_app(settings, lambda db: Credentials(db, Mock(return_value=aws_session)))
    headers = {'X-Tfprep': '1'}
    with TestClient(application) as client:
        assert client.post('/api/connection', headers=headers, json={'mode': 'profile', 'profile': 'course-sandbox'}).status_code == 200
        attempt = client.post('/api/attempts', headers=headers, json={'domain_id': '03'}).json()
        aid = attempt['id']; directory = Path(attempt['workspace'])
        for path in directory.glob('*.tf'):
            path.unlink()
        (directory / '.terraform.lock.hcl').unlink()
        (directory / 'tfprep.auto.tfvars.json').unlink()
        (directory / 'main.tf').write_text('resource "terraform_data" "sample" {\n  input = "terminal-test"\n}\n')
        services = application.state.services
        # This fixture has no AWS objects; exercise the real CLI without the AWS-only inventory adapter.
        monkeypatch.setattr(services['inventory'], 'capture', Mock())
        original_domain = services['content'].domain
        monkeypatch.setattr(services['content'], 'domain', lambda did: {**original_domain(did), 'resource_types': ['terraform_data']})

        def run(command, expected='succeeded', confirmed=False):
            response = client.post(f'/api/attempts/{aid}/terminal', headers=headers, json={'command': command, 'confirmed': confirmed})
            assert response.status_code == 200, response.text
            data = response.json()
            if 'job' not in data:
                return data
            job = data['job']; deadline = time.monotonic() + 15
            while job['status'] in ('queued', 'running') and time.monotonic() < deadline:
                time.sleep(.02)
                job = client.get('/api/jobs/' + job['id']).json()
            assert job['status'] == expected, job['log']
            return job

        assert 'Terraform commands' in run('help')['message']
        assert '-out=path' in run('terraform plan -help')['log']
        run('terraform init')
        run('terraform fmt -check -recursive')
        run('terraform validate -json')
        preview = run('terraform plan')
        assert preview['exit_code'] == 0 and preview['plan_hash'] is None
        assert not (directory / 'tfplan').exists()
        assert 'fresh saved plan' in run('terraform apply tfplan', 'failed')['log']
        saved = run('terraform plan -out tfplan -detailed-exitcode')
        assert saved['exit_code'] == 2 and saved['plan_hash']
        assert 'terraform_data.sample' in run('terraform show tfplan')['log']
        run('terraform apply tfplan')
        assert 'terraform_data.sample' in run('terraform state list')['log']
        assert 'terminal-test' in run('terraform state show terraform_data.sample')['log']
        services['db'].execute("UPDATE attempts SET status='apply_verified',verified_hash='previous-grade' WHERE id=?", (aid,))
        run('terraform state mv terraform_data.sample terraform_data.renamed')
        assert services['jobs'].attempt(aid)['verified_hash'] is None
        run('terraform state mv terraform_data.renamed terraform_data.sample')
        assert '1.12.2' in run('terraform version -json')['log']
        assert 'terraform.io/builtin/terraform' in run('terraform providers')['log']
        run('terraform plan')
        check = Check(id='no_changes', type='command_receipt', operation='plan-no-changes', description='Post-apply check')
        with pytest.raises(ValueError, match='detailed-exitcode'):
            services['jobs'].validator.receipt(check, attempt, directory)
        detailed = run('terraform plan -detailed-exitcode -out=tfplan')
        assert detailed['exit_code'] == 0
        services['jobs'].validator.receipt(check, attempt, directory)
        (directory / 'tfplan').write_bytes(b'tampered plan')
        assert 'Saved plan changed' in run('terraform apply tfplan', 'failed')['log']
        (directory / 'main.tf').write_text((directory / 'main.tf').read_text() + '\n# Edited\n')
        assert 'fresh saved plan' in run('terraform apply tfplan', 'failed')['log']
        before = len(services['db'].all('SELECT id FROM jobs'))
        assert run('terraform destroy')['confirmation_required']
        assert len(services['db'].all('SELECT id FROM jobs')) == before
        run('terraform destroy', confirmed=True)
        state = json.loads(run('terraform state pull')['log'].split('\n', 1)[1])
        assert not state.get('resources')
        assert services['db'].all('SELECT resource_id FROM resources') == []

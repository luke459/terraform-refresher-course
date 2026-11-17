import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time
from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient

from runner.api.content import Content
from runner.api.credentials import Credentials
from runner.api.jobs import Jobs
from runner.api.lab_actions import setup_import
from runner.api.main import create_app
from runner.api.resources import ResourceInventory
from runner.api.terraform import config_hash
from runner.api.validation import LabValidator


def insert_attempt(db, domain='01'):
    attempt={'id':'0123456789abcdef','domain_id':domain,'account':'123456789012','region':'us-east-1'}
    db.execute('INSERT INTO attempts(id,domain_id,account,region,created) VALUES (?,?,?,?,?)',(*attempt.values(),0))
    return attempt


def test_partial_import_setup_finishes_only_the_missing_fixture(db, credentials):
    attempt=insert_attempt(db,'07')
    inventory=ResourceInventory(db,credentials)
    bucket=f"tf004-{attempt['account']}-{attempt['id']}-import"
    inventory.register(attempt,'aws_s3_bucket.imported','aws_s3_bucket',bucket,attempt['region'])
    tags={'Project':'tf-004-prep','ManagedBy':'terraform','Learner':'local','Lab':'07','Attempt':attempt['id']}
    inventory.reconcile=Mock()
    inventory.inspect=Mock(return_value={'exists':True,'tags':tags})
    jobs=Mock(db=db,credentials=credentials,inventory=inventory)
    result=setup_import(attempt,jobs)
    credentials.client('s3').create_bucket.assert_not_called()
    credentials.client('iam').create_policy.assert_called_once()
    assert result['baseline']['aws_s3_bucket.imported']==bucket
    assert len(inventory.rows(attempt['id']))==2
    # A second retry reuses both live identities.
    setup_import(attempt,jobs)
    credentials.client('iam').create_policy.assert_called_once()


def test_restart_preserves_work_and_marks_pending_operations_interrupted(settings, db, credentials):
    jobs=Jobs(settings,db,credentials,Content(settings.root),ResourceInventory(db,credentials))
    attempt=jobs.start_attempt('01')
    directory=Path(attempt['workspace'])
    (directory/'notes.md').write_text('Learner work survives restart.')
    db.execute("INSERT INTO jobs(id,attempt_id,operation,params,status,created) VALUES (?,?,?,?,?,?)",('pending',attempt['id'],'apply','{}','running',0))
    jobs.start()
    try:
        assert jobs.get('pending')['status']=='interrupted'
        assert 'Inspect state' in jobs.get('pending')['log']
        assert (directory/'notes.md').read_text()=='Learner work survives restart.'
        second=Jobs(settings,db,credentials,Content(settings.root),Mock())
        try:
            with pytest.raises(RuntimeError,match='already owns'):
                second.start()
        finally:
            second.pool.shutdown()
            if second.lockfile:second.lockfile.close()
    finally:
        jobs.close()


def test_cancel_stops_the_actual_process_and_sanitizes_debug_files(settings, db, credentials, tmp_path):
    attempt=insert_attempt(db)
    db.execute("INSERT INTO jobs(id,attempt_id,operation,params,status,created) VALUES (?,?,?,?,?,?)",('cancel-me',attempt['id'],'plan','{}','running',0))
    jobs=Jobs(settings,db,credentials,Content(settings.root),Mock())
    env=credentials.environment();env['TF_LOG_PROVIDER']='DEBUG'
    marker=tmp_path/'child-finished'
    code="import pathlib,time; print('profile-secret-canary',flush=True); time.sleep(1.5); pathlib.Path('child-finished').write_text('unexpected')"
    timer=threading.Timer(.2,lambda:jobs.cancel('cancel-me'))
    timer.start()
    try:
        with pytest.raises(InterruptedError,match='canceled'):
            jobs.run_process('cancel-me',[sys.executable,'-c',code],tmp_path,env)
        assert not marker.exists()
        debug=tmp_path/'tf-debug.log'
        assert 'profile-secret-canary' not in debug.read_text()
        assert '[REDACTED]' in debug.read_text()
        assert debug.stat().st_mode & 0o777==0o600
        assert 'profile-secret-canary' not in jobs.get('cancel-me')['log']
    finally:
        timer.cancel();jobs.pool.shutdown()


def test_saved_plan_rejects_changed_configuration_or_plan_bytes(settings,db,credentials,tmp_path):
    attempt=insert_attempt(db)
    jobs=Jobs(settings,db,credentials,Content(settings.root),Mock())
    config=tmp_path/'main.tf';config.write_text('locals { name = "original" }')
    plan=tmp_path/'tfplan';plan.write_bytes(b'original-plan')
    db.execute("INSERT INTO jobs(id,attempt_id,operation,params,status,created,config_hash,plan_hash) VALUES (?,?,?,?,?,?,?,?)",('plan',attempt['id'],'plan','{}','succeeded',1,config_hash(tmp_path),hashlib.sha256(plan.read_bytes()).hexdigest()))
    apply={'operation':'apply','params':{}}
    try:
        config.write_text('locals { name = "changed" }')
        with pytest.raises(ValueError,match='fresh saved plan'):
            jobs.command(apply,attempt,tmp_path)
        config.write_text('locals { name = "original" }')
        plan.write_bytes(b'tampered-plan')
        with pytest.raises(ValueError,match='Saved plan changed'):
            jobs.command(apply,attempt,tmp_path)
    finally:
        jobs.pool.shutdown()


@pytest.mark.parametrize('code',['AccessDenied','ThrottlingException'])
def test_cloud_errors_cannot_award_completion_or_clear_inventory(settings,db,credentials,tmp_path,code):
    attempt=insert_attempt(db)
    inventory=ResourceInventory(db,credentials)
    inventory.register(attempt,'aws_s3_bucket.course','aws_s3_bucket','owned','us-east-1')
    inventory.reconcile=Mock()
    inventory.inspect=Mock(side_effect=ClientError({'Error':{'Code':code,'Message':'Unavailable'}},'HeadBucket'))
    validator=LabValidator(settings,db,Content(settings.root),credentials,inventory)
    validator.state=Mock(return_value={'values':{'root_module':{'resources':[]}}})
    db.execute("INSERT INTO jobs(id,attempt_id,operation,params,status,created) VALUES (?,?,?,?,?,?)",('destroy',attempt['id'],'destroy','{}','succeeded',0))
    with pytest.raises(ClientError):validator.teardown(attempt,tmp_path,{})
    assert db.one('SELECT status FROM attempts')['status']=='active'
    assert inventory.rows(attempt['id'])[0]['status']=='present'


def test_reconciliation_paginates_and_keeps_other_attempts(db,credentials):
    attempt=insert_attempt(db,'02')
    inventory=ResourceInventory(db,credentials)
    owned=f"/tf004/{attempt['id']}/one"
    foreign='/tf004/another-attempt/one'
    tags={'Project':'tf-004-prep','ManagedBy':'terraform','Lab':'02','Attempt':attempt['id']}
    paginator=credentials.client('ssm').get_paginator.return_value
    paginator.paginate.return_value=iter([{'Parameters':[{'Name':foreign}]},{'Parameters':[{'Name':owned}]}])
    inventory.inspect=lambda row:{'exists':True,'tags':tags if row['resource_id']==owned else {**tags,'Attempt':'another-attempt'}}
    assert inventory.reconcile(attempt)['reconciled_resources']==1
    assert [r['resource_id'] for r in inventory.rows(attempt['id'])]==[owned]


def test_private_artifact_purge_requires_cleanup_and_retains_source(settings,aws_session):
    application=create_app(settings,lambda db:Credentials(db,Mock(return_value=aws_session)))
    headers={'X-Tfprep':'1'}
    with TestClient(application) as client:
        client.post('/api/connection',headers=headers,json={'mode':'profile','profile':'test'})
        attempt=client.post('/api/attempts',headers=headers,json={'domain_id':'01'}).json()
        path=f"/api/attempts/{attempt['id']}/purge-artifacts"
        assert client.post(path,headers=headers).status_code==400
        directory=Path(attempt['workspace'])
        state=directory/'terraform.tfstate'
        state.write_text(json.dumps({'resources':[{'mode':'managed'}]}))
        application.state.services['db'].execute("UPDATE attempts SET status='complete' WHERE id=?",(attempt['id'],))
        assert client.post(path,headers=headers).status_code==400
        state.write_text(json.dumps({'resources':[]}))
        (directory/'tfplan').write_bytes(b'private-plan')
        result=client.post(path,headers=headers)
        assert result.status_code==200 and result.json()['removed_files']==2
        assert (directory/'main.tf').is_file() and not state.exists()

import json
import subprocess
import uuid
from unittest.mock import Mock
import pytest
from runner.api.content import Content
from runner.api.jobs import Jobs


def test_empty_migration_retains_actual_source_lineage(settings,db,credentials,tmp_path):
    directory=tmp_path/'migration';directory.mkdir()
    (directory/'main.tf').write_text('terraform {\n  backend "local" {}\n}\n')
    initialized=subprocess.run([settings.terraform,'init','-input=false'],cwd=directory,capture_output=True,text=True,timeout=20)
    assert initialized.returncode==0,initialized.stderr
    jobs=Jobs(settings,db,credentials,Content(settings.root),Mock())
    attempt={'id':'0123456789abcdef'}
    source={'version':4,'terraform_version':'1.12.2','serial':9,'lineage':str(uuid.uuid4()),'outputs':{},'resources':[]}
    jobs.empty_migrations[attempt['id']]=source
    result=jobs.finalize_empty_migration(attempt,directory)
    assert result['local_empty_snapshot_preserved']
    pulled=subprocess.run([settings.terraform,'state','pull'],cwd=directory,capture_output=True,text=True,timeout=20)
    assert pulled.returncode==0 and json.loads(pulled.stdout)['lineage']==source['lineage']
    assert json.loads(pulled.stdout)['resources']==[]
    foreign={**source,'lineage':str(uuid.uuid4())}
    (directory/'terraform.tfstate').write_text(json.dumps(foreign))
    with pytest.raises(ValueError,match='different state lineage'):
        jobs.finalize_empty_migration(attempt,directory)
    jobs.pool.shutdown()

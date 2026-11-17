import json
from pathlib import Path
from unittest.mock import Mock
import pytest
from pydantic import ValidationError
from runner.api.content import Content
from runner.api.models import Check, Validator
from runner.api.resources import ResourceInventory
from runner.api.terraform import parsed_hcl, select_nodes
from runner.api.validation import LabValidator


def test_actual_starter_fails_and_solution_satisfies_hcl_contract(settings, db, credentials):
    content = Content(settings.root)
    inventory = ResourceInventory(db, credentials)
    validator = LabValidator(settings, db, content, credentials, inventory)
    check = content.validator("01").checks[0]
    directory = content.directory("01")
    assert validator.run_check(check, {}, directory / "solution", {}, {})["assertions"] == 1
    with pytest.raises(ValueError, match="unexpected value"):
        validator.run_check(check, {}, directory / "starter", {}, {})
    assert select_nodes(parsed_hcl(directory / "solution"), "resource.aws_s3_bucket.*")
    imports=parsed_hcl(content.directory('07')/'solution')
    assert len(select_nodes(imports,'import'))==2


def test_unknown_check_type_is_rejected():
    with pytest.raises(ValidationError):
        Check(id="bad", type="pretend-pass", description="Invalid check")


def test_empty_state_does_not_prove_cloud_cleanup(settings, db, credentials):
    content = Content(settings.root)
    inventory = Mock()
    inventory.rows.return_value = [{"resource_id":"bucket-still-live"}]
    inventory.absence.return_value = ["aws_s3_bucket.course"]
    validator = LabValidator(settings, db, content, credentials, inventory)
    attempt = {"id":"0123456789abcdef", "domain_id":"01", "account":"123456789012", "region":"us-east-1"}
    db.execute("INSERT INTO attempts(id,domain_id,account,region,status,created) VALUES (?,?,?,?,?,?)", (*[attempt[k] for k in ('id','domain_id','account','region')],"cleanup_pending",0))
    db.execute("INSERT INTO jobs(id,attempt_id,operation,params,status,created) VALUES (?,?,?,?,?,?)", ("destroy",attempt["id"],"destroy","{}","succeeded",0))
    validator.state = Mock(return_value={"values":{"root_module":{"resources":[]}}})
    result = validator.teardown(attempt, settings.workspaces, {})
    assert not result["complete"]
    assert result["remaining_cloud"] == ["aws_s3_bucket.course"]
    assert db.one("SELECT status FROM attempts")["status"] != "complete"
    inventory.absence.return_value = []
    cleaned=validator.teardown(attempt, settings.workspaces, {})
    assert cleaned['cleaned'] and not cleaned['complete']
    db.execute("UPDATE attempts SET verified_hash='verified-config' WHERE id=?",(attempt['id'],))
    db.execute("INSERT INTO jobs(id,attempt_id,operation,params,status,created,finished,config_hash) VALUES (?,?,?,?,?,?,?,?)",('grade',attempt['id'],'validate-lab','{}','succeeded',-2,-1,'verified-config'))
    assert validator.teardown(attempt,settings.workspaces,{})['complete']


def test_cloud_adapter_refuses_unknown_operations(settings, db, credentials):
    validator = LabValidator(settings, db, Content(settings.root), credentials, Mock())
    validator.state = Mock(return_value={"values":{"root_module":{"resources":[{"type":"aws_s3_bucket"}]}}})
    check = Check(id="bad", type="aws_cli", description="Untrusted write", service="s3", operation="delete_bucket", assertions=[{'path':'Status','equals':'ok'}])
    with pytest.raises(ValueError, match="not allowlisted"):
        validator.run_check(check, {"region":"us-east-1"}, settings.workspaces, {}, {})


@pytest.mark.parametrize('status',['fail','unknown','error'])
def test_check_warnings_and_deferred_assertions_cannot_pass_grading(settings,db,credentials,status):
    content=Content(settings.root)
    validator=LabValidator(settings,db,content,credentials,Mock())
    check=next(c for c in content.validator('04').checks if c.id=='check_assertions')
    state={'values':{'root_module':{'resources':[{'type':'aws_vpc','mode':'managed'}]}},
        'checks':[{'address':{'kind':'check'},'status':'pass'}]}
    validator.run_check(check,{},settings.workspaces,{}, {'state':state})
    state['checks'][0]['status']=status
    with pytest.raises(ValueError,match='Unexpected value'):
        validator.run_check(check,{},settings.workspaces,{}, {'state':state})


@pytest.mark.parametrize('snapshot',[{}, {'version':4}, {'version':3,'lineage':'old'}])
def test_missing_or_invalid_state_never_looks_like_successful_empty_state(settings,db,credentials,monkeypatch,snapshot):
    validator=LabValidator(settings,db,Content(settings.root),credentials,Mock())
    monkeypatch.setattr('runner.api.validation.terraform_json',lambda *args:snapshot)
    with pytest.raises(ValueError,match='State is missing'):
        validator.state(settings.workspaces,{})


def test_saved_plan_assertions_reject_real_changes_and_missing_artifacts(settings,db,credentials,monkeypatch):
    validator=LabValidator(settings,db,Content(settings.root),credentials,Mock())
    check=Check(id='no_changes',type='tf_plan_json',description='No managed changes',assertions=[{'path':"resource_changes[?mode=='managed' && change.actions!=`[\"no-op\"]`]",'absent':True}])
    document={'format_version':'1.2','resource_changes':[{'mode':'managed','change':{'actions':['no-op']}}]}
    monkeypatch.setattr('runner.api.validation.terraform_json',lambda *args:document)
    validator.run_check(check,{},settings.workspaces,{},{})
    document['resource_changes'][0]['change']['actions']=['create']
    with pytest.raises(ValueError,match='Unexpected value'):
        validator.run_check(check,{},settings.workspaces,{},{})
    document.clear()
    with pytest.raises(ValueError,match='saved plan'):
        validator.run_check(check,{},settings.workspaces,{},{})


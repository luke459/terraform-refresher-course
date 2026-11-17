from unittest.mock import Mock
import json
import pytest
from runner.api.content import Content
from runner.api.jobs import Jobs
from runner.api.models import Check
from runner.api.resources import ResourceInventory
from runner.api.validation import LabValidator


def test_disallowed_paid_resources_are_rejected_before_apply(settings,db,credentials):
    jobs=Jobs(settings,db,credentials,Content(settings.root),Mock())
    attempt={'domain_id':'01','id':'0123456789abcdef'}
    plan={'resource_changes':[{'mode':'managed','type':'aws_nat_gateway','change':{'actions':['create'],'after':{}}}]}
    with pytest.raises(ValueError,match='allowlist'):
        jobs.guard_plan(attempt,plan)
    tags={'Project':'tf-004-prep','ManagedBy':'terraform','Lab':'01','Attempt':attempt['id']}
    plan['resource_changes'][0]={'mode':'managed','type':'aws_s3_bucket','change':{'actions':['create'],'after':{'tags_all':tags}}}
    jobs.guard_plan(attempt,plan)
    plan['resource_changes'][0]['change']['after']['tags_all']['Attempt']='different-attempt'
    with pytest.raises(ValueError,match='ownership tags'):
        jobs.guard_plan(attempt,plan)
    jobs.pool.shutdown()


def test_replaced_old_id_does_not_require_the_old_object_to_stay_live(db,credentials):
    attempt={'id':'0123456789abcdef','domain_id':'03','account':'123456789012','region':'us-east-1'}
    db.execute('INSERT INTO attempts(id,domain_id,account,region,created) VALUES (?,?,?,?,?)',(*attempt.values(),0))
    inventory=ResourceInventory(db,credentials)
    inventory.register(attempt,'aws_security_group.app','aws_security_group','sg-old','us-east-1')
    inventory.register(attempt,'aws_security_group.app','aws_security_group','sg-new','us-east-1')
    tags={'Project':'tf-004-prep','ManagedBy':'terraform','Lab':'03','Attempt':attempt['id']}
    inventory.inspect=lambda resource:{'exists':resource['resource_id']=='sg-new','tags':tags}
    assert inventory.verify_owned(attempt,{'sg-new'})['verified_resources']==1
    assert next(r for r in inventory.rows(attempt['id']) if r['resource_id']=='sg-old')['status']=='absent'


def test_reaper_never_deletes_a_contradictory_owner(db,credentials):
    attempt={'id':'0123456789abcdef','domain_id':'01','account':'123456789012','region':'us-east-1'}
    db.execute('INSERT INTO attempts(id,domain_id,account,region,created) VALUES (?,?,?,?,?)',(*attempt.values(),0))
    inventory=ResourceInventory(db,credentials)
    row={'address':'bucket','type':'aws_s3_bucket','resource_id':'bucket','region':'us-east-1','ownership_verified':1}
    inventory.inspect=Mock(return_value={'exists':True,'tags':{'Project':'tf-004-prep','Attempt':'another-attempt'}})
    with pytest.raises(ValueError,match='Refusing deletion'):
        inventory.delete(attempt,row)


def test_secret_scanner_catches_values_under_unrelated_field_names(settings,db,credentials,tmp_path,monkeypatch):
    directory=tmp_path/'secret-lab';directory.mkdir()
    credentials.client=Mock()
    credentials.client.return_value.get_secret_value.return_value={'SecretString':'known-negative-canary'}
    validator=LabValidator(settings,db,Content(settings.root),credentials,Mock())
    state={'values':{'root_module':{'resources':[
        {'type':'aws_secretsmanager_secret','values':{'id':'owned-secret'}},
        {'type':'aws_secretsmanager_secret_version','values':{'secret_string_wo':None}},
    ]}}}
    schema={'provider_schemas':{'registry.terraform.io/hashicorp/aws':{'resource_schemas':{'aws_secretsmanager_secret_version':{'block':{'attributes':{'secret_string_wo':{'write_only':True}}}}}}}}
    monkeypatch.setattr('runner.api.validation.terraform_json',lambda settings,directory,args,env:schema if args[0]=='providers' else {'format_version':'1.2'})
    (directory/'terraform.tfstate').write_text(json.dumps(state))
    assert validator.secret_check({'region':'us-east-1'},directory,{},state)['live_value_compared']
    state['values']['unrelated']={'nested':['known-negative-canary']}
    with pytest.raises(ValueError,match='live secret appears'):
        validator.secret_check({'region':'us-east-1'},directory,{},state)
    state['values'].pop('unrelated')
    (directory/'surprise.txt').write_text('known-negative-canary')
    with pytest.raises(ValueError,match='retained workspace artifact'):
        validator.secret_check({'region':'us-east-1'},directory,{},state)


def test_workload_reaper_does_not_wait_for_or_delete_bootstrap(db,credentials):
    attempt={'id':'0123456789abcdef','domain_id':'06','account':'123456789012','region':'us-east-1'}
    db.execute('INSERT INTO attempts(id,domain_id,account,region,created) VALUES (?,?,?,?,?)',(*attempt.values(),0))
    inventory=ResourceInventory(db,credentials)
    inventory.register(attempt,'aws_ssm_parameter.detached','aws_ssm_parameter','owned-parameter','us-east-1')
    inventory.register(attempt,'bootstrap.aws_s3_bucket.state','aws_s3_bucket','owned-backend','us-east-1')
    live={'owned-parameter':True,'owned-backend':True}
    inventory.reconcile=Mock()
    inventory.inspect=lambda row:{'exists':live[row['resource_id']],'tags':{}}
    deleted=[]
    def delete(attempt,row):
        deleted.append(row['resource_id']);live[row['resource_id']]=False
    inventory.delete=delete
    result=inventory.reap(attempt,execute=True)
    assert result['remaining']==[] and deleted==['owned-parameter'] and live['owned-backend']


def test_missing_tag_recovery_requires_previously_verified_exact_identity(db,credentials):
    attempt={'id':'0123456789abcdef','domain_id':'01','account':'123456789012','region':'us-east-1'}
    inventory=ResourceInventory(db,credentials)
    row={'address':'aws_ssm_parameter.metadata','type':'aws_ssm_parameter','resource_id':'/tf004/0123456789abcdef/metadata','region':'us-east-1','ownership_verified':0}
    inventory.inspect=Mock(return_value={'exists':True,'tags':{'ManagedBy':'terraform','Lab':'01','Attempt':attempt['id']}})
    with pytest.raises(ValueError,match='Refusing deletion'):
        inventory.delete(attempt,row)
    credentials.client('ssm').delete_parameter.assert_not_called()
    row['ownership_verified']=1
    inventory.delete(attempt,row)
    credentials.client('ssm').delete_parameter.assert_called_once_with(Name=row['resource_id'])


def test_rule_drift_changes_only_the_owned_private_lab_group(credentials,tmp_path):
    from runner.api.lab_actions import lab_action
    attempt={'id':'0123456789abcdef','domain_id':'03','account':'123456789012','region':'us-east-1'}
    jobs=Mock(credentials=credentials)
    jobs.validator.state.return_value={'values':{'root_module':{'resources':[]}}}
    jobs.inventory.rows.return_value=[{'address':'aws_security_group.app','resource_id':'sg-owned'}]
    ec2=credentials.client('ec2')
    ec2.describe_security_groups.return_value={'SecurityGroups':[{'IpPermissions':[]}]}
    result=lab_action('simulate-drift',attempt,tmp_path,jobs)
    expected=[{'IpProtocol':'tcp','FromPort':8443,'ToPort':8443,'IpRanges':[{'CidrIp':'10.43.0.0/16','Description':'Controlled tfprep drift'}]}]
    ec2.authorize_security_group_ingress.assert_called_once_with(GroupId='sg-owned',IpPermissions=expected)
    assert not result['rule_already_present']
    ec2.describe_security_groups.return_value={'SecurityGroups':[{'IpPermissions':expected}]}
    assert lab_action('simulate-drift',attempt,tmp_path,jobs)['rule_already_present']
    ec2.authorize_security_group_ingress.assert_called_once()


"""Verify the real debugging workshop; apply only its isolated built-in resource."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from runner.api.config import Settings


def main():
    settings=Settings.load()
    base=settings.root/'curriculum/troubleshooting'
    tflint=str(settings.root/'.tools/tflint') if (settings.root/'.tools/tflint').is_file() else shutil.which('tflint')
    if not tflint:raise SystemExit('Use the course container or install the pinned TFLint runtime.')
    env={key:value for key,value in os.environ.items() if key in {'PATH','HOME','LANG','LC_ALL','TMPDIR','SSL_CERT_FILE','SSL_CERT_DIR'}}
    env.update(TF_IN_AUTOMATION='1',TF_INPUT='0',AWS_EC2_METADATA_DISABLED='true')
    checks=[]
    with tempfile.TemporaryDirectory(prefix='tfprep-debugging-') as temporary:
        directory=Path(temporary)/'repository'
        shutil.copytree(base/'repository',directory,ignore=shutil.ignore_patterns('.terraform','*.tfstate*','tfplan*'))
        def command(name,args,expected=0,where=None):
            result=subprocess.run(args,cwd=where or directory,env=env,capture_output=True,text=True,timeout=90)
            if result.returncode!=expected:
                raise AssertionError(f'{name}: expected exit {expected}, got {result.returncode}\n{result.stdout}{result.stderr}')
            checks.append({'check':name,'exit_code':result.returncode,'passed':True})
            return result
        def tf(name,*args,expected=0,where=None):return command(name,[settings.terraform,*args],expected,where)
        tf('starter_formatting_detected','fmt','-check','-recursive',expected=3)
        tf('formatting_repaired','fmt','-recursive')
        tf('initialize_builtin_provider','init','-backend=false','-input=false')
        invalid=tf('invalid_module_interface_detected','validate','-json',expected=1)
        assert any(item['summary']=='Unsupported attribute' for item in json.loads(invalid.stdout)['diagnostics'])
        main_file=directory/'main.tf'
        main_file.write_text(main_file.read_text().replace('module.service.internal_id','module.service.id'))
        tf('module_interface_repaired','validate','-json')
        lint_args=[tflint,'--recursive','--format=json','--config='+str(directory/'.tflint.hcl')]
        lint=command('missing_explicit_type_detected',lint_args,expected=2)
        issues=json.loads(lint.stdout)['issues']
        assert issues and all(issue['rule']['name']=='terraform_typed_variables' for issue in issues),lint.stdout
        main_file.write_text(main_file.read_text().replace('variable "replicas" {','variable "replicas" {\n  type = number'))
        tf('format_explicit_type','fmt','-recursive')
        command('lint_repaired',lint_args)
        invalid=tf('invalid_replica_default_detected','plan','-input=false','-no-color','-detailed-exitcode',expected=1)
        assert 'replicas must be a positive whole number' in invalid.stdout+invalid.stderr
        main_file.write_text(re.sub(r'(default\s*=\s*)0\b',lambda match:match.group(1)+'2',main_file.read_text()))
        tf('format_final_repair','fmt','-recursive')
        tf('final_format_check','fmt','-check','-recursive')
        tf('final_validate','validate','-json')
        command('final_lint',lint_args)
        tf('review_local_creation','plan','-input=false','-no-color','-detailed-exitcode','-out=tfplan',expected=2)
        plan=json.loads(tf('inspect_plan','show','-json','tfplan').stdout)
        changes=[item for item in plan['resource_changes'] if item.get('mode')=='managed']
        assert len(changes)==1 and changes[0]['type']=='terraform_data' and changes[0]['change']['actions']==['create']
        tf('apply_reviewed_local_plan','apply','-input=false','-no-color','tfplan')
        tf('idempotency_after_repair','plan','-input=false','-no-color','-detailed-exitcode')
        tf('destroy_local_fixture','destroy','-input=false','-auto-approve','-no-color')
        assert not tf('empty_state_after_cleanup','state','list').stdout.strip()
        # Keep the supplied repair aligned with the behavior just proved.
        reference=Path(temporary)/'solution'
        shutil.copytree(base/'solution',reference,ignore=shutil.ignore_patterns('.terraform','*.tfstate*','tfplan*'))
        tf('reference_format','fmt','-check','-recursive',where=reference)
        tf('reference_init','init','-backend=false','-input=false',where=reference)
        tf('reference_validate','validate','-json',where=reference)
        command('reference_lint',[tflint,'--recursive','--config='+str(reference/'.tflint.hcl')],where=reference)
    report={'terraform':'1.12.2','cloud_resources_created':0,'aws_credentials_required':False,
        'temporary_workspace_removed':True,'passed':True,'checks':checks}
    output=settings.root/'docs/evidence/troubleshooting-workshop.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()

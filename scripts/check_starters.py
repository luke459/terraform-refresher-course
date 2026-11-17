"""Verify each starter's intentional teaching failure without applying to AWS."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from unittest.mock import Mock

from runner.api.config import Settings
from runner.api.content import Content
from runner.api.validation import LabValidator
from runner.api.terraform import parsed_hcl,select_nodes


def main():
    settings=Settings.load();content=Content(settings.root)
    validator=LabValidator(settings,Mock(),content,None,Mock())
    report=[]
    for domain in content.domains():
        did=domain['id'];source=content.directory(did)/'starter'
        record={'domain_id':did,'declared_failures':domain['expected_starter_failures']}
        failures=[]
        for check in content.validator(did).checks:
            if check.type=='hcl_ast':
                try:validator.run_check(check,{},source,{},{})
                except ValueError as exc:failures.append({'check':check.id,'message':str(exc)})
        record['hcl_failures']=failures
        if did in {'01','02','06','08'}:
            assert failures,f'Domain {did} must reject its incomplete HCL'
        if did in {'03','05','07'}:
            with tempfile.TemporaryDirectory(prefix='tfprep-starter-') as temporary:
                directory=Path(temporary)/'workspace'
                shutil.copytree(source,directory,ignore=shutil.ignore_patterns('.terraform','*.tfstate*','tfplan*'))
                def run(*args):
                    return subprocess.run([settings.terraform,*args],cwd=directory,capture_output=True,text=True,timeout=120)
                if did=='03':
                    record['format_exit']=run('fmt','-check','-recursive').returncode
                    assert record['format_exit']==3,'The formatting defect must be visible before fmt'
                    assert run('fmt','-recursive').returncode==0
                init_args=['init','-backend=false','-input=false','-lockfile=readonly']
                cache=settings.state/'plugin-cache'
                if cache.is_dir():init_args.append('-plugin-dir='+str(cache))
                initialized=run(*init_args)
                validated=run('validate','-no-color') if initialized.returncode==0 else initialized
                if did in {'05','07'} and initialized.returncode==0:
                    # Validate treats module instances as unknown. Console resolves
                    # the known instance/output shape and rejects this real expression.
                    expression=select_nodes(parsed_hcl(directory),'resource.aws_ssm_parameter.summary.value' if did=='05' else 'import.to')[0]
                    if expression.startswith('${'):expression=expression[2:-1]
                    validated=subprocess.run([settings.terraform,'console','-no-color','-var=account_id=123456789012','-var=attempt_id=0123456789abcdef'],cwd=directory,input=expression+'\n',capture_output=True,text=True,timeout=60)
                message=validated.stdout+validated.stderr
                expected={'03':'CIDR','05':'Unsupported attribute','07':'undeclared resource'}[did]
                assert validated.returncode!=0 and expected.lower() in message.lower(),f'Domain {did} failed for an unexpected reason: {message}'
                record['expected_static_error']=expected
        if did=='04':
            # The input-dependent precondition is evaluated during plan, not validate.
            # Read its independent real-cloud negative test instead of claiming an offline pass.
            records=[json.loads(p.read_text()) for p in (settings.root/'docs/evidence').glob('live-domain04-*.json')]
            record['live_contract_negative_regions']=sorted({r['region'] for r in records if r.get('negative_contract_rejected') and r.get('complete')})
            record['offline_scope']='Input-dependent rejection requires the separate live negative-contract test.'
        report.append(record)
        print('Domain',did,'expected starter behavior verified' if did!='04' or record['live_contract_negative_regions'] else 'offline checks complete; live negative contract test is not included',flush=True)
    output=settings.root/'docs/evidence/starter-checks.json'
    output.parent.mkdir(exist_ok=True,parents=True);output.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()

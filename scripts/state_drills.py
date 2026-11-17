"""Exercise state inspection/mv/rm on an isolated built-in resource, without AWS."""
import json
from pathlib import Path
import subprocess
import tempfile

from runner.api.config import Settings


def main():
    settings=Settings.load()
    report={'terraform':'1.12.2','cloud_resources_created':0,'commands':[]}
    with tempfile.TemporaryDirectory(prefix='tfprep-state-drills-') as temporary:
        directory=Path(temporary)
        config=directory/'main.tf'
        config.write_text('terraform { required_version = "= 1.12.2" }\nresource "terraform_data" "legacy" { input = "disposable-local-example" }\n')
        def run(*args,accepted=(0,)):
            result=subprocess.run([settings.terraform,*args],cwd=directory,capture_output=True,text=True,timeout=60)
            report['commands'].append({'args':list(args),'exit_code':result.returncode})
            if result.returncode not in accepted:
                raise RuntimeError(result.stdout+result.stderr)
            return result.stdout
        run('init','-input=false')
        run('apply','-input=false','-auto-approve')
        assert run('state','list').strip()=='terraform_data.legacy'
        assert 'disposable-local-example' in run('state','show','terraform_data.legacy')
        before=json.loads(run('state','pull'))
        original=before['resources'][0]['instances'][0]['attributes']['id']
        run('state','mv','terraform_data.legacy','terraform_data.renamed')
        config.write_text(config.read_text().replace('"legacy"','"renamed"'))
        renamed=json.loads(run('state','pull'))
        assert renamed['resources'][0]['instances'][0]['attributes']['id']==original
        run('plan','-input=false','-detailed-exitcode')
        run('state','rm','terraform_data.renamed')
        assert not json.loads(run('state','pull'))['resources']
        assert run('state','list').strip()==''
        run('plan','-input=false','-detailed-exitcode',accepted=(2,))
        config.write_text('terraform { required_version = "= 1.12.2" }\n')
        run('destroy','-input=false','-auto-approve')
        report.update(mv_preserves_identity=True,rm_forgets_association=True,configuration_after_rm_proposes_creation=True,temporary_workspace_removed=True)
    output=settings.root/'docs/evidence/state-drills.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()

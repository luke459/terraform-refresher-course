"""Validate reference HCL without applying or requiring cloud credentials."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from runner.api.config import Settings

settings=Settings.load()
root=settings.root
env=os.environ.copy()
plugin_cache=settings.state/'plugin-cache'
directories=[root/f'curriculum/domain-{n:02}/solution' for n in range(1,9)]+[root/'curriculum/domain-06/bootstrap']
report=[]
for directory in directories:
    record={'directory':str(directory.relative_to(root)),'checks':{}}
    commands=[('format',[settings.terraform,'fmt','-check','-recursive'])]
    init=[settings.terraform,'init','-backend=false','-input=false','-lockfile=readonly']
    if plugin_cache.is_dir():
        init.append('-plugin-dir='+str(plugin_cache))
    commands += [('init',init),('validate',[settings.terraform,'validate','-no-color'])]
    tflint=str(root/'.tools/tflint') if (root/'.tools/tflint').is_file() else shutil.which('tflint')
    if not tflint:
        raise SystemExit('TFLint is required for the static gate. Use the pinned Docker runtime or install the frozen toolchain.')
    if tflint:
        env['TFLINT_PLUGIN_DIR']=os.environ.get('TFLINT_PLUGIN_DIR',str(root/'.state/tflint/plugins')) if (root/'.state/tflint/plugins').is_dir() else os.environ.get('TFLINT_PLUGIN_DIR','/root/.tflint.d/plugins')
        commands.append(('lint',[tflint,'--config='+str(root/'.tflint.hcl'),'--format=compact']))
    for name,command in commands:
        result=subprocess.run(command,cwd=directory,env=env,capture_output=True,text=True,timeout=180)
        record['checks'][name]={'passed':result.returncode==0,'output':(result.stdout+result.stderr).strip()}
        print(str(directory.relative_to(root)),name,'PASS' if result.returncode==0 else result.stdout+result.stderr,flush=True)
        if result.returncode:
            break
    report.append(record)
output=root/'docs/evidence/terraform-static.json';output.parent.mkdir(exist_ok=True,parents=True)
output.write_text(json.dumps(report,indent=2)+'\n')
if any(not check['passed'] for item in report for check in item['checks'].values()):
    sys.exit(1)

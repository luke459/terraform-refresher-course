"""Boot a disposable credential-free image, check tools and persisted progress."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import subprocess
import time
import urllib.request
import uuid


def docker(*args):
    return subprocess.check_output(['docker',*args],text=True).strip()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--image',default='tfprep:local')
    parser.add_argument('--platform',default=None)
    args=parser.parse_args()
    name='tfprep-smoke-'+uuid.uuid4().hex[:10]
    volume=name+'-state'
    report={'image':args.image,'platform':args.platform,'checked_at':datetime.now(timezone.utc).isoformat(),
        'image_id':docker('image','inspect','--format','{{.Id}}',args.image)}
    command=['run','-d','--name',name,'-p','127.0.0.1::8080','--mount',f'type=volume,source={volume},target=/var/lib/tfprep']
    if args.platform:command+=['--platform',args.platform]
    command.append(args.image)
    started=time.monotonic()
    try:
        docker(*command)
        port=docker('port',name,'8080/tcp').split(':')[-1]
        base=f'http://127.0.0.1:{port}/api'
        def request(path,data=None):
            req=urllib.request.Request(base+path,data=json.dumps(data).encode() if data is not None else None,
                headers={'Content-Type':'application/json','X-Tfprep':'1'})
            with urllib.request.urlopen(req,timeout=3) as response:return json.load(response)
        deadline=time.monotonic()+30
        while True:
            try:
                assert request('/health')['status']=='ok';break
            except Exception:
                if time.monotonic()>deadline:raise
                time.sleep(.15)
        report['warm_start_seconds']=round(time.monotonic()-started,2)
        assert report['warm_start_seconds']<15
        assert len(request('/domains'))==8
        assert request('/connection')['connected'] is False
        terraform=json.loads(docker('exec',name,'terraform','version','-json'))
        assert terraform['terraform_version']=='1.12.2'
        report['terraform']=terraform
        report['aws_cli']=docker('exec',name,'aws','--version')
        report['tflint']=docker('exec',name,'tflint','--version')
        request('/domains/01/checkpoints',{'question_id':'cp01-1','selected':['a']})
        docker('restart',name)
        port=docker('port',name,'8080/tcp').split(':')[-1]
        base=f'http://127.0.0.1:{port}/api'
        deadline=time.monotonic()+30
        while True:
            try:
                progress=request('/progress')
                assert progress['domains'][0]['checkpoints'][0]['question_id']=='cp01-1';break
            except Exception:
                if time.monotonic()>deadline:raise
                time.sleep(.2)
        report['progress_survives_restart']=True
        report['credential_free_content']=True
        print(json.dumps(report,indent=2))
        path=Path(__file__).resolve().parents[1]/'docs/evidence'/f"image-smoke-{terraform['platform']}.json"
        path.parent.mkdir(exist_ok=True,parents=True);path.write_text(json.dumps(report,indent=2)+'\n')
    except BaseException:
        print('Container state:',docker('inspect','--format','{{json .State}}',name))
        print(docker('logs','--tail','60',name))
        raise
    finally:
        subprocess.run(['docker','rm','-f',name],capture_output=True)
        subprocess.run(['docker','volume','rm',volume],capture_output=True)


if __name__=='__main__':main()

"""Read-only cloud absence audit for known course attempts, never account-wide deletion."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path

from runner.api.config import Settings
from runner.api.credentials import Credentials
from runner.api.db import Database
from runner.api.models import AWSConnection
from runner.api.resources import ResourceInventory


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--profile',required=True)
    parser.add_argument('--state',action='append',required=True,help='Known verification database directory; repeat for isolated runners')
    args=parser.parse_args()
    report={'checked_at':datetime.now(timezone.utc).isoformat(),'profile':args.profile,'scope':'Exact known course attempts only','attempts':[]}
    for path in args.state:
        directory=Path(path).resolve()
        if not (directory/'course.sqlite3').is_file():raise ValueError('Verification state database does not exist')
        db=Database(directory);credentials=Credentials(db)
        try:
            identity=credentials.connect(AWSConnection(mode='profile',profile=args.profile))
            report['account']=identity['account']
            inventory=ResourceInventory(db,credentials)
            if db.one("SELECT id FROM jobs WHERE status IN ('queued','running')"):
                raise ValueError('Wait for the active verification job before auditing absence')
            for attempt in db.all('SELECT * FROM attempts ORDER BY created'):
                credentials.verify(attempt['account'])
                discovered=inventory.reconcile(attempt)
                remaining=inventory.absence(attempt)
                report['attempts'].append({'attempt_id':attempt['id'],'domain_id':attempt['domain_id'],'region':attempt['region'],
                    'recorded_status':attempt['status'],'inventory_count':len(inventory.rows(attempt['id'])),'remaining_cloud':remaining,**discovered})
        finally:credentials.disconnect()
    report['passed']=bool(report['attempts']) and all(not item['remaining_cloud'] for item in report['attempts'])
    output=Settings.load().root/'docs/evidence/final-cleanup.json'
    output.parent.mkdir(exist_ok=True,parents=True)
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'account':report.get('account'),'attempts_checked':len(report['attempts']),'all_owned_resources_absent':report['passed']},indent=2))
    if not report['passed']:raise SystemExit('Owned cloud resources still require cleanup; see the evidence report')


if __name__=='__main__':main()

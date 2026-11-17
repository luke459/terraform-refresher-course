"""Recovery client; defaults to preview and delegates ownership checks to the runner."""
import argparse
from runner.cli.main import follow,request

parser=argparse.ArgumentParser(description='Preview or delete only an exact tfprep attempt inventory.')
parser.add_argument('--attempt',required=True,help='Exact attempt ID; never the shared Project tag')
parser.add_argument('--execute',action='store_true',help='Delete matching owned resources after checking their current identity')
args=parser.parse_args()
follow(request('POST',f'/attempts/{args.attempt}/reaper'+('?execute=true' if args.execute else '')))

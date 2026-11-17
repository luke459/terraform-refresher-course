"""Exercise the first vertical slice against the explicitly selected AWS profile."""
import argparse
import json
from pathlib import Path
import time
import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--region", default="us-east-1", choices=["eu-west-1", "us-east-1", "eu-west-2"])
    args = parser.parse_args()
    client = httpx.Client(base_url="http://127.0.0.1:8080/api", headers={"X-Tfprep":"1"}, timeout=40)
    def request(method, path, data=None):
        response = client.request(method, path, json=data)
        if response.status_code >= 400:
            raise RuntimeError(f"{path}: {response.text}")
        return response.json()
    identity = request("POST", "/connection", {"mode":"profile","profile":args.profile,"region":args.region})
    print("Verified account", identity["account"], "in", args.region, flush=True)
    attempt = request("POST", "/attempts", {"domain_id":"01"})
    aid = attempt["id"]
    print("Attempt", aid, flush=True)
    evidence = {"attempt_id":aid,"account":identity["account"],"region":args.region,"terraform":"1.12.2","jobs":[]}
    def job(operation, endpoint="run", expect_success=True):
        result = request("POST", f"/attempts/{aid}/{endpoint}", {"operation":operation} if endpoint=="run" else None)
        deadline = time.monotonic()+900
        while result["status"] in {"queued","running"} and time.monotonic()<deadline:
            time.sleep(1)
            result = request("GET", "/jobs/"+result["id"])
        print(operation or endpoint, result["status"], result["exit_code"], flush=True)
        evidence["jobs"].append({key:result[key] for key in ["id","operation","status","exit_code","config_hash","plan_hash","result"]})
        if expect_success and result["status"] != "succeeded":
            raise RuntimeError(result["log"])
        return result
    try:
        for op in ["init","fmt","validate","plan","apply","plan"]:
            job(op)
        negative = job("", "validate", expect_success=False)
        assert negative["status"]=="failed" and negative["result"]["apply_verified"] is False
        evidence["negative_starter_checks"] = negative["result"]["checks"]
        for path in (ROOT/"curriculum/domain-01/solution").glob("*.tf"):
            request("PUT",f"/attempts/{aid}/files",{"path":path.name,"content":path.read_text()})
        for op in ["plan","apply","plan"]:
            job(op)
        graded = job("", "validate")
        assert graded["result"]["percentage"]==50
        job("destroy")
        cleanup=job("", "teardown-check")
        assert cleanup["result"]["complete"]
        evidence["complete"] = True
    finally:
        if not evidence.get('complete'):
            try:
                job('destroy')
                cleanup=job('', 'teardown-check', expect_success=False)
                evidence['failure_cleanup']=cleanup['result']
            except Exception as cleanup_error:
                evidence['cleanup_attention_required']=str(cleanup_error)
        destination=ROOT/"docs/evidence"
        destination.mkdir(exist_ok=True,parents=True)
        (destination/f"live-domain01-{args.region}-{aid}.json").write_text(json.dumps(evidence,indent=2)+"\n")
        print("Evidence saved for",aid,flush=True)


if __name__=="__main__":
    main()

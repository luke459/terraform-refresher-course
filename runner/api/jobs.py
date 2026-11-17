from concurrent.futures import ThreadPoolExecutor
import fcntl
import hashlib
import json
import os
from pathlib import Path
import queue
import shutil
import signal
import sqlite3
import subprocess
import threading
import time
import uuid
from .terraform import config_hash, state_resources, terraform_json


class Jobs:
    def __init__(self, settings, db, credentials, content, inventory):
        self.settings, self.db, self.credentials, self.content, self.inventory = settings, db, credentials, content, inventory
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tfprep")
        self.canceled = set()
        self.guard = threading.RLock()
        self.lockfile = None
        self.validator = None
        self.empty_migrations = {}

    def start(self):
        self.lockfile = (self.settings.state / "runner.lock").open("a")
        try:
            fcntl.flock(self.lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another tfprep server already owns this state directory") from None
        self.db.execute("UPDATE jobs SET status='interrupted',finished=?,log=log || ? WHERE status IN ('running','queued')",
            (time.time(), "\nServer restarted. Inspect state before retrying this operation.\n"))

    def close(self):
        for row in self.db.all("SELECT id FROM jobs WHERE status IN ('running','queued')"):
            self.canceled.add(row["id"])
        self.pool.shutdown(wait=True, cancel_futures=True)
        if self.lockfile:
            fcntl.flock(self.lockfile, fcntl.LOCK_UN)
            self.lockfile.close()

    def attempt(self, attempt_id):
        attempt = self.db.one("SELECT * FROM attempts WHERE id=?", (attempt_id,))
        if not attempt:
            raise ValueError("Lab attempt not found")
        return attempt

    def directory(self, attempt):
        path = self.settings.workspaces / f"{attempt['domain_id']}-{attempt['id']}"
        if path.is_symlink() or path.resolve().parent != self.settings.workspaces.resolve():
            raise ValueError("Invalid workspace path")
        return path

    def start_attempt(self, domain_id):
        self.credentials.verify()
        attempt_id = uuid.uuid4().hex[:16]
        identity = self.credentials.status()
        self.db.execute("INSERT INTO attempts(id,domain_id,account,region,created) VALUES (?,?,?,?,?)",
            (attempt_id, domain_id, identity["account"], identity["region"], time.time()))
        attempt = self.attempt(attempt_id)
        directory = self.directory(attempt)
        self.settings.workspaces.mkdir(exist_ok=True, parents=True, mode=0o700)
        shutil.copytree(self.content.directory(domain_id) / "starter", directory,
            ignore=shutil.ignore_patterns('.terraform','*.tfstate*','tfplan*','tf-debug.log','__pycache__'))
        directory.chmod(0o700)
        variables = {"attempt_id": attempt_id, "account_id": identity["account"], "region": identity["region"]}
        (directory / "tfprep.auto.tfvars.json").write_text(json.dumps(variables, indent=2) + "\n")
        if (directory / "bootstrap").is_dir():
            (directory / "bootstrap" / "tfprep.auto.tfvars.json").write_text(json.dumps(variables, indent=2) + "\n")
        for path in directory.rglob("*"):
            if path.is_file():
                path.chmod(0o600)
        return self.detail(attempt_id)

    def detail(self, attempt_id):
        attempt = self.attempt(attempt_id)
        directory = self.directory(attempt)
        current = config_hash(directory)
        if attempt["verified_hash"] and attempt["verified_hash"] != current and attempt["status"] not in {"complete","cleanup_pending"}:
            self.db.execute("UPDATE attempts SET status='active',verified_hash=NULL WHERE id=?", (attempt_id,))
            attempt = self.attempt(attempt_id)
        return {**attempt, "workspace": str(directory), "results": json.loads(attempt["results"]),
                "baseline": json.loads(attempt["baseline"]), "jobs": self.db.all("SELECT * FROM jobs WHERE attempt_id=? ORDER BY created DESC", (attempt_id,)),
                "resources": self.inventory.rows(attempt_id), "current_hash": current,
                "percentage": 100 if attempt["status"] == "complete" else 50 if attempt['verified_hash'] and attempt["status"] in {"apply_verified", "cleanup_pending"} else 0}

    def submit(self, attempt_id, operation, params=None):
        with self.guard:
            attempt = self.attempt(attempt_id)
            self.credentials.require(attempt["account"])
            if attempt["status"] == "complete":
                raise ValueError("This attempt is complete. Start a new attempt to run more infrastructure operations.")
            job_id = uuid.uuid4().hex
            try:
                self.db.execute("INSERT INTO jobs(id,attempt_id,operation,params,status,created) VALUES (?,?,?,?,?,?)",
                    (job_id, attempt_id, operation, json.dumps(params or {}), "queued", time.time()))
            except sqlite3.IntegrityError:
                raise ValueError("An operation is already queued or running for this workspace") from None
            if operation in {'apply','bootstrap-apply','setup-import','simulate-drift'}:
                self.db.execute("UPDATE attempts SET verified_hash=NULL,status='active' WHERE id=?",(attempt_id,))
            self.pool.submit(self.execute, job_id)
            return self.get(job_id)

    def get(self, job_id):
        row = self.db.one("SELECT * FROM jobs WHERE id=?", (job_id,))
        if not row:
            raise ValueError("Job not found")
        return {**row, "params": json.loads(row["params"]), "result": json.loads(row["result"]) if row["result"] else None}

    def cancel(self, job_id):
        self.get(job_id)
        self.canceled.add(job_id)
        return {"cancel_requested": True}

    def log(self, job_id, message):
        message = self.credentials.redact(message)
        self.db.execute("UPDATE jobs SET log=substr(log || ?, -200000) WHERE id=?", (message, job_id))

    def execute(self, job_id):
        job = self.get(job_id)
        attempt = self.attempt(job["attempt_id"])
        directory = self.directory(attempt)
        self.db.execute("UPDATE jobs SET status='running',started=?,config_hash=? WHERE id=?", (time.time(), config_hash(directory), job_id))
        exit_code, result, status = None, None, "failed"
        try:
            if job_id in self.canceled:
                raise InterruptedError("Job canceled before execution")
            self.credentials.verify(attempt["account"])
            env = self.credentials.environment(attempt["account"])
            cache = self.settings.state / "plugin-cache"
            cache.mkdir(exist_ok=True, mode=0o700)
            env["TF_PLUGIN_CACHE_DIR"] = str(cache)
            operation = job["operation"]
            if operation == "validate-lab":
                result = self.validator.validate(attempt, directory, env)
                exit_code = 0 if all(check["status"] == "pass" for check in result["checks"]) else 1
            elif operation == "teardown-check":
                result = self.validator.teardown(attempt, directory, env)
                exit_code = 0 if result["complete"] else 1
            elif operation in {"reaper-preview", "reaper-execute"}:
                result = self.inventory.reap(attempt, execute=operation == "reaper-execute")
                exit_code = 0
            elif operation in {"setup-import", "capture-baseline", "simulate-drift", "reconcile-locks"}:
                from .lab_actions import lab_action
                result = lab_action(operation, attempt, directory, self)
                exit_code = 0
            else:
                working_dir, args = self.command(job, attempt, directory)
                if job["params"].get("debug"):
                    # Capture debug output through the sanitizer rather than letting Terraform write raw logs.
                    env['TF_LOG_PROVIDER']='DEBUG'
                self.log(job_id, "$ terraform " + " ".join(args) + "\n")
                exit_code = self.run_process(job_id, [self.settings.terraform, *args], working_dir, env)
                if operation=='migrate-local' and exit_code==0:
                    result=self.finalize_empty_migration(attempt,directory)
                if operation == 'generate-config' and (directory/'generated.tf').is_file():
                    result = {'generated_config':True,'sha256':hashlib.sha256((directory/'generated.tf').read_bytes()).hexdigest(),
                              'message':'Review and refine generated configuration even if planning reported an error.'}
                if operation in {"plan", "bootstrap-plan"} and exit_code in {0, 2}:
                    plan_file = working_dir / "tfplan"
                    if plan_file.exists():
                        self.db.execute("UPDATE jobs SET plan_hash=? WHERE id=?", (hashlib.sha256(plan_file.read_bytes()).hexdigest(), job_id))
                if operation in {"apply", "destroy", "bootstrap-apply", "bootstrap-destroy"}:
                    try:
                        state = terraform_json(self.settings, working_dir, ["show", "-json"], env)
                        self.inventory.capture(attempt, state, prefix="bootstrap." if operation.startswith("bootstrap-") else "")
                    except Exception as exc:
                        self.log(job_id, f"\nInventory needs attention: {type(exc).__name__}. Run validation before cleanup.\n")
                        if exit_code == 0 and operation in {"apply", "bootstrap-apply"}:
                            raise ValueError("Apply finished but inventory capture failed. Inspect state before continuing.") from None
                if operation == "destroy" and exit_code == 0:
                    self.db.execute("UPDATE attempts SET status='cleanup_pending' WHERE id=?", (attempt["id"],))
            accepted = {0, 2} if operation in {"plan", "bootstrap-plan"} else {0}
            status = "succeeded" if exit_code in accepted else "failed"
        except InterruptedError as exc:
            status = "canceled"
            self.log(job_id, str(exc) + "\n")
        except Exception as exc:
            # AWS error strings may contain request parameters. Expose only the code for SDK failures.
            from botocore.exceptions import BotoCoreError, ClientError
            if isinstance(exc, ClientError):
                message = "AWS operation failed: " + exc.response.get("Error", {}).get("Code", "Unknown")
            elif isinstance(exc, BotoCoreError):
                message = "AWS credentials or network unavailable; reconnect and retry."
            else:
                message = str(exc) if isinstance(exc, (ValueError, FileNotFoundError)) else f"Operation failed ({type(exc).__name__})"
            self.log(job_id, message + "\n")
        finally:
            self.empty_migrations.pop(attempt['id'],None)
            if job['operation'] in {'apply','bootstrap-apply','destroy','bootstrap-destroy'} and 'env' in locals():
                try:
                    working=directory/'bootstrap' if job['operation'].startswith('bootstrap-') else directory
                    state=terraform_json(self.settings,working,['show','-json'],env)
                    self.inventory.capture(attempt,state,prefix='bootstrap.' if job['operation'].startswith('bootstrap-') else '')
                except Exception:
                    self.log(job_id,'\nPost-operation inventory inspection could not finish; use recovery inventory before abandoning the attempt.\n')
            if job["operation"] in {"fmt", "provider-lock"}:
                self.db.execute("UPDATE jobs SET config_hash=? WHERE id=?", (config_hash(directory), job_id))
            self.db.execute("UPDATE jobs SET status=?,finished=?,exit_code=?,result=? WHERE id=?",
                (status, time.time(), exit_code, json.dumps(result) if result is not None else None, job_id))
            self.canceled.discard(job_id)

    def command(self, job, attempt, directory):
        operation, params = job["operation"], job["params"]
        working = directory / "bootstrap" if operation.startswith("bootstrap-") else directory
        op = operation.removeprefix("bootstrap-")
        commands = {
            "init": ["init", "-input=false", "-lockfile=readonly"],
            "fmt": ["fmt", "-recursive"],
            "validate": ["validate", "-no-color"],
            "plan": ["plan", "-input=false", "-no-color", "-detailed-exitcode", "-out=tfplan", "-lock-timeout=10s"],
            "apply": ["apply", "-input=false", "-no-color", "tfplan"],
            "destroy": ["destroy", "-input=false", "-auto-approve", "-no-color", "-lock-timeout=10s"],
            "state-list": ["state", "list"],
            "output": ["output", "-no-color"],
            "provider-lock": ["providers", "lock", "-platform=linux_amd64", "-platform=linux_arm64", "-platform=darwin_arm64"],
            "generate-config": ["plan", "-input=false", "-no-color", "-generate-config-out=generated.tf", "-lock-timeout=10s"],
        }
        if operation in {"migrate-remote", "migrate-local"}:
            from .lab_actions import migrate_backend
            return migrate_backend(operation, attempt, directory, self)
        if op not in commands:
            raise ValueError("Unsupported course operation")
        args = commands[op].copy()
        if op == 'generate-config' and (working/'generated.tf').exists():
            raise ValueError('generated.tf already exists. Review/refine it rather than overwriting it with another generation.')
        if params.get("replace"):
            if op != "plan":
                raise ValueError("Replacement is supported only when creating a plan")
            args.append("-replace=" + params["replace"])
        if params.get("refresh_only"):
            if op != "plan":
                raise ValueError("Refresh-only is supported only when creating a plan")
            args.append("-refresh-only")
        if op == "apply":
            previous = self.db.one("SELECT * FROM jobs WHERE attempt_id=? AND operation=? AND status='succeeded' ORDER BY created DESC LIMIT 1",
                (attempt["id"], "bootstrap-plan" if operation.startswith("bootstrap-") else "plan"))
            plan_file = working / "tfplan"
            if not previous or previous["config_hash"] != config_hash(directory) or not plan_file.is_file():
                raise ValueError("Create a fresh saved plan for this configuration before applying")
            if hashlib.sha256(plan_file.read_bytes()).hexdigest() != previous["plan_hash"]:
                raise ValueError("Saved plan changed; generate and review a new plan")
            plan=terraform_json(self.settings,working,['show','-json','tfplan'],self.credentials.environment(attempt['account']))
            self.guard_plan(attempt,plan)
        return working, args

    def guard_plan(self,attempt,plan):
        allowed=set(self.content.domain(attempt['domain_id'])['resource_types'])
        changes=[r for r in plan.get('resource_changes',[]) if r.get('mode')=='managed']
        if len(changes)>32:
            raise ValueError('The course limits each plan to 32 managed resource instances')
        required={'Project':'tf-004-prep','ManagedBy':'terraform','Lab':attempt['domain_id'],'Attempt':attempt['id']}
        from .resources import PRIMARY
        for resource in changes:
            if resource['type'] not in allowed:
                raise ValueError(f"Resource type {resource['type']} is outside this lab's cost/cleanup allowlist")
            after=resource.get('change',{}).get('after')
            if after is not None and resource['type'] in PRIMARY:
                tags=after.get('tags_all') or after.get('tags') or {}
                if any(tags.get(key)!=value for key,value in required.items()):
                    raise ValueError('Every taggable planned object must keep the exact course attempt ownership tags')

    def finalize_empty_migration(self,attempt,directory):
        snapshot=self.empty_migrations.get(attempt['id'])
        if not snapshot or snapshot.get('version')!=4 or not snapshot.get('lineage') or any(r.get('mode')=='managed' for r in snapshot.get('resources',[])):
            raise ValueError('A verified empty source snapshot is required to finish this migration')
        backend=json.loads((directory/'.terraform/terraform.tfstate').read_text()).get('backend',{})
        if backend.get('type')!='local':
            raise ValueError('The local backend has not initialized successfully')
        destination=directory/'terraform.tfstate'
        if destination.is_file() and destination.read_text().strip():
            current=json.loads(destination.read_text())
            if current.get('lineage') and current['lineage']!=snapshot['lineage']:
                raise ValueError('The destination contains a different state lineage; inspect it before continuing')
        # Core can omit copying an empty snapshot. Preserve the actual, already-read source
        # rather than interpreting a missing local file as proof of empty state.
        temporary=directory/'.tfprep-state-migration'
        temporary.write_text(json.dumps(snapshot,indent=2)+'\n')
        temporary.chmod(0o600)
        temporary.replace(destination)
        return {'local_empty_snapshot_preserved':True,'lineage':snapshot['lineage'],'serial':snapshot.get('serial')}

    def run_process(self, job_id, command, directory, env, timeout=900):
        if not directory.is_dir():
            raise ValueError("This lab does not have a bootstrap workspace")
        proc = subprocess.Popen(command, cwd=directory, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
        lines = queue.Queue()

        def reader():
            for line in iter(proc.stdout.readline, b""):
                lines.put(line.decode("utf-8", errors="replace"))
            proc.stdout.close()

        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        deadline = time.monotonic() + timeout
        debug_handle=None
        if env.get('TF_LOG_PROVIDER'):
            debug_path=directory/'tf-debug.log'
            debug_handle=debug_path.open('w')
            debug_path.chmod(0o600)
        try:
            while proc.poll() is None or thread.is_alive() or not lines.empty():
                if job_id in self.canceled or time.monotonic() >= deadline:
                    raise InterruptedError("Operation canceled or timed out. Inspect state before retrying.")
                try:
                    line = lines.get(timeout=0.15)
                    if debug_handle:
                        debug_handle.write(self.credentials.redact(line))
                        debug_handle.flush()
                    self.log(job_id, line)
                except queue.Empty:
                    pass
            return proc.wait()
        finally:
            if debug_handle:
                debug_handle.close()
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
            for path in directory.glob("tf*"):
                if path.is_file():
                    path.chmod(0o600)


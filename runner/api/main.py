from contextlib import asynccontextmanager
import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from urllib.parse import urlparse
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field
from .config import Settings
from .content import Content
from .credentials import ConnectionRequired, Credentials
from .db import Database
from .exams import ExamService
from .jobs import Jobs
from .models import AWSConnection, Answer, Contract, CreateExam, RunOperation, StartAttempt
from .resources import ResourceInventory
from .validation import LabValidator
from runner.regions import SUPPORTED_REGIONS


class FileEdit(Contract):
    path: str
    content: str = Field(max_length=500000)


def create_app(settings=None, credentials_factory=Credentials):
    settings = settings or Settings.load()
    db = Database(settings.state)
    content = Content(settings.root)
    credentials = credentials_factory(db)
    inventory = ResourceInventory(db, credentials)
    jobs = Jobs(settings, db, credentials, content, inventory)
    jobs.validator = LabValidator(settings, db, content, credentials, inventory)
    exams = ExamService(db, content)

    @asynccontextmanager
    async def lifespan(app):
        jobs.start()
        yield
        jobs.close()
        credentials.disconnect()

    app = FastAPI(title="Terraform 004 Refresher", version="0.1.0", lifespan=lifespan)
    app.state.services = {"db": db, "content": content, "credentials": credentials, "jobs": jobs, "exams": exams, "inventory": inventory}

    @app.middleware("http")
    async def local_access(request: Request, call_next):
        host = request.url.hostname
        if host not in {"127.0.0.1", "localhost", "::1", "testserver"}:
            return JSONResponse({"detail": "This app accepts localhost requests only"}, status_code=403)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            allowed = {f"{request.url.scheme}://{request.headers.get('host')}"}
            dev = os.environ.get("TFPREP_DEV_ORIGIN")
            if dev and urlparse(dev).hostname in {"localhost", "127.0.0.1"}:
                allowed.add(dev)
            if (origin and origin not in allowed) or request.headers.get("x-tfprep") != "1":
                return JSONResponse({"detail": "Same-origin course request required"}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        return JSONResponse({"detail": [{"loc": item["loc"], "type": item["type"], "msg": "Invalid field value"} for item in exc.errors()]}, status_code=422)

    @app.exception_handler(ConnectionRequired)
    async def missing_connection(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(ValueError)
    async def invalid_operation(request, exc):
        return JSONResponse({"detail": credentials.redact(str(exc))}, status_code=400)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "terraform_baseline": "1.12.2", "version": "0.1.0"}

    @app.get("/api/connection")
    def connection():
        return credentials.status()

    def idle_credentials():
        if db.one("SELECT id FROM jobs WHERE status IN ('queued','running') LIMIT 1"):
            raise ValueError("Wait for the active lab operation to finish before changing credentials")

    @app.post("/api/connection")
    def connect(payload: AWSConnection):
        with jobs.guard:
            idle_credentials()
            return credentials.connect(payload)

    @app.delete("/api/connection")
    def disconnect():
        with jobs.guard:
            idle_credentials()
            credentials.disconnect()
            return credentials.status()

    @app.post("/api/connection/test")
    def test_connection():
        credentials.verify()
        return credentials.status()

    @app.get("/api/doctor")
    def doctor():
        try:
            result = subprocess.run([settings.terraform, "version", "-json"], capture_output=True, text=True, timeout=10)
            version = json.loads(result.stdout).get("terraform_version") if result.returncode == 0 else None
        except (OSError, ValueError, subprocess.TimeoutExpired):
            version = None
        settings.workspaces.mkdir(exist_ok=True,parents=True,mode=0o700)
        aws=credentials.status()
        permissions=[]
        if aws['connected']:
            try:
                credentials.verify()
                aws['identity_verified']=True
            except ConnectionRequired as exc:
                aws.update(identity_verified=False,error=str(exc))
            if aws.get('identity_verified'):
                from botocore.exceptions import BotoCoreError, ClientError
                probes=[('s3','list_buckets',{},aws['region']),('iam','list_policies',{'Scope':'Local','MaxItems':1},'us-east-1'),
                    ('ec2','describe_vpcs',{'MaxResults':5},aws['region']),('secretsmanager','list_secrets',{'MaxResults':1},aws['region']),
                    ('sns','list_topics',{},aws['region'])]
                probes += [('ssm','describe_parameters',{'MaxResults':5},region) for region in SUPPORTED_REGIONS]
                for service,operation,parameters,region in probes:
                    item={'service':service,'operation':operation,'region':region}
                    try:
                        getattr(credentials.client(service,region),operation)(**parameters)
                        item['status']='pass'
                    except (BotoCoreError,ClientError) as exc:
                        item.update(status='error',message=exc.response.get('Error',{}).get('Code','AWS error') if isinstance(exc,ClientError) else 'credential/network error')
                    permissions.append(item)
        return {"terraform": {"version": version, "correct": version == "1.12.2", "executable": settings.terraform},
                "aws_cli": bool(shutil.which("aws")), "tflint": bool(shutil.which("tflint") or (settings.root/'.tools/tflint').is_file()),
                "state_writable": os.access(settings.state, os.W_OK), "workspaces_writable":os.access(settings.workspaces,os.W_OK),
                "schema_version":db.one('SELECT MAX(version) AS version FROM schema_version')['version'],
                "aws":aws,"read_permission_checks":permissions,
                "permission_scope":"Read-only diagnostics; create/update/delete permissions are checked by actual lab operations."}

    @app.get("/api/domains")
    def domains():
        return content.domains()

    @app.get("/api/domains/{domain_id}")
    def domain(domain_id: str):
        return content.domain(domain_id)

    @app.get("/api/progress")
    def progress():
        domains = []
        for domain in content.domains():
            attempts = db.all("SELECT id,status,created FROM attempts WHERE domain_id=? ORDER BY created DESC", (domain["id"],))
            for attempt in attempts:
                # Revalidate content hashes before presenting cached progress.
                detail = jobs.detail(attempt["id"])
                attempt["status"] = detail["status"]
                attempt["percentage"] = detail["percentage"]
            domains.append({"domain_id": domain["id"], "attempts": attempts, "mastery": exams.mastery(domain["id"]),
                "checkpoints": db.all("SELECT question_id,correct,selected FROM checkpoints WHERE domain_id=?", (domain["id"],))})
        return {"domains": domains, "exams": db.all("SELECT id,mode,created,deadline,submitted,score FROM exams ORDER BY created DESC")}

    @app.post("/api/attempts")
    def start(payload: StartAttempt):
        return jobs.start_attempt(payload.domain_id)

    @app.get("/api/attempts/{attempt_id}")
    def attempt(attempt_id: str):
        return jobs.detail(attempt_id)

    @app.post("/api/attempts/{attempt_id}/run")
    def run(attempt_id: str, payload: RunOperation):
        return jobs.submit(attempt_id, payload.operation, payload.model_dump(exclude={"operation"}))

    @app.post("/api/attempts/{attempt_id}/validate")
    def validate(attempt_id: str):
        return jobs.submit(attempt_id, "validate-lab")

    @app.post("/api/attempts/{attempt_id}/teardown-check")
    def teardown(attempt_id: str):
        return jobs.submit(attempt_id, "teardown-check")

    @app.post("/api/attempts/{attempt_id}/reaper")
    def reaper(attempt_id: str, execute: bool = False):
        return jobs.submit(attempt_id, "reaper-execute" if execute else "reaper-preview")

    @app.post('/api/attempts/{attempt_id}/purge-artifacts')
    def purge_artifacts(attempt_id:str):
        with jobs.guard:
            attempt=jobs.attempt(attempt_id)
            if attempt['status']!='complete' or db.one("SELECT id FROM jobs WHERE attempt_id=? AND status IN ('queued','running')",(attempt_id,)):
                raise ValueError('Private artifacts can be purged only after verified course cleanup')
            directory=jobs.directory(attempt)
            for current in [directory/'terraform.tfstate',directory/'bootstrap/terraform.tfstate']:
                if current.is_file() and not current.is_symlink():
                    state=json.loads(current.read_text())
                    if state.get('resources'):
                        raise ValueError('Current local state contains resources; inspect and clean them before purging')
            removed=0
            for path in directory.rglob('*'):
                if path.is_file() and not path.is_symlink() and (path.name=='tf-debug.log' or path.name.startswith('tfplan') or '.tfstate' in path.name):
                    if path.resolve().is_relative_to(directory.resolve()):
                        path.unlink();removed+=1
            return {'removed_files':removed,'source_and_progress_retained':True}

    def editable_path(attempt_id, relative):
        directory = jobs.directory(jobs.attempt(attempt_id))
        path = directory / relative
        if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()) or any(part.startswith(".") for part in Path(relative).parts):
            raise ValueError("File path must remain inside the attempt workspace")
        if path.suffix not in {".tf", ".hcl", ".md"} or path.name.startswith("tfprep"):
            raise ValueError("Only course configuration files are editable")
        return path

    @app.get("/api/attempts/{attempt_id}/files")
    def files(attempt_id: str):
        directory = jobs.directory(jobs.attempt(attempt_id))
        return [{"path": str(path.relative_to(directory)), "content": path.read_text()} for path in sorted(directory.rglob("*"))
            if path.is_file() and not path.is_symlink() and path.suffix in {".tf", ".hcl", ".md"}
            and not any(part.startswith(".") for part in path.relative_to(directory).parts)
            and path.resolve().is_relative_to(directory.resolve()) and path.stat().st_size < 500000]

    @app.put("/api/attempts/{attempt_id}/files")
    def edit_file(attempt_id: str, payload: FileEdit):
        with jobs.guard:
            if db.one("SELECT id FROM jobs WHERE attempt_id=? AND status IN ('queued','running')", (attempt_id,)):
                raise ValueError("Wait for the workspace operation to finish before editing")
            if jobs.attempt(attempt_id)["status"] == "complete":
                raise ValueError("Start a new attempt to edit a completed lab")
            path = editable_path(attempt_id, payload.path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(payload.content)
            path.chmod(0o600)
            return {"saved": True, "attempt": jobs.detail(attempt_id)}

    @app.get("/api/domains/{domain_id}/solution")
    def solution(domain_id: str):
        directory = content.directory(domain_id) / "solution"
        return [{"path": str(path.relative_to(directory)), "content": path.read_text()} for path in sorted(directory.rglob("*.tf"))]

    @app.get("/api/jobs/{job_id}")
    def job(job_id: str):
        return jobs.get(job_id)

    @app.post("/api/jobs/{job_id}/cancel")
    def cancel(job_id: str):
        return jobs.cancel(job_id)

    @app.get("/api/jobs/{job_id}/events")
    async def events(job_id: str):
        jobs.get(job_id)
        async def stream():
            previous = None
            while True:
                current = jobs.get(job_id)
                serialized = json.dumps(current)
                if serialized != previous:
                    yield f"data: {serialized}\n\n"
                    previous = serialized
                if current["status"] not in {"queued", "running"}:
                    break
                await asyncio.sleep(0.5)
        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.post("/api/domains/{domain_id}/checkpoints")
    def checkpoint(domain_id: str, payload: Answer):
        return exams.checkpoint(domain_id, payload)

    @app.post("/api/exams")
    def create_exam(payload: CreateExam):
        return exams.create(payload)

    @app.get("/api/exams/{exam_id}")
    def exam(exam_id: str):
        return exams.get(exam_id)

    @app.put("/api/exams/{exam_id}/answers")
    def answer(exam_id: str, payload: Answer):
        return exams.answer(exam_id, payload)

    @app.post("/api/exams/{exam_id}/submit")
    def submit_exam(exam_id: str):
        return exams.submit(exam_id)

    dist = settings.root / "runner" / "web" / "dist"
    if (dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}")
    def frontend(path: str):
        if path.startswith("api/"):
            return JSONResponse({"detail": "API route not found"}, status_code=404)
        if not (dist / "index.html").is_file():
            return JSONResponse({"detail": "Build the frontend with make web before starting the course"}, status_code=503)
        return FileResponse(dist / "index.html")

    return app


app = create_app()

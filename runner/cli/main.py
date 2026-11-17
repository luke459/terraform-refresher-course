import json
import time
from urllib.parse import urlparse
import httpx
import typer
from runner.regions import SUPPORTED_REGIONS

app = typer.Typer(help="Terraform Associate 004 course CLI. Start the local server first.", no_args_is_help=True)


def request(method, path, data=None):
    import os
    base = os.environ.get("TFPREP_URL", "http://127.0.0.1:8080")
    if urlparse(base).hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise typer.BadParameter("TFPREP_URL must point to the local course server")
    try:
        response = httpx.request(method, base.rstrip("/") + "/api" + path, json=data, headers={"X-Tfprep":"1"}, timeout=40)
    except httpx.HTTPError:
        typer.echo("The local course server is unavailable. Start it with make serve or docker compose up.", err=True)
        raise typer.Exit(1)
    if response.status_code >= 400:
        typer.echo(str(response.json().get("detail", "Request failed")), err=True)
        raise typer.Exit(1)
    return response.json()


def output(value):
    typer.echo(json.dumps(value, indent=2))


def attempt_for(domain_id, attempt=None):
    if attempt:
        result = request("GET", "/attempts/" + attempt)
        if result["domain_id"] != domain_id:
            raise typer.BadParameter("Attempt does not belong to the requested domain")
        return attempt
    progress = request("GET", "/progress")
    domain = next((item for item in progress["domains"] if item["domain_id"] == domain_id), None)
    if not domain or not domain["attempts"]:
        typer.echo("Start a lab attempt with tfprep start " + domain_id, err=True)
        raise typer.Exit(1)
    return domain["attempts"][0]["id"]


def follow(job):
    offset = 0
    try:
        while True:
            text = job["log"]
            if len(text) > offset:
                typer.echo(text[offset:], nl=False)
                offset = len(text)
            if job["status"] not in {"queued", "running"}:
                break
            time.sleep(0.5)
            job = request("GET", "/jobs/" + job["id"])
    except KeyboardInterrupt:
        request("POST", "/jobs/" + job["id"] + "/cancel")
        typer.echo("Cancellation requested. Inspect state before retrying.", err=True)
        raise typer.Exit(130)
    if job["result"] is not None:
        output(job["result"])
    typer.echo(f"Job {job['id']}: {job['status']}")
    if job["status"] != "succeeded":
        raise typer.Exit(1)
    return job


@app.command()
def setup(profile: str | None = typer.Option(None), region: str = typer.Option("us-east-1"), keys: bool = typer.Option(False, help="Prompt for access keys without putting secrets in shell arguments")):
    """Connect a named AWS CLI profile or memory-only IAM access keys."""
    if region not in SUPPORTED_REGIONS:
        raise typer.BadParameter("Use eu-west-1, us-east-1 or eu-west-2")
    if keys and profile:
        raise typer.BadParameter("Choose a profile or access keys")
    if not keys and not profile:
        mode = typer.prompt("AWS connection method (profile/keys)", default="profile")
        if mode not in {"profile", "keys"}:
            raise typer.BadParameter("Choose profile or keys")
        keys = mode == "keys"
    if keys:
        payload = {"mode":"keys", "region":region,
            "access_key_id":typer.prompt("Access key ID", hide_input=True),
            "secret_access_key":typer.prompt("Secret access key", hide_input=True)}
        token = typer.prompt("Session token (optional)", default="", hide_input=True, show_default=False)
        if token:
            payload["session_token"] = token
    else:
        payload = {"mode":"profile", "profile":profile or typer.prompt("AWS CLI profile name"), "region":region}
    output(request("POST", "/connection", payload))


@app.command()
def disconnect():
    """Clear session credentials without deleting learner work."""
    output(request("DELETE", "/connection"))


@app.command()
def doctor():
    """Inspect runtime and connection status without printing credentials."""
    output(request("GET", "/doctor"))


@app.command()
def start(domain: str):
    """Create a new isolated attempt for domain 01..08."""
    output(request("POST", "/attempts", {"domain_id":domain.zfill(2)}))


@app.command(context_settings={"allow_extra_args": True})
def run(ctx: typer.Context, domain: str, attempt: str | None = typer.Option(None), replace: str | None = typer.Option(None), refresh_only: bool = typer.Option(False), debug: bool = typer.Option(False)):
    """Execute an approved operation, e.g. tfprep run 01 -- plan."""
    if len(ctx.args) != 1:
        raise typer.BadParameter("Supply one operation after --, such as init, plan, apply, or destroy")
    aid = attempt_for(domain.zfill(2), attempt)
    follow(request("POST", f"/attempts/{aid}/run", {"operation":ctx.args[0], "replace":replace, "refresh_only":refresh_only, "debug":debug}))


@app.command()
def validate(domain: str, attempt: str | None = typer.Option(None)):
    """Grade the live AWS challenge."""
    aid = attempt_for(domain.zfill(2), attempt)
    follow(request("POST", f"/attempts/{aid}/validate"))


@app.command("teardown-check")
def teardown_check(domain: str, attempt: str | None = typer.Option(None)):
    """Verify empty state and cloud absence before awarding completion."""
    aid = attempt_for(domain.zfill(2), attempt)
    follow(request("POST", f"/attempts/{aid}/teardown-check"))


@app.command()
def status():
    """Show saved lab, checkpoint and practice progress."""
    output(request("GET", "/progress"))


@app.command()
def exam(domain: str | None = typer.Option(None), mock: str | None = typer.Option(None, help="Mock set A or B"), questions: int | None = typer.Option(None,min=1,max=57,help="Optional shorter mock length")):
    """Start an assessment and print its local browser URL."""
    if mock and mock not in {"A", "B"}:
        raise typer.BadParameter("Choose mock A or B")
    if questions and not mock:
        raise typer.BadParameter('--questions requires --mock A or B')
    result = request("POST", "/exams", {"mode":"mock" if mock else "practice", "domain_id":domain.zfill(2) if domain else None, "mock_set":mock or "A",'question_count':questions})
    typer.echo("Open http://127.0.0.1:8080/exam/" + result["id"])


if __name__ == "__main__":
    app()

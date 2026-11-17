import json
from unittest.mock import Mock
from fastapi.testclient import TestClient
from runner.api.credentials import Credentials
from runner.api.main import create_app

HEADERS = {"X-Tfprep": "1"}


def test_connection_and_startup_flow(settings, aws_session):
    application = create_app(settings, lambda db: Credentials(db, Mock(return_value=aws_session)))
    with TestClient(application) as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/connection").json()["connected"] is False
        assert client.get("/api/domains").json()[0]["id"] == "01"
        result = client.post("/api/connection", headers=HEADERS, json={"mode":"keys", "access_key_id":"api-key-canary", "secret_access_key":"api-secret-canary"})
        assert result.status_code == 200 and result.json()["account"] == "123456789012"
        assert "api-secret-canary" not in result.text
        started = client.post("/api/attempts", headers=HEADERS, json={"domain_id":"01"})
        assert started.status_code == 200
        attempt = started.json()
        variables = json.loads((settings.workspaces / f"01-{attempt['id']}" / "tfprep.auto.tfvars.json").read_text())
        assert variables["account_id"] == "123456789012"
        assert "api-secret-canary" not in json.dumps(variables)
        assert attempt["percentage"] == 0
        assert client.get(f"/api/attempts/{attempt['id']}/files").status_code == 200
        escape = client.put(f"/api/attempts/{attempt['id']}/files", headers=HEADERS, json={"path":"../../escape.tf", "content":"bad"})
        assert escape.status_code == 400
        assert not (settings.workspaces.parent / "escape.tf").exists()
        for payload in [{'operation':'plan; touch /tmp/tfprep-spoofed'},
                        {'operation':'plan','replace':'aws_s3_bucket.course -destroy'},
                        {'operation':'apply','arbitrary_command':'echo unsafe'}]:
            rejected=client.post(f"/api/attempts/{attempt['id']}/run",headers=HEADERS,json=payload)
            assert rejected.status_code==422
        assert application.state.services['db'].all('SELECT id FROM jobs')==[]


def test_browser_request_guards_and_secret_validation(settings, aws_session):
    application = create_app(settings, lambda db: Credentials(db, Mock(return_value=aws_session)))
    with TestClient(application) as client:
        payload = {"mode":"profile", "profile":"default"}
        assert client.post("/api/connection", json=payload).status_code == 403
        assert client.post("/api/connection", json=payload, headers={**HEADERS,"Origin":"https://evil.example"}).status_code == 403
        assert client.get("/api/health", headers={"Host":"evil.example"}).status_code == 403
        result = client.post("/api/connection", headers=HEADERS, json={"mode":"profile", "profile":"default", "secret_access_key":"secret-must-not-echo"})
        assert result.status_code == 422 and "secret-must-not-echo" not in result.text
        assert client.post("/api/attempts", headers=HEADERS, json={"domain_id":"01"}).status_code == 409


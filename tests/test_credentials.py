import json
from unittest.mock import Mock
import pytest
from runner.api.credentials import ConnectionRequired, Credentials
from runner.api.models import AWSConnection


def test_explicit_profile_overrides_ambient_keys(credentials, monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "unrelated-key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "unrelated-secret")
    monkeypatch.setenv("AWS_PROFILE", "wrong-profile")
    monkeypatch.setenv("TF_VAR_secret", "unrelated-variable")
    monkeypatch.setenv("TF_CLI_ARGS", "-destroy")
    env = credentials.environment("123456789012")
    credentials.factory.assert_called_with(profile_name="course-sandbox", region_name="us-east-1")
    assert env["AWS_SECRET_ACCESS_KEY"] == "profile-secret-canary"
    assert env["AWS_SESSION_TOKEN"] == "profile-token-canary"
    assert "AWS_PROFILE" not in env and "TF_VAR_secret" not in env and 'TF_CLI_ARGS' not in env
    assert "unrelated" not in json.dumps(env)
    assert credentials.redact("profile-secret-canary") == "[REDACTED]"


def test_keys_are_session_only_and_have_no_profile_fallback(db, aws_session, monkeypatch):
    monkeypatch.setenv("AWS_PROFILE", "default")
    factory = Mock(return_value=aws_session)
    credentials = Credentials(db, factory)
    credentials.connect(AWSConnection(mode="keys", access_key_id="key-canary", secret_access_key="secret-canary", session_token="token-canary"))
    factory.assert_called_once_with(aws_access_key_id="key-canary", aws_secret_access_key="secret-canary", aws_session_token="token-canary", region_name="us-east-1")
    env = credentials.environment()
    assert env["AWS_SECRET_ACCESS_KEY"] == "secret-canary" and "AWS_PROFILE" not in env
    assert "secret-canary" not in db.path.read_bytes().decode(errors="ignore")
    assert "secret-canary" not in json.dumps(credentials.status())
    assert credentials.redact("secret-canary token-canary key-canary") == "[REDACTED] [REDACTED] [REDACTED]"
    credentials.disconnect()
    assert not credentials.status()["connected"]
    with pytest.raises(ConnectionRequired):
        credentials.environment()
    restored = Credentials(db, factory)
    assert not restored.status()["connected"]


def test_account_binding_is_rechecked(credentials, aws_session):
    with pytest.raises(ConnectionRequired, match="different AWS account"):
        credentials.require("999999999999")
    aws_session.client.return_value.get_caller_identity.return_value["Account"] = "999999999999"
    with pytest.raises(ConnectionRequired, match="account changed"):
        credentials.verify("123456789012")


def test_bad_profile_selection_fails_closed_without_falling_back(credentials):
    from botocore.exceptions import ProfileNotFound
    credentials.factory.side_effect=ProfileNotFound(profile='missing-profile')
    with pytest.raises(ConnectionRequired,match='connection unavailable'):
        credentials.connect(AWSConnection(mode='profile',profile='missing-profile'))
    assert not credentials.status()['connected']
    with pytest.raises(ConnectionRequired):
        credentials.environment()


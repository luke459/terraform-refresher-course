from pathlib import Path
from unittest.mock import Mock
import pytest
from runner.api.config import Settings
from runner.api.credentials import Credentials
from runner.api.db import Database
from runner.api.models import AWSConnection

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def settings(tmp_path):
    return Settings(ROOT, tmp_path / "state", tmp_path / "workspaces", str(ROOT / ".tools" / "terraform"))


@pytest.fixture
def db(settings):
    return Database(settings.state)


@pytest.fixture
def aws_session():
    session = Mock()
    session.client.return_value.get_caller_identity.return_value = {"Account": "123456789012", "Arn": "arn:aws:iam::123456789012:user/course"}
    frozen = Mock(access_key="ASIAEXAMPLE0000000000", secret_key="profile-secret-canary", token="profile-token-canary")
    session.get_credentials.return_value.get_frozen_credentials.return_value = frozen
    return session


@pytest.fixture
def credentials(db, aws_session):
    instance = Credentials(db, session_factory=Mock(return_value=aws_session))
    instance.connect(AWSConnection(mode="profile", profile="course-sandbox"))
    return instance


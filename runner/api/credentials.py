import os
import re
import threading
from typing import Any
import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError, SSOError, TokenRetrievalError
from .models import AWSConnection
from .sso import use_memory_sso_refresh


class ConnectionRequired(ValueError):
    pass


class Credentials:
    """One local learner's explicitly selected, memory-only AWS connection."""
    def __init__(self, db, session_factory=boto3.Session):
        self.db = db
        self.factory = session_factory
        self.lock = threading.RLock()
        self.selection: AWSConnection | None = None
        self.identity: dict[str, str] | None = None
        self.session: Any = None
        self.resolved_secrets = set()

    def connect(self, request: AWSConnection):
        with self.lock:
            self.selection = self.session = self.identity = None
            self.resolved_secrets.clear()
            try:
                if request.mode == "profile":
                    # Explicit profile_name disables the ambient environment provider in botocore.
                    candidate = self.factory(profile_name=request.profile, region_name=request.region)
                    use_memory_sso_refresh(candidate, request.profile, request.region)
                else:
                    candidate = self.factory(
                        aws_access_key_id=request.access_key_id.get_secret_value(),
                        aws_secret_access_key=request.secret_access_key.get_secret_value(),
                        aws_session_token=request.session_token.get_secret_value() if request.session_token else None,
                        region_name=request.region,
                    )
                identity = candidate.client("sts", config=Config(connect_timeout=5, read_timeout=10, retries={"max_attempts": 1})).get_caller_identity()
            except (BotoCoreError, ClientError, OSError) as exc:
                raise ConnectionRequired(self.friendly_error(exc)) from None
            self.selection = request
            self.session = candidate
            self.identity = {"account": identity["Account"], "arn": identity["Arn"], "region": request.region, "mode": request.mode}
            metadata = {**self.identity, "profile": request.profile}
            self.db.save_setting("aws_connection", metadata)
            return self.status()

    @staticmethod
    def friendly_error(exc):
        if isinstance(exc, (SSOError, TokenRetrievalError)):
            return "Your AWS SSO session needs a new sign-in. Sign in on the host, then reconnect on the AWS connection page."
        if isinstance(exc, OSError):
            return "AWS sign-in files could not be read or refreshed. Refresh your AWS SSO login on the host, then reconnect on the AWS connection page."
        if isinstance(exc, ClientError):
            code = exc.response.get("Error", {}).get("Code", "Unknown")
            return f"AWS identity check failed ({code}). Check the selected credentials and retry."
        return "AWS connection unavailable. Check the profile, host SSO login, credentials, and network."

    def disconnect(self):
        with self.lock:
            self.selection = self.session = self.identity = None
            self.resolved_secrets.clear()

    def status(self):
        with self.lock:
            if self.identity:
                return {"connected": True, **self.identity, "profile": self.selection.profile}
            previous = self.db.setting("aws_connection", {})
            return {"connected": False, "profile": previous.get("profile"), "region": previous.get("region", "us-east-1")}

    def require(self, account=None):
        if not self.identity or not self.selection or not self.session:
            raise ConnectionRequired("Connect an AWS profile or access keys before starting a live lab.")
        if account and self.identity["account"] != account:
            raise ConnectionRequired("This attempt belongs to a different AWS account. Reconnect the original account.")
        return self.session

    def verify(self, account=None):
        session = self.require(account)
        try:
            identity = session.client("sts", config=Config(connect_timeout=5, read_timeout=10, retries={"max_attempts": 1})).get_caller_identity()
        except (BotoCoreError, ClientError, OSError) as exc:
            raise ConnectionRequired(self.friendly_error(exc)) from None
        if identity["Account"] != self.identity["account"] or (account and identity["Account"] != account):
            raise ConnectionRequired("AWS account changed. Reconnect the account that owns this attempt.")
        return identity

    def client(self, service, region=None):
        return self.require().client(service, region_name=region or self.selection.region,
            config=Config(connect_timeout=5, read_timeout=15, retries={"mode": "standard", "max_attempts": 3}))

    def environment(self, account=None):
        self.require(account)
        # Never inherit alternate AWS identities or arbitrary TF_VAR_/TF_CLI_ARGS values.
        allowed = {"PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "SSL_CERT_FILE", "SSL_CERT_DIR"}
        env = {key: value for key, value in os.environ.items() if key in allowed}
        env.update({"AWS_REGION": self.selection.region, "AWS_DEFAULT_REGION": self.selection.region,
                    "AWS_EC2_METADATA_DISABLED": "true", "TF_IN_AUTOMATION": "1", "TF_INPUT": "0"})
        if self.selection.mode == "profile":
            # Export the selected profile's resolved credentials to every tool, including backends.
            # This also avoids CLI/SDK differences in ambient credential precedence.
            resolved = self.session.get_credentials()
            if resolved is None:
                raise ConnectionRequired("The selected profile did not resolve credentials.")
            resolved = resolved.get_frozen_credentials()
            self.resolved_secrets.update(value for value in (resolved.access_key, resolved.secret_key, resolved.token) if value)
            env.update({"AWS_ACCESS_KEY_ID": resolved.access_key, "AWS_SECRET_ACCESS_KEY": resolved.secret_key})
            if resolved.token:
                env["AWS_SESSION_TOKEN"] = resolved.token
        else:
            env.update({"AWS_ACCESS_KEY_ID": self.selection.access_key_id.get_secret_value(),
                        "AWS_SECRET_ACCESS_KEY": self.selection.secret_access_key.get_secret_value()})
            if self.selection.session_token:
                env["AWS_SESSION_TOKEN"] = self.selection.session_token.get_secret_value()
        return env

    def redact(self, text):
        for secret in self.resolved_secrets:
            text = text.replace(secret, "[REDACTED]")
        if self.selection:
            for value in [self.selection.access_key_id, self.selection.secret_access_key, self.selection.session_token]:
                if value:
                    text = text.replace(value.get_secret_value(), "[REDACTED]")
        text = re.sub(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b", "[REDACTED]", text)
        text = re.sub(r'(?i)(?<![A-Za-z0-9_.])((?:aws_secret_access_key|aws_session_token|secret_string|password)\s*[=:]\s*)[^\s,]+', r'\1[REDACTED]', text)
        return text


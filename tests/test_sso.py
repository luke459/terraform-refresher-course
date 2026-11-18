import errno
import hashlib
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import boto3
import pytest
from botocore.session import Session
from botocore.tokens import SSOTokenProvider
from botocore.utils import JSONFileCache
from fastapi.testclient import TestClient

from runner.api.credentials import Credentials
from runner.api.main import create_app
from runner.api.sso import use_memory_sso_refresh


@pytest.mark.parametrize('assume_role', [False, True])
def test_sso_refresh_uses_memory_with_readonly_host_cache(tmp_path, monkeypatch, assume_role):
    now = datetime.now(timezone.utc)
    stamp = lambda value: value.strftime('%Y-%m-%dT%H:%M:%SZ')
    cache = tmp_path / 'cache'
    cache.mkdir()
    token_file = cache / (hashlib.sha1(b'course-sso').hexdigest() + '.json')
    token_file.write_text(json.dumps({
        'startUrl': 'https://example.awsapps.com/start', 'region': 'eu-west-1',
        'accessToken': 'old-access-canary', 'expiresAt': stamp(now - timedelta(minutes=1)),
        'refreshToken': 'refresh-canary', 'clientId': 'client-canary',
        'clientSecret': 'client-secret-canary', 'registrationExpiresAt': stamp(now + timedelta(days=1)),
    }))
    original = token_file.read_bytes()
    profile = 'course-source' if assume_role else 'course-sandbox'
    config = tmp_path / 'config'
    config.write_text(f'''[profile {profile}]
sso_session = course-sso
sso_account_id = 123456789012
sso_role_name = Learner
[sso-session course-sso]
sso_start_url = https://example.awsapps.com/start
sso_region = eu-west-1
''')
    if assume_role:
        with config.open('a') as stream:
            stream.write('''[profile course-sandbox]
role_arn = arn:aws:iam::123456789012:role/CourseLab
source_profile = course-source
''')
    core = Session(profile='course-sandbox')
    core.set_config_variable('config_file', str(config))
    core.set_config_variable('credentials_file', str(tmp_path / 'no-shared-credentials'))
    monkeypatch.setattr(SSOTokenProvider, '_SSO_TOKEN_CACHE_DIR', str(cache))
    oidc, sso, sts = Mock(), Mock(), Mock()
    oidc.create_token.return_value = {'accessToken': 'refreshed-access-canary', 'expiresIn': 3600, 'refreshToken': 'new-refresh-canary'}
    sso.get_role_credentials.return_value = {'roleCredentials': {
        'accessKeyId': 'role-key-canary', 'secretAccessKey': 'role-secret-canary',
        'sessionToken': 'role-session-canary', 'expiration': int((now + timedelta(hours=1)).timestamp() * 1000),
    }}
    sts.assume_role.return_value = {'Credentials': {
        'AccessKeyId': 'assumed-key-canary', 'SecretAccessKey': 'assumed-secret-canary',
        'SessionToken': 'assumed-session-canary', 'Expiration': now + timedelta(hours=1),
    }}
    monkeypatch.setattr(core, 'create_client', lambda name, **kwargs: {'sso-oidc': oidc, 'sso': sso, 'sts': sts}[name])

    def forbid_disk_write(*args, **kwargs):
        raise OSError(errno.EROFS, 'Read-only file system')

    monkeypatch.setattr(JSONFileCache, '__setitem__', forbid_disk_write)
    candidate = boto3.Session(botocore_session=core)
    memory = use_memory_sso_refresh(candidate, 'course-sandbox', 'eu-west-1')
    resolved = candidate.get_credentials().get_frozen_credentials()
    assert resolved.access_key == ('assumed-key-canary' if assume_role else 'role-key-canary')
    oidc.create_token.assert_called_once()
    assert sso.get_role_credentials.call_args.kwargs['accessToken'] == 'refreshed-access-canary'
    # Reusing the session does not reload the expired disk token or write secrets.
    candidate.get_credentials().get_frozen_credentials()
    oidc.create_token.assert_called_once()
    reloaded = SSOTokenProvider(core, cache=memory, profile_name=profile).load_token().get_frozen_token()
    assert reloaded.token == 'refreshed-access-canary'
    # Another refresh cycle must also read and update the memory cache correctly.
    later = SSOTokenProvider(core, cache=memory, profile_name=profile, time_fetcher=lambda: now + timedelta(minutes=70))
    assert later.load_token().get_frozen_token().token == 'refreshed-access-canary'
    assert oidc.create_token.call_count == 2
    assert oidc.create_token.call_args.kwargs['refreshToken'] == 'new-refresh-canary'
    assert token_file.read_bytes() == original
    assert list(cache.iterdir()) == [token_file]


@pytest.mark.parametrize('during_connect', [False, True])
def test_signin_file_error_returns_json_without_creating_attempt(settings, aws_session, during_connect):
    application = create_app(settings, lambda db: Credentials(db, Mock(return_value=aws_session)))
    with TestClient(application) as client:
        headers = {'X-Tfprep': '1'}
        if during_connect:
            aws_session.client.return_value.get_caller_identity.side_effect = OSError(errno.EROFS, '/private/sign-in-secret-canary')
        response = client.post('/api/connection', headers=headers, json={'mode': 'profile', 'profile': 'course-sandbox'})
        if not during_connect:
            assert response.status_code == 200
            aws_session.client.return_value.get_caller_identity.side_effect = OSError(errno.EROFS, '/private/sign-in-secret-canary')
            response = client.post('/api/attempts', headers=headers, json={'domain_id': '02'})
        assert response.status_code == 409
        assert response.headers['content-type'].startswith('application/json')
        assert 'AWS SSO login' in response.json()['detail']
        assert 'sign-in-secret-canary' not in response.text
        assert application.state.services['db'].all('SELECT id FROM attempts') == []

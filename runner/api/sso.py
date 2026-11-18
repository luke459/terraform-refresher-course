"""Read host SSO sign-in files without writing refreshed tokens back to them."""
from datetime import datetime, timezone
from botocore.credentials import ProfileProviderBuilder, SSOProvider
from botocore.session import Session
from botocore.tokens import SSOTokenProvider
from botocore.utils import JSONFileCache


class MemoryRefreshCache(dict):
    """Read through to the host cache; keep refreshed tokens in session memory."""

    def __init__(self, directory):
        super().__init__()
        self.source = JSONFileCache(directory)

    def __contains__(self, key):
        return super().__contains__(key) or key in self.source

    def __getitem__(self, key):
        if super().__contains__(key):
            return super().__getitem__(key)
        return self.source[key]

    def __setitem__(self, key, value):
        # Match JSONFileCache's timestamp format, so later refreshes can reload it.
        token = dict(value)
        for field in ('expiresAt', 'registrationExpiresAt'):
            if isinstance(token.get(field), datetime):
                token[field] = token[field].astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        super().__setitem__(key, token)


def use_memory_sso_refresh(candidate, profile, region):
    # These integration points are covered against the pinned botocore version,
    # including assume-role profiles whose source profile uses SSO.
    session = getattr(candidate, '_session', None)
    if not isinstance(session, Session):
        return
    cache = MemoryRefreshCache(SSOTokenProvider._SSO_TOKEN_CACHE_DIR)
    resolver = session.get_component('credential_provider')
    provider = resolver.get_provider('sso')
    replacement = SSOProvider(
        load_config=lambda: session.full_config,
        client_creator=session.create_client,
        profile_name=profile,
        cache=provider.cache,
        token_cache=cache,
        token_provider=SSOTokenProvider(session, cache=cache, profile_name=profile),
    )
    resolver.remove('sso')
    resolver.insert_before('shared-credentials-file', replacement)
    assume_role = resolver.get_provider('assume-role')
    assume_role._profile_provider_builder = ProfileProviderBuilder(
        session, cache=assume_role.cache, region_name=region, sso_token_cache=cache,
    )
    return cache

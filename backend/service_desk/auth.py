"""Explicit local bearer-token bindings; not an enterprise identity provider."""
from hashlib import sha256
from hmac import compare_digest
from .contracts import Actor, Role


class AuthenticationFailed(Exception):
    pass


class TokenAuthenticator:
    def __init__(self, bindings: dict[str, Actor]):
        if not bindings:
            raise ValueError('Authentication configuration required.')
        self._bindings = []
        for token, actor in bindings.items():
            if (not isinstance(token, str) or not 32 <= len(token) <= 512
                    or not token.isascii() or any(c.isspace() or ord(c) < 33 or ord(c) > 126 for c in token)
                    or not isinstance(actor, Actor) or not actor.actor_id
                    or not actor.tenant_id or not isinstance(actor.role, Role)):
                raise ValueError('Invalid authentication configuration.')
            self._bindings.append((sha256(token.encode()).digest(), actor))

    def authenticate(self, authorization: str) -> Actor:
        scheme, separator, token = authorization.partition(' ')
        if (scheme.lower() != 'bearer' or not separator or not 32 <= len(token) <= 512
                or not token.isascii() or any(c.isspace() for c in token)):
            raise AuthenticationFailed()
        digest = sha256(token.encode()).digest()
        actor = None
        for expected, candidate in self._bindings:
            if compare_digest(expected, digest):
                actor = candidate
        if actor is None:
            raise AuthenticationFailed()
        return actor

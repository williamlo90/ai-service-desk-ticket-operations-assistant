"""Dependency-free WSGI API, exercised in-process without Docker or a server."""
from dataclasses import asdict
from http import HTTPStatus
import json
import re

from .auth import AuthenticationFailed, TokenAuthenticator
from .cases import CaseError, CaseRepository, CaseService
from .contracts import AccessDenied

MAX_BODY = 16384


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key.')
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError('Invalid JSON constant.')


class CaseAPI:
    def __init__(self, authenticator: TokenAuthenticator, repository: CaseRepository):
        self.authenticator = authenticator
        self.service = CaseService(repository)

    def __call__(self, environ, start_response):
        extra = []
        try:
            status, body = self.dispatch(environ)
        except AuthenticationFailed:
            status, body = 401, {'error':'unauthorized'}
            extra.append(('WWW-Authenticate','Bearer'))
        except AccessDenied:
            status, body = 403, {'error':'forbidden'}
        except CaseError as exc:
            code = str(exc)
            status = {'invalid_request':400, 'invalid_idempotency_key':400,
                      'not_found':404, 'idempotency_conflict':409,
                      'storage_capacity':503, 'payload_too_large':413,
                      'unsupported_media_type':415, 'length_required':411}.get(code,500)
            body = {'error':code if status != 500 else 'internal_error'}
        except Exception:
            # Never return raw exceptions, input, credentials or upstream errors.
            status, body = 500, {'error':'internal_error'}
        encoded = json.dumps(body, allow_nan=False).encode('utf-8')
        start_response(f'{status} {HTTPStatus(status).phrase}', [
            ('Content-Type','application/json; charset=utf-8'),
            ('Content-Length',str(len(encoded))), ('Cache-Control','no-store'),
            ('X-Content-Type-Options','nosniff'), *extra])
        return [encoded]

    def dispatch(self, env):
        method, path = env.get('REQUEST_METHOD',''), env.get('PATH_INFO','')
        if method == 'GET' and path == '/healthz':
            return 200, {'status':'ok'}
        actor = self.authenticator.authenticate(env.get('HTTP_AUTHORIZATION',''))
        if method == 'POST' and path == '/v1/cases':
            if env.get('CONTENT_TYPE','').split(';',1)[0].strip().lower() != 'application/json':
                raise CaseError('unsupported_media_type')
            raw_length = env.get('CONTENT_LENGTH','')
            if not raw_length:
                raise CaseError('length_required')
            if not re.fullmatch(r'[0-9]{1,10}', raw_length):
                raise CaseError('invalid_request')
            length = int(raw_length)
            if length > MAX_BODY:
                raise CaseError('payload_too_large')
            raw = env['wsgi.input'].read(length)
            if len(raw) != length:
                raise CaseError('invalid_request')
            try:
                data = json.loads(raw.decode('utf-8'), object_pairs_hook=strict_object,
                                  parse_constant=reject_constant)
            except (ValueError, UnicodeError, RecursionError):
                raise CaseError('invalid_request') from None
            case, created = self.service.create(actor, env.get('HTTP_IDEMPOTENCY_KEY',''), data)
            return (201 if created else 200), {'case':asdict(case),'created':created}
        match = re.fullmatch(r'/v1/cases/([a-f0-9-]{36})', path)
        if method == 'GET' and match:
            return 200, {'case':asdict(self.service.get(actor,match[1]))}
        return 404, {'error':'not_found'}

import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests

from app.updates import constants as settings
from app.updates.manifest import (
    checked_digest,
    checked_repository,
    reject_duplicate_fields,
)


class TransportError(ValueError):
    pass


def checked_release_url(value):
    if not isinstance(value, str) or len(value) > settings.MAX_RELEASE_URL_LENGTH:
        raise TransportError(settings.TRANSPORT_ERROR)
    if "\\" in value or any(ord(character) < 32 for character in value):
        raise TransportError(settings.TRANSPORT_ERROR)
    try:
        parsed = urlsplit(value)
        allowed = (
            parsed.scheme == "https"
            and parsed.hostname in settings.TRUSTED_RELEASE_HOSTS
        )
        allowed = allowed and parsed.port in {None, settings.HTTPS_PORT}
    except ValueError as error:
        raise TransportError(settings.TRANSPORT_ERROR) from error
    if (
        not allowed
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise TransportError(settings.TRANSPORT_ERROR)
    return parsed.geturl()


def checked_archive_source(value, repository):
    value = checked_release_url(value)
    parsed = urlsplit(value)
    repository = checked_repository(repository)
    prefix = f"/{repository}/releases/download/"
    api_prefix = f"/repos/{repository}/releases/assets/"
    expected_prefix = prefix if parsed.hostname == "github.com" else api_prefix
    if (
        parsed.hostname not in settings.INITIAL_RELEASE_HOSTS
        or not parsed.path.casefold().startswith(expected_prefix.casefold())
    ):
        raise TransportError(settings.REPOSITORY_ERROR)
    if parsed.query or not parsed.path[len(expected_prefix) :]:
        raise TransportError(settings.TRANSPORT_ERROR)
    return value


@contextmanager
def release_session(existing=None):
    session = existing if existing is not None else requests.Session()
    session.trust_env = False
    session.auth = None
    session.proxies = {}
    session.headers.clear()
    session.cookies.clear()
    try:
        yield session
    finally:
        if existing is None:
            session.close()


def initial_release_response(session, url, headers=None):
    current = checked_release_url(url)
    for attempt in range(settings.MAX_REDIRECTS + 1):
        session.cookies.clear()
        response = session.get(
            current,
            headers=dict(
                settings.RELEASE_REQUEST_HEADERS if headers is None else headers
            ),
            timeout=settings.REQUEST_TIMEOUT,
            allow_redirects=False,
            stream=True,
            verify=True,
            proxies={},
            auth=None,
        )
        if response.status_code == settings.SUCCESS_STATUS:
            return response
        try:
            location = response.headers.get("Location")
            if response.status_code not in settings.REDIRECT_STATUSES or not location:
                raise TransportError(settings.TRANSPORT_ERROR)
            if attempt == settings.MAX_REDIRECTS:
                raise TransportError(settings.TRANSPORT_ERROR)
            current = checked_release_url(urljoin(current, location))
        finally:
            response.close()
    raise TransportError(settings.TRANSPORT_ERROR)


@contextmanager
def release_response(url, session=None, headers=None):
    try:
        with release_session(session) as client:
            response = initial_release_response(client, url, headers)
            try:
                yield response
            finally:
                response.close()
    except requests.RequestException as error:
        raise TransportError(settings.TRANSPORT_ERROR) from error


def checked_content_length(response, maximum, expected=None):
    value = response.headers.get("Content-Length")
    if value is None:
        return
    if (
        not isinstance(value, str)
        or not value.isascii()
        or not value.isdecimal()
        or len(value) > settings.MAX_LENGTH_HEADER_DIGITS
    ):
        raise TransportError(settings.DOWNLOAD_SIZE_ERROR)
    length = int(value)
    if length > maximum or expected is not None and length != expected:
        raise TransportError(settings.DOWNLOAD_SIZE_ERROR)


def bounded_chunks(response, maximum):
    total = 0
    for chunk in response.iter_content(chunk_size=settings.CHUNK_BYTES):
        if not chunk:
            continue
        if type(chunk) is not bytes:
            raise TransportError(settings.TRANSPORT_ERROR)
        total += len(chunk)
        if total > maximum:
            raise TransportError(settings.DOWNLOAD_SIZE_ERROR)
        yield chunk


def fetch_release_json(url, session=None):
    with release_response(
        url, session, settings.RELEASE_JSON_REQUEST_HEADERS
    ) as response:
        checked_content_length(response, settings.MAX_RELEASE_JSON_BYTES)
        payload = b"".join(bounded_chunks(response, settings.MAX_RELEASE_JSON_BYTES))
    try:
        result = json.loads(
            payload.decode("utf-8"), object_pairs_hook=reject_duplicate_fields
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as error:
        raise TransportError(settings.TRANSPORT_ERROR) from error
    if type(result) is not dict:
        raise TransportError(settings.TRANSPORT_ERROR)
    return result


def checked_archive_metadata(manifest):
    digest = checked_digest(manifest["archive_sha256"])
    size = manifest["archive_size"]
    if type(size) is not int or not 1 <= size <= settings.MAX_ARCHIVE_BYTES:
        raise TransportError(settings.DOWNLOAD_SIZE_ERROR)
    return digest, size


def write_verified_archive(response, handle, digest, size):
    checked_content_length(response, size, expected=size)
    hasher = hashlib.sha256()
    total = 0
    for chunk in bounded_chunks(response, size):
        handle.write(chunk)
        hasher.update(chunk)
        total += len(chunk)
    if total != size:
        raise TransportError(settings.DOWNLOAD_SIZE_ERROR)
    if hasher.hexdigest() != digest:
        raise TransportError(settings.DOWNLOAD_DIGEST_ERROR)
    handle.flush()
    os.fsync(handle.fileno())


def download_release_archive(url, destination, manifest, session=None):
    source = checked_archive_source(url, manifest["repository"])
    digest, size = checked_archive_metadata(manifest)
    destination = Path(destination)
    if destination.is_symlink():
        raise TransportError(settings.TRANSPORT_ERROR)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            temporary.chmod(settings.PRIVATE_DOWNLOAD_MODE)
            with release_response(source, session) as response:
                write_verified_archive(response, handle, digest, size)
        os.replace(temporary, destination)
        return destination
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

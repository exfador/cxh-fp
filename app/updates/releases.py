from urllib.parse import quote

from app.constants.update_runtime import (
    UPDATE_ARCHIVE_ASSET,
    UPDATE_MANIFEST_ASSET,
    UPDATE_RELEASE_API,
)
from app.updates.manifest import verify_envelope
from app.updates.transport import fetch_release_json


def release_asset(release, name, repository):
    assets = release.get("assets")
    if not isinstance(assets, list):
        raise ValueError("Release assets missing")
    matches = [
        item for item in assets if isinstance(item, dict) and item.get("name") == name
    ]
    if len(matches) != 1:
        raise ValueError("Release asset missing or duplicated")
    asset = matches[0]
    url = asset.get("browser_download_url", "")
    prefix = f"https://github.com/{repository}/releases/download/"
    if not isinstance(url, str) or not url.startswith(prefix):
        raise ValueError("Release asset belongs to another repository")
    return url


def latest_release(repository, public_key, current_version, fetch=fetch_release_json):
    release = fetch(UPDATE_RELEASE_API.format(repository))
    if release.get("draft") is not False or release.get("prerelease") is not False:
        return None
    if release.get("tag_name") in (f"v{current_version}", current_version):
        return None
    envelope_url = release_asset(release, UPDATE_MANIFEST_ASSET, repository)
    envelope = fetch(envelope_url)
    manifest = verify_envelope(envelope, public_key, repository, current_version)
    if release.get("tag_name") != f"v{manifest['version']}":
        raise ValueError("Signed release version does not match tag")
    archive = release_asset(release, UPDATE_ARCHIVE_ASSET, repository)
    expected = f"https://github.com/{repository}/releases/download/v{quote(manifest['version'])}/"
    if not archive.startswith(expected) or not envelope_url.startswith(expected):
        raise ValueError("Release asset version mismatch")
    return manifest, archive, envelope

"""Resolve Kubernetes release tags and download OpenAPI specs from GitHub.

Uses only stdlib (urllib) for HTTP. Specs are cached locally so repeated runs
skip already-downloaded versions.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
GITHUB_RAW = "https://raw.githubusercontent.com"
REPO = "kubernetes/kubernetes"


def _get_github_token() -> str | None:
    """Return a GitHub token from GITHUB_TOKEN env var or ``gh auth token``."""
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    import subprocess  # noqa: PLC0415

    try:
        result = subprocess.run(  # noqa: S603, S607
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip() or None
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


_SEMVER_RE = re.compile(
    r"^v?(\d+)\.(\d+)\.(\d+)"
    r"(?:-(alpha|beta|rc)\.(\d+))?$"
)

_PRE_ORDER = {"alpha": 0, "beta": 1, "rc": 2}


def _semver_sort_key(tag: str) -> tuple[int, int, int, int, int]:
    """Return a sort key for a Kubernetes version tag.

    Stable releases sort higher than pre-releases.
    """
    m = _SEMVER_RE.match(tag)
    if not m:
        return (0, 0, 0, -1, 0)
    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    pre_label, pre_num = m.group(4), m.group(5)
    if pre_label is None:
        return (major, minor, patch, 3, 0)
    return (major, minor, patch, _PRE_ORDER.get(pre_label, -1), int(pre_num))


def _github_get(url: str, *, max_retries: int = 3) -> Any:
    """GET a GitHub API URL and return parsed JSON.

    Retries on 403 (rate limit), 5xx, and network errors with exponential backoff.
    """
    for attempt in range(max_retries):
        headers: dict[str, str] = {"Accept": "application/vnd.github+json"}
        token = _get_github_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            retryable = exc.code == 403 or exc.code >= 500
            if retryable and attempt < max_retries - 1:
                delay = 2 ** (attempt + 1)
                logger.warning(
                    "GitHub API %s returned %s, retrying in %ss", url, exc.code, delay
                )
                time.sleep(delay)
                continue
            raise
        except urllib.error.URLError as exc:
            if attempt < max_retries - 1:
                delay = 2 ** (attempt + 1)
                logger.warning(
                    "GitHub API %s network error: %s, retrying in %ss",
                    url,
                    exc.reason,
                    delay,
                )
                time.sleep(delay)
                continue
            raise
    msg = f"GitHub API request failed after {max_retries} attempts: {url}"
    raise RuntimeError(msg)


def _download_file(url: str, dest: Path, *, max_retries: int = 3) -> None:
    """Download a file from a URL into dest, creating parent dirs as needed."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(max_retries):
        headers: dict[str, str] = {}
        token = _get_github_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                dest.write_bytes(resp.read())
            return
        except urllib.error.HTTPError as exc:
            retryable = exc.code == 403 or exc.code >= 500
            if retryable and attempt < max_retries - 1:
                delay = 2 ** (attempt + 1)
                logger.warning(
                    "Download %s returned %s, retrying in %ss", url, exc.code, delay
                )
                time.sleep(delay)
                continue
            raise
        except urllib.error.URLError as exc:
            if attempt < max_retries - 1:
                delay = 2 ** (attempt + 1)
                logger.warning(
                    "Download %s network error: %s, retrying in %ss",
                    url,
                    exc.reason,
                    delay,
                )
                time.sleep(delay)
                continue
            raise
    msg = f"Download failed after {max_retries} attempts: {url}"
    raise RuntimeError(msg)


def resolve_latest_release(minor_version: str) -> str:
    """Find the latest release tag for a Kubernetes minor version.

    Queries the GitHub Releases API first. If no stable release is found
    (e.g. for bleeding-edge versions like 1.37), falls back to the git
    tags API to find alpha/beta/rc tags.

    Args:
        minor_version: e.g. "1.35"

    Returns:
        Full tag string, e.g. "v1.35.4" or "v1.37.0-alpha.0".

    Raises:
        ValueError: If no release or tag is found for the given version.
    """
    prefix = f"v{minor_version}."

    best_tag = _search_releases(prefix)
    if best_tag is not None:
        return best_tag

    best_tag = _search_git_tags(prefix)
    if best_tag is not None:
        return best_tag

    msg = f"No release or tag found for Kubernetes {minor_version}"
    raise ValueError(msg)


def _search_releases(prefix: str, *, max_pages: int = 10) -> str | None:
    """Search paginated GitHub releases for tags matching prefix.

    Stops early when candidates have been found and a subsequent page
    contains no new matches, or after *max_pages* to bound API usage.
    """
    page = 1
    candidates: list[str] = []
    while page <= max_pages:
        url = f"{GITHUB_API}/repos/{REPO}/releases?per_page=100&page={page}"
        releases = _github_get(url)
        if not releases:
            break
        found_match = False
        for rel in releases:
            tag = rel.get("tag_name", "")
            if tag.startswith(prefix):
                candidates.append(tag)
                found_match = True
        if candidates and not found_match:
            break
        page += 1
    if not candidates:
        return None
    candidates.sort(key=_semver_sort_key)
    return candidates[-1]


def _search_git_tags(prefix: str) -> str | None:
    """Search git refs/tags for tags matching prefix (for pre-release versions)."""
    url = f"{GITHUB_API}/repos/{REPO}/git/refs/tags/{prefix}"
    try:
        refs = _github_get(url)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    if not isinstance(refs, list):
        refs = [refs]
    candidates: list[str] = []
    for ref in refs:
        ref_name = ref.get("ref", "")
        tag = ref_name.removeprefix("refs/tags/")
        if tag.startswith(prefix):
            candidates.append(tag)
    if not candidates:
        return None
    candidates.sort(key=_semver_sort_key)
    return candidates[-1]


@dataclass
class DownloadedSpecs:
    """Paths to downloaded spec files for a single Kubernetes version."""

    swagger_path: Path
    v3_dir: Path


def download_specs(tag: str, cache_dir: Path) -> DownloadedSpecs:
    """Download v2 swagger.json and v3 per-group specs for a release tag.

    Skips download if the swagger.json already exists in the cache
    (cache hit for the whole tag).

    Args:
        tag: Full release tag, e.g. "v1.35.4".
        cache_dir: Root cache directory (e.g. `.cache/schemas`).

    Returns:
        DownloadedSpecs with paths to the downloaded files.
    """
    tag_dir = cache_dir / tag
    swagger_path = tag_dir / "swagger.json"
    v3_dir = tag_dir / "v3"
    sentinel = tag_dir / ".complete"

    if sentinel.exists():
        logger.info("Cache hit for %s, skipping download", tag)
        return DownloadedSpecs(swagger_path=swagger_path, v3_dir=v3_dir)

    logger.info("Downloading specs for %s", tag)
    tag_dir.mkdir(parents=True, exist_ok=True)

    swagger_url = f"{GITHUB_RAW}/{REPO}/{tag}/api/openapi-spec/swagger.json"
    _download_file(swagger_url, swagger_path)

    contents_url = f"{GITHUB_API}/repos/{REPO}/contents/api/openapi-spec/v3?ref={tag}"
    entries = _github_get(contents_url)
    for entry in entries:
        name = entry.get("name", "")
        if name.endswith(".json"):
            file_url = f"{GITHUB_RAW}/{REPO}/{tag}/api/openapi-spec/v3/{name}"
            _download_file(file_url, v3_dir / name)

    sentinel.touch()
    return DownloadedSpecs(swagger_path=swagger_path, v3_dir=v3_dir)


def fetch_all_specs(
    minor_versions: list[str], cache_dir: Path
) -> dict[str, DownloadedSpecs]:
    """Resolve and download specs for a list of Kubernetes minor versions.

    Args:
        minor_versions: e.g. ["1.32", "1.33", "1.35"]
        cache_dir: Root cache directory.

    Returns:
        Mapping of minor version to DownloadedSpecs.
    """
    results: dict[str, DownloadedSpecs] = {}
    for version in minor_versions:
        logger.info("Resolving latest release for %s", version)
        tag = resolve_latest_release(version)
        logger.info("Resolved %s -> %s", version, tag)
        specs = download_specs(tag, cache_dir)
        results[version] = specs
    return results

from __future__ import annotations

import json
import urllib.error
from email.message import Message
from io import BytesIO
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from scripts.codegen.fetch_specs import (
    DownloadedSpecs,
    _semver_sort_key,
    download_specs,
    fetch_all_specs,
    resolve_latest_release,
)


def _mock_urlopen(data: Any, *, status: int = 200) -> MagicMock:
    body = json.dumps(data).encode() if not isinstance(data, bytes) else data
    resp = MagicMock()
    resp.read.return_value = body
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    if status >= 400:
        raise urllib.error.HTTPError(
            url="https://example.com",
            code=status,
            msg="err",
            hdrs=Message(),
            fp=BytesIO(body),
        )
    return resp


def _make_releases(tags: list[str]) -> list[dict[str, str]]:
    return [{"tag_name": t} for t in tags]


def _make_refs(tags: list[str]) -> list[dict[str, str]]:
    return [{"ref": f"refs/tags/{t}"} for t in tags]


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        ("v1.35.4", (1, 35, 4, 3, 0)),
        ("v1.37.0-alpha.0", (1, 37, 0, 0, 0)),
        ("v1.37.0-beta.1", (1, 37, 0, 1, 1)),
        ("v1.37.0-rc.2", (1, 37, 0, 2, 2)),
        ("not-a-version", (0, 0, 0, -1, 0)),
    ],
)
def test_semver_sort_key(tag: str, expected: tuple[int, ...]) -> None:
    assert _semver_sort_key(tag) == expected


def test_semver_sort_order() -> None:
    tags = ["v1.37.0-alpha.0", "v1.37.0-rc.1", "v1.37.0-beta.2", "v1.37.0"]
    sorted_tags = sorted(tags, key=_semver_sort_key)
    assert sorted_tags == [
        "v1.37.0-alpha.0",
        "v1.37.0-beta.2",
        "v1.37.0-rc.1",
        "v1.37.0",
    ]


@patch("scripts.codegen.fetch_specs.urllib.request.urlopen")
def test_resolve_latest_release_stable(mock_urlopen: MagicMock) -> None:
    page1 = _make_releases(["v1.35.4", "v1.35.3", "v1.34.8", "v1.35.2"])
    mock_urlopen.side_effect = [
        _mock_urlopen(page1),
        _mock_urlopen([]),
    ]
    result = resolve_latest_release("1.35")
    assert result == "v1.35.4"


@patch("scripts.codegen.fetch_specs.urllib.request.urlopen")
def test_resolve_latest_release_prerelease_fallback(mock_urlopen: MagicMock) -> None:
    page1 = _make_releases(["v1.36.1", "v1.35.4"])
    refs = _make_refs(["v1.37.0-alpha.0", "v1.37.0-alpha.1"])
    mock_urlopen.side_effect = [
        _mock_urlopen(page1),
        _mock_urlopen([]),
        _mock_urlopen(refs),
    ]
    result = resolve_latest_release("1.37")
    assert result == "v1.37.0-alpha.1"


@patch("scripts.codegen.fetch_specs.urllib.request.urlopen")
def test_resolve_latest_release_not_found(mock_urlopen: MagicMock) -> None:
    mock_urlopen.side_effect = [
        _mock_urlopen([]),
        urllib.error.HTTPError(
            url="https://example.com",
            code=404,
            msg="Not Found",
            hdrs=Message(),
            fp=BytesIO(b""),
        ),
    ]
    with pytest.raises(ValueError, match="No release or tag found"):
        resolve_latest_release("1.99")


@patch("scripts.codegen.fetch_specs.urllib.request.urlopen")
def test_resolve_latest_release_multiple_pages(mock_urlopen: MagicMock) -> None:
    page1 = _make_releases([f"v1.34.{i}" for i in range(100)])
    page2 = _make_releases(["v1.35.0", "v1.35.1"])
    mock_urlopen.side_effect = [
        _mock_urlopen(page1),
        _mock_urlopen(page2),
        _mock_urlopen([]),
    ]
    result = resolve_latest_release("1.35")
    assert result == "v1.35.1"


@patch("scripts.codegen.fetch_specs._download_file")
@patch("scripts.codegen.fetch_specs._github_get")
def test_download_specs_cache_miss(
    mock_github_get: MagicMock, mock_download: MagicMock, tmp_path: Path
) -> None:
    mock_github_get.return_value = [
        {"name": "api__v1_openapi.json"},
        {"name": "apis__apps__v1_openapi.json"},
        {"name": "README.md"},
    ]
    result = download_specs("v1.35.4", tmp_path)
    assert result.swagger_path == tmp_path / "v1.35.4" / "swagger.json"
    assert result.v3_dir == tmp_path / "v1.35.4" / "v3"
    assert mock_download.call_count == 3
    downloaded_names = [Path(c.args[1]).name for c in mock_download.call_args_list]
    assert "swagger.json" in downloaded_names
    assert "api__v1_openapi.json" in downloaded_names
    assert "apis__apps__v1_openapi.json" in downloaded_names


@patch("scripts.codegen.fetch_specs._download_file")
@patch("scripts.codegen.fetch_specs._github_get")
def test_download_specs_cache_hit(
    mock_github_get: MagicMock, mock_download: MagicMock, tmp_path: Path
) -> None:
    tag_dir = tmp_path / "v1.35.4"
    tag_dir.mkdir(parents=True)
    (tag_dir / "swagger.json").write_text("{}")
    (tag_dir / "v3").mkdir()
    (tag_dir / ".complete").touch()

    result = download_specs("v1.35.4", tmp_path)
    assert result.swagger_path == tag_dir / "swagger.json"
    mock_github_get.assert_not_called()
    mock_download.assert_not_called()


@patch("scripts.codegen.fetch_specs._download_file")
@patch("scripts.codegen.fetch_specs._github_get")
def test_download_specs_v3_only_json_files(
    mock_github_get: MagicMock, mock_download: MagicMock, tmp_path: Path
) -> None:
    mock_github_get.return_value = [
        {"name": "api__v1_openapi.json"},
        {"name": ".gitkeep"},
        {"name": "some_file.yaml"},
    ]
    download_specs("v1.35.4", tmp_path)
    v3_downloads = [c for c in mock_download.call_args_list if "v3/" in str(c.args[0])]
    assert len(v3_downloads) == 1
    assert "api__v1_openapi.json" in str(v3_downloads[0].args[0])


@patch("scripts.codegen.fetch_specs.download_specs")
@patch("scripts.codegen.fetch_specs.resolve_latest_release")
def test_fetch_all_specs(
    mock_resolve: MagicMock, mock_download: MagicMock, tmp_path: Path
) -> None:
    mock_resolve.side_effect = ["v1.35.4", "v1.36.1"]
    mock_download.side_effect = [
        DownloadedSpecs(
            swagger_path=tmp_path / "v1.35.4" / "swagger.json",
            v3_dir=tmp_path / "v1.35.4" / "v3",
        ),
        DownloadedSpecs(
            swagger_path=tmp_path / "v1.36.1" / "swagger.json",
            v3_dir=tmp_path / "v1.36.1" / "v3",
        ),
    ]
    results = fetch_all_specs(["1.35", "1.36"], tmp_path)
    assert len(results) == 2
    assert results["1.35"].swagger_path == tmp_path / "v1.35.4" / "swagger.json"
    assert results["1.36"].swagger_path == tmp_path / "v1.36.1" / "swagger.json"
    mock_resolve.assert_any_call("1.35")
    mock_resolve.assert_any_call("1.36")
    mock_download.assert_any_call("v1.35.4", tmp_path)
    mock_download.assert_any_call("v1.36.1", tmp_path)

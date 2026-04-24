from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from scripts.codegen.__main__ import app
from scripts.codegen.fetch_specs import DownloadedSpecs

runner = CliRunner()


@patch("scripts.codegen.__main__.run_verify")
@patch("scripts.codegen.__main__.run_generate")
@patch("scripts.codegen.fetch_specs.fetch_all_specs")
def test_regenerate_calls_fetch_generate_verify_in_order(
    mock_fetch: MagicMock,
    mock_generate: MagicMock,
    mock_verify: MagicMock,
    tmp_path: Path,
) -> None:
    specs_135 = DownloadedSpecs(
        swagger_path=tmp_path / "v1.35.4" / "swagger.json",
        v3_dir=tmp_path / "v1.35.4" / "v3",
    )
    specs_136 = DownloadedSpecs(
        swagger_path=tmp_path / "v1.36.1" / "swagger.json",
        v3_dir=tmp_path / "v1.36.1" / "v3",
    )
    mock_fetch.return_value = {"1.35": specs_135, "1.36": specs_136}
    mock_generate.side_effect = [
        tmp_path / "packages" / "kubex-k8s-1-35",
        tmp_path / "packages" / "kubex-k8s-1-36",
    ]
    mock_verify.return_value = 0

    result = runner.invoke(
        app,
        [
            "regenerate",
            "--versions",
            "1.35,1.36",
            "--cache-dir",
            str(tmp_path / "cache"),
        ],
    )

    assert result.exit_code == 0
    mock_fetch.assert_called_once_with(["1.35", "1.36"], tmp_path / "cache")
    assert mock_generate.call_count == 2
    assert mock_verify.call_count == 2

    gen_calls = mock_generate.call_args_list
    assert gen_calls[0].args[0] == specs_135.swagger_path
    assert gen_calls[0].args[1] == "1.35"
    assert gen_calls[0].kwargs["v3_dir"] == specs_135.v3_dir
    assert gen_calls[1].args[0] == specs_136.swagger_path
    assert gen_calls[1].args[1] == "1.36"
    assert gen_calls[1].kwargs["v3_dir"] == specs_136.v3_dir


@patch("scripts.codegen.__main__.run_verify")
@patch("scripts.codegen.__main__.run_generate")
@patch("scripts.codegen.fetch_specs.fetch_all_specs")
def test_regenerate_no_verify(
    mock_fetch: MagicMock,
    mock_generate: MagicMock,
    mock_verify: MagicMock,
    tmp_path: Path,
) -> None:
    specs = DownloadedSpecs(
        swagger_path=tmp_path / "v1.35.4" / "swagger.json",
        v3_dir=tmp_path / "v1.35.4" / "v3",
    )
    mock_fetch.return_value = {"1.35": specs}
    mock_generate.return_value = tmp_path / "packages" / "kubex-k8s-1-35"

    result = runner.invoke(
        app,
        ["regenerate", "--versions", "1.35", "--no-verify"],
    )

    assert result.exit_code == 0
    mock_generate.assert_called_once()
    mock_verify.assert_not_called()


def test_regenerate_no_versions() -> None:
    result = runner.invoke(app, ["regenerate", "--versions", ""])
    assert result.exit_code == 1
    assert "No versions specified" in result.output


@patch("scripts.codegen.__main__.run_verify")
@patch("scripts.codegen.__main__.run_generate")
@patch("scripts.codegen.fetch_specs.fetch_all_specs")
def test_regenerate_generate_failure_reports_in_summary(
    mock_fetch: MagicMock,
    mock_generate: MagicMock,
    mock_verify: MagicMock,
    tmp_path: Path,
) -> None:
    specs = DownloadedSpecs(
        swagger_path=tmp_path / "v1.35.4" / "swagger.json",
        v3_dir=tmp_path / "v1.35.4" / "v3",
    )
    mock_fetch.return_value = {"1.35": specs}
    mock_generate.side_effect = RuntimeError("codegen broke")

    result = runner.invoke(
        app,
        ["regenerate", "--versions", "1.35"],
    )

    assert result.exit_code == 1
    assert "generate failed" in result.output
    mock_verify.assert_not_called()


@patch("scripts.codegen.__main__.run_verify")
@patch("scripts.codegen.__main__.run_generate")
@patch("scripts.codegen.fetch_specs.fetch_all_specs")
def test_regenerate_verify_failure_reports_in_summary(
    mock_fetch: MagicMock,
    mock_generate: MagicMock,
    mock_verify: MagicMock,
    tmp_path: Path,
) -> None:
    specs = DownloadedSpecs(
        swagger_path=tmp_path / "v1.35.4" / "swagger.json",
        v3_dir=tmp_path / "v1.35.4" / "v3",
    )
    mock_fetch.return_value = {"1.35": specs}
    mock_generate.return_value = tmp_path / "packages" / "kubex-k8s-1-35"
    mock_verify.return_value = 1

    result = runner.invoke(
        app,
        ["regenerate", "--versions", "1.35"],
    )

    assert result.exit_code == 1
    assert "verify failed" in result.output


@patch("scripts.codegen.__main__.run_verify")
@patch("scripts.codegen.__main__.run_generate")
@patch("scripts.codegen.fetch_specs.fetch_all_specs")
def test_regenerate_passes_package_version_and_output(
    mock_fetch: MagicMock,
    mock_generate: MagicMock,
    mock_verify: MagicMock,
    tmp_path: Path,
) -> None:
    specs = DownloadedSpecs(
        swagger_path=tmp_path / "v1.35.4" / "swagger.json",
        v3_dir=tmp_path / "v1.35.4" / "v3",
    )
    mock_fetch.return_value = {"1.35": specs}
    mock_generate.return_value = tmp_path / "out" / "kubex-k8s-1-35"
    mock_verify.return_value = 0

    result = runner.invoke(
        app,
        [
            "regenerate",
            "--versions",
            "1.35",
            "--package-version",
            "2.0.0",
            "--output",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code == 0
    call_kwargs = mock_generate.call_args.kwargs
    assert call_kwargs["package_version"] == "2.0.0"
    assert call_kwargs["output"] == tmp_path / "out"


@pytest.mark.parametrize(
    ("versions_arg", "expected_parsed"),
    [
        ("1.35", ["1.35"]),
        ("1.35,1.36,1.37", ["1.35", "1.36", "1.37"]),
        ("1.35 , 1.36 ", ["1.35", "1.36"]),
    ],
)
@patch("scripts.codegen.__main__.run_verify")
@patch("scripts.codegen.__main__.run_generate")
@patch("scripts.codegen.fetch_specs.fetch_all_specs")
def test_regenerate_version_parsing(
    mock_fetch: MagicMock,
    mock_generate: MagicMock,
    mock_verify: MagicMock,
    versions_arg: str,
    expected_parsed: list[str],
    tmp_path: Path,
) -> None:
    mock_fetch.return_value = {
        v: DownloadedSpecs(
            swagger_path=tmp_path / f"v{v}.0" / "swagger.json",
            v3_dir=tmp_path / f"v{v}.0" / "v3",
        )
        for v in expected_parsed
    }
    mock_generate.return_value = tmp_path / "pkg"
    mock_verify.return_value = 0

    result = runner.invoke(
        app,
        ["regenerate", "--versions", versions_arg],
    )

    assert result.exit_code == 0
    actual_versions = mock_fetch.call_args.args[0]
    assert actual_versions == expected_parsed

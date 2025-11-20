from __future__ import annotations

from pathlib import Path

from gmake2cmake import cli


def _run_fixture(name: str, tmp_path: Path, extra_args: list[str] | None = None) -> Path:
    fixture = Path("tests/e2e/fixtures") / name
    output = tmp_path / f"out-{name}"
    argv = ["--source-dir", str(fixture), "--config", str(fixture / "config.yaml"), "--output-dir", str(output)]
    if extra_args:
        argv.extend(extra_args)
    exit_code = cli.run(argv)
    assert exit_code == 0
    return output


def _read_expected(fixture: str, name: str) -> str:
    path = Path("tests/e2e/fixtures") / fixture / "golden" / name
    return path.read_text()


def _assert_matches(actual_path: Path, fixture: str, expected_name: str) -> None:
    expected = _read_expected(fixture, expected_name).rstrip()
    actual = actual_path.read_text().rstrip()
    assert actual == expected


def test_ts21_global_config(tmp_path):
    output = _run_fixture("ts21-global", tmp_path)
    _assert_matches(output / "CMakeLists.txt", "ts21-global", "CMakeLists.txt")
    _assert_matches(output / "ProjectGlobalConfig.cmake", "ts21-global", "ProjectGlobalConfig.cmake")
    _assert_matches(output / "src/CMakeLists.txt", "ts21-global", "src_CMakeLists.txt")


def test_ts22_alias_linking(tmp_path):
    output = _run_fixture("ts22-alias", tmp_path)
    _assert_matches(output / "CMakeLists.txt", "ts22-alias", "CMakeLists.txt")
    _assert_matches(output / "app/CMakeLists.txt", "ts22-alias", "app_CMakeLists.txt")


def test_ts23_interface_and_imported(tmp_path):
    output = _run_fixture("ts23-interface-imported", tmp_path)
    _assert_matches(output / "CMakeLists.txt", "ts23-interface-imported", "CMakeLists.txt")
    _assert_matches(output / "include/CMakeLists.txt", "ts23-interface-imported", "include_CMakeLists.txt")
    _assert_matches(output / "vendor/CMakeLists.txt", "ts23-interface-imported", "vendor_CMakeLists.txt")


def test_ts24_packaging_outputs(tmp_path):
    output = _run_fixture("ts24-packaging", tmp_path, extra_args=["--with-packaging"])
    _assert_matches(output / "CMakeLists.txt", "ts24-packaging", "CMakeLists.txt")
    _assert_matches(output / "src/CMakeLists.txt", "ts24-packaging", "src_CMakeLists.txt")
    _assert_matches(output / "Packaging.cmake", "ts24-packaging", "Packaging.cmake")
    _assert_matches(output / "TS24Config.cmake", "ts24-packaging", "TS24Config.cmake")
    _assert_matches(output / "TS24ConfigVersion.cmake", "ts24-packaging", "TS24ConfigVersion.cmake")


def test_ts25_global_vs_target_flags(tmp_path):
    output = _run_fixture("ts25-flags", tmp_path)
    _assert_matches(output / "CMakeLists.txt", "ts25-flags", "CMakeLists.txt")
    _assert_matches(output / "ProjectGlobalConfig.cmake", "ts25-flags", "ProjectGlobalConfig.cmake")
    _assert_matches(output / "src/CMakeLists.txt", "ts25-flags", "src_CMakeLists.txt")

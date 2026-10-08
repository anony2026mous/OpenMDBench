"""Security and resource quota contracts for declarative V2 scenario packages."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any

import pytest
from openmdbench.scenarios import declarative_v2

DECLARATIVE: Any = declarative_v2


def _limits(**changes: Any) -> Any:
    limits_type: Any = DECLARATIVE.PackageLimitsV2
    values = {
        "max_entries": 8,
        "max_entry_bytes": 1024,
        "max_total_bytes": 4096,
        "max_yaml_depth": 8,
        "max_yaml_nodes": 128,
        "max_yaml_aliases": 0,
        "max_compression_ratio": 20.0,
    }
    values.update(changes)
    return limits_type(**values)


def _manifest(extra: bytes = b"") -> bytes:
    return b"schema_version: package@2.0\nscenario:\n  schema_version: '2.0'\n" + extra


def _assert_package_error(call: Any, code: str) -> None:
    with pytest.raises(declarative_v2.CompilerErrorV2) as captured:
        call()
    assert captured.value.code == code
    assert captured.value.file and captured.value.reason and captured.value.suggestion


@pytest.mark.parametrize(
    ("entries", "limits", "code"),
    (
        (
            [("scenario.yaml", _manifest()), ("a.yaml", b"a: 1"), ("b.yaml", b"b: 2")],
            {"max_entries": 2},
            "package.entry_count_exceeded",
        ),
        (
            [("scenario.yaml", _manifest(b"x: " + b"a" * 100))],
            {"max_entry_bytes": 32},
            "package.entry_size_exceeded",
        ),
        (
            [("scenario.yaml", _manifest()), ("a.yaml", b"a: " + b"x" * 80)],
            {"max_total_bytes": 64},
            "package.total_size_exceeded",
        ),
        ([("scenario.yaml", b"\xff\xfe")], {}, "package.encoding_invalid"),
    ),
)
def test_from_entries_enforces_count_size_total_and_utf8(
    entries: list[tuple[str, bytes]], limits: dict[str, Any], code: str
) -> None:
    _assert_package_error(
        lambda: DECLARATIVE.ScenarioPackageV2.from_entries(entries, limits=_limits(**limits)),
        code,
    )


@pytest.mark.parametrize(
    ("yaml_body", "limits", "code"),
    (
        (b"a:\n  b:\n    c:\n      d: 1\n", {"max_yaml_depth": 2}, "package.yaml_depth_exceeded"),
        (b"a: [1,2,3,4,5,6,7,8]\n", {"max_yaml_nodes": 4}, "package.yaml_nodes_exceeded"),
        (b"a: &x [1]\nb: *x\n", {}, "package.yaml_alias_forbidden"),
        (b"x: !!python/object/apply:os.system ['id']\n", {}, "package.yaml_tag_forbidden"),
        (b"x: 1\nx: 2\n", {}, "package.duplicate_key"),
    ),
)
def test_yaml_parser_enforces_structural_quotas_and_safe_data_only(
    yaml_body: bytes, limits: dict[str, Any], code: str
) -> None:
    _assert_package_error(
        lambda: DECLARATIVE.ScenarioPackageV2.from_entries(
            [("scenario.yaml", _manifest(yaml_body))], limits=_limits(**limits)
        ),
        code,
    )


def _archive(entries: list[tuple[zipfile.ZipInfo | str, bytes]]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries:
            archive.writestr(name, data)
    return stream.getvalue()


def _mark_encrypted(data: bytes) -> bytes:
    forged = bytearray(data)
    for signature, flag_offset in ((b"PK\x03\x04", 6), (b"PK\x01\x02", 8)):
        start = 0
        while (index := forged.find(signature, start)) >= 0:
            flags = int.from_bytes(forged[index + flag_offset : index + flag_offset + 2], "little")
            forged[index + flag_offset : index + flag_offset + 2] = (flags | 1).to_bytes(
                2, "little"
            )
            start = index + 4
    return bytes(forged)


@pytest.mark.parametrize("name", ("../scenario.yaml", "/scenario.yaml", "C:/scenario.yaml"))
def test_archive_rejects_escaping_and_absolute_paths(name: str) -> None:
    data = _archive([(name, _manifest())])
    _assert_package_error(
        lambda: DECLARATIVE.ScenarioPackageV2.from_archive(data, limits=_limits()),
        "package.archive_path_invalid",
    )


def test_archive_rejects_duplicate_paths_symlink_and_unknown_role() -> None:
    duplicate = _archive([("scenario.yaml", _manifest()), ("scenario.yaml", _manifest())])
    _assert_package_error(
        lambda: DECLARATIVE.ScenarioPackageV2.from_archive(duplicate, limits=_limits()),
        "package.archive_duplicate",
    )
    link = zipfile.ZipInfo("scenario.yaml")
    link.external_attr = 0o120777 << 16
    symlink = _archive([(link, b"target")])
    _assert_package_error(
        lambda: DECLARATIVE.ScenarioPackageV2.from_archive(symlink, limits=_limits()),
        "package.archive_symlink",
    )
    _assert_package_error(
        lambda: DECLARATIVE.ScenarioPackageV2.from_entries(
            [("scenario.yaml", _manifest(b"roles: {mystery: x.yaml}\n"))], limits=_limits()
        ),
        "package.role_unknown",
    )


def test_archive_rejects_compression_bomb_corruption_and_encryption() -> None:
    bomb = _archive([("scenario.yaml", _manifest(b"x: " + b"a" * 5000))])
    _assert_package_error(
        lambda: DECLARATIVE.ScenarioPackageV2.from_archive(
            bomb,
            limits=_limits(max_entry_bytes=10000, max_total_bytes=10000, max_compression_ratio=2),
        ),
        "package.archive_ratio_exceeded",
    )
    corrupted = bomb[:-8]
    _assert_package_error(
        lambda: DECLARATIVE.ScenarioPackageV2.from_archive(corrupted, limits=_limits()),
        "package.archive_corrupt",
    )
    encrypted = _mark_encrypted(_archive([("scenario.yaml", _manifest())]))
    _assert_package_error(
        lambda: DECLARATIVE.ScenarioPackageV2.from_archive(encrypted, limits=_limits()),
        "package.archive_encrypted",
    )


def test_directory_loader_rejects_symlinked_manifest_and_include(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside.yaml"
    outside.write_bytes(_manifest())
    (tmp_path / "scenario.yaml").symlink_to(outside)
    _assert_package_error(
        lambda: DECLARATIVE.ScenarioPackageV2.from_directory(tmp_path, limits=_limits()),
        "package.directory_symlink",
    )


def test_directory_loader_rejects_symlinked_include(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside.yaml"
    outside.write_bytes(b"entities: []\n")
    (tmp_path / "scenario.yaml").write_bytes(
        b"schema_version: package@2.0\nincludes: [entities.yaml]\n"
    )
    (tmp_path / "entities.yaml").symlink_to(outside)
    _assert_package_error(
        lambda: DECLARATIVE.ScenarioPackageV2.from_directory(tmp_path, limits=_limits()),
        "package.directory_symlink",
    )

"""Fail-closed guards for the private applicant acceptance loopback.

This module deliberately has no Django imports.  Call :func:`build_config`
before migrations, fixture creation, or application setup so unsafe scope is
rejected before any database or filesystem write can occur.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
from typing import Mapping
from urllib.parse import unquote, urlparse


class GuardError(RuntimeError):
    """The requested acceptance run is outside its approved private scope."""


@dataclass(frozen=True)
class SharedLoopbackConfig:
    expected_sha: str
    expected_source_tree_sha256: str
    source_dir: Path
    run_id: str
    acceptance_root: Path
    media_dir: Path
    output_path: Path
    bind_host: str
    bind_port: int
    image: str
    candidate_container: str
    clone_database: str
    owner_role: str
    app_role: str
    owner_url: str
    app_url: str


_SHA_RE = re.compile(r"[0-9a-f]{40}")
_TREE_SHA_RE = re.compile(r"[0-9a-f]{64}")
_RUN_RE = re.compile(r"applicant-\d{8}T\d{6}Z-[0-9a-f]{8}")
_SAFE_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]*")
_IMAGE_ID_RE = re.compile(r"sha256:[0-9a-f]{64}")


def _required(env: Mapping[str, str], key: str) -> str:
    value = env.get(key, "")
    if not value:
        raise GuardError(f"missing required acceptance value: {key}")
    return value


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def source_tree_sha256(root: Path) -> str:
    """Return a deterministic digest of source paths and file bytes."""

    root = Path(root).resolve()
    if not root.is_dir():
        raise GuardError("source tree directory does not exist")

    digest = hashlib.sha256()
    files: list[Path] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in {".git", ".venv", "__pycache__"} for part in relative.parts):
            continue
        if path.is_file() and path.suffix != ".pyc":
            files.append(path)

    for path in sorted(files, key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        with path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
    return digest.hexdigest()


def _database_identity(url: str, expected_role: str) -> tuple[str, str, str, int]:
    parsed = urlparse(url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise GuardError("acceptance database URL must use PostgreSQL")
    role = unquote(parsed.username or "")
    if role != expected_role:
        raise GuardError(f"acceptance database URL must login as {expected_role}")
    if not parsed.password:
        raise GuardError(f"acceptance database URL for {expected_role} requires a password")
    database = unquote(parsed.path.lstrip("/"))
    if database == "ctm" or not database.startswith("ctm_accept_"):
        raise GuardError("acceptance database must be a ctm_accept_ clone, never shared ctm")
    if not parsed.hostname:
        raise GuardError("acceptance database URL requires a host")
    try:
        port = parsed.port or 5432
    except ValueError as error:
        raise GuardError("acceptance database URL has an invalid port") from error
    return role, database, parsed.hostname, port


def build_config(
    env: Mapping[str, str],
    *,
    release_base: Path = Path("/opt/ctm/releases"),
    acceptance_base: Path = Path("/srv/ctm/acceptance"),
) -> SharedLoopbackConfig:
    """Validate all private-loopback inputs without performing writes."""

    expected_sha = _required(env, "CTM_ACCEPT_EXPECTED_SHA")
    if not _SHA_RE.fullmatch(expected_sha):
        raise GuardError("expected commit SHA must be exactly 40 lowercase hex characters")

    source_dir = Path(_required(env, "CTM_ACCEPT_SOURCE_DIR")).resolve()
    expected_source = (Path(release_base).resolve() / expected_sha[:7]).resolve()
    if source_dir != expected_source:
        raise GuardError("source directory must be the exact immutable release path")
    if not source_dir.is_dir():
        raise GuardError("source directory does not exist")

    expected_tree_hash = _required(env, "CTM_ACCEPT_EXPECTED_SOURCE_TREE_SHA256")
    if not _TREE_SHA_RE.fullmatch(expected_tree_hash):
        raise GuardError("expected source tree SHA256 is invalid")
    actual_tree_hash = source_tree_sha256(source_dir)
    if actual_tree_hash != expected_tree_hash:
        raise GuardError("source tree SHA256 does not match the approved release")

    run_id = _required(env, "CTM_ACCEPT_RUN_ID")
    if not _RUN_RE.fullmatch(run_id):
        raise GuardError("acceptance run id is invalid")

    acceptance_base = Path(acceptance_base).resolve()
    acceptance_root = Path(_required(env, "CTM_ACCEPT_ROOT")).resolve()
    if acceptance_root != acceptance_base / run_id:
        raise GuardError("acceptance artifact root must exactly match its protected run directory")
    if not acceptance_root.is_dir():
        raise GuardError("acceptance artifact root does not exist")
    if os.name == "posix" and stat.S_IMODE(acceptance_root.stat().st_mode) != 0o700:
        raise GuardError("acceptance artifact root must have mode 0700")

    media_dir = Path(_required(env, "CTM_ACCEPT_MEDIA")).resolve()
    output_path = Path(_required(env, "CTM_ACCEPT_OUTPUT")).resolve()
    if not _is_within(media_dir, acceptance_root) or media_dir == acceptance_root:
        raise GuardError("media artifact path must stay below the protected run directory")
    if not _is_within(output_path, acceptance_root) or output_path.parent != acceptance_root:
        raise GuardError("result artifact path must stay directly in the protected run directory")

    bind = _required(env, "CTM_ACCEPT_BIND")
    if bind != "127.0.0.1:0":
        raise GuardError("acceptance server must bind only to ephemeral IPv4 loopback")

    image = _required(env, "CTM_ACCEPT_IMAGE")
    candidate_container = _required(env, "CTM_ACCEPT_CANDIDATE_CONTAINER")
    if not _SAFE_NAME_RE.fullmatch(image) or not _SAFE_NAME_RE.fullmatch(candidate_container):
        raise GuardError("candidate image and container names must be literal safe identifiers")
    if image != f"ctm-application:{expected_sha[:7]}":
        raise GuardError("candidate image tag does not match the approved release")
    if candidate_container != f"ctm-test-candidate-{expected_sha[:7]}":
        raise GuardError("candidate container does not match the approved release")

    owner_url = _required(env, "CTM_APPLICANT_POSTGRES_OWNER_URL")
    app_url = _required(env, "CTM_APPLICANT_POSTGRES_APP_URL")
    owner_role, owner_database, owner_host, owner_port = _database_identity(owner_url, "ctm_owner")
    app_role, app_database, app_host, app_port = _database_identity(app_url, "ctm_app")
    if (owner_database, owner_host, owner_port) != (app_database, app_host, app_port):
        raise GuardError("owner and app URLs must address the same acceptance clone")
    expected_clone = "ctm_accept_" + re.sub(r"[^a-z0-9]+", "_", run_id.lower())
    if owner_database != expected_clone:
        raise GuardError("database URLs must address the exact run clone")

    return SharedLoopbackConfig(
        expected_sha=expected_sha,
        expected_source_tree_sha256=expected_tree_hash,
        source_dir=source_dir,
        run_id=run_id,
        acceptance_root=acceptance_root,
        media_dir=media_dir,
        output_path=output_path,
        bind_host="127.0.0.1",
        bind_port=0,
        image=image,
        candidate_container=candidate_container,
        clone_database=owner_database,
        owner_role=owner_role,
        app_role=app_role,
        owner_url=owner_url,
        app_url=app_url,
    )


def validate_image_evidence(
    *,
    candidate_image_id: str,
    candidate_image_tag: str,
    tagged_image_id: str,
    expected_tag: str,
) -> dict[str, str]:
    """Prove the running candidate and expected tag share one image ID."""

    if not _IMAGE_ID_RE.fullmatch(candidate_image_id):
        raise GuardError("candidate image ID is invalid")
    if not _IMAGE_ID_RE.fullmatch(tagged_image_id):
        raise GuardError("tagged image ID is invalid")
    if candidate_image_tag != expected_tag:
        raise GuardError("candidate image tag does not match the expected image")
    if candidate_image_id != tagged_image_id:
        raise GuardError("candidate and tagged image IDs do not match")
    return {"image_id": candidate_image_id, "image_tag": expected_tag}


def inspect_image_evidence(config: SharedLoopbackConfig) -> dict[str, str]:
    """Read immutable image evidence without changing Docker state."""

    candidate_image_id = subprocess.check_output(
        ["docker", "inspect", "--format", "{{.Image}}", config.candidate_container],
        text=True,
    ).strip()
    candidate_image_tag = subprocess.check_output(
        ["docker", "inspect", "--format", "{{.Config.Image}}", config.candidate_container],
        text=True,
    ).strip()
    tagged_image_id = subprocess.check_output(
        ["docker", "image", "inspect", "--format", "{{.Id}}", config.image],
        text=True,
    ).strip()
    return validate_image_evidence(
        candidate_image_id=candidate_image_id,
        candidate_image_tag=candidate_image_tag,
        tagged_image_id=tagged_image_id,
        expected_tag=config.image,
    )


def redact_runtime_environment(env: Mapping[str, str]) -> dict[str, str]:
    """Return a copy with credentials removed before Django setup."""

    sensitive_markers = ("SECRET", "PASSWORD", "TOKEN", "CREDENTIAL", "_KEY")
    external_prefixes = ("STRIPE_", "EMAIL_", "MICROSOFT_", "GOOGLE_", "APPLE_", "MEILI_")
    return {
        key: value
        for key, value in env.items()
        if not any(marker in key.upper() for marker in sensitive_markers)
        and not key.upper().startswith(external_prefixes)
        and key not in {"CTM_APPLICANT_POSTGRES_OWNER_URL", "CTM_APPLICANT_POSTGRES_APP_URL"}
    }


def safe_preflight_evidence(
    config: SharedLoopbackConfig, image_evidence: Mapping[str, str]
) -> dict[str, object]:
    """Return evidence suitable for logs and acceptance artifacts."""

    return {
        "expected_sha": config.expected_sha,
        "source_dir": str(config.source_dir),
        "source_tree_sha256": config.expected_source_tree_sha256,
        "run_id": config.run_id,
        "acceptance_root": str(config.acceptance_root),
        "clone_database": config.clone_database,
        "owner_role": config.owner_role,
        "app_role": config.app_role,
        "bind": f"{config.bind_host}:{config.bind_port}",
        **image_evidence,
    }


def main() -> int:
    config = build_config(os.environ)
    evidence = safe_preflight_evidence(config, inspect_image_evidence(config))
    print(json.dumps({"preflight": "passed", **evidence}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


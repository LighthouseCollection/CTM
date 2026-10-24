import os
import stat
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from applicant_shared_loopback import (
    GuardError,
    build_config,
    redact_runtime_environment,
    safe_preflight_evidence,
    source_tree_sha256,
    validate_image_evidence,
)


def fixture_paths(tmp_path):
    release_base = tmp_path / "releases"
    source = release_base / "dccbd63"
    source.mkdir(parents=True)
    (source / "manage.py").write_text("print('fixture')\n", encoding="utf-8")
    (source / "ctm").mkdir()
    (source / "ctm" / "settings.py").write_text("SETTING = True\n", encoding="utf-8")
    acceptance_base = tmp_path / "acceptance"
    run_id = "applicant-20261022T010203Z-a1b2c3d4"
    root = acceptance_base / run_id
    root.mkdir(parents=True)
    root.chmod(stat.S_IRWXU)
    media = root / "media"
    media.mkdir()
    output = root / "result.json"
    return release_base, source, acceptance_base, run_id, root, media, output


def valid_environment(tmp_path):
    release_base, source, acceptance_base, run_id, root, media, output = fixture_paths(tmp_path)
    env = {
        "CTM_ACCEPT_EXPECTED_SHA": "dccbd6380abfdc47f84b877f8d63fb2081e9a2ad",
        "CTM_ACCEPT_EXPECTED_SOURCE_TREE_SHA256": source_tree_sha256(source),
        "CTM_ACCEPT_SOURCE_DIR": str(source),
        "CTM_ACCEPT_RUN_ID": run_id,
        "CTM_ACCEPT_ROOT": str(root),
        "CTM_ACCEPT_MEDIA": str(media),
        "CTM_ACCEPT_OUTPUT": str(output),
        "CTM_ACCEPT_BIND": "127.0.0.1:0",
        "CTM_ACCEPT_IMAGE": "ctm-application:dccbd63",
        "CTM_ACCEPT_CANDIDATE_CONTAINER": "ctm-test-candidate-dccbd63",
        "CTM_APPLICANT_POSTGRES_OWNER_URL":
            "postgresql://ctm_owner:owner-secret@postgres:5432/ctm_accept_applicant_20261022t010203z_a1b2c3d4",
        "CTM_APPLICANT_POSTGRES_APP_URL":
            "postgresql://ctm_app:app-secret@postgres:5432/ctm_accept_applicant_20261022t010203z_a1b2c3d4",
    }
    return env, release_base, acceptance_base


def test_build_config_accepts_exact_clone_and_protected_paths(tmp_path):
    env, release_base, acceptance_base = valid_environment(tmp_path)
    config = build_config(env, release_base=release_base, acceptance_base=acceptance_base)
    assert config.clone_database == "ctm_accept_applicant_20261022t010203z_a1b2c3d4"
    assert config.owner_role == "ctm_owner"
    assert config.app_role == "ctm_app"
    assert config.bind_host == "127.0.0.1" and config.bind_port == 0
    assert config.output_path.parent == config.acceptance_root


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("CTM_ACCEPT_BIND", "0.0.0.0:8000", "loopback"),
        ("CTM_ACCEPT_RUN_ID", "../escape", "run id"),
        ("CTM_APPLICANT_POSTGRES_OWNER_URL", "postgresql://ctm_owner:x@postgres:5432/ctm", "clone"),
        ("CTM_APPLICANT_POSTGRES_APP_URL", "postgresql://ctm_owner:x@postgres:5432/ctm_accept_applicant_20261022t010203z_a1b2c3d4", "ctm_app"),
        ("CTM_ACCEPT_EXPECTED_SOURCE_TREE_SHA256", "0" * 64, "source tree"),
    ],
)
def test_build_config_rejects_unsafe_scope(tmp_path, key, value, message):
    env, release_base, acceptance_base = valid_environment(tmp_path)
    env[key] = value
    with pytest.raises(GuardError, match=message):
        build_config(env, release_base=release_base, acceptance_base=acceptance_base)


def test_build_config_rejects_artifact_escape_and_loose_permissions(tmp_path):
    env, release_base, acceptance_base = valid_environment(tmp_path)
    env["CTM_ACCEPT_OUTPUT"] = str(tmp_path / "escaped.json")
    with pytest.raises(GuardError, match="artifact"):
        build_config(env, release_base=release_base, acceptance_base=acceptance_base)

    if os.name == "posix":
        env, release_base, acceptance_base = valid_environment(tmp_path / "loose")
        Path(env["CTM_ACCEPT_ROOT"]).chmod(0o755)
        with pytest.raises(GuardError, match="0700"):
            build_config(env, release_base=release_base, acceptance_base=acceptance_base)


def test_build_config_rejects_a_retained_clone_from_another_run(tmp_path):
    env, release_base, acceptance_base = valid_environment(tmp_path)
    retained = "ctm_accept_applicant_20261021t010203z_deadbeef"
    env["CTM_APPLICANT_POSTGRES_OWNER_URL"] = f"postgresql://ctm_owner:x@postgres:5432/{retained}"
    env["CTM_APPLICANT_POSTGRES_APP_URL"] = f"postgresql://ctm_app:x@postgres:5432/{retained}"
    with pytest.raises(GuardError, match="exact run clone"):
        build_config(env, release_base=release_base, acceptance_base=acceptance_base)


def test_source_hash_ignores_runtime_cache_but_detects_source_change(tmp_path):
    env, release_base, acceptance_base = valid_environment(tmp_path)
    source = Path(env["CTM_ACCEPT_SOURCE_DIR"])
    before = source_tree_sha256(source)
    cache = source / "ctm" / "__pycache__"
    cache.mkdir()
    (cache / "settings.cpython-312.pyc").write_bytes(b"cache")
    assert source_tree_sha256(source) == before
    (source / "ctm" / "settings.py").write_text("SETTING = False\n", encoding="utf-8")
    assert source_tree_sha256(source) != before


def test_image_evidence_requires_candidate_and_tag_to_share_immutable_id():
    evidence = validate_image_evidence(
        candidate_image_id="sha256:" + "a" * 64,
        candidate_image_tag="ctm-application:dccbd63",
        tagged_image_id="sha256:" + "a" * 64,
        expected_tag="ctm-application:dccbd63",
    )
    assert evidence["image_id"] == "sha256:" + "a" * 64
    with pytest.raises(GuardError, match="image"):
        validate_image_evidence(
            candidate_image_id="sha256:" + "a" * 64,
            candidate_image_tag="ctm-application:dccbd63",
            tagged_image_id="sha256:" + "b" * 64,
            expected_tag="ctm-application:dccbd63",
        )


def test_safe_preflight_evidence_never_serializes_database_urls(tmp_path):
    env, release_base, acceptance_base = valid_environment(tmp_path)
    config = build_config(env, release_base=release_base, acceptance_base=acceptance_base)
    evidence = safe_preflight_evidence(
        config,
        {"image_id": "sha256:" + "a" * 64, "image_tag": config.image},
    )
    serialized = repr(evidence)
    assert "owner-secret" not in serialized
    assert "app-secret" not in serialized
    assert "owner_url" not in evidence and "app_url" not in evidence


def test_redacted_environment_removes_external_credentials_without_mutating_input():
    original = {
        "PATH": os.environ.get("PATH", ""),
        "DJANGO_SECRET_KEY": "runtime-secret",
        "STRIPE_SECRET_KEY": "stripe-secret",
        "STRIPE_WEBHOOK_SECRET": "webhook-secret",
        "EMAIL_HOST_PASSWORD": "mail-secret",
        "MICROSOFT_CLIENT_SECRET": "microsoft-secret",
        "MICROSOFT_CLIENT_ID": "microsoft-id",
        "GOOGLE_CLIENT_SECRET": "google-secret",
        "GOOGLE_CLIENT_ID": "google-id",
        "APPLE_PRIVATE_KEY": "apple-secret",
        "APPLE_CLIENT_ID": "apple-id",
        "EMAIL_HOST_USER": "mailer",
        "STRIPE_PUBLISHABLE_KEY": "stripe-public-value",
        "MEILI_MASTER_KEY": "search-secret",
        "CTM_ACCEPT_RUN_ID": "safe-run",
    }
    sanitized = redact_runtime_environment(original)
    assert sanitized["PATH"] == original["PATH"]
    assert sanitized["CTM_ACCEPT_RUN_ID"] == "safe-run"
    for key in original:
        if key.startswith(("DJANGO_SECRET", "STRIPE_", "EMAIL_", "MICROSOFT_", "GOOGLE_", "APPLE_", "MEILI_")):
            assert key not in sanitized
    assert original["STRIPE_SECRET_KEY"] == "stripe-secret"


"""D-0023: /version.json - four public facts, nothing else."""

import tomllib
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET


def _build_dir() -> Path:
    return Path(getattr(settings, "CTM_BUILD_INFO_DIR", settings.BASE_DIR))


def _version(build_dir: Path) -> str | None:
    # The image carries a copy in the build dir; a checkout has it at BASE_DIR.
    for path in (build_dir / "pyproject.toml", Path(settings.BASE_DIR) / "pyproject.toml"):
        if path.is_file():
            return tomllib.loads(path.read_text(encoding="utf-8"))["project"]["version"]
    return None


def _build_time(build_dir: Path) -> str | None:
    path = build_dir / "BUILD_TIME"
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8").strip() or None


@require_GET
def version(request):
    build_dir = _build_dir()
    return JsonResponse(
        {
            "name": "CTM 3.0",
            "version": _version(build_dir),
            "plenix_version": settings.PLENIX_BASE.rstrip("/").rsplit("/", 1)[-1],
            "build_time": _build_time(build_dir),
        }
    )

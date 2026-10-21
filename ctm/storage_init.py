"""One-shot private-volume ownership setup; never changes existing file owners."""

import os
from pathlib import Path


def main():
    if os.geteuid() != 0:
        raise SystemExit("Storage initialization requires the one-shot root service.")
    path = Path(os.environ.get("CTM_MEDIA_ROOT", "/srv/ctm/media"))
    if not path.is_absolute():
        raise SystemExit("Private storage root must be absolute.")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fchown(descriptor, 1000, 1000)
        os.fchmod(descriptor, 0o700)
    finally:
        os.close(descriptor)
    print("Private storage directory prepared; existing files unchanged.")


if __name__ == "__main__":
    main()

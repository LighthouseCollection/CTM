#!/usr/bin/env bash
# Install the GitHub Actions runner that deploys every merge to main to the live
# site (#90). Run once, as root, on VM 107:
#
#   RUNNER_TOKEN=<one-time code from GitHub> bash install-runner.sh
#
# The code comes from GitHub -> LighthouseCollection/CTM -> Settings -> Actions
# -> Runners -> New self-hosted runner (valid one hour). It is used once to
# register the runner and is not stored.
#
# What it sets up (idempotent):
#   - user ctm-runner: no docker group, no general sudo
#   - runner "ctm-vm" (labels self-hosted, ctm-vm) as a systemd service
#   - /usr/local/sbin/ctm-live-update <sha>: root-owned; refuses anything that is
#     not a commit on main, then runs that commit's deploy/live-update.sh
#   - sudoers: ctm-runner may run exactly that one command as root
set -euo pipefail

REPO="LighthouseCollection/CTM"
RUNNER_USER="ctm-runner"
RUNNER_DIR="/home/$RUNNER_USER/actions-runner"

[[ $EUID -eq 0 ]] || { echo "run as root"; exit 2; }
[[ -n "${RUNNER_TOKEN:-}" ]] || { echo "set RUNNER_TOKEN to the code from GitHub's New self-hosted runner page"; exit 2; }

# --- 1. user -----------------------------------------------------------------
id "$RUNNER_USER" >/dev/null 2>&1 || useradd -m -s /bin/bash "$RUNNER_USER"
echo "user $RUNNER_USER ready"

# --- 2. the one root command the runner may use --------------------------------
cat >/usr/local/sbin/ctm-live-update <<'WRAPPER'
#!/usr/bin/env bash
# Deploy one commit of main to the live site. Called by the CTM deploy workflow.
set -euo pipefail
REPO="LighthouseCollection/CTM"
sha="${1:-}"
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || { echo "usage: ctm-live-update <40-character commit id>"; exit 2; }
# Only commits that are on main (identical to it or behind it).
status="$(curl -fsSL "https://api.github.com/repos/$REPO/compare/$sha...main" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status",""))')"
[[ "$status" == "identical" || "$status" == "ahead" ]] || { echo "refused: $sha is not on main ($status)"; exit 2; }
script="/root/live-update-$sha.sh"
curl -fsSL "https://raw.githubusercontent.com/$REPO/$sha/deploy/live-update.sh" -o "$script"
exec bash "$script" "$sha"
WRAPPER
chown root:root /usr/local/sbin/ctm-live-update
chmod 755 /usr/local/sbin/ctm-live-update
echo "$RUNNER_USER ALL=(root) NOPASSWD: /usr/local/sbin/ctm-live-update" >/etc/sudoers.d/ctm-runner
chmod 440 /etc/sudoers.d/ctm-runner
visudo -cf /etc/sudoers.d/ctm-runner >/dev/null
echo "deploy command /usr/local/sbin/ctm-live-update ready"

# --- 3. runner (latest release, checksum from the release notes) ----------------
if [[ ! -f "$RUNNER_DIR/.runner" ]]; then
  release="$(curl -fsSL https://api.github.com/repos/actions/runner/releases/latest)"
  version="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"].lstrip("v"))' <<<"$release")"
  sum="$(grep -oE '<!-- BEGIN SHA linux-x64 -->[0-9a-f]{64}' <<<"$release" | grep -oE '[0-9a-f]{64}$' | head -1)"
  [[ -n "$version" && -n "$sum" ]] || { echo "could not read the runner release"; exit 1; }
  tarball="actions-runner-linux-x64-$version.tar.gz"
  install -d -o "$RUNNER_USER" -g "$RUNNER_USER" "$RUNNER_DIR"
  curl -fsSL "https://github.com/actions/runner/releases/download/v$version/$tarball" -o "/tmp/$tarball"
  echo "$sum  /tmp/$tarball" | sha256sum -c - >/dev/null || { echo "runner download checksum mismatch"; exit 1; }
  tar -xzf "/tmp/$tarball" -C "$RUNNER_DIR"
  rm -f "/tmp/$tarball"
  chown -R "$RUNNER_USER:$RUNNER_USER" "$RUNNER_DIR"
  "$RUNNER_DIR/bin/installdependencies.sh" >/dev/null
  su - "$RUNNER_USER" -c "cd '$RUNNER_DIR' && ./config.sh --unattended --url 'https://github.com/$REPO' \
    --token '$RUNNER_TOKEN' --name ctm-vm --labels ctm-vm --work _work --replace" >/dev/null
  echo "runner $version registered as ctm-vm"
else
  echo "runner already registered"
fi
unset RUNNER_TOKEN

cd "$RUNNER_DIR"
./svc.sh install "$RUNNER_USER" >/dev/null 2>&1 || true   # fails harmlessly when already installed
./svc.sh start >/dev/null 2>&1 || true
systemctl is-active --quiet "actions.runner.${REPO/\//-}.ctm-vm.service" && echo "DONE: runner ctm-vm is running"

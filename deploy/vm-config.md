# CTM VM configuration

## VM identity

| Property | Value |
|---|---|
| VMID | 107 |
| Name | CTM |
| Node | pve |
| OS | Debian 12.14 (bookworm) |
| IP | 10.0.0.40/22 |
| Gateway | 10.0.0.1 |
| DNS | 10.0.0.1 (AdGuard on UDM SE) |
| Hostname | ctm |
| FQDN | ctm.lighthouseway.org |

## Resources

| Resource | Allocation |
|---|---|
| CPU | 8 vCPU (host type) |
| RAM | 16 GB |
| Disk | 120 GB LVM-thin on `Storage` |
| Network | virtio on vmbr0 |
| QEMU agent | Enabled |

## Docker Compose services

| Service | Image | Network | Purpose |
|---|---|---|---|
| postgres | postgres:16.6-bookworm | ctm-internal | Primary database (CTM + Engram Cloud DBs) |
| redis | redis:7.4-bookworm | ctm-internal | Celery broker (noeviction) + cache |
| meilisearch | meilisearch:v1.52.4 | ctm-internal | Full-text search index |
| clamav | clamav/clamav:1.4.6-debian | ctm-internal + ctm-egress | File scanning (freshclam updates) |
| django | custom build | ctm-internal + ctm-egress | Django app + Gunicorn, port 10.0.0.40:8000 |
| celery-default | custom build | ctm-internal + ctm-egress | Notifications, payments (email/Stripe egress) |
| celery-documents | custom docworker | ctm-internal | PaddleOCR, OCRmyPDF, Docling (no egress) |
| celery-media | custom mediaworker | ctm-internal | FFmpeg audio/video processing (no egress) |
| celery-beat | custom build | ctm-internal | Periodic task scheduler |
| engram | engram:v2.0.0 | ctm-internal + ctm-egress | Developer memory Cloud (own DB, port 127.0.0.1:18080) |

## Networks

| Network | Type | Purpose |
|---|---|---|
| ctm-internal | bridge, internal | Inter-service communication; no outbound internet |
| ctm-egress | bridge | Outbound internet for OAuth, Stripe, email, freshclam |

Services on ctm-internal only (postgres, redis, meilisearch, celery-documents, celery-media, celery-beat, engram) cannot reach the internet. Services on both networks can communicate with internal services and reach external APIs.

### Candidate replacement procedure

A manually started Django candidate must attach to **both** ctm-internal (with its fixed application IP) and ctm-egress before it replaces the live container. Attaching only ctm-internal makes the health endpoint succeed but prevents Microsoft OAuth host resolution and sign-in. Verify DNS and HTTPS access to login.microsoftonline.com and graph.microsoft.com inside the candidate before accepting a replacement.

## Database roles

| Role | Superuser | BYPASSRLS | Purpose |
|---|---|---|---|
| ctm_owner | yes | yes | Migrations only |
| ctm_app | no | no | Django/Gunicorn runtime (RLS-subject) |
| ctm_worker | no | no | Celery workers and beat (RLS-subject) |

## Volumes

| Volume | Host path | Purpose |
|---|---|---|
| pgdata | Docker managed | PostgreSQL data (ctm + engram_cloud DBs) |
| redisdata | Docker managed | Redis AOF persistence |
| meilidata | Docker managed | Meilisearch indexes |
| clamdata | Docker managed | ClamAV signature database |
| uploads | /srv/ctm/media | Uploaded documents, audio, video |
| staticfiles | /srv/ctm/static | Collected Django static files |

## Backup schedule

| Target | Method | Frequency | Retention |
|---|---|---|---|
| PostgreSQL | `pg_dump` via cron inside container | Daily 02:00 | 14 daily, 4 weekly |
| /srv/ctm/media | Restic to /srv/ctm/backups (or remote) | Daily 03:00 | 14 daily, 4 weekly |
| Full VM | Proxmox vzdump | Weekly Sunday 04:00 | 4 weekly |
| Meilisearch | Rebuild from PostgreSQL source | On demand | -- |

Backup destination for off-VM storage is deferred per delivery-dependencies.md. Choose a separate recovery location before live sensitive data.

## Security

### Wazuh agent
- Agent name: CTM-VM
- Manager: 10.0.0.26
- Enrollment: automatic via setup script

### Firewall (UFW)
- Default deny incoming
- SSH (22/tcp) from 10.0.0.0/22
- Django (8000/tcp) from 10.0.0.0/22 and 10.0.0.20 (NPM)
- All non-application Docker ports (ClamAV 3310, Engram 18080) bound to 127.0.0.1 only

### Network isolation
- `ctm-internal` Docker network: bridge + internal (no outbound)
- `ctm-egress` Docker network: bridge (internet-capable)
- PostgreSQL, Redis, Meilisearch: no published ports (internal-only network)
- ClamAV: 127.0.0.1:3310 (host debug only, on egress for freshclam updates)
- Engram Cloud: 127.0.0.1:18080 (host-local dashboard, no CTM app connection)
- Django: 10.0.0.40:8000 (reachable from NPM reverse proxy)
- Medical documents never sent to external AI (celery-documents is internal-only)
- HTTPS termination at NPM (10.0.0.20) reverse proxy

### Expected UniFi firewall
- NPM (10.0.0.20) -> CTM (10.0.0.40:8000) allowed via default LAN rules
- No direct WAN exposure; all external traffic routes through NPM with SSL

## Reverse proxy (NPM on LXC 102)

Add proxy host after VM is running:
- Domain: ctm.lighthouseway.org
- Scheme: http
- Forward hostname/IP: 10.0.0.40
- Forward port: 8000
- SSL: Let's Encrypt certificate
- Force SSL: yes
- WebSockets: enabled in NPM; tus transfers themselves use HTTP POST/PATCH/HEAD.
- Block common exploits: yes

## Engram Cloud

Engram Cloud runs as an authenticated service on the CTM VM for developer memory sync. It is **not** a CTM application dependency — Django and Celery have no connection to it.

- Image: ghcr.io/gentleman-programming/engram:v2.0.0
- Database: `engram_cloud` on shared postgres instance
- Dashboard: http://127.0.0.1:18080/dashboard (host-local only)
- Auth: bearer token (ENGRAM_CLOUD_TOKEN) + admin token (ENGRAM_CLOUD_ADMIN)
- Project allowlist: ENGRAM_CLOUD_ALLOWED_PROJECTS (server-enforced)
- Client config: `engram cloud config --server http://10.0.0.40:18080` from AdminPC


## Verified route and launch prerequisites - 2026-10-21

The operator created NPM proxy30 for `ctm.lighthouseway.org` to `http://10.0.0.40:8000` and issued its Let's Encrypt certificate (reported expiry2027-01-19). DNS and certificate-validated HTTPS502 were independently verified. Port8000 has no listener yet. This is now an upstream application/service task; do not recreate the existing proxy host.

The current validation container remains private and uses test settings. It is not the production upstream. Complete production migration ownership, runtime/function grants and readiness gates before a public launch. Use staged Microsoft configuration from its protected server file; do not embed secrets or test settings in the image. After origin ingress is limited to NPM and NPM overwrites forwarded scheme headers, enable CTM_TRUST_PROXY_SSL=true to preserve HTTPS callbacks/secure cookies through its HTTP upstream.

Application static assets now live in the versioned image at `/srv/ctm/static`; no persistent static volume masks upgrades. Only media persists through the existing uploads bind volume. The no-network init-storage service adjusts the root media directory to UID/GID1000 and0700 before media writers start, without recursively changing existing file owners. Backups restore private media plus the database; static assets are rebuilt from the pinned application image. Inspect existing file ownership separately before adopting any older media tree. No operational volume or database was changed by these source updates.

Tus protocol reference: https://tus.io/protocols/resumable-upload . WebSocket support alone does not implement resumable upload handling; that application endpoint remains planned.

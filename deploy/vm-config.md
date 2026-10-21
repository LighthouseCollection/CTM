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
- Websockets: yes (for Tus upload progress)
- Block common exploits: yes

## Engram Cloud

Engram Cloud runs as an authenticated service on the CTM VM for developer memory sync. It is **not** a CTM application dependency — Django and Celery have no connection to it.

- Image: ghcr.io/gentleman-programming/engram:v2.0.0
- Database: `engram_cloud` on shared postgres instance
- Dashboard: http://127.0.0.1:18080/dashboard (host-local only)
- Auth: bearer token (ENGRAM_CLOUD_TOKEN) + admin token (ENGRAM_CLOUD_ADMIN)
- Project allowlist: ENGRAM_CLOUD_ALLOWED_PROJECTS (server-enforced)
- Client config: `engram cloud config --server http://10.0.0.40:18080` from AdminPC

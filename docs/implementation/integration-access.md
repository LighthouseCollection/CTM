# Integration administration access

Verified 2026-10-21 from AdminPC. This inventory describes management access, not a claim that CTM provider login is live.

| Service | Management route | Verified state / next requirement |
|---|---|---|
| CTM VM | `ssh ctm` as admin, existing Ed25519 key | Connected; alias added to the operator's SSH config; agent forwarding disabled |
| Docker / PostgreSQL | Docker Compose and `docker exec` over SSH | Existing containers visible; no public database port or Docker socket opened |
| Meilisearch | Private HTTP API through CTM network / SSH | Health reports available; application authenticated indexing remains separate work |
| ClamAV | Private daemon / scanner through SSH | Scanner version responds |
| Redis | Private authenticated broker through SSH | Container healthy; unauthenticated CLI rejected, as expected |
| Microsoft Entra | Azure CLI 2.91.0 and Microsoft Graph | Installed on AdminPC; Diocese tenant authenticated; CTM app and enterprise application registered; runtime browser login still pending |
| Google Cloud | Existing gcloud CLI | Cached account exists but refresh fails with invalid_grant; fresh operator sign-in required |
| Apple | Apple Developer account / Sign in with Apple setup | No authenticated management access verified |
| Stripe | Stripe dashboard/API, test credentials | No authenticated management access verified; no charges made |
| Email | Chosen mail service SMTP/API and inbound webhook | Provider authorization not established |
| OCR / media | Existing CTM worker containers / server-side applications | No external provider authorization needed for local-server processing; pipeline work remains |
| Translation / transcription | Configured engine APIs or server engine | Provider selection/credentials remain unconfigured |

## Operator commands

From the application checkout, use `./deploy/azure.ps1 version` and `./deploy/azure.ps1 login --use-device-code --allow-no-subscriptions --output none`. The wrapper uses Azure CLI's isolated Python interpreter; the generic pip `az.bat` otherwise resolves an unrelated ComfyUI interpreter on this workstation. Google reauthorization uses `gcloud auth login`.

SSH config is local to the operator account. No private key was copied or generated. The VM directory `/opt/ctm/secrets` was created root-owned with mode 0700, ready for provider configuration. Microsoft credentials are stored in `/opt/ctm/secrets/microsoft.env`, root-owned mode 0600, transferred directly over SSH without repository storage or printed secret output. Secrets must be provisioned there through protected SSH input and explicitly connected to the reviewed Compose environment; directory creation alone does not configure CTM.

## Microsoft login registration target

After operator authentication and tenant verification, create or reuse a CTM-specific single-tenant confidential Web application. Exact callback: `https://ctm.lighthouseway.org/accounts/microsoft/login/callback/`. The installed allauth Microsoft adapter calls Graph `/v1.0/me` and requests delegated `User.Read`. CTM should request no directory-wide write privileges for ordinary login. Operator administration permissions are separate from CTM login permissions.

Store the application client ID, tenant ID and secret in protected server configuration using the existing `MICROSOFT_*` environment variables. Preserve all existing app credentials when adding a credential; do not reset unrelated application secrets. Verify the tenant and existing registrations before creating duplicates. Council users must still be preauthorized by their Microsoft object identity in CTM; successful Microsoft authentication alone does not create a council account or grant a council role.

The CTM login registration and enterprise application were created after successful operator sign-in. No tenant-wide consent, cloud hosting deployment or production service restart was performed. Public DNS currently resolves CTM; DNS resolution alone does not validate HTTPS, callback routing or readiness.

## References

- [Microsoft interactive CLI authentication](https://learn.microsoft.com/en-us/cli/azure/authenticate-azure-cli-interactively)
- [Microsoft Entra app registration commands](https://learn.microsoft.com/en-us/cli/azure/ad/app)

An MCP is optional for administration. SSH and supported vendor CLIs/APIs already supply the required routes; a chat connector for Outlook or Teams does not authorize Entra app registration or configure CTM's login.

## Microsoft registration established

- Tenant: `ee61b06d-1985-4e76-b7d4-9c6da59ed3b4` — Coptic Orthodox Church Diocese of Los Angeles Southern Cal & Hawaii.
- Client/application ID: `4cbf023f-90b7-4c61-83fe-3c6f16f8e1a9`.
- Application object: `f7eff338-3e57-4321-8f0d-5d38a261ff04`.
- Enterprise application object: `9b731f8f-5ef2-4618-b3f6-62d7a02865e1`.
- Single-tenant Web callback and delegated Graph User.Read configured as above.
- Secret expires April 21, 2027; rotate before expiration. Secret values are intentionally absent from this document.
- Credentials are staged on the VM, not yet loaded by a production CTM service. Callback HTTPS routing, complete browser login and preauthorized council identity onboarding remain acceptance gates.
- The operator has tenant-level CLI access without an accessible Azure subscription; hosting entitlement is separate from login registration.

## Callback routing diagnosis

On 2026-10-21, an ephemeral container using the staged Microsoft configuration returned HTTP 302 from POST `/accounts/microsoft/login/` with the exact Diocese tenant authorization URL, the HTTPS CTM callback, User.Read scope and nonempty OAuth state. This verifies authorization-request construction only; it is not a completed browser authorization-code exchange. The probe used the isolated validation database and test client, with an explicit allowed-host override, and had no listening port.

The CTM VM can reach Microsoft's login endpoint. Nginx Proxy Manager in LXC 102 is reachable through Proxmox SSH and listens at 10.0.0.20 on ports 80/443. During that earlier inspection, its configured hostnames included the older `ctm.lighthousecollection.net`, but not the new hostname. The new route was subsequently configured by the operator; see the verified update below.

The existing `ctm-validation-backend` is internal-only and uses test settings; it must not be exposed as the new production upstream. Complete the production database grants/settings and deploy a separately configured service, then add the new NPM host and valid certificate through its supported management interface. Verify the upstream from NPM, HTTPS/CSRF/proxy handling, council identity authorization and full Microsoft callback exchange before declaring login live. Operator app registration access is established; public runtime login remains pending.


## Public route established - 2026-10-21

Operator-reported configuration: NPM host30 forwards `ctm.lighthouseway.org` to `http://10.0.0.40:8000`, with a Let's Encrypt certificate expiring2027-01-19, forced HTTPS, HSTS, HTTP/2 and WebSocket forwarding. Current read-only verification confirms DNS CNAME to `npm.lighthouseway.org` /76.246.228.252 and a certificate-validated HTTPS502 response from OpenResty. This supersedes the earlier TLS/timeout diagnosis; no NPM host was changed by this verification.

SSH confirms no process is listening on VM port8000. Infrastructure containers are running; `ctm-validation-backend` still has no published host port and uses its validation image. Microsoft secret staging retains root0700 directory /0600 file permissions. UFW currently allows SSH and8000 from10.0.0.0/22. The new production service must use production settings, trusted-proxy HTTPS handling and reviewed database ownership/grants. Docker published ports also need network enforcement appropriate to the NPM source; UFW alone must not be assumed to filter Docker forwarding. Readiness gates, full provider login and remaining source/schema protections are still pending. No validation container was exposed and no production migration ran.

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

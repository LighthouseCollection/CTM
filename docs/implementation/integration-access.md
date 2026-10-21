# Integration administration access

Verified 2026-10-21 from AdminPC. This inventory describes management access, not a claim that CTM provider login is live.

| Service | Management route | Verified state / next requirement |
|---|---|---|
| CTM VM | `ssh ctm` as admin, existing Ed25519 key | Connected; alias added to the operator's SSH config; agent forwarding disabled |
| Docker / PostgreSQL | Docker Compose and `docker exec` over SSH | Existing containers visible; no public database port or Docker socket opened |
| Meilisearch | Private HTTP API through CTM network / SSH | Health reports available; application authenticated indexing remains separate work |
| ClamAV | Private daemon / scanner through SSH | Scanner version responds |
| Redis | Private authenticated broker through SSH | Container healthy; unauthenticated CLI rejected, as expected |
| Microsoft Entra | Azure CLI 2.91.0 and Microsoft Graph | Installed on AdminPC; interactive device sign-in initiated; tenant access/app registration not yet verified |
| Google Cloud | Existing gcloud CLI | Cached account exists but refresh fails with invalid_grant; fresh operator sign-in required |
| Apple | Apple Developer account / Sign in with Apple setup | No authenticated management access verified |
| Stripe | Stripe dashboard/API, test credentials | No authenticated management access verified; no charges made |
| Email | Chosen mail service SMTP/API and inbound webhook | Provider authorization not established |
| OCR / media | Existing CTM worker containers / server-side applications | No external provider authorization needed for local-server processing; pipeline work remains |
| Translation / transcription | Configured engine APIs or server engine | Provider selection/credentials remain unconfigured |

## Operator commands

From the application checkout, use `./deploy/azure.ps1 version` and `./deploy/azure.ps1 login --use-device-code --allow-no-subscriptions --output none`. The wrapper uses Azure CLI's isolated Python interpreter; the generic pip `az.bat` otherwise resolves an unrelated ComfyUI interpreter on this workstation. Google reauthorization uses `gcloud auth login`.

SSH config is local to the operator account. No private key was copied or generated. The VM directory `/opt/ctm/secrets` was created root-owned with mode 0700, ready for provider configuration. It currently contains no provider credentials created by this setup. Secrets must be provisioned there through protected SSH input and explicitly connected to the reviewed Compose environment; directory creation alone does not configure CTM.

## Microsoft login registration target

After operator authentication and tenant verification, create or reuse a CTM-specific single-tenant confidential Web application. Exact callback: `https://ctm.lighthouseway.org/accounts/microsoft/login/callback/`. The installed allauth Microsoft adapter calls Graph `/v1.0/me` and requests delegated `User.Read`. CTM should request no directory-wide write privileges for ordinary login. Operator administration permissions are separate from CTM login permissions.

Store the application client ID, tenant ID and secret in protected server configuration using the existing `MICROSOFT_*` environment variables. Preserve all existing app credentials when adding a credential; do not reset unrelated application secrets. Verify the tenant and existing registrations before creating duplicates. Council users must still be preauthorized by their Microsoft object identity in CTM; successful Microsoft authentication alone does not create a council account or grant a council role.

No login registration, tenant-wide consent, cloud resource deployment or production service restart has been performed by this access setup. Public DNS currently resolves CTM; DNS resolution alone does not validate HTTPS, callback routing or readiness.

## References

- [Microsoft interactive CLI authentication](https://learn.microsoft.com/en-us/cli/azure/authenticate-azure-cli-interactively)
- [Microsoft Entra app registration commands](https://learn.microsoft.com/en-us/cli/azure/ad/app)

An MCP is optional for administration. SSH and supported vendor CLIs/APIs already supply the required routes; a chat connector for Outlook or Teams does not authorize Entra app registration or configure CTM's login.

# Engram development installation

Installed 2026-10-21 after architecture consolidation. This is a workstation development aid, not a CTM business-data service or application dependency.

| Item | Verified result |
|---|---|
| Core release |3.5.1, stable GitHub release |
| Binary | `C:/Users/AdminMan/AppData/Local/Programs/Engram/3.5.1/engram.exe` |
| Download SHA256 | `23cd4fec76a4aa6047e2e87ac66c4c995e8f5773880e1071da54c0a24caf0abc` matched release checksums.txt |
| Codex registration | Enabled stdio MCP, absolute binary path, `mcp --tools=agent` |
| Codex plugin | `engram@engram`, version0.1.5, installed and enabled by official `engram setup codex` |
| Project | `.engram/config.json`, project CTM (normalized resolver `ctm`) |
| Command availability | Engram install folder added to user PATH; newly started processes receive it |
| Cloud | No enrollment/cloud configuration/sync requested or enabled by this installation |
| Diagnostics | Doctor10checks, all OK; isolated quick reliability tests both passed |
| MCP verification | Initialize, list22agent tools and read-only current-project call passed; see `engram-validation.json` |
| Activation | Restart Codex to reload MCP/plugin/hooks and updated PATH. Current conversation is not claimed to have active Engram tools. |

Official setup wrote the MCP configuration and informational instruction files, then registered the Codex plugin. Configuration files existing beforehand were backed up under `C:/Users/AdminMan/AppData/Local/CTM-Engram-Install/3.5.1/config-backup/`. The plugin marketplace follows the upstream main reference as installed by official setup; core binary is release-pinned. Do not describe plugin source as release-pinned or fully security-audited.

No CTM source documents, conversations, question-bank bodies or case data were bulk-imported into memory. The read-only MCP validation did not fabricate a runtime session to write observations. After restart, use confirmed runtime session binding for normal memory writes.

## Memory use boundary

Use concise development decisions and file pointers, with this build specification as authoritative. Do not feed actual applicant records, medical reports, evidence or credentials into the development chat/memory. The stock integration includes a user-prompt capture hook and session context hooks: development prompts may be saved locally. Installation does not make automatic capture a case-data-safe store. No claim is made that the stock plugin filters all sensitive data. The scope restriction applies to what developers put into the coding session as well as deliberate memory saves.

Existing Codex memory files were not edited. Engram storage is separate from CTM PostgreSQL and its retention/permissions. Future cloud enrollment, memory import or broad sync requires separate explicit scope.

References: [release](https://github.com/Gentleman-Programming/engram/releases/tag/v3.5.1), [installation](https://github.com/Gentleman-Programming/engram/blob/v3.5.1/docs/INSTALLATION.md), [Codex setup](https://github.com/Gentleman-Programming/engram/blob/v3.5.1/docs/AGENT-SETUP.md#codex).

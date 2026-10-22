# Private testimony invitations

Source-only candidates at backend `d724ba56b8bd5cf501d55fbbca416470108f963a` and applicant `72ee829eb1eabc436c19a084f81235b6a029528c`.
No row proves physical schema parity, production readiness or a security failure.

| Contract table | Adapter candidate | Columns without direct mapping | Storage candidate |
| --- | --- | --- | --- |
| `testimony_appointments` | `tribunal.TestimonyAppointment` | `case_id`, `created_by_id` | None mapped |
| `testimony_appointment_versions` | `tribunal.TestimonyAppointmentVersion` | None; semantics still unverified | None mapped |
| `testimony_invitation_responses` | `tribunal.AppointmentResponse` | `request_id`, `appointment_version_id`, `party_id` | None mapped |

[All field targets and source locations](field-mapping.csv) · [Full JSON](result.json) · [Findings and limits](README.md)

"""Own lifecycle capabilities; mutations recheck all conditions under locks."""
from tribunal import models as m
from .closed_filings import CLOSED_INTAKE


def own_filing_actions(app, actor):
    if app.owner_id != actor.pk:
        return {}
    pending_result = (app.kind == "appeal" or (app.origin == CLOSED_INTAKE and app.status == "submitted"))
    if pending_result:
        withdrawable = app.status == "submitted" and not m.AppealDisposition.objects.filter(application=app).exists()
    else:
        withdrawable = bool(app.status in {"submitted", "accepted", "returned"} and app.case
            and app.case.status == "open" and (app.case.proceedings.filter(status="open").exists()
                if app.origin == CLOSED_INTAKE else app.proceeding and app.proceeding.status == "open"))
    from .closed_filings import council_filing
    result = {"can_delete_draft": bool(app.status == "draft" and not app.submitted_at
                and not app.checkoutintent_set.exists()), "can_withdraw": withdrawable}
    if council_filing(app):
        result.update(can_supplement=bool(app.status == "submitted" and not m.AppealDisposition.objects.filter(application=app).exists()),
            supplements=[{"id": str(row.pk), "text": row.text, "manifest": row.manifest,
                "timestamp": row.created_at.isoformat(), "idempotency_key": row.idempotency_key}
                for row in m.AppealSupplement.objects.filter(application=app, actor=actor).order_by("created_at", "id")])
    return result

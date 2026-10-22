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
    return {"can_delete_draft": bool(app.status == "draft" and not app.submitted_at
                and not app.checkoutintent_set.exists()), "can_withdraw": withdrawable}

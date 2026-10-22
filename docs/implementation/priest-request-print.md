# External-priest request print transport

`GET /api/requests/{request_id}/print/` returns a private HTML document suitable
for browser Print / Save as PDF. It is not a server-generated PDF download.

An active council account must be the request's case writer: administrator,
secretary or assigned manager. The case and proceeding must be open, the request
must be `external_priest`, and its state must be draft or sent. A priest bearer
link does not authorize this council endpoint. GET has no mutation, token issue,
notification, completion or audit side effect. Non-GET returns405.

The projection contains only the saved title, instructions, subject name, priest
name, language and request ID, followed by blank writing lines. Django escapes
all content. Arabic requests use Arabic language/RTL; individual saved text
blocks use automatic direction for mixed scripts. No substitute question,
testimony, signature or approved wording is generated. A draft request need not
have an issued online link to be printed.

The response is private/no-store and no-referrer, with a restrictive CSP that
permits only the inline print styles. No script, remote image/font, form, token,
token hash, email address, saved response or completed report is rendered.
Private-response middleware preserves an explicit stricter referrer policy.

Council owns the link/button and browser print experience. The council user can
save the resulting print output as PDF. A direct generated-PDF contract remains
unfinished; do not label this endpoint `application/pdf` or promise automatic
printing. This view does not upload or complete the request. The separate
paper-completion API retains a validated uploaded original.

Eleven restricted PostgreSQL runtime tests cover content escaping, Arabic/RTL,
private fields, read-only behavior, writer permissions, terminal/closed/other-kind
denial, bearer-only denial, unknown ID and method handling.

Full backend validation:874 PostgreSQL passed,1 skipped; no model drift. A
synthetic Arabic template generated a one-page47,518-byte PDF in Chromium. This
is print transport smoke evidence, not council UI or approved-content acceptance.

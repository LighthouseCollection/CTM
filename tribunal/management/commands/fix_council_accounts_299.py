"""One-time, audited council account correction for issue #299 (owner decision, chat, 2026-11-10).

- Delete the account fryouhannayoussef@lacopts.org. Fr. Youhanna Youssef is
  frjohnyoussef@lacopts.org.
- Before the delete, every reference in an editable table moves to
  frjohnyoussef@lacopts.org. History tables (``Immutable`` models) are never
  rewritten: if one points to the account, the delete stops, unless
  ``--suspend-if-history`` is given, which suspends the account instead.
- Correct "Fr. Youhana Ibrahim" / fryouhanaibrahim@ to "Fr. Youhanna Ibrahim" /
  fryouhannaibrahim@lacopts.org, and the unbound council enrolment record with it,
  so his first Microsoft sign-in still matches.

The default is a dry run: the whole change runs inside one transaction and is
rolled back, so the report proves the change would apply (constraints and
triggers included) without writing. ``--apply`` needs the literal confirmation.
The report prints table names and row counts only, never case data. The
database backup is taken by ``deploy/live-fix-accounts-299.sh`` before ``--apply``.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, connection, transaction
from django.db.models.deletion import ProtectedError, RestrictedError
from tribunal import models as m

ISSUE = 299
CONFIRMATION = "ISSUE-299-COUNCIL-ACCOUNTS"
SOURCE = "maintenance:fix_council_accounts_299"
DELETE_EMAIL = "fryouhannayoussef@lacopts.org"
KEEP_EMAIL = "frjohnyoussef@lacopts.org"
IBRAHIM_OLD_EMAIL = "fryouhanaibrahim@lacopts.org"
IBRAHIM_NEW_EMAIL = "fryouhannaibrahim@lacopts.org"
IBRAHIM_NAME = ("Fr. Youhanna", "Ibrahim")
# Rows that belong to the sign-in itself (allauth addresses and provider links):
# they go with the deleted account and are never moved to another person.
OWNED_APPS = {"account", "socialaccount", "admin"}


class DryRun(Exception):
    """Raised at the end of a dry run to roll the transaction back."""


def _label(model, field):
    return f"{model._meta.db_table}.{field.column}"


def _relations():
    """Every relation that points at an Account row, from the model registry."""
    out = []
    for rel in m.Account._meta.related_objects:
        model = rel.related_model
        if rel.many_to_many:
            kind = "owned" if model._meta.app_label in OWNED_APPS else "many-to-many"
        elif model._meta.app_label in OWNED_APPS:
            kind = "owned"
        elif issubclass(model, m.Immutable):
            kind = "history"
        else:
            kind = "editable"
        out.append((rel, model, rel.field, kind))
    return sorted(out, key=lambda item: _label(item[1], item[2]))


def _count(model, field, account):
    if field.many_to_many:
        return model._base_manager.filter(**{field.name: account}).count()
    return model._base_manager.filter(**{field.attname: account.pk}).count()


def _constraint(exc):
    diag = getattr(getattr(exc, "__cause__", None), "diag", None)
    name = getattr(diag, "constraint_name", None)
    return f"{type(exc).__name__}{f' ({name})' if name else ''}"


class Command(BaseCommand):
    help = "Issue #299: delete fryouhannayoussef@, correct Fr. Youhanna Ibrahim (dry run by default)."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Write the change (default: dry run).")
        parser.add_argument("--confirmation", default="", help=f"Required with --apply: {CONFIRMATION}.")
        parser.add_argument(
            "--suspend-if-history",
            action="store_true",
            help="If history rows point to the account, suspend it instead of stopping.",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        if apply and options["confirmation"] != CONFIRMATION:
            raise CommandError("Confirmation did not match; nothing was written.")
        self.problems = []
        self.say(f"#{ISSUE} council account correction: {'APPLY' if apply else 'DRY RUN (rolled back)'}")
        try:
            with transaction.atomic():
                self.fix_youssef(options["suspend_if_history"])
                self.fix_ibrahim()
                if self.problems:
                    raise CommandError(
                        "Stopped, nothing was written: " + "; ".join(self.problems)
                    )
                if not apply:
                    raise DryRun()
        except DryRun:
            self.say("dry run: the change applies cleanly; rolled back, nothing was written")
            return
        self.say("applied")

    def say(self, line):
        self.stdout.write(line)

    def audit(self, action, account_id, metadata):
        m.AuditEvent.objects.create(
            actor=None,
            action=action,
            source=SOURCE,
            source_id=account_id,
            metadata={"issue": ISSUE, **metadata},
        )

    # --- 1. fryouhannayoussef@ -> delete, references to frjohnyoussef@ ---------
    def fix_youssef(self, suspend_if_history):
        target = m.Account.objects.select_for_update().filter(email__iexact=DELETE_EMAIL).first()
        keep = m.Account.objects.select_for_update().filter(email__iexact=KEEP_EMAIL).first()
        self.say(
            f"keep {KEEP_EMAIL}: "
            + (f"present, role {keep.role}, active {keep.is_active}" if keep else "MISSING")
        )
        if target is None:
            self.say(f"delete {DELETE_EMAIL}: not present (already deleted); nothing to do")
            return
        self.say(
            f"delete {DELETE_EMAIL}: present, role {target.role}, active {target.is_active}, "
            f"Microsoft bound {bool(target.microsoft_subject)}, person linked {target.person_id is not None}"
        )
        if target.last_name != "Youssef":
            self.problems.append(f"{DELETE_EMAIL} is not a Youssef account; refusing")
            return
        if target.role == "admin":
            self.problems.append(f"{DELETE_EMAIL} is an administrator; refusing")
            return

        relations = [(r, model, field, kind, _count(model, field, target)) for r, model, field, kind in _relations()]
        found = [item for item in relations if item[4]]
        for _rel, model, field, kind, n in found:
            self.say(f"  references {_label(model, field)}: {n} ({kind})")
        if not found:
            self.say("  references: none")
        history = [item for item in found if item[3] == "history"]
        editable = [item for item in found if item[3] in ("editable", "many-to-many")]
        groups = target.groups.count() + target.user_permissions.count()

        if editable:
            if keep is None or not keep.is_active or keep.role == "applicant":
                self.problems.append(
                    f"{len(editable)} table(s) reference {DELETE_EMAIL} but {KEEP_EMAIL} is missing, "
                    "suspended or an applicant; cannot move them"
                )
                return
            moved = {}
            for _rel, model, field, kind, n in editable:
                label = _label(model, field)
                if kind == "many-to-many":
                    self.problems.append(f"{label}: many-to-many references are not moved automatically")
                    continue
                try:
                    with transaction.atomic():
                        changed = model._base_manager.filter(**{field.attname: target.pk}).update(
                            **{field.attname: keep.pk}
                        )
                except DatabaseError as exc:
                    self.problems.append(f"{label}: cannot move ({_constraint(exc)})")
                    continue
                moved[label] = changed
                self.say(f"  moved {label}: {changed} -> {KEEP_EMAIL}")
            if self.problems:
                return
            self.audit(
                "maintenance_account_references_moved",
                target.pk,
                {"from": DELETE_EMAIL, "to": KEEP_EMAIL, "to_account": str(keep.pk), "moved": moved},
            )

        if history:
            counts = {_label(model, field): n for _r, model, field, _k, n in history}
            if not suspend_if_history:
                self.problems.append(
                    f"history rows point to {DELETE_EMAIL} ({', '.join(counts)}); history is never "
                    "rewritten. Rerun with --suspend-if-history to suspend it instead"
                )
                return
            target.is_active = False
            target.save(update_fields=["is_active"])
            self.audit(
                "maintenance_account_suspended",
                target.pk,
                {"email": DELETE_EMAIL, "reason": "history rows kept", "history": counts},
            )
            self.say(f"  suspended {DELETE_EMAIL} (history kept: {sum(counts.values())} rows)")
            return

        owned = {_label(model, field): n for _r, model, field, kind, n in found if kind == "owned"}
        target_id = target.pk
        try:
            with transaction.atomic():
                target.groups.clear()
                target.user_permissions.clear()
                target.delete()
        except (ProtectedError, RestrictedError, DatabaseError) as exc:
            self.problems.append(f"delete of {DELETE_EMAIL} refused ({_constraint(exc)})")
            return
        self.audit(
            "maintenance_account_deleted",
            target_id,
            {"email": DELETE_EMAIL, "deleted_with_it": owned, "group_and_permission_links": groups},
        )
        self.say(f"  deleted {DELETE_EMAIL}" + (f" (with its sign-in rows: {owned})" if owned else ""))

    # --- 2. Fr. Youhana Ibrahim / fryouhanaibrahim@ -> two n's -----------------
    def fix_ibrahim(self):
        old = m.Account.objects.select_for_update().filter(email__iexact=IBRAHIM_OLD_EMAIL).first()
        new = m.Account.objects.select_for_update().filter(email__iexact=IBRAHIM_NEW_EMAIL).first()
        self.say(
            f"Ibrahim: {IBRAHIM_OLD_EMAIL} {'present' if old else 'not present'}, "
            f"{IBRAHIM_NEW_EMAIL} {'present' if new else 'not present'}"
        )
        if old and new:
            self.problems.append(
                f"both {IBRAHIM_OLD_EMAIL} and {IBRAHIM_NEW_EMAIL} exist; joining two accounts is not automatic"
            )
            return
        account = old or new
        if account is None:
            self.say("  Ibrahim: no account; nothing to do")
            return
        if account.last_name != IBRAHIM_NAME[1]:
            self.problems.append(f"{account.email} is not an Ibrahim account; refusing")
            return
        before = {"email": account.email, "first_name": account.first_name, "last_name": account.last_name}
        account.email = IBRAHIM_NEW_EMAIL
        account.first_name, account.last_name = IBRAHIM_NAME
        after = {"email": account.email, "first_name": account.first_name, "last_name": account.last_name}
        if before == after:
            self.say("  Ibrahim: already correct; nothing to do")
            return
        account.save(update_fields=["email", "first_name", "last_name"])
        enrolment = self.move_enrolment_email(account.pk)
        addresses = self.move_allauth_addresses(account.pk, before["email"])
        self.audit(
            "maintenance_account_corrected",
            account.pk,
            {"before": before, "after": after, "enrolment_rows": enrolment, "sign_in_addresses": addresses},
        )
        self.say(
            f"  corrected {before['first_name']} {before['last_name']} <{before['email']}> -> "
            f"{after['first_name']} {after['last_name']} <{after['email']}>; "
            f"unbound enrolment record updated: {enrolment}; sign-in address rows updated: {addresses}; "
            f"Microsoft bound {bool(account.microsoft_subject)}"
        )

    def move_enrolment_email(self, account_id):
        """The first Microsoft binding needs ctm_council_enrolment.email to equal the account email."""
        if connection.vendor != "postgresql":
            return 0
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('public.ctm_council_enrolment') IS NOT NULL")
            if not cursor.fetchone()[0]:
                return 0
            cursor.execute(
                "UPDATE public.ctm_council_enrolment SET email=%s WHERE account_id=%s AND bound_at IS NULL",
                [IBRAHIM_NEW_EMAIL, account_id],
            )
            return cursor.rowcount

    def move_allauth_addresses(self, account_id, old_email):
        try:
            from allauth.account.models import EmailAddress
        except ImportError:  # pragma: no cover - allauth is installed in every settings module
            return 0
        if EmailAddress.objects.filter(email__iexact=IBRAHIM_NEW_EMAIL).exists():
            return 0
        return EmailAddress.objects.filter(user_id=account_id, email__iexact=old_email).update(
            email=IBRAHIM_NEW_EMAIL, verified=False
        )

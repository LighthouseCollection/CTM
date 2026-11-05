-- D-0021 (#66): "an admin already added this member" is an enrolment record,
-- written only when the enrolment path inserts the council account. The first
-- Microsoft binding consumes it. (#65): every refusal is one uniform denial.
CREATE TABLE public.ctm_council_enrolment(
  account_id uuid PRIMARY KEY REFERENCES public.tribunal_account(id) ON DELETE CASCADE,
  email text NOT NULL,
  role text NOT NULL,
  enrolled_by_id uuid,
  enrolled_at timestamptz NOT NULL DEFAULT statement_timestamp(),
  bound_at timestamptz
);
REVOKE ALL ON TABLE public.ctm_council_enrolment FROM PUBLIC;
-- Runtime roles hold no privilege at all; only the owner's definer functions
-- below read or write it, so the one policy is scoped to the owner role.
ALTER TABLE public.ctm_council_enrolment ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ctm_council_enrolment FORCE ROW LEVEL SECURITY;
CREATE POLICY ctm_council_enrolment_owner_only ON public.ctm_council_enrolment TO CURRENT_USER
  USING (account_id IS NOT NULL) WITH CHECK (account_id IS NOT NULL AND email=lower(email));

-- The account-insert policy (0037) admits a council account only for an admin
-- actor with ctm.enroll_account set to that id; record exactly that insert.
CREATE FUNCTION public.ctm_record_council_enrolment() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 IF NEW.role IN ('member','president','secretary','admin')
    AND NEW.id::text=current_setting('ctm.enroll_account',true)
    AND (public.ctm_actor_role()='admin' OR public.ctm_migration_caller()) THEN
  INSERT INTO public.ctm_council_enrolment(account_id,email,role,enrolled_by_id)
   VALUES (NEW.id,lower(NEW.email),NEW.role,public.ctm_actor_id());
 END IF;
 RETURN NULL;
END $$;
REVOKE ALL ON FUNCTION public.ctm_record_council_enrolment() FROM PUBLIC;
CREATE TRIGGER ctm_council_enrolment_record AFTER INSERT ON public.tribunal_account
  FOR EACH ROW EXECUTE FUNCTION public.ctm_record_council_enrolment();

-- Backfill: council accounts enrolled before this migration that have not
-- bound yet, from the enrolment audit rows written at that time.
INSERT INTO public.ctm_council_enrolment(account_id,email,role,enrolled_by_id,enrolled_at)
SELECT DISTINCT ON (a.id) a.id,lower(a.email),a.role,e.actor_id,e.created_at
  FROM public.tribunal_account a
  JOIN public.tribunal_auditevent e ON e.source_id=a.id AND e.action='council_enrolled' AND e.source='tribunal.account'
 WHERE a.microsoft_subject='' AND a.role IN ('member','president','secretary','admin')
 ORDER BY a.id,e.created_at;

CREATE OR REPLACE FUNCTION public.ctm_bind_microsoft_subject(target uuid) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE
 subject text=current_setting('ctm.provider_subject',true);
 emails jsonb;
 account record;
 allowed boolean=false;
BEGIN
 -- Tenant: the database has no trusted copy of the council tenant id; the
 -- sign-in service checks the token's tid/iss before setting these (#64).
 BEGIN
  emails=current_setting('ctm.provider_emails',true)::jsonb;
 EXCEPTION WHEN others THEN emails=NULL;
 END;
 SELECT a.id,a.is_active,a.role,a.email,a.microsoft_subject INTO account
   FROM public.tribunal_account a WHERE a.id=target FOR UPDATE;
 allowed = FOUND
   AND current_setting('ctm.provider',true) IS NOT DISTINCT FROM 'microsoft'
   AND subject IS NOT NULL AND btrim(subject)<>'' AND length(subject)<=200
   AND jsonb_typeof(emails) IS NOT DISTINCT FROM 'array'
   AND account.is_active AND account.role IN ('admin','president','secretary','member')
   AND account.microsoft_subject=''
   AND right(lower(account.email),12)='@lacopts.org' AND emails @> jsonb_build_array(lower(account.email))
   AND NOT EXISTS(SELECT 1 FROM public.tribunal_account a WHERE a.microsoft_subject=subject)
   AND EXISTS(SELECT 1 FROM public.ctm_council_enrolment r
     WHERE r.account_id=target AND r.bound_at IS NULL AND r.email=lower(account.email));
 IF allowed IS NOT TRUE THEN
  -- One message, no detail: the caller must not learn which condition failed.
  RAISE EXCEPTION 'Microsoft sign-in cannot be linked to this account' USING ERRCODE='42501';
 END IF;
 BEGIN
  INSERT INTO public.ctm_microsoft_binding_grant(account_id,subject) VALUES (target,subject);
  UPDATE public.tribunal_account SET microsoft_subject=subject WHERE id=target;
  DELETE FROM public.ctm_microsoft_binding_grant WHERE account_id=target;
  UPDATE public.ctm_council_enrolment SET bound_at=statement_timestamp() WHERE account_id=target;
 EXCEPTION WHEN unique_violation THEN
  RAISE EXCEPTION 'Microsoft sign-in cannot be linked to this account' USING ERRCODE='42501';
 END;
END $$;
REVOKE ALL ON FUNCTION public.ctm_bind_microsoft_subject(uuid) FROM PUBLIC;

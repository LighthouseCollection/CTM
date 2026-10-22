CREATE FUNCTION public.ctm_assignment_president(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT EXISTS(SELECT 1 FROM public.tribunal_account a WHERE a.id=target AND a.is_active AND a.role<>'applicant'
  AND (a.role='president' OR EXISTS(SELECT 1 FROM public.staff_memberships m JOIN public.staff_roles r ON r.membership_id=m.id
   WHERE m.account_id=a.id AND m.tribunal_id::text=current_setting('ctm.tribunal_id',true)
   AND m.active_from<=statement_timestamp() AND (m.active_until IS NULL OR m.active_until>statement_timestamp())
   AND r.role='president' AND r.revoked_at IS NULL)))
$$;

CREATE FUNCTION public.ctm_assignment_recorder(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT EXISTS(SELECT 1 FROM public.tribunal_account a WHERE a.id=target AND a.is_active AND a.role<>'applicant'
  AND (a.role IN ('admin','secretary') OR EXISTS(SELECT 1 FROM public.staff_memberships m JOIN public.staff_roles r ON r.membership_id=m.id
   WHERE m.account_id=a.id AND m.tribunal_id::text=current_setting('ctm.tribunal_id',true)
   AND m.active_from<=statement_timestamp() AND (m.active_until IS NULL OR m.active_until>statement_timestamp())
   AND r.role IN ('admin','secretary') AND r.revoked_at IS NULL)))
$$;

CREATE FUNCTION public.ctm_staff_readable() RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT public.ctm_is_council()
$$;

CREATE FUNCTION public.ctm_staff_writable(resource text,data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT public.ctm_actor_role()='admin' AND CASE resource
  WHEN 'tribunal' THEN btrim(data->>'code')<>'' AND btrim(data->>'name_en')<>''
  WHEN 'staffmembership' THEN data->>'appointed_by_id'=public.ctm_actor_id()::text
   AND data->>'tribunal_id'=current_setting('ctm.tribunal_id',true) AND data->>'active_until' IS NULL
   AND EXISTS(SELECT 1 FROM public.tribunal_account a WHERE a.id=(data->>'account_id')::uuid AND a.is_active AND a.role<>'applicant')
  WHEN 'staffrole' THEN data->>'role' IN ('president','admin','secretary') AND data->>'revoked_at' IS NULL
   AND data->>'granted_by_id'=public.ctm_actor_id()::text
   AND EXISTS(SELECT 1 FROM public.staff_memberships m JOIN public.tribunal_account a ON a.id=m.account_id
    WHERE m.id=(data->>'membership_id')::uuid AND m.tribunal_id::text=current_setting('ctm.tribunal_id',true)
    AND a.is_active AND a.role<>'applicant' AND m.active_from<=statement_timestamp() AND (m.active_until IS NULL OR m.active_until>statement_timestamp()))
  ELSE false END
$$;

CREATE FUNCTION public.ctm_staff_mutable(resource text,data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT public.ctm_actor_role()='admin' AND CASE resource
  WHEN 'staffmembership' THEN data->>'tribunal_id'=current_setting('ctm.tribunal_id',true)
  WHEN 'staffrole' THEN data->>'role' IN ('president','admin','secretary') AND EXISTS(SELECT 1 FROM public.staff_memberships m
   WHERE m.id=(data->>'membership_id')::uuid AND m.tribunal_id::text=current_setting('ctm.tribunal_id',true))
  ELSE false END
$$;

CREATE FUNCTION public.ctm_guard_staff_provenance() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 IF TG_TABLE_NAME='staff_memberships' THEN
  IF (to_jsonb(NEW)-'active_until') IS DISTINCT FROM (to_jsonb(OLD)-'active_until')
   OR OLD.active_until IS NOT NULL OR NEW.active_until IS NULL OR NEW.active_until<NEW.active_from THEN
   RAISE EXCEPTION 'Membership provenance and termination history are retained' USING ERRCODE='42501';
  END IF;
 ELSIF TG_TABLE_NAME='staff_roles' THEN
  IF (to_jsonb(NEW)-'revoked_at') IS DISTINCT FROM (to_jsonb(OLD)-'revoked_at')
   OR OLD.revoked_at IS NOT NULL OR NEW.revoked_at IS NULL OR NEW.revoked_at<NEW.created_at THEN
   RAISE EXCEPTION 'Role provenance and revocation history are retained' USING ERRCODE='42501';
  END IF;
 ELSE RAISE EXCEPTION 'Tribunal identity is retained' USING ERRCODE='42501';
 END IF;
 RETURN NEW;
END
$$;

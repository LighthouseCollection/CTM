-- Forced privacy policies for the current Django source slice.
-- This does not replace the151-table contract or the remaining role/security work.
-- Trusted server code sets transaction-local actor/capability context.
-- Runtime roles must not own these tables or inherit the migration owner.

CREATE FUNCTION public.ctm_actor_id() RETURNS uuid
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE value text;
BEGIN
  value=current_setting('ctm.actor_id',true);
  IF value IS NULL OR value='' THEN RETURN NULL; END IF;
  BEGIN RETURN value::uuid; EXCEPTION WHEN invalid_text_representation THEN RETURN NULL; END;
END $$;

CREATE FUNCTION public.ctm_external_context_valid(allow_completed boolean) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT EXISTS(SELECT 1 FROM public.tribunal_reportrequest r
    JOIN public.tribunal_proceeding p ON p.id=r.proceeding_id JOIN public.tribunal_case c ON c.id=r.case_id
    WHERE r.id::text=current_setting('ctm.external_request',true) AND r.kind='external_priest'
    AND r.token_hash=current_setting('ctm.external_digest',true) AND r.token_hash<>''
    AND r.expires_at>now() AND p.status='open' AND c.status='open'
    AND (r.state='sent' OR (allow_completed AND r.state='completed')))
$$;

CREATE FUNCTION public.ctm_paid_filing_actor(target uuid) RETURNS uuid
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT a.owner_id FROM public.tribunal_checkoutintent i JOIN public.tribunal_application a ON a.id=i.application_id
 JOIN public.tribunal_feeobligation f ON f.application_id=a.id
 WHERE i.id=target AND i.state IN ('paid','needs_review','finalized') AND f.status='paid'
 AND EXISTS(SELECT 1 FROM public.tribunal_paymentevent e WHERE e.application_id=a.id AND e.kind='paid'
    AND e.provider_reference=i.provider_reference AND e.amount_minor=25000 AND e.currency='USD')
$$;

CREATE FUNCTION public.ctm_preserve_source_provenance() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 IF TG_TABLE_NAME='tribunal_application' THEN
   IF NEW.owner_id IS DISTINCT FROM OLD.owner_id OR NEW.kind IS DISTINCT FROM OLD.kind THEN
      RAISE EXCEPTION 'Original filing owner and purpose cannot be reassigned' USING ERRCODE='23514';
   END IF;
   IF OLD.submitted_at IS NOT NULL AND (
       NEW.submitted_at IS DISTINCT FROM OLD.submitted_at OR NEW.case_id IS DISTINCT FROM OLD.case_id
       OR NEW.party_id IS DISTINCT FROM OLD.party_id OR NEW.proceeding_id IS DISTINCT FROM OLD.proceeding_id
       OR NEW.questionnaire_id IS DISTINCT FROM OLD.questionnaire_id) THEN
      RAISE EXCEPTION 'Submitted filing provenance cannot be erased or reassigned' USING ERRCODE='23514';
   END IF;
   IF EXISTS(SELECT 1 FROM public.tribunal_submission s WHERE s.application_id=OLD.id)
      AND (NEW.submitted_at IS NULL OR NEW.status IN ('draft','expired','deleted')) THEN
      RAISE EXCEPTION 'Submitted history cannot become a disposable draft' USING ERRCODE='23514';
   END IF;
 ELSIF TG_TABLE_NAME='tribunal_attachment' THEN
   IF NEW.owner_id IS DISTINCT FROM OLD.owner_id OR NEW.application_id IS DISTINCT FROM OLD.application_id
      OR NEW.report_request_id IS DISTINCT FROM OLD.report_request_id THEN
      RAISE EXCEPTION 'Original file ownership and source request cannot be reassigned' USING ERRCODE='23514';
   END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION public.ctm_actor_role() RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT role FROM public.tribunal_account WHERE id=public.ctm_actor_id() AND is_active
$$;

CREATE FUNCTION public.ctm_anonymous_source_writable(resource text,data jsonb) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 IF resource='auditevent' AND data->>'actor_id' IS NULL AND data->>'action'='payment_verified' AND data->>'source'='tribunal.paymentevent' THEN
    RETURN EXISTS(SELECT 1 FROM public.tribunal_paymentevent e WHERE e.id=(data->>'source_id')::uuid AND e.kind='paid' AND e.amount_minor=25000 AND e.currency='USD');
 ELSIF resource='notification' AND data->>'kind'='paid_filing_review' THEN
    RETURN EXISTS(SELECT 1 FROM public.tribunal_checkoutintent i JOIN public.tribunal_account recipient ON recipient.id=(data->>'recipient_id')::uuid
       WHERE i.state='needs_review' AND public.ctm_paid_filing_actor(i.id) IS NOT NULL AND recipient.is_active
       AND recipient.role IN ('admin','secretary') AND data->>'key'='paid_filing_review:'||i.id::text||':'||recipient.id::text);
 END IF;
 IF resource='reportrevision' THEN
    RETURN data->>'actor_id' IS NULL AND coalesce(data->>'observations','')='' AND public.ctm_external_context_valid(false)
      AND EXISTS(SELECT 1 FROM public.tribunal_report p WHERE p.id=(data->>'report_id')::uuid
          AND p.request_id::text=current_setting('ctm.external_request',true) AND p.author_id IS NULL AND p.method='external');
 ELSIF resource='auditevent' THEN
    RETURN data->>'actor_id' IS NULL AND data->>'action'='external_report_submitted' AND data->>'source'='tribunal.report'
      AND public.ctm_external_context_valid(true) AND EXISTS(SELECT 1 FROM public.tribunal_report p JOIN public.tribunal_reportrequest r ON r.id=p.request_id
          WHERE p.id=(data->>'source_id')::uuid AND r.id::text=current_setting('ctm.external_request',true) AND r.case_id::text=data->>'case_id');
 ELSIF resource='notification' THEN
    RETURN data->>'kind'='report_received' AND public.ctm_external_context_valid(true)
      AND EXISTS(SELECT 1 FROM public.tribunal_report p JOIN public.tribunal_reportrequest r ON r.id=p.request_id
          JOIN public.tribunal_case c ON c.id=r.case_id WHERE r.id::text=current_setting('ctm.external_request',true)
          AND c.id::text=data->>'case_id' AND c.assigned_member_id::text=data->>'recipient_id'
          AND data->>'key'='report_received:'||p.id::text||':'||c.assigned_member_id::text);
 END IF;
 RETURN false;
END $$;

CREATE FUNCTION public.ctm_decree_released(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT EXISTS(SELECT 1 FROM public.tribunal_decree d
   JOIN public.tribunal_decisionrevision v ON v.id=d.decision_id
   JOIN public.tribunal_party p ON p.case_id=(SELECT case_id FROM public.tribunal_proceeding WHERE id=v.proceeding_id)
   WHERE d.signed_file_id=target AND p.account_id=public.ctm_actor_id()
   AND v.entitlements->>p.id::text='certificate'
   AND (SELECT x.action FROM public.tribunal_decreerelease x WHERE x.decree_id=d.id AND x.party_id=p.id ORDER BY x.created_at DESC,x.id DESC LIMIT 1)='release')
$$;

CREATE FUNCTION public.ctm_is_council() RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT coalesce(public.ctm_actor_role() IN ('member','president','admin','secretary'),false)
$$;

CREATE FUNCTION public.ctm_source_deletable(resource text,data jsonb) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE source_app uuid; actor uuid=public.ctm_actor_id();
BEGIN
 IF public.ctm_actor_role() IS NULL THEN RETURN false; END IF;
 CASE resource
   WHEN 'application' THEN source_app=(data->>'id')::uuid;
   WHEN 'answerrevision' THEN source_app=(data->>'application_id')::uuid;
   WHEN 'attachment' THEN source_app=(data->>'application_id')::uuid;
   WHEN 'fileversion' THEN SELECT a.application_id INTO source_app FROM public.tribunal_attachment a WHERE a.id=(data->>'attachment_id')::uuid;
   WHEN 'filetechnicalevent','documenttext' THEN SELECT a.application_id INTO source_app FROM public.tribunal_fileversion v JOIN public.tribunal_attachment a ON a.id=v.attachment_id WHERE v.id=(data->>'file_id')::uuid;
   ELSE RETURN false;
 END CASE;
 RETURN EXISTS(SELECT 1 FROM public.tribunal_application a WHERE a.id=source_app AND a.owner_id=actor AND a.status='draft' AND a.submitted_at IS NULL
   AND NOT EXISTS(SELECT 1 FROM public.tribunal_submission s WHERE s.application_id=a.id));
END $$;

CREATE FUNCTION public.ctm_application_visible(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT coalesce(EXISTS(SELECT 1 FROM public.tribunal_application a WHERE a.id=target
   AND public.ctm_actor_role() IS NOT NULL
   AND (a.owner_id=public.ctm_actor_id() OR (public.ctm_is_council() AND a.submitted_at IS NOT NULL))),false)
$$;

CREATE FUNCTION public.ctm_attachment_visible(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT coalesce(EXISTS(SELECT 1 FROM public.tribunal_attachment f
   LEFT JOIN public.tribunal_application a ON a.id=f.application_id
   WHERE f.id=target AND public.ctm_actor_role() IS NOT NULL AND (
     (f.owner_id=public.ctm_actor_id() AND f.visibility<>'council') OR
     (public.ctm_is_council() AND (f.application_id IS NULL OR a.submitted_at IS NOT NULL)
       AND (f.visibility<>'medical' OR EXISTS(SELECT 1 FROM public.tribunal_medicalrelease r WHERE r.request_id=f.report_request_id AND r.subject_id=f.owner_id AND r.scope->>'council'='true'))) OR
     EXISTS(SELECT 1 FROM public.tribunal_fileversion v WHERE v.attachment_id=f.id AND public.ctm_decree_released(v.id))
   )),false)
$$;

CREATE FUNCTION public.ctm_case_writer(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT EXISTS(SELECT 1 FROM public.tribunal_case c WHERE c.id=target AND c.status='open'
  AND (public.ctm_actor_role() IN ('admin','secretary') OR
       (public.ctm_is_council() AND c.assigned_member_id=public.ctm_actor_id())))
$$;

CREATE FUNCTION public.ctm_message_visible(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT coalesce(EXISTS(SELECT 1 FROM public.tribunal_message m WHERE m.id=target
   AND public.ctm_actor_role() IS NOT NULL AND (public.ctm_is_council() OR m.sender_id=public.ctm_actor_id() OR EXISTS(
      SELECT 1 FROM public.tribunal_messagerecipient r JOIN public.tribunal_party p ON p.id=r.party_id
      WHERE r.message_id=m.id AND p.account_id=public.ctm_actor_id()))),false)
$$;

CREATE FUNCTION public.ctm_report_visible(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT coalesce(EXISTS(SELECT 1 FROM public.tribunal_report p
   JOIN public.tribunal_reportrequest r ON r.id=p.request_id
   JOIN public.tribunal_party s ON s.id=r.subject_id
   WHERE p.id=target AND public.ctm_actor_role() IS NOT NULL AND (
      (public.ctm_is_council() AND (r.kind NOT IN ('medical','psychological') OR EXISTS(
         SELECT 1 FROM public.tribunal_medicalrelease release WHERE release.request_id=r.id AND release.scope->>'council'='true' AND release.subject_id=s.account_id))) OR
      (p.author_id=public.ctm_actor_id() AND s.account_id=public.ctm_actor_id() AND r.kind NOT IN ('interview','external_priest')))),false)
$$;

CREATE FUNCTION public.ctm_attachment_writable(data jsonb) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE actor uuid=public.ctm_actor_id(); target_case uuid=(data->>'case_id')::uuid;
BEGIN
 IF public.ctm_actor_role() IS NULL THEN RETURN false; END IF;
 IF data->>'application_id' IS NOT NULL THEN
   RETURN EXISTS(SELECT 1 FROM public.tribunal_application a WHERE a.id=(data->>'application_id')::uuid
      AND a.owner_id::text=data->>'owner_id' AND a.case_id IS NOT DISTINCT FROM target_case
      AND a.proceeding_id IS NOT DISTINCT FROM (data->>'proceeding_id')::uuid
      AND (a.owner_id=actor OR (a.submitted_at IS NOT NULL AND public.ctm_case_writer(a.case_id))));
 ELSIF data->>'report_request_id' IS NOT NULL THEN
   RETURN EXISTS(SELECT 1 FROM public.tribunal_reportrequest r JOIN public.tribunal_party p ON p.id=r.subject_id
      WHERE r.id=(data->>'report_request_id')::uuid AND r.case_id=target_case AND r.proceeding_id=(data->>'proceeding_id')::uuid
      AND p.account_id::text=data->>'owner_id' AND r.state='sent'
      AND (p.account_id=actor OR public.ctm_case_writer(r.case_id)));
 ELSE
   RETURN public.ctm_case_writer(target_case) AND data->>'visibility' IN ('council','medical')
      AND EXISTS(SELECT 1 FROM public.tribunal_proceeding p WHERE p.id=(data->>'proceeding_id')::uuid AND p.case_id=target_case AND p.status='open');
 END IF;
END $$;

CREATE FUNCTION public.ctm_file_row_readable(attachment_id uuid,file_id uuid,version_number integer) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT EXISTS(SELECT 1 FROM public.tribunal_attachment a WHERE a.id=attachment_id
   AND public.ctm_actor_role() IS NOT NULL AND (
      (public.ctm_is_council() AND public.ctm_attachment_visible(a.id)) OR
      public.ctm_decree_released(file_id) OR
      (a.owner_id=public.ctm_actor_id() AND a.visibility<>'council' AND NOT EXISTS(
         SELECT 1 FROM public.tribunal_fileversion v WHERE v.attachment_id=a.id AND v.number>version_number))))
$$;

CREATE OR REPLACE FUNCTION public.ctm_file_visible(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT EXISTS(SELECT 1 FROM public.tribunal_fileversion v WHERE v.id=target
    AND public.ctm_file_row_readable(v.attachment_id,v.id,v.number))
$$;

CREATE OR REPLACE FUNCTION public.ctm_source_writable(resource text,data jsonb) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE actor uuid=public.ctm_actor_id(); role_name text=public.ctm_actor_role();
BEGIN
 IF actor IS NULL OR role_name IS NULL THEN RETURN public.ctm_anonymous_source_writable(resource,data); END IF;
 CASE resource
   WHEN 'application' THEN RETURN (data->>'owner_id'=actor::text OR (role_name IN ('admin','secretary') AND data->>'submitted_at' IS NOT NULL))
      AND (data->>'case_id' IS NULL OR EXISTS(SELECT 1 FROM public.tribunal_party p WHERE p.case_id=(data->>'case_id')::uuid AND p.account_id=(data->>'owner_id')::uuid))
      AND (data->>'proceeding_id' IS NULL OR EXISTS(SELECT 1 FROM public.tribunal_proceeding p WHERE p.id=(data->>'proceeding_id')::uuid AND p.case_id=(data->>'case_id')::uuid));
   WHEN 'answerrevision','submission' THEN
      RETURN data->>'actor_id'=actor::text AND EXISTS(SELECT 1 FROM public.tribunal_application a WHERE a.id=(data->>'application_id')::uuid
        AND (a.owner_id=actor OR (resource='answerrevision' AND role_name IN ('admin','secretary') AND a.submitted_at IS NOT NULL)));
   WHEN 'attachment' THEN RETURN public.ctm_attachment_writable(data);
   WHEN 'fileversion' THEN RETURN data->>'actor_id'=actor::text AND EXISTS(SELECT 1 FROM public.tribunal_attachment a
      WHERE a.id=(data->>'attachment_id')::uuid AND public.ctm_attachment_writable(to_jsonb(a)));
   WHEN 'filetechnicalevent' THEN RETURN EXISTS(SELECT 1 FROM public.tribunal_fileversion v JOIN public.tribunal_attachment a ON a.id=v.attachment_id
      WHERE v.id=(data->>'file_id')::uuid AND public.ctm_attachment_writable(to_jsonb(a)));
   WHEN 'documenttext' THEN RETURN false; -- background executor scope is configured separately
   WHEN 'reportrevision' THEN RETURN data->>'actor_id'=actor::text AND EXISTS(
      SELECT 1 FROM public.tribunal_report p JOIN public.tribunal_reportrequest r ON r.id=p.request_id JOIN public.tribunal_party s ON s.id=r.subject_id
      WHERE p.id=(data->>'report_id')::uuid AND p.author_id=actor
      AND ((role_name='applicant' AND s.account_id=actor AND coalesce(data->>'observations','')='') OR public.ctm_case_writer(r.case_id)));
   WHEN 'medicalrelease' THEN RETURN data->>'subject_id'=actor::text AND EXISTS(SELECT 1 FROM public.tribunal_reportrequest r JOIN public.tribunal_party p ON p.id=r.subject_id
      WHERE r.id=(data->>'request_id')::uuid AND p.account_id=actor);
   WHEN 'message' THEN RETURN data->>'sender_id'=actor::text AND (public.ctm_case_writer((data->>'case_id')::uuid)
      OR (role_name IN ('admin','secretary')) OR EXISTS(SELECT 1 FROM public.tribunal_case c WHERE c.id=(data->>'case_id')::uuid AND c.assigned_member_id=actor AND public.ctm_is_council())
      OR (role_name='applicant' AND EXISTS(SELECT 1 FROM public.tribunal_party p WHERE p.case_id=(data->>'case_id')::uuid AND p.account_id=actor)));
   WHEN 'messagerecipient' THEN RETURN EXISTS(SELECT 1 FROM public.tribunal_message m JOIN public.tribunal_party p ON p.case_id=m.case_id
      WHERE m.id=(data->>'message_id')::uuid AND p.id=(data->>'party_id')::uuid AND m.sender_id=actor
      AND (public.ctm_is_council() OR p.account_id=actor));
   WHEN 'notification' THEN RETURN true;
   WHEN 'auditevent' THEN RETURN data->>'actor_id'=actor::text;
   WHEN 'historicalworkspace' THEN RETURN role_name='admin' AND data->>'actor_id'=actor::text;
   ELSE RETURN false;
 END CASE;
END $$;

CREATE FUNCTION public.ctm_source_mutable(resource text,data jsonb) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT CASE WHEN resource='attachment' AND data->>'application_id' IS NOT NULL THEN
    EXISTS(SELECT 1 FROM public.tribunal_application a WHERE a.id=(data->>'application_id')::uuid AND a.owner_id::text=data->>'owner_id'
      AND public.ctm_actor_role() IS NOT NULL AND (a.owner_id=public.ctm_actor_id() OR (a.submitted_at IS NOT NULL AND public.ctm_case_writer(a.case_id))))
    ELSE public.ctm_source_writable(resource,data) END
$$;

CREATE FUNCTION public.ctm_source_readable(resource text,data jsonb) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE actor uuid=public.ctm_actor_id(); role_name text=public.ctm_actor_role();
BEGIN
 IF actor IS NULL OR role_name IS NULL THEN RETURN false; END IF;
 CASE resource
   WHEN 'application' THEN RETURN data->>'owner_id'=actor::text OR (public.ctm_is_council() AND data->>'submitted_at' IS NOT NULL);
   WHEN 'answerrevision','submission' THEN RETURN public.ctm_application_visible((data->>'application_id')::uuid);
   WHEN 'attachment' THEN RETURN public.ctm_attachment_visible((data->>'id')::uuid);
   WHEN 'fileversion' THEN RETURN public.ctm_file_row_readable((data->>'attachment_id')::uuid,(data->>'id')::uuid,(data->>'number')::int);
   WHEN 'filetechnicalevent','documenttext' THEN RETURN public.ctm_file_visible((data->>'file_id')::uuid);
   WHEN 'reportrevision' THEN RETURN public.ctm_report_visible((data->>'report_id')::uuid);
   WHEN 'medicalrelease' THEN RETURN data->>'subject_id'=actor::text OR (public.ctm_is_council() AND data->'scope'->>'council'='true');
   WHEN 'message' THEN RETURN public.ctm_message_visible((data->>'id')::uuid);
   WHEN 'messagerecipient' THEN RETURN public.ctm_is_council() OR EXISTS(
      SELECT 1 FROM public.tribunal_party p WHERE p.id=(data->>'party_id')::uuid AND p.account_id=actor);
   WHEN 'notification' THEN RETURN data->>'recipient_id'=actor::text;
   WHEN 'auditevent' THEN RETURN role_name IN ('admin','secretary') OR (public.ctm_is_council() AND data->>'case_id' IS NOT NULL);
   WHEN 'historicalworkspace' THEN RETURN role_name='admin' AND data->>'actor_id'=actor::text;
   ELSE RETURN false;
 END CASE;
END $$;

CREATE TRIGGER preserve_source_provenance BEFORE UPDATE ON public.tribunal_application
FOR EACH ROW EXECUTE FUNCTION public.ctm_preserve_source_provenance();

CREATE TRIGGER preserve_source_provenance BEFORE UPDATE ON public.tribunal_attachment
FOR EACH ROW EXECUTE FUNCTION public.ctm_preserve_source_provenance();

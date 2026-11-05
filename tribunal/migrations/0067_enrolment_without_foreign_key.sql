-- ctm_council_enrolment is not a Django model, so Django's flush cannot
-- truncate it alongside tribunal_account; its foreign key made every
-- transactional test teardown fail. The same cleanup (an enrolment row never
-- outlives its account) is kept by a delete trigger instead.
ALTER TABLE public.ctm_council_enrolment DROP CONSTRAINT ctm_council_enrolment_account_id_fkey;

CREATE FUNCTION public.ctm_forget_council_enrolment() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 DELETE FROM public.ctm_council_enrolment WHERE account_id=OLD.id;
 RETURN NULL;
END $$;
REVOKE ALL ON FUNCTION public.ctm_forget_council_enrolment() FROM PUBLIC;
CREATE TRIGGER ctm_council_enrolment_forget AFTER DELETE ON public.tribunal_account
  FOR EACH ROW EXECUTE FUNCTION public.ctm_forget_council_enrolment();

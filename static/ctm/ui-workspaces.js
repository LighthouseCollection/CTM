/* UI-owned adapters for existing account, directory and system read contracts. */
(() => {
  "use strict";
  const canAdminister = (user) => ["admin", "secretary"].includes(user?.role);
  const canEnroll = (user) => user?.role === "admin";
  const roles = ["member", "president", "secretary", "admin"];
  const words = {
    en: {
      profile: "Profile", name: "Name", email: "Signed-in email", role: "Role", portal: "Portal",
      council: "Council", applicant: "Applicant", member: "Council member", president: "President", secretary: "Secretary", admin: "Administrator",
      preferences: "Account Settings", administration: "CTM Administration", members: "Council members", configuration: "Configuration", audit: "System audit",
      unavailable: "You do not have access to this workspace.", loading: "Loading…", failed: "Unable to load this information.", loadFailed: "Unable to load this information.", retry: "Retry", expired: "Your session has expired. Sign in again.", forbidden: "You do not have access to perform this action.", conflict: "This record changed. Reload and try again.", actionFailed: "Unable to save. Please try again.",
      noRows: "No records to display.", choose: "Select a record", query: "Search loaded records", action: "Action", source: "Record type", actor: "Recorded by", date: "Date and time",
      from: "From date", to: "To date", datesHelp: "Dates use Los Angeles time.", all: "All", reset: "Clear filters", dateOrder: "The end date must be on or after the start date.",
      count: "Loaded records", limited: "Filters apply to the records returned by the server.", version: "Version", value: "Value", active: "Active", yes: "Yes", no: "No",
      system: "System", otherAccount: "Other account",
      can_authorize_assignment: "Can authorize assignment", can_record_assignment: "Can record assignment",
      sessions: "Sessions", allSessions: "All sessions", upcoming: "Upcoming", past: "Past and closed",
      historical: "Historical case entry", unsaved: "Unsaved changes", unsavedHelp: "Leave this page and discard your unsaved changes?", leave: "Discard and leave", stay: "Stay",
      ui_language: "Interface language", notification_language: "Notification language", en: "English", ar: "Arabic",
      enroll: "Add council member", first_name: "First name", last_name: "Last name", emailField: "Email", save: "Add member", added: "Council member added.",
      emailInvalid: "Enter a valid email address.", roleRequired: "Choose a council role.", namesRequired: "Enter first and last names.",
      translation_prompt: "Translation instructions", translation_routing: "Translation routing", tribunal_contact: "Tribunal contact", email_templates: "Email templates", document_categories: "Document categories", recommended_doctors: "Recommended doctors",
    },
    ar: {
      profile: "حسابي", name: "الاسم", email: "البريد المستخدم لتسجيل الدخول", role: "الدور", portal: "البوابة",
      council: "المجلس", applicant: "مقدم الطلب", member: "عضو المجلس", president: "الرئيس", secretary: "السكرتير", admin: "المسؤول",
      preferences: "إعدادات الحساب", administration: "إدارة النظام", members: "أعضاء المجلس", configuration: "إعدادات النظام", audit: "سجل النظام",
      unavailable: "ليس لديك صلاحية الوصول إلى هذه الصفحة.", loading: "جارٍ التحميل…", failed: "تعذر تحميل هذه المعلومات.", loadFailed: "تعذر تحميل هذه المعلومات.", retry: "إعادة المحاولة", expired: "انتهت صلاحية الجلسة. سجّل الدخول مجددًا.", forbidden: "ليس لديك صلاحية تنفيذ هذا الإجراء.", conflict: "تغيّر السجل. أعد التحميل ثم حاول مجددًا.", actionFailed: "تعذر الحفظ. حاول مجددًا.",
      noRows: "لا توجد سجلات لعرضها.", choose: "اختر سجلًا", query: "البحث في السجلات المحملة", action: "الإجراء", source: "نوع السجل", actor: "سُجّل بواسطة", date: "التاريخ والوقت",
      from: "من تاريخ", to: "إلى تاريخ", datesHelp: "التواريخ بتوقيت لوس أنجلوس.", all: "الكل", reset: "مسح عوامل التصفية", dateOrder: "يجب ألا يسبق تاريخ النهاية تاريخ البداية.",
      count: "السجلات المحملة", limited: "تُطبّق عوامل التصفية على السجلات التي أعادها الخادم.", version: "الإصدار", value: "القيمة", active: "نشط", yes: "نعم", no: "لا",
      system: "النظام", otherAccount: "حساب آخر",
      can_authorize_assignment: "يمكنه اعتماد التعيين", can_record_assignment: "يمكنه تسجيل التعيين",
      sessions: "الجلسات", allSessions: "كل الجلسات", upcoming: "القادمة", past: "السابقة والمغلقة",
      historical: "إدخال قضية تاريخية", unsaved: "تغييرات غير محفوظة", unsavedHelp: "هل تريد مغادرة الصفحة وتجاهل التغييرات غير المحفوظة؟", leave: "تجاهل ومغادرة", stay: "البقاء",
      ui_language: "لغة الواجهة", notification_language: "لغة الإشعارات", en: "الإنجليزية", ar: "العربية",
      enroll: "إضافة عضو إلى المجلس", first_name: "الاسم الأول", last_name: "اسم العائلة", emailField: "البريد الإلكتروني", save: "إضافة العضو", added: "تمت إضافة عضو المجلس.",
      emailInvalid: "أدخل بريدًا إلكترونيًا صالحًا.", roleRequired: "اختر دورًا في المجلس.", namesRequired: "أدخل الاسم الأول واسم العائلة.",
      translation_prompt: "تعليمات الترجمة", translation_routing: "توجيه الترجمة", tribunal_contact: "بيانات الاتصال بالمحكمة", email_templates: "قوالب البريد الإلكتروني", document_categories: "فئات المستندات", recommended_doctors: "الأطباء الموصى بهم",
    },
  };
  const translator = (lang) => (key) => words[lang === "ar" ? "ar" : "en"][key] || key;
  function auditDay(timestamp) {
    const date = new Date(timestamp);
    if (!Number.isFinite(date.getTime())) return "";
    const parts = Object.fromEntries(new Intl.DateTimeFormat("en-US", { timeZone: "America/Los_Angeles", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(date).map((part) => [part.type, part.value]));
    return `${parts.year}-${parts.month}-${parts.day}`;
  }
  function filterAudit(rows, filters = {}) {
    const query = (filters.query || "").trim().toLocaleLowerCase();
    return rows.filter((row) => {
      const day = auditDay(row.timestamp);
      return (!filters.action || row.action === filters.action) && (!filters.source || row.source === filters.source) &&
        (!filters.actor || (row.actor_id || row.actor) === filters.actor) && (!filters.from || day && day >= filters.from) && (!filters.to || day && day <= filters.to) &&
        (!query || [row.label, row.action, row.source, row.actor].some((value) => String(value || "").toLocaleLowerCase().includes(query)));
    });
  }
  function enrollmentProblem(form) {
    if (!form.first_name?.trim() || !form.last_name?.trim()) return "namesRequired";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email?.trim() || "")) return "emailInvalid";
    return roles.includes(form.role) ? null : "roleRequired";
  }
  function filterSessions(rows, filters, today) {
    return rows.filter((row) => {
      const upcoming = row.state === "planned" && row.date >= today;
      return (!filters.view || filters.view === "all" || (filters.view === "upcoming" ? upcoming : !upcoming)) &&
        (!filters.from || row.date >= filters.from) && (!filters.to || row.date <= filters.to);
    });
  }
  function SessionFilters({ filters, onChange, lang, showView = true }) {
    const P = window.Plenix, h = window.React.createElement, t = translator(lang);
    return h(P.Inline, { wrap: true, align: "end" },
      showView ? h(P.Field, { label: t("sessions") }, h(P.Select, { value: filters.view || "all", onChange: (event) => onChange({ ...filters, view: event.target.value }), options: ["all", "upcoming", "past"].map((value) => ({ value, label: t(value === "all" ? "allSessions" : value) })) })) : null,
      ...["from", "to"].map((key) => h(P.Field, { key, label: t(key) }, h(P.Input, { type: "date", value: filters[key] || "", onChange: (event) => onChange({ ...filters, [key]: event.target.value }) }))),
      h(P.Button, { variant: "ghost", onClick: () => onChange({}) }, t("reset")),
      filters.from && filters.to && filters.from > filters.to ? h(P.Notice, { tone: "warning" }, t("dateOrder")) : null);
  }
  function AuditFilters({ rows, filters, onChange, lang, includeActor = true }) {
    const P = window.Plenix, h = window.React.createElement, t = translator(lang);
    const field = (key, control) => h(P.Field, { key, label: t(key) }, control);
    const update = (key, value) => onChange({ ...filters, [key]: value });
    const options = (key) => {
      const values = [...new Set(rows.map((row) => key === "actor" ? row.actor_id || row.actor : row[key]).filter(Boolean))].sort();
      return [{ value: "", label: t("all") }, ...values.map((value) => {
        const row = rows.find((item) => (key === "actor" ? item.actor_id || item.actor : item[key]) === value);
        const label = key === "action" ? row.label || value : key === "actor" ? row.actor === "system" ? t("system") : row.actor || `${t("otherAccount")} (${value})` : value;
        return { value, label };
      })];
    };
    return h(P.Stack, { gap: "sm" },
      h(P.Inline, { wrap: true, align: "end" },
        field("query", h(P.Input, { type: "search", value: filters.query || "", onChange: (event) => update("query", event.target.value) })),
        ...["action", "source", ...(includeActor ? ["actor"] : [])].map((key) => field(key, h(P.Select, {
          value: filters[key] || "", onChange: (event) => update(key, event.target.value),
          options: options(key),
        }))),
        ...["from", "to"].map((key) => field(key, h(P.Input, { type: "date", value: filters[key] || "", onChange: (event) => update(key, event.target.value) }))),
        h(P.Button, { variant: "ghost", onClick: () => onChange({}) }, t("reset")),
      ),
      h(P.Text, { variant: "secondary" }, t("datesHelp")),
      filters.from && filters.to && filters.from > filters.to ? h(P.Notice, { tone: "warning" }, t("dateOrder")) : null,
    );
  }
  function Properties({ entries, lang }) {
    const P = window.Plenix, h = window.React.createElement, t = translator(lang);
    return h(P.PropertyList, { layout: "stacked" }, ...entries.filter(([, value]) => value !== undefined && value !== null && value !== "").map(([key, value]) => h(P.PropertyList.Item, { key, label: t(key) }, typeof value === "boolean" ? t(value ? "yes" : "no") : ["role", "portal", "ui_language", "notification_language"].includes(key) ? t(String(value)) : String(value))));
  }
  function Profile({ user, lang, onSettings }) {
    const P = window.Plenix, h = window.React.createElement, t = translator(lang);
    return h(P.Stack, { gap: "lg" }, h(P.Text, { as: "h1", variant: "title" }, t("profile")),
      h(P.Panel, { icon: "user", title: user.name || t("profile") },
        h(Properties, { lang, entries: [["name", user.name], ["email", user.email], ["role", user.role], ["portal", user.portal], ["ui_language", user.ui_language], ["notification_language", user.notification_language]] })),
      h(P.Button, { onClick: onSettings }, t("preferences")));
  }
  function ConfigurationValue({ value, lang }) {
    const P = window.Plenix, h = window.React.createElement, t = translator(lang);
    if (value === null || value === undefined) return h(P.Text, null, "—");
    if (Array.isArray(value)) return value.length ? h(P.List, { items: value.map((item) => ({ children: h(ConfigurationValue, { value: item, lang }) })) }) : h(P.EmptyState, { title: t("noRows") });
    if (typeof value === "object") return h(P.PropertyList, { layout: "stacked" }, ...Object.entries(value).map(([key, item]) => h(P.PropertyList.Item, { key, label: t(key) }, h(ConfigurationValue, { value: item, lang }))));
    return h(P.Text, { as: "p" }, typeof value === "boolean" ? t(value ? "yes" : "no") : String(value));
  }
  function useDraftGuard({ dirty, pending, onNavigationGuard, lang }) {
    const R = window.React, P = window.Plenix, h = R.createElement, t = translator(lang);
    const [move, setMove] = R.useState(null);
    const navigate = R.useCallback((next) => { if (pending) return; if (dirty) setMove(() => next); else next(); }, [dirty, pending]);
    R.useEffect(() => {
      onNavigationGuard?.(navigate);
      return () => onNavigationGuard?.(null);
    }, [navigate, onNavigationGuard]);
    R.useEffect(() => {
      if (!dirty && !pending) return;
      const guard = (event) => { event.preventDefault(); event.returnValue = ""; };
      window.addEventListener("beforeunload", guard);
      return () => window.removeEventListener("beforeunload", guard);
    }, [dirty, pending]);
    return { navigate, dialog: h(P.ConfirmDialog, { open: Boolean(move), title: t("unsaved"), message: t("unsavedHelp"), confirmLabel: t("leave"), cancelLabel: t("stay"), onConfirm: () => { const next = move; setMove(null); next?.(); }, onCancel: () => setMove(null) }) };
  }
  function Enrollment({ api, user, lang, onAdded, onNavigationGuard }) {
    const R = window.React, P = window.Plenix, h = R.createElement, t = translator(lang);
    const [form, setForm] = R.useState({ first_name: "", last_name: "", email: "", role: "member" });
    const [pending, setPending] = R.useState(false), [problem, setProblem] = R.useState(null), [failure, setFailure] = R.useState(null);
    const guard = useDraftGuard({ dirty: Boolean(form.first_name || form.last_name || form.email || form.role !== "member"), pending, onNavigationGuard, lang });
    if (!canEnroll(user)) return null;
    async function save(event) {
      event.preventDefault();
      if (pending) return;
      const issue = enrollmentProblem(form);
      setProblem(issue);
      if (issue) return;
      setPending(true); setFailure(null);
      try {
        await api("/api/council/enroll/", { method: "POST", body: JSON.stringify({ ...form, first_name: form.first_name.trim(), last_name: form.last_name.trim(), email: form.email.trim() }) });
        setForm({ first_name: "", last_name: "", email: "", role: "member" }); onAdded();
      } catch (error) { setFailure(window.CTMCouncil.serverMessage(error, t)); }
      finally { setPending(false); }
    }
    return h(P.Panel, { title: t("enroll"), icon: "user", collapsible: true, defaultExpanded: false, strings: { collapse: lang === "ar" ? "طي {title}" : "Collapse {title}", expand: lang === "ar" ? "توسيع {title}" : "Expand {title}" } },
      h(P.Form, { label: t("enroll"), onSubmit: save, noValidate: true },
        h(P.Inline, { wrap: true }, ...["first_name", "last_name", "email"].map((key) => h(P.Field, { key, label: t(key === "email" ? "emailField" : key), required: true }, h(P.Input, { type: key === "email" ? "email" : "text", value: form[key], maxLength: key === "email" ? 254 : 150, disabled: pending, onChange: (event) => { setForm({ ...form, [key]: event.target.value }); setProblem(null); } }))),
          h(P.Field, { label: t("role"), required: true }, h(P.Select, { value: form.role, disabled: pending, onChange: (event) => setForm({ ...form, role: event.target.value }), options: roles.map((value) => ({ value, label: t(value) })) }))),
        problem ? h(P.Notice, { tone: "warning" }, t(problem)) : null,
        failure ? h(P.Notice, { tone: "danger" }, failure) : null,
        h(P.FormActions, { sticky: false }, h(P.Button, { type: "submit", variant: "primary", disabled: pending, loading: pending }, t("save")))), guard.dialog);
  }
  function Administration({ api, user, lang, onNavigationGuard, onCase }) {
    const R = window.React, P = window.Plenix, h = R.createElement, t = translator(lang), base = window.CTMCouncil;
    const [section, setSection] = R.useState("members"), [filters, setFilters] = R.useState({}), [notice, setNotice] = R.useState(false);
    const sectionGuard = R.useRef(null);
    const registerGuard = R.useCallback((guard) => { sectionGuard.current = guard; onNavigationGuard?.(guard); }, [onNavigationGuard]);
    const allowed = canAdminister(user);
    const [state, retry] = base.useLoad(() => allowed && section !== "historical" ? api({ members: "/api/council/members/", configuration: "/api/system/settings/", audit: "/api/system/audit/" }[section]) : Promise.resolve({ items: [] }), [section, allowed]);
    if (!allowed) return h(P.Notice, { tone: "danger" }, t("unavailable"));
    const rows = state.data?.items || [];
    const filtered = section === "audit" ? filterAudit(rows, filters) : rows;
    const columns = section === "members" ? [{ title: t("name"), field: "name", kind: "name" }, { title: t("role"), field: "role", render: (row) => t(row.role) }] : section === "configuration" ? [{ title: t("configuration"), field: "key", kind: "name", render: (row) => t(row.key) }, { title: t("version"), field: "version" }] : [{ title: t("action"), field: "action", kind: "name" }, { title: t("source"), field: "source" }, { title: t("date"), field: "timestamp", render: (row) => base.formatWhen(row.timestamp, lang) }];
    return h(P.Stack, { gap: "lg", className: "plx-u-flex-1 plx-u-min-h-0" },
      h(P.Text, { as: "h1", variant: "title" }, t("administration")),
      h(P.Inline, { wrap: true }, ...["members", "configuration", "audit", ...(canEnroll(user) ? ["historical"] : [])].map((key) => h(P.Button, { key, selected: key === section, onClick: () => { if (key === section) return; const move = () => { setSection(key); setFilters({}); setNotice(false); }; if (sectionGuard.current) sectionGuard.current(move); else move(); } }, t(key)))),
      notice ? h(P.Notice, { tone: "success", onDismiss: () => setNotice(false) }, t("added")) : null,
      section === "members" ? h(Enrollment, { api, user, lang, onNavigationGuard: registerGuard, onAdded: () => { setNotice(true); retry(); } }) : null,
      section === "historical" ? h(window.CTMHistorical.Workspace, { api, user, lang, onNavigationGuard: registerGuard, onCase }) : null,
      section === "audit" ? h(AuditFilters, { rows, filters, onChange: setFilters, lang, includeActor: false }) : null,
      section === "historical" ? null : state.pending ? base.loadingView(P, h, t) : state.error ? base.loadFailure(P, h, t, retry, state.error) : h(R.Fragment, null,
        h(P.Text, { variant: "secondary" }, `${t("count")}: ${filtered.length}. ${t("limited")}`),
        h(window.CTMShell.Workspace, { key: section, label: t(section), rows: filtered, columns, empty: t("noRows"), selectionPrompt: t("choose") }, (row) => h(P.Stack, { gap: "md" },
          h(P.Text, { as: "h2", variant: "heading" }, row.name || t(row.key || row.action)),
          section === "configuration" ? h(ConfigurationValue, { value: row.value, lang }) : h(Properties, { lang, entries: section === "members" ? [["name", row.name], ["role", row.role], ["active", row.active], ["can_authorize_assignment", row.can_authorize_assignment], ["can_record_assignment", row.can_record_assignment]] : [["action", row.action], ["source", row.source], ["date", base.formatWhen(row.timestamp, lang)]] }),
        ))));
  }
  window.CTMUI = Object.freeze({ canAdminister, canEnroll, filterAudit, filterSessions, enrollmentProblem, translator, AuditFilters, SessionFilters, useDraftGuard, Profile, Administration });
})();

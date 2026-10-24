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
      administration: "CTM Administration", members: "Council members", configuration: "Configuration", audit: "System audit",
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
      administration: "إدارة النظام", members: "أعضاء المجلس", configuration: "إعدادات النظام", audit: "سجل النظام",
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
  function Profile({ api, user, lang, onUserUpdated }) {
    const R = window.React, P = window.Plenix, h = R.createElement, t = translator(lang);
    const [form, setForm] = R.useState({ first_name: user.first_name || user.name?.split(" ")[0] || "", last_name: user.last_name || user.name?.split(" ").slice(1).join(" ") || "" });
    const [saving, setSaving] = R.useState(false), [notice, setNotice] = R.useState(null), [failure, setFailure] = R.useState(null);
    const [state, retry] = window.CTMCouncil.useLoad(() => Promise.all([api("/api/account/sessions/"), api("/api/account/activity/")]).then(([sessions, activity]) => ({ sessions: sessions.items || [], activity: activity.items || [] })), []);
    const save = async (event) => {
      event.preventDefault();
      setSaving(true); setFailure(null); setNotice(null);
      try {
        const updated = await api("/api/account/settings/", { method: "POST", body: JSON.stringify({ first_name: form.first_name.trim(), last_name: form.last_name.trim() }) });
        onUserUpdated?.(updated); setNotice("Profile updated.");
      } catch (error) { setFailure(window.CTMCouncil.serverMessage(error, t)); }
      finally { setSaving(false); }
    };
    const preference = async (field, value) => {
      setSaving(true); setFailure(null); setNotice(null);
      try { const updated = await api("/api/account/settings/", { method: "POST", body: JSON.stringify({ [field]: value }) }); onUserUpdated?.(updated); setNotice("Notification preferences updated."); }
      catch (error) { setFailure(window.CTMCouncil.serverMessage(error, t)); }
      finally { setSaving(false); }
    };
    const role = t(user.role || "member"), portal = t(user.portal || "council");
    return h(P.Stack, { gap: "lg" },
      h(P.Text, { as: "h1", variant: "title" }, "My Account"),
      h("header", { className: "ctm-account-hero" },
        h("span", { className: "ctm-account-hero__avatar", "aria-hidden": true }, (user.name || "?").split(/\s+/).map((word) => word[0]).join("").slice(0, 2)),
        h("div", null, h(P.Text, { as: "h2", variant: "heading" }, user.name), h(P.Text, { variant: "secondary" }, `${role} · ${portal}`)),
      ),
      notice ? h(P.Notice, { tone: "success", onDismiss: () => setNotice(null) }, notice) : null,
      failure ? h(P.Notice, { tone: "danger", onDismiss: () => setFailure(null) }, failure) : null,
      h(P.Panel, { icon: "person", title: "Profile" }, h(P.Form, { onSubmit: save, label: "Profile", noValidate: true },
        h("div", { className: "ctm-account-grid" },
          h(P.Field, { label: "First name", required: true }, h(P.Input, { value: form.first_name, maxLength: 150, disabled: saving, onChange: (event) => setForm({ ...form, first_name: event.target.value }) })),
          h(P.Field, { label: "Last name", required: true }, h(P.Input, { value: form.last_name, maxLength: 150, disabled: saving, onChange: (event) => setForm({ ...form, last_name: event.target.value }) })),
          h(P.Field, { label: "Signed-in email" }, h(P.Input, { value: user.email || "", disabled: true })),
        ), h(P.FormActions, { sticky: false }, h(P.Button, { type: "submit", variant: "primary", loading: saving, disabled: saving }, "Save changes")))),
      h(P.Panel, { icon: "lock", title: "Security" }, h(P.Stack, { gap: "md" },
        h(P.Text, { variant: "secondary" }, "Your account uses your authorized identity-provider sign-in. Password changes are managed by that provider."),
        state.pending ? h(P.Text, { variant: "secondary" }, t("loading")) : state.error ? h(P.Button, { onClick: retry }, t("retry")) : h(P.PropertyList, { layout: "stacked" },
          h(P.PropertyList.Item, { label: "Active sessions" }, String(state.data.sessions.length)),
          h(P.PropertyList.Item, { label: "Current session" }, state.data.sessions.some((item) => item.current) ? "Active" : "—"),
        ),
      )),
      h(P.Panel, { icon: "settings-users", title: "Tribunal Role" }, h(P.PropertyList, { layout: "stacked" },
        h(P.PropertyList.Item, { label: "Role" }, role), h(P.PropertyList.Item, { label: "Portal" }, portal), h(P.PropertyList.Item, { label: "Permissions" }, "Managed by tribunal administration"),
      )),
      h(P.Panel, { icon: "hdr-bell", title: "Notifications" }, h(P.Stack, { gap: "md" },
        h(P.Text, { variant: "secondary" }, "Choose the language used for notification messages."),
        h(P.Inline, { wrap: true }, ...["en", "ar"].map((value) => h(P.Button, { key: value, selected: user.notification_language === value, disabled: saving, onClick: () => preference("notification_language", value) }, t(value)))),
      )),
      h(P.Panel, { icon: "activity", title: "Activity Log" },
        state.pending ? h(P.Text, { variant: "secondary" }, t("loading")) : state.error ? h(P.Button, { onClick: retry }, t("retry")) : state.data.activity.length ? h(P.List, { variant: "bullets", items: state.data.activity.map((item) => ({ children: `${item.action} · ${window.CTMCouncil.formatWhen(item.timestamp, lang)}` })) }) : h(P.EmptyState, { title: "No account activity is available yet." }),
      ),
    );
  }

  function SecuritySessions({ api, lang }) {
    const R = window.React, P = window.Plenix, h = R.createElement;
    const [saving, setSaving] = R.useState(false), [failure, setFailure] = R.useState(null);
    const [state, retry] = window.CTMCouncil.useLoad(() => api("/api/account/sessions/"), []);
    const sessions = state.data?.items || [];
    const revoke = async (row) => { setSaving(true); setFailure(null); try { await api(`/api/account/sessions/${encodeURIComponent(row.handle)}/revoke/`, { method: "POST", body: "{}" }); retry(); } catch (error) { setFailure(window.CTMCouncil.serverMessage(error)); } finally { setSaving(false); } };
    const revokeOthers = async () => { setSaving(true); setFailure(null); try { for (const row of sessions.filter((item) => !item.current)) await api(`/api/account/sessions/${encodeURIComponent(row.handle)}/revoke/`, { method: "POST", body: "{}" }); retry(); } catch (error) { setFailure(window.CTMCouncil.serverMessage(error)); } finally { setSaving(false); } };
    return h(P.Panel, { title: "Active Sessions", icon: "lock" }, h(P.Stack, { gap: "md" },
      h(P.Inline, { align: "between", wrap: true }, h(P.Text, { variant: "secondary" }, "Sessions currently signed in to your account."), h(P.Button, { disabled: saving || !sessions.some((row) => !row.current), onClick: revokeOthers }, "Revoke all other sessions")),
      failure ? h(P.Notice, { tone: "danger", onDismiss: () => setFailure(null) }, failure) : null,
      state.pending ? h(P.Text, { variant: "secondary" }, "Loading sessions…") : state.error ? h(P.Button, { onClick: retry }, "Retry") : sessions.length ? h(P.List, { items: sessions.map((row) => ({ children: h(P.Inline, { align: "between", wrap: true }, h("span", null, row.current ? "Current session" : `Session ending ${window.CTMCouncil.formatWhen(row.expires_at, lang)}`), row.current ? h(P.Text, { variant: "secondary" }, "Current session") : h(P.Button, { size: "xs", variant: "danger-secondary", disabled: saving, onClick: () => revoke(row) }, "Revoke")) })) }) : h(P.EmptyState, { title: "No active sessions." })
    ));
  }  function ConfigurationValue({ value, lang }) {
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
        await api("/api/system/members/", { method: "POST", body: JSON.stringify({ ...form, first_name: form.first_name.trim(), last_name: form.last_name.trim(), email: form.email.trim() }) });
        setForm({ first_name: "", last_name: "", email: "", role: "member" }); onAdded();
      } catch (error) { setFailure(window.CTMCouncil.serverMessage(error, t)); }
      finally { setPending(false); }
    }
    return h(P.Panel, { title: t("enroll"), icon: "person", collapsible: true, defaultExpanded: false, strings: { collapse: lang === "ar" ? "طي {title}" : "Collapse {title}", expand: lang === "ar" ? "توسيع {title}" : "Expand {title}" } },
      h(P.Form, { label: t("enroll"), onSubmit: save, noValidate: true },
        h(P.Inline, { wrap: true }, ...["first_name", "last_name", "email"].map((key) => h(P.Field, { key, label: t(key === "email" ? "emailField" : key), required: true }, h(P.Input, { type: key === "email" ? "email" : "text", value: form[key], maxLength: key === "email" ? 254 : 150, disabled: pending, onChange: (event) => { setForm({ ...form, [key]: event.target.value }); setProblem(null); } }))),
          h(P.Field, { label: t("role"), required: true }, h(P.Select, { value: form.role, disabled: pending, onChange: (event) => setForm({ ...form, role: event.target.value }), options: roles.map((value) => ({ value, label: t(value) })) }))),
        problem ? h(P.Notice, { tone: "warning" }, t(problem)) : null,
        failure ? h(P.Notice, { tone: "danger" }, failure) : null,
        h(P.FormActions, { sticky: false }, h(P.Button, { type: "submit", variant: "primary", disabled: pending, loading: pending }, t("save")))), guard.dialog);
  }
  function MemberDirectory({ api, user, lang, rows, pending, retry, onNavigationGuard, onAdded }) {
    const R = window.React, P = window.Plenix, h = R.createElement, t = translator(lang);
    const [view, setView] = R.useState("active"), [enrolling, setEnrolling] = R.useState(false), [editing, setEditing] = R.useState(null), [archiveTarget, setArchiveTarget] = R.useState(null), [saving, setSaving] = R.useState(false), [failure, setFailure] = R.useState(null);
    const visibleRows = rows.filter((row) => view === "active" ? row.active : !row.active);
    const updateMember = async (event) => {
      event.preventDefault();
      if (!editing || saving) return;
      setSaving(true); setFailure(null);
      try {
        await api(`/api/system/members/${encodeURIComponent(editing.id)}/`, { method: "POST", body: JSON.stringify({ first_name: editing.first_name.trim(), last_name: editing.last_name.trim(), expected_version: editing.profile_version }) });
        setEditing(null); retry();
      } catch (error) { setFailure(window.CTMCouncil.serverMessage(error, t)); }
      finally { setSaving(false); }
    };
    const changeStatus = async () => {
      if (!archiveTarget || saving) return;
      setSaving(true); setFailure(null);
      try {
        await api(`/api/system/accounts/${encodeURIComponent(archiveTarget.id)}/status/`, { method: "POST", body: JSON.stringify({ enabled: !archiveTarget.active, expected_version: archiveTarget.status_version }) });
        setArchiveTarget(null); retry();
      } catch (error) { setFailure(window.CTMCouncil.serverMessage(error, t)); }
      finally { setSaving(false); }
    };
    const columns = [
      { title: "Name", field: "name", kind: "name", render: (row) => `${row.first_name} ${row.last_name}`.trim() },
      { title: "Role", field: "role", render: (row) => t(row.role) },
      { title: "Email", field: "email", kind: "data" },
      { title: "Active cases", field: "active_case_count", type: "number", kind: "data" },
      { title: "Status", field: "status", render: (row) => row.active ? "Active" : "Archived" },
      { title: "Actions", field: "actions", kind: "actions", minWidth: "20rem", render: (row) => h(P.Inline, { gap: "xs", wrap: true },
        h(P.Button, { size: "xs", icon: "pencil", disabled: saving, onClick: () => setEditing({ ...row }) }, "Edit"),
        h(P.Button, { size: "xs", icon: "key", disabled: saving, onClick: () => setEditing({ ...row }) }, "Manage access"),
        row.active && row.can_suspend ? h(P.Button, { size: "xs", icon: "archive", variant: "danger-secondary", disabled: saving, onClick: () => setArchiveTarget(row) }, "Archive") : null,
        !row.active && row.can_reactivate ? h(P.Button, { size: "xs", icon: "restore", disabled: saving, onClick: () => setArchiveTarget(row) }, "Restore") : null,
      ) },
    ];
    return h(P.Stack, { gap: "md" },
      h(P.Inline, { align: "between", wrap: true }, h(P.Text, { as: "h2", variant: "heading" }, "Users"), h(P.Button, { icon: "add", onClick: () => setEnrolling(true) }, "Add staff user")),
      h(P.Tabs, { variant: "contained", label: "Users", value: view, onChange: setView, items: [
        { value: "active", label: "Active Members", content: h(window.CTMShell.Table, { label: "Active members", rows: visibleRows, columns, empty: "No active members." }) },
        { value: "previous", label: "Previous Members", content: h(window.CTMShell.Table, { label: "Previous members", rows: visibleRows, columns, empty: "No previous members." }) },
      ] }),
      enrolling ? h(P.Dialog, { open: true, title: "Add staff user", size: "lg", onClose: () => !saving && setEnrolling(false) }, h(Enrollment, { api, user, lang, onNavigationGuard, onAdded: () => { setEnrolling(false); onAdded(); } })) : null,
      editing ? h(P.Dialog, { open: true, title: "Edit staff user", size: "sm", onClose: () => !saving && setEditing(null) }, h(P.Form, { label: "Edit staff user", onSubmit: updateMember, noValidate: true },
        h(P.Stack, { gap: "md" },
          h(P.Field, { label: "First name", required: true }, h(P.Input, { value: editing.first_name, maxLength: 150, disabled: saving, onChange: (event) => setEditing({ ...editing, first_name: event.target.value }) })),
          h(P.Field, { label: "Last name", required: true }, h(P.Input, { value: editing.last_name, maxLength: 150, disabled: saving, onChange: (event) => setEditing({ ...editing, last_name: event.target.value }) })),
          h(P.Field, { label: "Email" }, h(P.Input, { value: editing.email, disabled: true })),
          h(P.Text, { variant: "secondary" }, "Account access uses the member’s verified lacopts.org Microsoft sign-in."),
          failure ? h(P.Notice, { tone: "danger" }, failure) : null,
          h(P.FormActions, { sticky: false }, h(P.Button, { type: "submit", variant: "primary", loading: saving, disabled: saving }, "Save changes"))
        )
      )) : null,
      h(P.ConfirmDialog, { open: Boolean(archiveTarget), title: archiveTarget?.active ? "Archive staff user" : "Restore staff user", message: archiveTarget?.active ? `Archive ${archiveTarget.first_name} ${archiveTarget.last_name}? Their account access will be disabled.` : `Restore ${archiveTarget?.first_name || "this user"}? Their account access will be enabled.`, confirmLabel: archiveTarget?.active ? "Archive" : "Restore", cancelLabel: "Cancel", onConfirm: changeStatus, onCancel: () => !saving && setArchiveTarget(null) }, failure ? h(P.Notice, { tone: "danger" }, failure) : null)
    );
  }  function ConfigurationWorkspace({ api, rows, lang, onNavigationGuard }) {
    const R = window.React, P = window.Plenix, h = R.createElement;
    const byKey = Object.fromEntries(rows.map((row) => [row.key, row]));
    const [tab, setTab] = R.useState("diocese"), [saving, setSaving] = R.useState(false), [notice, setNotice] = R.useState(null), [failure, setFailure] = R.useState(null);
    const defaultDiocese = { diocese_name: "Diocese of Los Angeles", system_email: "tribunal@lacopts.org", case_id_prefix: "CTM", default_session_day: "Tuesday", session_location: "", presiding_bishop: "", tribunal_secretary: "" };
    const [diocese, setDiocese] = R.useState(byKey.diocese_settings?.value || defaultDiocese);
    const [mobile, setMobile] = R.useState(byKey.mobile_settings?.value || { system_available_mobile: true });
    const [drafts, setDrafts] = R.useState({}), [versions, setVersions] = R.useState({});
    R.useEffect(() => { if (byKey.diocese_settings?.value) setDiocese(byKey.diocese_settings.value); if (byKey.mobile_settings?.value) setMobile(byKey.mobile_settings.value); }, [rows.length]);
    const valueFor = (key, fallback) => drafts[key] === undefined ? JSON.stringify(byKey[key]?.value || fallback, null, 2) : drafts[key];
    async function save(key, value) {
      setSaving(true); setFailure(null); setNotice(null);
      try {
        await api("/api/system/settings/", { method: "POST", body: JSON.stringify({ key, value, expected_version: byKey[key]?.version || 0, schema_version: 1 }) });
        setNotice(`${key.replaceAll("_", " ")} saved.`);
      } catch (error) { setFailure(window.CTMCouncil.serverMessage(error)); }
      finally { setSaving(false); }
    }
    function jsonCard(key, title, help, fallback) {
      const value = valueFor(key, fallback);
      return h(P.Panel, { title, icon: "settings" }, h(P.Stack, { gap: "md" },
        h(P.Text, { variant: "secondary" }, help),
        h(P.Field, { label: title }, h(P.Textarea, { value, rows: 14, disabled: saving, onChange: (event) => setDrafts({ ...drafts, [key]: event.target.value }) })),
        h(P.FormActions, { sticky: false }, h(P.Button, { variant: "primary", disabled: saving, loading: saving, onClick: () => { try { save(key, JSON.parse(value)); } catch { setFailure("Use valid JSON before saving."); } } }, "Save changes"))
      ));
    }
    const dioceseCard = h(P.Panel, { title: "Diocese Settings", icon: "church" }, h(P.Form, { label: "Diocese settings", onSubmit: (event) => { event.preventDefault(); save("diocese_settings", diocese); } }, h(P.Stack, { gap: "md" },
      h(P.Inline, { wrap: true }, ...[["diocese_name", "Diocese name"], ["system_email", "System email"], ["case_id_prefix", "Case ID prefix"], ["session_location", "Session location"], ["presiding_bishop", "Presiding bishop"], ["tribunal_secretary", "Tribunal secretary"]].map(([key, label]) => h(P.Field, { key, label, required: key !== "case_id_prefix" }, h(P.Input, { type: key === "system_email" ? "email" : "text", value: diocese[key], disabled: saving, onChange: (event) => setDiocese({ ...diocese, [key]: event.target.value }) }))),
        h(P.Field, { label: "Default session day", required: true }, h(P.Select, { value: diocese.default_session_day, disabled: saving, onChange: (event) => setDiocese({ ...diocese, default_session_day: event.target.value }), options: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].map((value) => ({ value, label: value })) }))),
      h(P.FormActions, { sticky: false }, h(P.Button, { type: "submit", variant: "primary", disabled: saving, loading: saving }, "Save changes"))
    )));
    const mobileCard = h(P.Panel, { title: "Mobile Settings", icon: "mobile" }, h(P.Form, { label: "Mobile settings", onSubmit: (event) => { event.preventDefault(); save("mobile_settings", mobile); } }, h(P.Stack, { gap: "md" },
      h(P.Checkbox, { label: "System available on mobile", checked: mobile.system_available_mobile, disabled: saving, onChange: (event) => setMobile({ system_available_mobile: event.target.checked }) }),
      h(P.Text, { variant: "secondary" }, "Desktop access remains available. This setting controls whether the CTM interface is offered on mobile devices."),
      h(P.FormActions, { sticky: false }, h(P.Button, { type: "submit", variant: "primary", disabled: saving, loading: saving }, "Save changes"))
    )));
    const tabs = [
      { value: "diocese", label: "Diocese Settings", content: dioceseCard },
      { value: "templates", label: "Document Templates", content: jsonCard("document_templates", "Document Templates", "Create and maintain the reusable tribunal document templates.", { templates: [] }) },
      { value: "outcomes", label: "Decision Outcomes", content: jsonCard("decision_outcomes", "Decision Outcomes", "Configure the available decision outcomes and their rationale requirement.", { outcomes: [] }) },
      { value: "stages", label: "Case Workflow Stages", content: jsonCard("workflow_stages", "Case Workflow Stages", "Configure workflow labels, colors, and active stages.", { stages: [] }) },
      { value: "reasons", label: "Canonical Reasons", content: jsonCard("canonical_reasons", "Canonical Reasons", "Configure canonical reasons, colors, and availability.", { reasons: [] }) },
    ];
    return h(P.Stack, { gap: "md" }, notice ? h(P.Notice, { tone: "success", onDismiss: () => setNotice(null) }, notice) : null, failure ? h(P.Notice, { tone: "danger", onDismiss: () => setFailure(null) }, failure) : null, h(P.Tabs, { variant: "contained", label: "Tribunal configuration", value: tab, onChange: setTab, items: tabs }), tab === "diocese" ? null : null, mobileCard);
  }  function Administration({ api, user, lang, onNavigationGuard, onCase, initialSection = "members", onSectionChange }) {
    const R = window.React, P = window.Plenix, h = R.createElement, t = translator(lang), base = window.CTMCouncil;
    const [section, setSection] = R.useState(initialSection), [filters, setFilters] = R.useState({}), [notice, setNotice] = R.useState(false);
    const sectionGuard = R.useRef(null);
    const registerGuard = R.useCallback((guard) => { sectionGuard.current = guard; onNavigationGuard?.(guard); }, [onNavigationGuard]);
    const allowed = canAdminister(user);
    const [state, retry] = base.useLoad(
      () => allowed && section !== "historical"
        ? api({ members: "/api/system/members/", configuration: "/api/system/settings/", audit: "/api/system/audit/" }[section])
        : Promise.resolve({ items: [] }),
      [section, allowed]
    );
    if (!allowed) return h(P.Notice, { tone: "danger" }, t("unavailable"));
    const rows = state.data?.items || [];
    const filtered = section === "audit" ? filterAudit(rows, filters) : rows;
    const columns = section === "members"
      ? [{ title: t("name"), field: "name", kind: "name" }, { title: t("role"), field: "role", render: (row) => t(row.role) }]
      : section === "configuration"
        ? [{ title: t("configuration"), field: "key", kind: "name", render: (row) => t(row.key) }, { title: t("version"), field: "version" }]
        : [{ title: t("action"), field: "action", kind: "name" }, { title: t("source"), field: "source" }, { title: t("date"), field: "timestamp", render: (row) => base.formatWhen(row.timestamp, lang) }];
    const table = (detail) => state.pending
      ? base.loadingView(P, h, t)
      : state.error
        ? base.loadFailure(P, h, t, retry, state.error)
        : h(window.CTMShell.Workspace, { key: section, label: t(section), rows: filtered, columns, empty: t("noRows"), selectionPrompt: t("choose") }, detail);
    const switchTab = (key) => {
      if (key === section) return;
      const move = () => { setSection(key); setFilters({}); setNotice(false); onSectionChange?.(key); };
      if (sectionGuard.current) sectionGuard.current(move); else move();
    };
    const memberContent = h(R.Fragment, null,
      notice ? h(P.Notice, { tone: "success", onDismiss: () => setNotice(false) }, t("added")) : null,
      h(MemberDirectory, { api, user, lang, rows, pending: state.pending, retry, onNavigationGuard: registerGuard, onAdded: () => { setNotice(true); retry(); } })
    );    const configurationContent = state.pending ? base.loadingView(P, h, t) : state.error ? base.loadFailure(P, h, t, retry, state.error) : h(ConfigurationWorkspace, { api, rows, lang, onNavigationGuard: registerGuard });
    const auditContent = h(R.Fragment, null,
      h(SecuritySessions, { api, lang }),
      h(AuditFilters, { rows, filters, onChange: setFilters, lang, includeActor: false }),
      table((row) => h(Properties, { lang, entries: [["action", row.action], ["source", row.source], ["date", base.formatWhen(row.timestamp, lang)]] }))
    );
    const tabs = [
      { value: "members", label: "Users & Roles", content: memberContent },
      { value: "configuration", label: "Tribunal Config", content: configurationContent },
      ...(canEnroll(user) ? [{ value: "historical", label: "Data & Records", content: h(window.CTMHistorical.Workspace, { api, user, lang, onNavigationGuard: registerGuard, onCase }) }] : []),
      { value: "audit", label: "Audit & Security", content: auditContent },
    ];
    return h(P.Stack, { gap: "lg", className: "plx-u-flex-1 plx-u-min-h-0" },
      h(P.Text, { as: "h1", variant: "title" }, "CTM Settings"),
      h(P.Tabs, { variant: "contained", label: "CTM Settings", value: section, onChange: switchTab, items: tabs })
    );
  }
  window.CTMUI = Object.freeze({ canAdminister, canEnroll, filterAudit, filterSessions, enrollmentProblem, translator, AuditFilters, SessionFilters, useDraftGuard, Profile, Administration });
})();

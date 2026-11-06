/* UI-owned adapters for existing account, directory and system read contracts.
 *
 * #97 slice 6 (D-0034): My account and CTM Settings are Plenix settings pages (settings-page.md: SettingsLayout with
 * a NavList, SettingsSection, SettingsRow). Users and the system audit are listing pages (listing-page.md through
 * CTMShell.Listing); configuration values are edited with one field per setting and saved in the shape the server
 * stores (tribunal/services/setting_schemas.py). Who sees what is unchanged: canAdminister / canEnroll below.
 */
(() => {
  "use strict";
  const canAdminister = (user) => ["admin", "secretary"].includes(user?.role);
  const canEnroll = (user) => user?.role === "admin";
  const roles = ["member", "president", "secretary", "admin"];
  const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
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
      settingsTitle: "CTM Settings", settingsNav: "Settings sections", usersRoles: "Users & Roles", tribunalConfig: "Tribunal Config", dataRecords: "Data & Records", auditSecurity: "Audit & Security",
      users: "Users", activeMembers: "Active Members", previousMembers: "Previous Members", memberView: "Members shown", searchMembers: "Search members",
      addStaff: "Add staff user", editStaff: "Edit staff user", manageAccess: "Manage access", edit: "Edit", archive: "Archive", restore: "Restore", cancel: "Cancel", saveChanges: "Save changes",
      archiveStaff: "Archive staff user", restoreStaff: "Restore staff user", archiveConfirm: "Archive {name}? Their account access will be disabled.", restoreConfirm: "Restore {name}? Their account access will be enabled.", thisUser: "this user",
      activeCases: "Active cases", status: "Status", archived: "Archived", noActive: "No active members.", noPrevious: "No previous members.",
      accessHelp: "Account access uses the member’s verified lacopts.org Microsoft sign-in.",
      diocese_settings: "Diocese Settings", diocese_name: "Diocese name", system_email: "System email", case_id_prefix: "Case ID prefix", session_location: "Session location", presiding_bishop: "Presiding bishop", tribunal_secretary: "Tribunal secretary", default_session_day: "Default session day",
      Monday: "Monday", Tuesday: "Tuesday", Wednesday: "Wednesday", Thursday: "Thursday", Friday: "Friday", Saturday: "Saturday", Sunday: "Sunday",
      mobile_settings: "Mobile Settings", system_available_mobile: "System available on mobile", mobileHelp: "Desktop access remains available. This setting controls whether the CTM interface is offered on mobile devices.",
      document_templates: "Document Templates", templatesHelp: "Create and maintain the reusable tribunal document templates.",
      decision_outcomes: "Decision Outcomes", outcomesHelp: "Configure the available decision outcomes and their rationale requirement.",
      workflow_stages: "Case Workflow Stages", stagesHelp: "Configure workflow labels, colors, and active stages.",
      canonical_reasons: "Canonical Reasons", reasonsHelp: "Configure canonical reasons, colors, and availability.",
      title: "Title", category: "Category", body: "Body", label: "Label", description: "Description", rationale: "Requires rationale", color: "Color", colorHelp: "A # followed by six hexadecimal digits.", inactive: "Inactive",
      addItem: "Add item", editItem: "Edit item", remove: "Remove", apply: "Apply", itemRequired: "Fill in every required field.", colorInvalid: "Enter the color as # followed by six hexadecimal digits.", duplicate: "Another item already uses this name.", savedSetting: "{name} saved.", noItems: "No items yet.",
      signInSessions: "Active Sessions", signInSessionsHelp: "Sessions currently signed in to your account.", revokeOthers: "Revoke all other sessions", revoke: "Revoke", currentSession: "Current session", sessionEnding: "Session ending {when}", noSignInSessions: "No active sessions.",
      myAccount: "My Account", accountNav: "Account sections", profileSection: "Profile", security: "Security", securityHelp: "Your account uses your authorized identity-provider sign-in. Password changes are managed by that provider.",
      activeSessionCount: "Active sessions", tribunalRole: "Tribunal Role", permissions: "Permissions", permissionsManaged: "Managed by tribunal administration",
      notifications: "Notifications", notificationsHelp: "Choose the language used for notification messages.", activityLog: "Activity Log", noActivity: "No account activity is available yet.",
      profileUpdated: "Profile updated.", preferencesUpdated: "Notification preferences updated.",
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
      settingsTitle: "إعدادات CTM", settingsNav: "أقسام الإعدادات", usersRoles: "المستخدمون والأدوار", tribunalConfig: "إعدادات المحكمة", dataRecords: "البيانات والسجلات", auditSecurity: "التدقيق والأمان",
      users: "المستخدمون", activeMembers: "الأعضاء الحاليون", previousMembers: "الأعضاء السابقون", memberView: "الأعضاء المعروضون", searchMembers: "البحث في الأعضاء",
      addStaff: "إضافة مستخدم من الموظفين", editStaff: "تحرير مستخدم من الموظفين", manageAccess: "إدارة الوصول", edit: "تحرير", archive: "أرشفة", restore: "استعادة", cancel: "إلغاء", saveChanges: "حفظ التغييرات",
      archiveStaff: "أرشفة مستخدم من الموظفين", restoreStaff: "استعادة مستخدم من الموظفين", archiveConfirm: "هل تريد أرشفة {name}؟ سيتم تعطيل وصوله إلى الحساب.", restoreConfirm: "هل تريد استعادة {name}؟ سيتم تمكين وصوله إلى الحساب.", thisUser: "هذا المستخدم",
      activeCases: "القضايا النشطة", status: "الحالة", archived: "مؤرشف", noActive: "لا يوجد أعضاء حاليون.", noPrevious: "لا يوجد أعضاء سابقون.",
      accessHelp: "يتم الوصول إلى الحساب بتسجيل دخول Microsoft الموثّق للعضو على lacopts.org.",
      diocese_settings: "إعدادات الإيبارشية", diocese_name: "اسم الإيبارشية", system_email: "البريد الإلكتروني للنظام", case_id_prefix: "بادئة رقم القضية", session_location: "مكان الجلسة", presiding_bishop: "الأسقف الرئيس", tribunal_secretary: "سكرتير المحكمة", default_session_day: "يوم الجلسة الافتراضي",
      Monday: "الاثنين", Tuesday: "الثلاثاء", Wednesday: "الأربعاء", Thursday: "الخميس", Friday: "الجمعة", Saturday: "السبت", Sunday: "الأحد",
      mobile_settings: "إعدادات الأجهزة المحمولة", system_available_mobile: "النظام متاح على الأجهزة المحمولة", mobileHelp: "يبقى الوصول من أجهزة الكمبيوتر متاحًا. يحدد هذا الإعداد ما إذا كانت واجهة CTM متاحة على الأجهزة المحمولة.",
      document_templates: "قوالب المستندات", templatesHelp: "أنشئ قوالب مستندات المحكمة القابلة لإعادة الاستخدام وحافظ عليها.",
      decision_outcomes: "نتائج القرار", outcomesHelp: "اضبط نتائج القرار المتاحة وما إذا كانت تتطلب تسبيبًا.",
      workflow_stages: "مراحل سير القضية", stagesHelp: "اضبط تسميات مراحل سير العمل وألوانها والمراحل النشطة.",
      canonical_reasons: "الأسباب الكنسية", reasonsHelp: "اضبط الأسباب الكنسية وألوانها وإتاحتها.",
      title: "العنوان", category: "الفئة", body: "النص", label: "التسمية", description: "الوصف", rationale: "يتطلب تسبيبًا", color: "اللون", colorHelp: "علامة # تليها ستة أرقام سداسية عشرية.", inactive: "غير نشط",
      addItem: "إضافة عنصر", editItem: "تحرير العنصر", remove: "إزالة", apply: "تطبيق", itemRequired: "املأ كل الحقول المطلوبة.", colorInvalid: "أدخل اللون بعلامة # تليها ستة أرقام سداسية عشرية.", duplicate: "يستخدم عنصر آخر هذا الاسم بالفعل.", savedSetting: "تم حفظ {name}.", noItems: "لا توجد عناصر بعد.",
      signInSessions: "جلسات تسجيل الدخول النشطة", signInSessionsHelp: "جلسات تسجيل الدخول الحالية إلى حسابك.", revokeOthers: "إبطال كل جلسات تسجيل الدخول الأخرى", revoke: "إبطال", currentSession: "جلسة تسجيل الدخول الحالية", sessionEnding: "جلسة تنتهي في {when}", noSignInSessions: "لا توجد جلسات تسجيل دخول نشطة.",
      myAccount: "حسابي", accountNav: "أقسام الحساب", profileSection: "ملف التعريف", security: "الأمان", securityHelp: "يستخدم حسابك تسجيل الدخول المعتمد من موفر الهوية. يدير هذا الموفر تغييرات كلمة المرور.",
      activeSessionCount: "جلسات تسجيل الدخول النشطة", tribunalRole: "الدور في المحكمة", permissions: "الأذونات", permissionsManaged: "تديرها إدارة المحكمة",
      notifications: "الإشعارات", notificationsHelp: "اختر اللغة المستخدمة في رسائل الإشعارات.", activityLog: "سجل النشاط", noActivity: "لا يوجد نشاط للحساب حتى الآن.",
      profileUpdated: "تم تحديث ملف التعريف.", preferencesUpdated: "تم تحديث تفضيلات الإشعارات.",
    },
  };
  const translator = (lang) => (key) => words[lang === "ar" ? "ar" : "en"][key] || key;
  const fill = (text, values) => String(text).replace(/\{(\w+)\}/g, (all, key) => (values[key] ?? all));
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

  // My account: one settings page (settings-page.md); the NavList moves to each section.
  function Profile({ api, user, lang, onUserUpdated }) {
    const R = window.React, P = window.Plenix, h = R.createElement, t = translator(lang);
    const [form, setForm] = R.useState({ first_name: user.first_name || user.name?.split(" ")[0] || "", last_name: user.last_name || user.name?.split(" ").slice(1).join(" ") || "" });
    const [saving, setSaving] = R.useState(false), [notice, setNotice] = R.useState(null), [failure, setFailure] = R.useState(null), [current, setCurrent] = R.useState("profile");
    const [state, retry] = window.CTMCouncil.useLoad(() => Promise.all([api("/api/account/sessions/"), api("/api/account/activity/")]).then(([sessions, activity]) => ({ sessions: sessions.items || [], activity: activity.items || [] })), []);
    const save = async (event) => {
      event.preventDefault();
      setSaving(true); setFailure(null); setNotice(null);
      try {
        const updated = await api("/api/account/settings/", { method: "POST", body: JSON.stringify({ first_name: form.first_name.trim(), last_name: form.last_name.trim() }) });
        onUserUpdated?.(updated); setNotice("profileUpdated");
      } catch (error) { setFailure(window.CTMCouncil.serverMessage(error, t)); }
      finally { setSaving(false); }
    };
    const preference = async (field, value) => {
      setSaving(true); setFailure(null); setNotice(null);
      try { const updated = await api("/api/account/settings/", { method: "POST", body: JSON.stringify({ [field]: value }) }); onUserUpdated?.(updated); setNotice("preferencesUpdated"); }
      catch (error) { setFailure(window.CTMCouncil.serverMessage(error, t)); }
      finally { setSaving(false); }
    };
    const role = t(user.role || "member"), portal = t(user.portal || "council");
    const loaded = (draw) => state.pending ? h(P.Text, { variant: "secondary" }, t("loading")) : state.error ? h(P.Button, { onClick: retry }, t("retry")) : draw(state.data);
    const sections = [
      ["profile", "profileSection"], ["security", "security"], ["role", "tribunalRole"], ["notifications", "notifications"], ["activity", "activityLog"],
    ];
    const go = (id) => { setCurrent(id); window.document?.getElementById(`ctm-account-${id}`)?.scrollIntoView({ block: "start" }); };
    const place = (id, child) => h("div", { key: id, id: `ctm-account-${id}` }, child);
    return h(P.SettingsLayout, {
      nav: h(P.NavList, { label: t("accountNav"), value: current, onSelect: go, items: sections.map(([id, key]) => ({ id, label: t(key) })) }),
    }, h(P.Stack, { gap: "md" },
      h(P.Text, { as: "h1", variant: "title" }, t("myAccount")),
      h(P.Inline, { gap: "md", align: "center" },
        h(P.Avatar, { name: user.name, size: "xl" }),
        h(P.Stack, { gap: "none" }, h(P.Text, { as: "h2", variant: "heading" }, user.name), h(P.Text, { variant: "secondary" }, `${role} · ${portal}`)),
      ),
      notice ? h(P.Notice, { tone: "success", onDismiss: () => setNotice(null) }, t(notice)) : null,
      failure ? h(P.Notice, { tone: "danger", onDismiss: () => setFailure(null) }, failure) : null,
      place("profile", h(P.Form, { onSubmit: save, label: t("profileSection"), noValidate: true },
        h(P.SettingsSection, { title: t("profileSection"), actions: h(P.Button, { type: "submit", variant: "primary", loading: saving, disabled: saving }, t("saveChanges")) },
          ...["first_name", "last_name"].map((key) => h(P.SettingsRow, { key, label: t(key), htmlFor: `ctm-account-${key}` },
            h(P.Input, { id: `ctm-account-${key}`, value: form[key], maxLength: 150, required: true, disabled: saving, onChange: (event) => setForm({ ...form, [key]: event.target.value }) }))),
          h(P.SettingsRow, { label: t("email"), htmlFor: "ctm-account-email" }, h(P.Input, { id: "ctm-account-email", value: user.email || "", disabled: true })),
        ))),
      place("security", h(P.SettingsSection, { title: t("security"), description: t("securityHelp") },
        loaded((data) => h(R.Fragment, null,
          h(P.SettingsRow, { label: t("activeSessionCount") }, h(P.Text, { variant: "data" }, String(data.sessions.length))),
          h(P.SettingsRow, { label: t("currentSession") }, h(P.Text, null, data.sessions.some((item) => item.current) ? t("active") : "—")),
        )))),
      place("role", h(P.SettingsSection, { title: t("tribunalRole") },
        h(P.SettingsRow, { label: t("role") }, h(P.Text, null, role)),
        h(P.SettingsRow, { label: t("portal") }, h(P.Text, null, portal)),
        h(P.SettingsRow, { label: t("permissions") }, h(P.Text, null, t("permissionsManaged"))))),
      place("notifications", h(P.SettingsSection, { title: t("notifications") },
        h(P.SettingsRow, { label: t("notification_language"), description: t("notificationsHelp") },
          h(P.SegmentedControl, { label: t("notification_language"), value: user.notification_language, readOnly: saving, onChange: (value) => value !== user.notification_language && preference("notification_language", value), options: ["en", "ar"].map((value) => ({ value, label: t(value) })) })))),
      place("activity", h(P.SettingsSection, { title: t("activityLog") },
        loaded((data) => data.activity.length
          ? h(P.List, { variant: "bullets", items: data.activity.map((item) => ({ children: `${item.action} · ${window.CTMCouncil.formatWhen(item.timestamp, lang)}` })) })
          : h(P.EmptyState, { title: t("noActivity") })))),
    ));
  }

  // The signed-in account's sign-in sessions, a settings section with one row per session.
  function SecuritySessions({ api, lang }) {
    const R = window.React, P = window.Plenix, h = R.createElement, t = translator(lang);
    const [saving, setSaving] = R.useState(false), [failure, setFailure] = R.useState(null);
    const [state, retry] = window.CTMCouncil.useLoad(() => api("/api/account/sessions/"), []);
    const sessions = state.data?.items || [];
    const revoke = async (row) => { setSaving(true); setFailure(null); try { await api(`/api/account/sessions/${encodeURIComponent(row.handle)}/revoke/`, { method: "POST", body: "{}" }); retry(); } catch (error) { setFailure(window.CTMCouncil.serverMessage(error, t)); } finally { setSaving(false); } };
    const revokeOthers = async () => { setSaving(true); setFailure(null); try { for (const row of sessions.filter((item) => !item.current)) await api(`/api/account/sessions/${encodeURIComponent(row.handle)}/revoke/`, { method: "POST", body: "{}" }); retry(); } catch (error) { setFailure(window.CTMCouncil.serverMessage(error, t)); } finally { setSaving(false); } };
    return h(P.SettingsSection, {
      title: t("signInSessions"), description: t("signInSessionsHelp"),
      actions: h(P.Button, { disabled: saving || !sessions.some((row) => !row.current), onClick: revokeOthers }, t("revokeOthers")),
    },
      failure ? h(P.Notice, { tone: "danger", onDismiss: () => setFailure(null) }, failure) : null,
      state.pending ? h(P.Text, { variant: "secondary" }, t("loading")) : state.error ? h(P.Button, { onClick: retry }, t("retry"))
        : sessions.length ? sessions.map((row, index) => h(P.SettingsRow, { key: row.handle || index, label: row.current ? t("currentSession") : fill(t("sessionEnding"), { when: window.CTMCouncil.formatWhen(row.expires_at, lang) }) },
          row.current ? h(P.Text, { variant: "secondary" }, t("currentSession")) : h(P.Button, { size: "xs", variant: "danger-secondary", disabled: saving, onClick: () => revoke(row) }, t("revoke"))))
          : h(P.EmptyState, { title: t("noSignInSessions") }),
    );
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
  function Enrollment({ api, user, lang, onAdded, onCancel, onNavigationGuard }) {
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
    return h(R.Fragment, null, h(P.Form, { label: t("enroll"), onSubmit: save, noValidate: true },
      h(P.FormSection, { title: t("enroll"), headingLevel: 3 },
        ...["first_name", "last_name", "email"].map((key) => h(P.Field, { key, label: t(key === "email" ? "emailField" : key), required: true }, h(P.Input, { type: key === "email" ? "email" : "text", value: form[key], maxLength: key === "email" ? 254 : 150, disabled: pending, onChange: (event) => { setForm({ ...form, [key]: event.target.value }); setProblem(null); } }))),
        h(P.Field, { label: t("role"), required: true }, h(P.Select, { value: form.role, disabled: pending, onChange: (event) => setForm({ ...form, role: event.target.value }), options: roles.map((value) => ({ value, label: t(value) })) }))),
      problem ? h(P.Notice, { tone: "warning" }, t(problem)) : null,
      failure ? h(P.Notice, { tone: "danger" }, failure) : null,
      h(P.FormActions, { sticky: false },
        onCancel ? h(P.Button, { disabled: pending, onClick: () => guard.navigate(onCancel) }, t("cancel")) : null,
        h(P.Button, { type: "submit", variant: "primary", disabled: pending, loading: pending }, t("save")))), guard.dialog);
  }

  // Users & Roles: a listing page (listing-page.md, CTMShell.Listing); row actions sit in the row menu.
  function MemberDirectory({ api, user, lang, rows, pending, retry, onNavigationGuard, onAdded }) {
    const R = window.React, P = window.Plenix, h = R.createElement, t = translator(lang);
    const [view, setView] = R.useState("active"), [enrolling, setEnrolling] = R.useState(false), [editing, setEditing] = R.useState(null), [archiveTarget, setArchiveTarget] = R.useState(null), [saving, setSaving] = R.useState(false), [failure, setFailure] = R.useState(null);
    const visibleRows = rows.filter((row) => view === "active" ? row.active : !row.active);
    const fullName = (row) => `${row.first_name || ""} ${row.last_name || ""}`.trim();
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
      { title: t("name"), field: "name", kind: "name", render: fullName },
      { title: t("role"), field: "role", render: (row) => t(row.role) },
      { title: t("emailField"), field: "email", kind: "data" },
      { title: t("activeCases"), field: "active_case_count", type: "number", kind: "data" },
      { title: t("status"), field: "status", render: (row) => t(row.active ? "active" : "archived") },
    ];
    const rowMenu = (row) => [
      { label: t("edit"), icon: "pencil", disabled: saving, onSelect: () => setEditing({ ...row }) },
      { label: t("manageAccess"), icon: "key", disabled: saving, onSelect: () => setEditing({ ...row }) },
      ...(row.active && row.can_suspend ? [{ separator: true }, { label: t("archive"), icon: "archive", danger: true, disabled: saving, onSelect: () => setArchiveTarget(row) }] : []),
      ...(!row.active && row.can_reactivate ? [{ separator: true }, { label: t("restore"), icon: "restore", disabled: saving, onSelect: () => setArchiveTarget(row) }] : []),
    ];
    const name = archiveTarget ? fullName(archiveTarget) || t("thisUser") : t("thisUser");
    return h(P.Stack, { gap: "md", className: "plx-u-flex-1 plx-u-min-h-0" },
      h(P.Text, { as: "h2", variant: "heading" }, t("users")),
      h(window.CTMShell.Listing, {
        label: t(view === "active" ? "activeMembers" : "previousMembers"), rows: visibleRows, columns, rowMenu, loading: pending,
        empty: t(view === "active" ? "noActive" : "noPrevious"),
        search: { text: (row) => [fullName(row), row.email, t(row.role)].join(" "), placeholder: t("searchMembers") },
        commandBar: {
          label: t("users"), count: visibleRows.length,
          actions: [
            { id: "view", label: t("memberView"), value: view, onChange: setView, choices: [{ value: "active", label: t("activeMembers") }, { value: "previous", label: t("previousMembers") }] },
            ...(canEnroll(user) ? [{ id: "add", label: t("addStaff"), icon: "add", primary: true, onSelect: () => setEnrolling(true) }] : []),
          ],
        },
      }),
      enrolling ? h(P.Dialog, { open: true, title: t("addStaff"), size: "lg", onClose: () => !saving && setEnrolling(false) }, h(Enrollment, { api, user, lang, onNavigationGuard, onCancel: () => setEnrolling(false), onAdded: () => { setEnrolling(false); onAdded(); } })) : null,
      editing ? h(P.Dialog, { open: true, title: t("editStaff"), size: "sm", onClose: () => !saving && setEditing(null) }, h(P.Form, { label: t("editStaff"), onSubmit: updateMember, noValidate: true },
        h(P.FormSection, { title: t("editStaff"), headingLevel: 3, description: t("accessHelp") },
          h(P.Field, { label: t("first_name"), required: true }, h(P.Input, { value: editing.first_name, maxLength: 150, disabled: saving, onChange: (event) => setEditing({ ...editing, first_name: event.target.value }) })),
          h(P.Field, { label: t("last_name"), required: true }, h(P.Input, { value: editing.last_name, maxLength: 150, disabled: saving, onChange: (event) => setEditing({ ...editing, last_name: event.target.value }) })),
          h(P.Field, { label: t("emailField") }, h(P.Input, { value: editing.email, disabled: true }))),
        failure ? h(P.Notice, { tone: "danger" }, failure) : null,
        h(P.FormActions, { sticky: false }, h(P.Button, { disabled: saving, onClick: () => setEditing(null) }, t("cancel")), h(P.Button, { type: "submit", variant: "primary", loading: saving, disabled: saving }, t("saveChanges"))),
      )) : null,
      h(P.ConfirmDialog, { open: Boolean(archiveTarget), title: t(archiveTarget?.active ? "archiveStaff" : "restoreStaff"), message: fill(t(archiveTarget?.active ? "archiveConfirm" : "restoreConfirm"), { name }), confirmLabel: t(archiveTarget?.active ? "archive" : "restore"), cancelLabel: t("cancel"), onConfirm: changeStatus, onCancel: () => !saving && setArchiveTarget(null) }, failure ? h(P.Notice, { tone: "danger" }, failure) : null)
    );
  }

  // The configuration lists the server stores as { <list>: [items] } (setting_schemas.py): one field per item property.
  const lists = [
    { key: "document_templates", list: "templates", help: "templatesHelp", name: "title", fields: [["title", "text", 300], ["category", "text", 100], ["body", "textarea", 20000], ["active", "switch"]] },
    { key: "decision_outcomes", list: "outcomes", help: "outcomesHelp", name: "label", fields: [["label", "text", 300], ["category", "text", 100], ["description", "textarea", 2000], ["rationale", "switch"], ["active", "switch"]] },
    { key: "workflow_stages", list: "stages", help: "stagesHelp", name: "name", fields: [["name", "text", 200], ["color", "color"], ["active", "switch"]] },
    { key: "canonical_reasons", list: "reasons", help: "reasonsHelp", name: "name", fields: [["name", "text", 200], ["color", "color"], ["active", "switch"]] },
  ];
  const emptyItem = (spec) => Object.fromEntries(spec.fields.map(([field, kind]) => [field, kind === "switch" ? field === "active" : ""]));
  function itemProblem(spec, item, items, index) {
    if (spec.fields.some(([field, kind]) => ["text", "textarea", "color"].includes(kind) && !/\S/.test(item[field] || ""))) return "itemRequired";
    if (spec.fields.some(([field, kind]) => kind === "color" && !/^#[0-9A-Fa-f]{6}$/.test(item[field]))) return "colorInvalid";
    return items.some((other, i) => i !== index && other[spec.name] === item[spec.name]) ? "duplicate" : null;
  }

  function ConfigurationWorkspace({ api, rows, lang, onNavigationGuard }) {
    const R = window.React, P = window.Plenix, h = R.createElement, t = translator(lang);
    const byKey = Object.fromEntries(rows.map((row) => [row.key, row]));
    const [saving, setSaving] = R.useState(false), [notice, setNotice] = R.useState(null), [failure, setFailure] = R.useState(null);
    const [saved, setSaved] = R.useState({}), [versions, setVersions] = R.useState({}), [drafts, setDrafts] = R.useState({}), [editing, setEditing] = R.useState(null);
    const defaultDiocese = { diocese_name: "Diocese of Los Angeles", system_email: "tribunal@lacopts.org", case_id_prefix: "CTM", default_session_day: "Tuesday", session_location: "", presiding_bishop: "", tribunal_secretary: "" };
    const fallback = { diocese_settings: defaultDiocese, mobile_settings: { system_available_mobile: true }, ...Object.fromEntries(lists.map((spec) => [spec.key, { [spec.list]: [] }])) };
    const stored = (key) => saved[key] || byKey[key]?.value || fallback[key];
    const value = (key) => drafts[key] === undefined ? stored(key) : drafts[key];
    const change = (key, next) => { setDrafts({ ...drafts, [key]: next }); setNotice(null); setFailure(null); };
    const dirty = Object.keys(drafts).some((key) => JSON.stringify(drafts[key]) !== JSON.stringify(stored(key)));
    const guard = useDraftGuard({ dirty, pending: saving, onNavigationGuard, lang });
    async function save(key) {
      if (saving) return;
      const next = value(key);
      setSaving(true); setFailure(null); setNotice(null);
      try {
        const row = await api("/api/system/settings/", { method: "POST", body: JSON.stringify({ key, value: next, expected_version: versions[key] ?? byKey[key]?.version ?? 0, schema_version: 1 }) });
        if (Number.isInteger(row?.version)) setVersions({ ...versions, [key]: row.version });
        setSaved({ ...saved, [key]: next });
        const { [key]: _done, ...rest } = drafts; setDrafts(rest);
        setNotice(fill(t("savedSetting"), { name: t(key) }));
      } catch (error) { setFailure(window.CTMCouncil.serverMessage(error, t)); }
      finally { setSaving(false); }
    }
    const saveButton = (key) => h(P.Button, { type: "submit", variant: "primary", disabled: saving, loading: saving }, t("saveChanges"));
    const submit = (key) => (event) => { event.preventDefault(); save(key); };
    const diocese = value("diocese_settings"), mobile = value("mobile_settings");
    const dioceseSection = h(P.Form, { key: "diocese", label: t("diocese_settings"), onSubmit: submit("diocese_settings"), noValidate: true },
      h(P.SettingsSection, { title: t("diocese_settings"), actions: saveButton("diocese_settings") },
        ...["diocese_name", "system_email", "case_id_prefix", "session_location", "presiding_bishop", "tribunal_secretary"].map((key) => h(P.SettingsRow, { key, label: t(key), htmlFor: `ctm-setting-${key}` },
          h(P.Input, { id: `ctm-setting-${key}`, type: key === "system_email" ? "email" : "text", value: diocese[key] ?? "", required: key !== "case_id_prefix", disabled: saving, onChange: (event) => change("diocese_settings", { ...diocese, [key]: event.target.value }) }))),
        h(P.SettingsRow, { label: t("default_session_day"), htmlFor: "ctm-setting-default_session_day" },
          h(P.Select, { id: "ctm-setting-default_session_day", value: diocese.default_session_day, disabled: saving, onChange: (event) => change("diocese_settings", { ...diocese, default_session_day: event.target.value }), options: days.map((day) => ({ value: day, label: t(day) })) })),
      ));
    const mobileSection = h(P.Form, { key: "mobile", label: t("mobile_settings"), onSubmit: submit("mobile_settings"), noValidate: true },
      h(P.SettingsSection, { title: t("mobile_settings"), actions: saveButton("mobile_settings") },
        h(P.SettingsRow, { label: t("system_available_mobile"), description: t("mobileHelp") },
          h(P.Switch, { label: t("system_available_mobile"), labelHidden: true, checked: Boolean(mobile.system_available_mobile), disabled: saving, onChange: (event) => change("mobile_settings", { ...mobile, system_available_mobile: event.target.checked }) })),
      ));
    const listSection = (spec) => {
      const current = value(spec.key), items = Array.isArray(current[spec.list]) ? current[spec.list] : [];
      const setItems = (next) => change(spec.key, { ...current, [spec.list]: next });
      const describe = (item) => [spec.fields.some(([f]) => f === "category") ? item.category : item.color, item.active === false ? t("inactive") : null].filter(Boolean).join(" · ");
      return h(P.Form, { key: spec.key, label: t(spec.key), onSubmit: submit(spec.key), noValidate: true },
        h(P.SettingsSection, {
          title: t(spec.key), description: t(spec.help),
          actions: h(R.Fragment, null, h(P.Button, { icon: "add", disabled: saving, onClick: () => setEditing({ spec, index: -1, item: emptyItem(spec), problem: null }) }, t("addItem")), saveButton(spec.key)),
        },
          items.length ? items.map((item, index) => h(P.SettingsRow, { key: `${index}-${item[spec.name]}`, label: item[spec.name] || "—", description: describe(item) || undefined },
            h(P.Inline, { gap: "xs", align: "center" },
              h(P.Switch, { label: `${t("active")}: ${item[spec.name] || ""}`, labelHidden: true, checked: item.active !== false, disabled: saving, onChange: (event) => setItems(items.map((row, i) => i === index ? { ...row, active: event.target.checked } : row)) }),
              h(P.Button, { size: "xs", icon: "pencil", disabled: saving, onClick: () => setEditing({ spec, index, item: { ...item }, problem: null }) }, t("edit")),
              h(P.Button, { size: "xs", icon: "delete", variant: "danger-secondary", disabled: saving, onClick: () => setItems(items.filter((_, i) => i !== index)) }, t("remove")),
            ))) : h(P.EmptyState, { title: t("noItems") }),
        ));
    };
    const applyItem = (event) => {
      event.preventDefault();
      const { spec, index, item } = editing;
      const current = value(spec.key), items = Array.isArray(current[spec.list]) ? current[spec.list] : [];
      const problem = itemProblem(spec, item, items, index);
      if (problem) return setEditing({ ...editing, problem });
      change(spec.key, { ...current, [spec.list]: index < 0 ? [...items, item] : items.map((row, i) => i === index ? item : row) });
      setEditing(null);
    };
    const field = ([key, kind, max]) => {
      const set = (next) => setEditing({ ...editing, item: { ...editing.item, [key]: next }, problem: null });
      if (kind === "switch") return h(P.Switch, { key, label: t(key), checked: Boolean(editing.item[key]), onChange: (event) => set(event.target.checked) });
      if (kind === "textarea") return h(P.Field, { key, label: t(key), required: true }, h(P.Textarea, { value: editing.item[key] || "", rows: 8, maxLength: max, onChange: (event) => set(event.target.value) }));
      return h(P.Field, { key, label: t(key), required: true, description: kind === "color" ? t("colorHelp") : undefined },
        h(P.Input, { value: editing.item[key] || "", maxLength: kind === "color" ? 7 : max, data: kind === "color" || undefined, onChange: (event) => set(event.target.value) }));
    };
    return h(P.Stack, { gap: "md" },
      notice ? h(P.Notice, { tone: "success", onDismiss: () => setNotice(null) }, notice) : null,
      failure ? h(P.Notice, { tone: "danger", onDismiss: () => setFailure(null) }, failure) : null,
      dioceseSection, ...lists.map(listSection), mobileSection,
      editing ? h(P.Dialog, { open: true, title: t(editing.index < 0 ? "addItem" : "editItem"), size: "md", onClose: () => setEditing(null) },
        h(P.Form, { label: t(editing.spec.key), onSubmit: applyItem, noValidate: true },
          h(P.FormSection, { title: t(editing.spec.key), headingLevel: 3 }, ...editing.spec.fields.map(field)),
          editing.problem ? h(P.Notice, { tone: "warning" }, t(editing.problem)) : null,
          h(P.FormActions, { sticky: false }, h(P.Button, { onClick: () => setEditing(null) }, t("cancel")), h(P.Button, { type: "submit", variant: "primary" }, t("apply"))))) : null,
      guard.dialog,
    );
  }

  // CTM Settings: a settings page (settings-page.md) whose NavList chooses the section; the sections and who may
  // open them are unchanged (Data & Records for administrators only).
  function Administration({ api, user, lang, onNavigationGuard, onCase, initialSection = "members", onSectionChange }) {
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
    const switchSection = (key) => {
      if (key === section) return;
      const move = () => { setSection(key); setFilters({}); setNotice(false); onSectionChange?.(key); };
      if (sectionGuard.current) sectionGuard.current(move); else move();
    };
    const sections = [
      { id: "members", label: t("usersRoles"), icon: "settings-users" },
      { id: "configuration", label: t("tribunalConfig"), icon: "settings" },
      ...(canEnroll(user) ? [{ id: "historical", label: t("dataRecords"), icon: "archive" }] : []),
      { id: "audit", label: t("auditSecurity"), icon: "lock" },
    ];
    const failedOr = (draw) => state.error ? base.loadFailure(P, h, t, retry, state.error) : draw();
    const content = section === "members"
      ? h(R.Fragment, null,
        notice ? h(P.Notice, { tone: "success", onDismiss: () => setNotice(false) }, t("added")) : null,
        // As before: a refused or failed load shows the empty directory (the server decides who may list users).
        h(MemberDirectory, { api, user, lang, rows, pending: state.pending, retry, onNavigationGuard: registerGuard, onAdded: () => { setNotice(true); retry(); } }))
      : section === "configuration"
        ? state.pending ? base.loadingView(P, h, t) : failedOr(() => h(ConfigurationWorkspace, { api, rows, lang, onNavigationGuard: registerGuard }))
        : section === "historical" && canEnroll(user)
          ? h(window.CTMHistorical.Workspace, { api, user, lang, onNavigationGuard: registerGuard, onCase })
          : h(R.Fragment, null,
            h(SecuritySessions, { api, lang }),
            h(P.Text, { as: "h2", variant: "heading" }, t("audit")),
            h(AuditFilters, { rows, filters, onChange: setFilters, lang, includeActor: false }),
            failedOr(() => h(window.CTMShell.Listing, {
              label: t("audit"), rows: filterAudit(rows, filters), loading: state.pending, empty: t("noRows"),
              columns: [{ title: t("action"), field: "action", kind: "name" }, { title: t("source"), field: "source" }, { title: t("date"), field: "timestamp", render: (row) => base.formatWhen(row.timestamp, lang) }],
            })));
    return h(P.SettingsLayout, {
      className: "plx-u-flex-1 plx-u-min-h-0",
      nav: h(P.NavList, { label: t("settingsNav"), value: section, onSelect: switchSection, items: sections }),
    },
      h(P.Text, { as: "h1", variant: "title" }, t("settingsTitle")),
      content,
    );
  }
  window.CTMUI = Object.freeze({ canAdminister, canEnroll, filterAudit, filterSessions, enrollmentProblem, translator, AuditFilters, SessionFilters, useDraftGuard, Profile, Administration });
})();

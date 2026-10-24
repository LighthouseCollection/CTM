/* Canonical same-origin locations for the CTM application shell. */
(() => {
  "use strict";

  const CASE_SECTIONS = Object.freeze({
    summary: "case",
    timeline: "timeline",
    spouses: "parties",
    marriage: "marriage",
    separation: "separation",
    email: "communications",
    calls: "calls",
    notes: "notes",
    petition: "petition",
    reports: "reports",
    hearings: "hearings",
    evidence: "evidence",
    documents: "documents",
    assessment: "medical",
    decision: "decision",
    decree: "decree",
    appeals: "appeals",
    audit: "audit",
  });
  const SECTION_PATHS = Object.freeze(Object.fromEntries(Object.entries(CASE_SECTIONS).map(([path, page]) => [page, path])));
  const PAGE_PATHS = Object.freeze({
    home: "/",
    sessions: "/sessions/current",
    sessionsUpcoming: "/sessions/upcoming",
    sessionsArchived: "/sessions/archived",
    newApplications: "/applications/new",
    review: "/applications/new",
    applications: "/applications",
    appointments: "/appointments",
    notifications: "/notifications",
    search: "/search",
    statistics: "/reports",
    myCases: "/cases/mine",
    cases: "/cases/active",
    archived: "/cases/archived",
    past: "/cases/past",
    profile: "/account",
    settings: "/settings/users",
    administration: "/settings/users",
  });
  const SETTINGS_SECTIONS = Object.freeze({ users: "members", configuration: "configuration", data: "historical", audit: "audit" });
  const SETTINGS_PATHS = Object.freeze(Object.fromEntries(Object.entries(SETTINGS_SECTIONS).map(([path, section]) => [section, path])));

  function decode(segment) {
    try {
      const value = decodeURIComponent(segment);
      return value && !value.includes("/") ? value : null;
    } catch {
      return null;
    }
  }

  function pathnameFor(parts) {
    return "/" + parts.map(encodeURIComponent).join("/");
  }

  function parse(pathname) {
    const raw = String(pathname || "/").replace(/\/+$/, "") || "/";
    const parts = raw === "/" ? [] : raw.slice(1).split("/");
    if (!parts.length) return { page: "home", selection: null, pathname: "/" };
    if (parts[0] === "sessions") {
      if (parts.length !== 2) return null;
      if (parts[1] === "current") return { page: "sessions", selection: null, pathname: "/sessions/current" };
      if (parts[1] === "upcoming") return { page: "sessionsUpcoming", selection: null, pathname: "/sessions/upcoming" };
      if (parts[1] === "archived") return { page: "sessionsArchived", selection: null, pathname: "/sessions/archived" };
      const selection = decode(parts[1]);
      return selection ? { page: "session", selection, pathname: pathnameFor(["sessions", selection]) } : null;
    }
    if (parts[0] === "applications") {
      if (parts.length === 1) return { page: "applications", selection: null, pathname: "/applications" };
      if (parts.length === 2 && parts[1] === "new") return { page: "newApplications", selection: null, pathname: "/applications/new" };
      const selection = parts.length === 2 ? decode(parts[1]) : null;
      return selection ? { page: "application", selection, pathname: pathnameFor(["applications", selection]) } : null;
    }
    if (parts.length === 1 && parts[0] === "appointments") return { page: "appointments", selection: null, pathname: "/appointments" };
    if (parts.length === 1 && parts[0] === "notifications") return { page: "notifications", selection: null, pathname: "/notifications" };
    if (parts.length === 1 && parts[0] === "search") return { page: "search", selection: null, pathname: "/search" };
    if (parts.length === 1 && parts[0] === "reports") return { page: "statistics", selection: null, pathname: "/reports" };
    if (parts[0] === "cases") {
      if (parts.length === 2 && parts[1] === "mine") return { page: "myCases", selection: null, pathname: "/cases/mine" };
      if (parts.length === 2 && parts[1] === "active") return { page: "cases", selection: null, pathname: "/cases/active" };
      if (parts.length === 2 && parts[1] === "archived") return { page: "archived", selection: null, pathname: "/cases/archived" };
      if (parts.length === 2 && parts[1] === "past") return { page: "past", selection: null, pathname: "/cases/past" };
      if (parts.length === 2 || parts.length === 3) {
        const selection = decode(parts[1]);
        const page = parts.length === 3 ? CASE_SECTIONS[parts[2]] : "case";
        return selection && page ? { page, selection, pathname: pathnameFor(parts.length === 3 ? ["cases", selection, parts[2]] : ["cases", selection]) } : null;
      }
      return null;
    }
    if (parts.length === 1 && parts[0] === "account") return { page: "profile", selection: null, pathname: "/account" };
    if (parts[0] === "settings" && parts.length === 2 && SETTINGS_SECTIONS[parts[1]])
      return { page: "settings", selection: SETTINGS_SECTIONS[parts[1]], pathname: `/settings/${parts[1]}` };
    return null;
  }

  function routeFor(page, selection) {
    if (page === "session" && selection) return pathnameFor(["sessions", selection]);
    if (selection && SECTION_PATHS[page]) return pathnameFor(["cases", selection, SECTION_PATHS[page]]);
    if (page === "case" && selection) return pathnameFor(["cases", selection]);
    if ((page === "settings" || page === "administration") && SETTINGS_PATHS[selection || "members"])
      return `/settings/${SETTINGS_PATHS[selection || "members"]}`;
    return PAGE_PATHS[page] || null;
  }

  window.CTMRoutes = Object.freeze({ parse, routeFor });
})();

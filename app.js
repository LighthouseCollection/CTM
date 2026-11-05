/* CTM 3.0 dashboard: layout reused from the Plenix Dashboard (overview, to do, decisions, done, team),
   on CTM's Plenix pin (0.86.0). Data: data.js, a snapshot taken from GitHub by collect.py. */
(function () {
  'use strict';
  var R = window.React, P = window.Plenix, D = window.CTM_DATA, h = R.createElement;
  var GH = 'https://github.com/LighthouseCollection/CTM';

  function fmt(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    return isNaN(d) ? iso : d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  }
  function role(r) { return r.replace(/-/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); }); }
  function link(href, text) { return h(P.Link, { href: href, external: true }, text); }
  var SEV = { S1: 'danger', S2: 'negative', S3: 'waiting', S4: 'neutral' };
  var STATE = {
    success: ['success', 'check', 'Pass'], failure: ['negative', 'warning', 'Fail'], cancelled: ['neutral', null, 'Cancelled'],
    skipped: ['neutral', null, 'Skipped'], review: ['neutral', 'info', 'Review only'], present: ['success', 'check', 'In place'],
  };
  function stateBadge(s) {
    var v = STATE[s] || ['waiting', 'clock', s || 'No run yet'];
    return h(P.Badge, { tone: v[0], icon: v[1] || undefined, size: 'sm' }, v[2]);
  }
  function siteBadge(code) {
    if (code === 200) return h(P.Badge, { tone: 'success', icon: 'check' }, 'Up');
    if (!code) return h(P.Badge, { tone: 'neutral' }, 'Not running');
    if (code === 404) return h(P.Badge, { tone: 'neutral' }, 'Not built yet');
    return h(P.Badge, { tone: 'negative', icon: 'warning' }, 'Down (' + code + ')');
  }

  var tasks = D.tasks, active = D.decisions.filter(function (d) { return d.status === 'active'; });
  var noCheck = active.filter(function (d) { return d.kind === 'review only'; });
  var failing = active.filter(function (d) { return d.state === 'failure'; });
  var urgent = tasks.filter(function (t) { return t.sev === 'S1' || t.sev === 'S2'; });
  var mine = tasks.filter(function (t) { return t.waiting; });

  function Sites() {
    var s = D.sites;
    var rows = [
      { id: 'live', site: 'Live CTM', url: s.live.url, code: s.live.code, info: s.live.version ? 'CTM ' + s.live.version.version + ' · Plenix ' + s.live.version.plenix_version : 'Bug #63' },
      { id: 'local', site: 'Local CTM (this PC)', url: s.local.url, code: s.local.code, info: s.local.version ? 'CTM ' + s.local.version.version + ' · Plenix ' + s.local.version.plenix_version + ' · synthetic data' : s.local.note },
      { id: 'pages', site: 'Dashboard web page (GitHub Pages)', url: s.pages.url, code: s.pages.code, info: 'Issue #61' },
    ];
    return h(P.Table, { label: 'Sites', data: rows, index: 'id', columns: [
      { title: 'Site', field: 'site' },
      { title: 'Address', field: 'url', render: function (r) { return link(r.url, r.url); } },
      { title: 'Status', field: 'code', render: function (r) { return siteBadge(r.code); } },
      { title: 'Notes', field: 'info' },
    ] });
  }

  function Overview() {
    var live = D.sites.live.code === 200;
    return h(P.Stack, { gap: 'lg' },
      live ? null : h(P.Banner, { tone: 'danger', title: 'The live site is down' },
        'ctm.lighthouseway.org answers ' + D.sites.live.code + ' Bad Gateway: the proxy is up, the CTM app behind it is not. Release Engineer has it: ', link(GH + '/issues/63', '#63'), '.'),
      h(P.Inline, { gap: 'md', wrap: true },
        h(P.Metric, { card: true, value: String(tasks.length), label: 'Open tasks', description: urgent.length + ' urgent (S1/S2)' }),
        h(P.Metric, { card: true, value: String(D.mergedPrs.length), label: 'Merged, last 3 days', description: D.closedIssues.length + ' issues closed' }),
        h(P.Metric, { card: true, value: String(active.length), label: 'Active decisions', description: noCheck.length + ' without a check yet' }),
        h(P.Metric, { card: true, value: String(failing.length), label: 'Decision checks failing', description: failing.map(function (d) { return d.id; }).join(', ') || 'None' })),
      h(P.Heading, { level: 2, size: 3 }, 'Sites'),
      h(Sites),
      h(P.Heading, { level: 2, size: 3 }, 'Waiting on you'),
      mine.length ? h(P.Stack, { gap: 'xs' }, mine.map(function (t) {
        return h(P.Text, { key: t.number }, link(t.url, '#' + t.number), ' ', t.waiting);
      }), h(P.Text, null, link(GH + '/issues/49', '#49'), ' Install the deploy runner on the server; until then merges do not reach the live site.'))
        : h(P.Text, { variant: 'secondary' }, 'Nothing.'),
      h(P.Heading, { level: 2, size: 3 }, 'Top of the list'),
      h(TaskTable, { rows: tasks.slice(0, 5) }));
  }

  function TaskTable(props) {
    return h(P.Table, { label: 'Tasks to do', data: props.rows, index: 'number', empty: 'Nothing open.', columns: [
      { title: '#', field: 'rank', width: '--plx-ref-size-48px' },
      { title: 'Issue', field: 'title', render: function (t) { return h(P.Stack, { gap: 'xs' }, link(t.url, '#' + t.number + ' ' + t.title), t.decision ? h(P.Badge, { tone: 'info', size: 'sm' }, 'Decision') : null); } },
      { title: 'Severity', field: 'sev', width: '--plx-ref-size-96px', render: function (t) { return h(P.Badge, { tone: SEV[t.sev] || 'neutral', size: 'sm' }, t.sev); } },
      { title: 'Owner', field: 'owners', render: function (t) { return t.waiting ? 'You (owner)' : t.owners.map(role).join(', '); } },
      { title: 'Next step', field: 'next' },
    ] });
  }

  function Todo() {
    return h(P.Stack, { gap: 'md' },
      h(P.Text, { variant: 'secondary' }, 'Every open work item on GitHub, in the Product Lead\'s priority order. To add one, open an issue from a template (Bug, Feature, UI/UX, Question).'),
      h(TaskTable, { rows: tasks }),
      D.openPrs.length ? h(P.Heading, { level: 2, size: 3 }, 'Open pull requests') : null,
      D.openPrs.length ? h(P.Stack, { gap: 'xs' }, D.openPrs.map(function (p) { return h(P.Text, { key: p.number }, link(p.url, '#' + p.number + ' ' + p.title), p.isDraft ? ' (draft)' : ''); })) : null);
  }

  function Decisions() {
    var rows = D.decisions.slice().reverse();
    return h(P.Stack, { gap: 'md' },
      h(P.Text, { variant: 'secondary' }, 'From decisions.yaml on main. "Check" is the rule that enforces each decision, with its latest result on main. To change a decision, comment on its issue.'),
      h(P.Table, { label: 'Decisions', data: rows, index: 'id', columns: [
        { title: 'Id', field: 'id', width: '--plx-ref-size-80px' },
        { title: 'Date', field: 'date', width: '--plx-ref-size-96px' },
        { title: 'Decision', field: 'decision' },
        { title: 'Decided by', field: 'by', width: '--plx-ref-size-160px', render: function (d) { return d.by === 'owner' ? 'Owner' : role(String(d.by).replace('agent:ctm3-', '')); } },
        { title: 'Status', field: 'status', width: '--plx-ref-size-120px', render: function (d) { return d.status === 'active' ? h(P.Badge, { tone: 'active', size: 'sm' }, 'Active') : h(P.Badge, { tone: 'neutral', size: 'sm' }, d.superseded_by ? 'Replaced by ' + d.superseded_by : d.status); } },
        { title: 'Check', field: 'state', render: function (d) {
          return h(P.Stack, { gap: 'xs' }, d.url ? h(P.Link, { href: d.url, external: true }, stateBadge(d.state)) : stateBadge(d.state), h(P.Text, { variant: 'secondary' }, d.check)); } },
      ] }));
  }

  function Done() {
    function list(items, at) {
      return items.length ? h(P.Stack, { gap: 'xs' }, items.map(function (x) { return h(P.Text, { key: x.number }, link(x.url, '#' + x.number + ' ' + x.title), ' · ', fmt(x[at])); }))
        : h(P.Text, { variant: 'secondary' }, 'None.');
    }
    return h(P.Stack, { gap: 'md' },
      h(P.Heading, { level: 2, size: 3 }, 'Merged pull requests (last 3 days)'), list(D.mergedPrs, 'mergedAt'),
      h(P.Heading, { level: 2, size: 3 }, 'Closed issues (last 3 days)'), list(D.closedIssues, 'closedAt'),
      h(P.Heading, { level: 2, size: 3 }, 'Latest check runs on main'),
      h(P.Table, { label: 'Workflows', data: D.workflows, index: 'file', columns: [
        { title: 'Workflow', field: 'name' },
        { title: 'Result', field: 'conclusion', render: function (w) { return h(P.Link, { href: w.url, external: true }, stateBadge(w.conclusion)); } },
        { title: 'When', field: 'at', render: function (w) { return fmt(w.at); } },
      ] }));
  }

  function Team() {
    var by = {};
    tasks.forEach(function (t) { t.owners.forEach(function (o) { (by[o] = by[o] || []).push(t); }); });
    var rows = Object.keys(by).sort().map(function (o) { return { id: o, agent: 'CTM3 - ' + role(o), items: by[o] }; });
    return h(P.Stack, { gap: 'md' },
      h(P.Text, { variant: 'secondary' }, 'One row per role, from the agent labels on open issues.'),
      h(P.Table, { label: 'Team', data: rows, index: 'id', columns: [
        { title: 'Role', field: 'agent', width: '--plx-ref-size-240px' },
        { title: 'Open items', field: 'items', render: function (r) { return String(r.items.length); }, width: '--plx-ref-size-120px' },
        { title: 'Holding', field: 'items', render: function (r) { return h(P.Stack, { gap: 'xs' }, r.items.map(function (t) { return h(P.Text, { key: t.number }, link(t.url, '#' + t.number), ' ', t.title); })); } },
      ] }));
  }

  function Pictures() {
    if (!D.shots.length) return h(P.Text, { variant: 'secondary' }, 'No screenshots yet.');
    return h(P.Stack, { gap: 'md' },
      h(P.Text, { variant: 'secondary' }, 'The latest screenshots CI took (' + D.shots[0].run + '), from the ci-screenshots branch. Synthetic data only.'),
      D.shots.map(function (s) {
        return h(P.Stack, { gap: 'xs', key: s.file }, h(P.Text, null, link(s.url, s.name)), h('img', { src: s.file, alt: s.name, className: 'shot' }));
      }));
  }

  function App() {
    return h(P.Stack, { gap: 'lg' },
      h(P.Stack, { gap: 'xs' },
        h(P.Heading, { level: 1, size: 1 }, 'CTM 3.0 Dashboard'),
        h(P.Text, { variant: 'secondary' }, 'Snapshot from GitHub, ' + fmt(D.generatedAt) + ' (main ' + D.mainSha + '). Source of truth: ', link(GH + '/issues/40', 'pinned dashboard issue #40'), '.')),
      h(P.Tabs, { label: 'Dashboard', items: [
        { value: 'overview', label: 'Overview', content: h(Overview) },
        { value: 'todo', label: 'To do', count: tasks.length, content: h(Todo) },
        { value: 'decisions', label: 'Decisions', count: D.decisions.length, content: h(Decisions) },
        { value: 'done', label: 'Done', count: D.mergedPrs.length, content: h(Done) },
        { value: 'team', label: 'Team', content: h(Team) },
        { value: 'pictures', label: 'Screenshots', count: D.shots.length, content: h(Pictures) },
      ] }));
  }

  window.ReactDOM.createRoot(document.getElementById('root')).render(h(App));
})();

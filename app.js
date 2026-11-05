/* CTM 3.0 dashboard on CTM's Plenix pin (0.86.0), built from the CDN's documented templates:
   SplitWorkspace (AppShell + SplitView: a DataGrid list, the chosen row in a ReadingPane) with a
   NavPane + NavList on the left. Data: data.js, a snapshot taken from GitHub by collect.py. */
(function () {
  'use strict';
  var R = window.React, P = window.Plenix, D = window.CTM_DATA, h = R.createElement;
  var GH = 'https://github.com/LighthouseCollection/CTM';

  function fmt(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    return isNaN(d) ? iso : d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  }
  function role(r) { return String(r).replace(/-/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); }); }
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
    if (code === 200) return h(P.Badge, { tone: 'success', icon: 'check', size: 'sm' }, 'Up');
    if (!code) return h(P.Badge, { tone: 'neutral', size: 'sm' }, 'Not running');
    if (code === 404) return h(P.Badge, { tone: 'neutral', size: 'sm' }, 'Not built yet');
    return h(P.Badge, { tone: 'negative', icon: 'warning', size: 'sm' }, 'Down (' + code + ')');
  }
  function sevBadge(t) { return h(P.Badge, { tone: SEV[t.sev] || 'neutral', size: 'sm' }, t.sev); }
  // One labelled fact in the reading pane.
  function Field(props) {
    return h(P.Stack, { gap: 'xs' }, h(P.Text, { variant: 'secondary' }, props.label), h('div', null, props.children));
  }
  function Detail(props) { return h(P.Stack, { gap: 'lg' }, props.children); }

  /* ---- Owner decisions: the questions waiting for the owner, kept apart from the team's to-do list ---- */
  var owner = (D.ownerDecisions || []).map(function (d) {
    var status = d.answer ? 'answered' : d.applied ? 'applied' : 'open';
    return Object.assign({}, d, { status: status });
  });
  var ownerIssues = {};
  owner.forEach(function (d) { ownerIssues[d.issue] = d; });
  var STATUS = {
    open: ['action-required', 'Needs your answer'],
    applied: ['waiting', 'Applied for now'],
    answered: ['success', 'You answered'],
  };
  function statusBadge(d) { var v = STATUS[d.status]; return h(P.Badge, { tone: v[0], size: 'sm' }, v[1]); }
  function plain(t) { return String(t || '').replace(/\*\*/g, '').replace(/`/g, ''); }
  function optionText(o) { var t = plain(o.text); return (t.charAt(0).toUpperCase() + t.slice(1)).split(' — risk: '); }

  /* ---- Posting the owner's answer as a comment in the decision's own GitHub thread ----
     The key is a fine-grained GitHub token the owner creates once (this repository only, Issues: read and write).
     It stays in this browser (localStorage); it is never in the page's files, the repository or data.js. */
  var KEY_NAME = 'ctm3-dashboard-github-key';
  var API = 'https://api.github.com/repos/LighthouseCollection/CTM';
  var memoryKey = '';
  function getKey() { try { return localStorage.getItem(KEY_NAME) || memoryKey; } catch (e) { return memoryKey; } }
  function setKey(v) { memoryKey = v || ''; try { if (v) localStorage.setItem(KEY_NAME, v); else localStorage.removeItem(KEY_NAME); } catch (e) { /* storage blocked: keep it for this visit */ } }
  function gh(path, opts) {
    return fetch(path.indexOf('http') === 0 ? path : 'https://api.github.com' + path, Object.assign({}, opts, {
      headers: { Accept: 'application/vnd.github+json', Authorization: 'Bearer ' + getKey(), 'X-GitHub-Api-Version': '2022-11-28', 'Content-Type': 'application/json' },
    })).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (!r.ok) { var e = new Error(j.message || ('GitHub answered ' + r.status)); e.status = r.status; throw e; }
        return j;
      });
    }, function () { throw new Error('This page cannot reach GitHub from here. Use the public page, lighthousecollection.github.io/CTM, or Copy answer.'); });
  }
  function keyError(e) {
    if (e.status === 401) return 'GitHub did not accept this key (wrong, expired or revoked). Create a new one and connect again.';
    if (e.status === 403 || e.status === 404) return 'This key cannot comment on LighthouseCollection/CTM issues. Give it this repository with Issues: Read and write; the organization may also need to approve it.';
    return e.message;
  }

  // Connect once: paste the key; it is checked against GitHub before it is kept.
  function Connect(props) {
    var vs = R.useState(''), value = vs[0], setValue = vs[1];
    var es = R.useState(''), error = es[0], setError = es[1];
    var bs = R.useState(false), busy = bs[0], setBusy = bs[1];
    function save() {
      setBusy(true); setError('');
      setKey(value.trim());
      gh('/user').then(function (u) {
        return gh(API).then(function () { props.onConnected(u.login); });
      }).catch(function (e) { setKey(''); setError(keyError(e)); }).then(function () { setBusy(false); });
    }
    return h(P.Stack, { gap: 'sm' },
      h(P.Banner, { tone: 'info', title: 'Connect GitHub once to answer here' },
        'Your answer then goes straight into the thread on GitHub, under your name. ',
        link('https://github.com/settings/personal-access-tokens/new', 'Create a key'),
        ': Resource owner LighthouseCollection, "Only select repositories" → CTM, and under Repository permissions set Issues to "Read and write". Nothing else. The key stays in this browser only.'),
      h(P.Field, { label: 'GitHub key', error: error || undefined },
        h(P.Input, { type: 'password', autoComplete: 'off', value: value, onChange: function (e) { setValue(e.target.value); } })),
      h(P.Inline, { gap: 'sm' }, h(P.Button, { variant: 'primary', loading: busy, disabled: !value.trim() || busy, onClick: save }, 'Connect')));
  }

  // The answer form: every option from the decision card (the recommended one marked), plus Other with a text box.
  function AnswerForm(props) {
    var d = props.d;
    var rec = (d.options.filter(function (o) { return o.recommended; })[0] || {}).key || '';
    var cs = R.useState(d.applied || rec), choice = cs[0], setChoice = cs[1];
    var ns = R.useState(''), note = ns[0], setNote = ns[1];
    var cp = R.useState(false), copied = cp[0], setCopied = cp[1];
    var ls = R.useState(''), login = ls[0], setLogin = ls[1];
    var ss = R.useState({ state: 'idle' }), send = ss[0], setSend = ss[1];
    R.useEffect(function () { if (getKey()) gh('/user').then(function (u) { setLogin(u.login); }, function () { setLogin(''); }); }, []);
    var options = d.options.map(function (o) {
      var parts = optionText(o);
      return {
        value: o.key,
        label: o.key + (o.recommended ? ' (Recommended)' : '') + (d.applied === o.key ? ' · applied now' : ''),
        description: parts[0] + (parts[1] ? ' Risk: ' + parts[1] : ''),
      };
    }).concat([{ value: 'other', label: 'Other', description: 'Write your own answer below.' }]);
    var chosen = d.options.filter(function (o) { return o.key === choice; })[0];
    var other = choice === 'other';
    var ready = other ? note.trim().length > 0 : !!chosen;
    var body = '**Answer to ' + d.id + ': ' + (other ? 'Other' : choice) + '**\n\n' +
      (other ? note.trim() : optionText(chosen)[0] + (note.trim() ? '\n\nNote: ' + note.trim() : '')) +
      '\n\n_Sent from the CTM 3.0 dashboard._';
    function post() {
      setSend({ state: 'busy' });
      gh(API + '/issues/' + d.issue + '/comments', { method: 'POST', body: JSON.stringify({ body: body }) })
        .then(function (c) { setSend({ state: 'done', url: c.html_url }); }, function (e) { setSend({ state: 'error', message: keyError(e) }); });
    }
    function copy() { if (navigator.clipboard) navigator.clipboard.writeText(body).then(function () { setCopied(true); }); }
    if (send.state === 'done') {
      return h(P.Banner, { tone: 'success', title: 'Answer posted on #' + d.issue },
        'It is in the thread under your name. The Product Lead applies it and updates decisions.yaml. ', link(send.url, 'See your comment'), '.');
    }
    return h(P.Stack, { gap: 'md' },
      h(P.RadioGroup, { label: 'Your answer', name: 'answer-' + d.id, value: choice, onChange: function (v) { setChoice(v && v.target ? v.target.value : v); }, options: options }),
      h(P.Field, { label: other ? 'Your answer' : 'Note (optional)', required: other },
        h(P.Textarea, { rows: 4, autoGrow: true, value: note, onChange: function (e) { setNote(e.target.value); } })),
      login ? h(P.Stack, { gap: 'sm' },
        send.state === 'error' ? h(P.Banner, { tone: 'danger', title: 'Not posted' }, send.message) : null,
        h(P.Inline, { gap: 'sm', wrap: true },
          h(P.Button, { variant: 'primary', loading: send.state === 'busy', disabled: !ready || send.state === 'busy', onClick: post }, 'Send answer to #' + d.issue),
          h(P.Button, { icon: 'content_copy', disabled: !ready, onClick: copy }, copied ? 'Copied' : 'Copy answer')),
        h(P.Text, { variant: 'secondary' }, 'Posts as ' + login + ' in the thread of ', link(d.url, '#' + d.issue), '. ',
          h(P.Link, { href: '#owner', onClick: function (e) { e.preventDefault(); setKey(''); setLogin(''); } }, 'Disconnect this browser'), '.'))
        : h(Connect, { onConnected: setLogin }));
  }

  var tasks = D.tasks.filter(function (t) { return !t.waiting; });
  var active = D.decisions.filter(function (d) { return d.status === 'active'; });
  var needAnswer = owner.filter(function (d) { return d.status === 'open'; });
  var toDecide = owner.filter(function (d) { return d.status !== 'answered'; });
  var answered = owner.filter(function (d) { return d.status === 'answered'; });
  var answerOf = {};
  answered.forEach(function (d) { answerOf[d.id] = d; });
  var noCheck = active.filter(function (d) { return d.kind === 'review only'; });
  var failing = active.filter(function (d) { return d.state === 'failure'; });
  var urgent = tasks.filter(function (t) { return t.sev === 'S1' || t.sev === 'S2'; });

  /* ---- Each section: rows, columns, the detail of the chosen row, and an optional toolbar ---- */

  var s = D.sites;
  var siteRows = [
    { id: 'live', site: 'Live CTM', url: s.live.url, code: s.live.code, info: s.live.version ? 'CTM ' + s.live.version.version + ' · Plenix ' + s.live.version.plenix_version : 'The proxy answers but the CTM app behind it does not. Release Engineer has it on #63.', issue: 63 },
    { id: 'local', site: 'Local CTM (this PC)', url: s.local.url, code: s.local.code, info: s.local.version ? 'CTM ' + s.local.version.version + ' · Plenix ' + s.local.version.plenix_version + ' · synthetic data. Sign-in providers are not set up on this PC.' : s.local.note },
    { id: 'pages', site: 'Dashboard web page', url: s.pages.url, code: s.pages.code, info: 'This page, on GitHub Pages. A snapshot; automatic refresh is #61.', issue: 61 },
  ];
  var doneRows = D.mergedPrs.map(function (p) { return { id: 'pr' + p.number, kind: 'Pull request', number: p.number, title: p.title, url: p.url, at: p.mergedAt }; })
    .concat(D.closedIssues.map(function (i) { return { id: 'is' + i.number, kind: 'Issue closed', number: i.number, title: i.title, url: i.url, at: i.closedAt }; }))
    .sort(function (a, b) { return a.at < b.at ? 1 : -1; });
  var byRole = {};
  tasks.forEach(function (t) { t.owners.forEach(function (o) { (byRole[o] = byRole[o] || []).push(t); }); });
  var teamRows = Object.keys(byRole).sort().map(function (o) { return { id: o, agent: 'CTM3 - ' + role(o), items: byRole[o], count: byRole[o].length }; });
  var known = {};
  D.decisions.forEach(function (d) { known[d.id] = true; });
  var decisionRows = answered.filter(function (d) { return !known[d.id]; }).map(function (d) {
    return { id: d.id, date: (d.answer.at || '').slice(0, 10), area: '', decision: plain(d.title), by: 'owner', status: 'answered',
      check: 'Your answer is being applied; the team records it in decisions.yaml.', kind: 'review only', state: 'review', url: null };
  }).concat(D.decisions.slice().reverse()).map(function (d) { return Object.assign({}, d, { owner: answerOf[d.id] || null }); });
  function decisionStatus(d) {
    if (d.status === 'answered') return h(P.Badge, { tone: 'success', size: 'sm' }, 'You answered');
    if (d.status === 'active') return h(P.Badge, { tone: 'active', size: 'sm' }, d.owner ? 'Active · you answered' : 'Active');
    return h(P.Badge, { tone: 'neutral', size: 'sm' }, d.superseded_by ? 'Replaced' : d.status);
  }

  var SECTIONS = [
    {
      id: 'overview', label: 'Overview', icon: 'dashboard', title: 'Sites',
      rows: siteRows,
      toolbar: h(P.Stack, { gap: 'md' },
        s.live.code === 200 ? null : h(P.Banner, { tone: 'danger', title: 'The live site is down' },
          'ctm.lighthouseway.org answers ' + s.live.code + ': the proxy is up, the CTM app behind it is not. Release Engineer has it: ', link(GH + '/issues/63', '#63'), '.'),
        h(P.Inline, { gap: 'md', wrap: true },
          h(P.Metric, { card: true, value: String(needAnswer.length), label: 'Waiting on you', description: owner.length + ' decisions in all' }),
          h(P.Metric, { card: true, value: String(tasks.length), label: 'Team to-do', description: urgent.length + ' urgent (S1/S2)' }),
          h(P.Metric, { card: true, value: String(D.mergedPrs.length), label: 'Merged, last 3 days', description: D.closedIssues.length + ' issues closed' }),
          h(P.Metric, { card: true, value: String(active.length), label: 'Active decisions', description: noCheck.length + ' without a check yet' }),
          h(P.Metric, { card: true, value: String(failing.length), label: 'Decision checks failing', description: failing.map(function (d) { return d.id; }).join(', ') || 'None' }))),
      columns: [
        { title: 'Site', field: 'site', kind: 'name' },
        { title: 'Status', field: 'code', kind: 'center', render: function (r) { return siteBadge(r.code); } },
        { title: 'Address', field: 'url', kind: 'data' },
      ],
      detail: function (r) {
        return h(Detail, null,
          h(Field, { label: 'Status' }, siteBadge(r.code)),
          h(Field, { label: 'Address' }, link(r.url, r.url)),
          h(Field, { label: 'Notes' }, h(P.Text, null, r.info)),
          r.issue ? h(Field, { label: 'Tracked in' }, link(GH + '/issues/' + r.issue, '#' + r.issue)) : null);
      },
    },
    {
      id: 'owner', label: 'To decide', icon: 'flag', title: 'Decisions waiting on you', rows: toDecide,
      toolbar: h(P.Text, { variant: 'secondary' }, 'Your decisions, apart from the team’s to-do list. Where the team could not wait, it applied the recommended option and keeps working; you can still change it. Choose a row to answer.'),
      columns: [
        { title: 'Decision', field: 'id', kind: 'data', width: 88 },
        { title: 'Question', field: 'title', kind: 'name', render: function (d) { return plain(d.title); } },
        { title: 'Status', field: 'status', kind: 'center', width: 168, render: statusBadge },
      ],
      detail: function (d) {
        return h(Detail, null,
          h(P.Heading, { level: 2, size: 4 }, d.id + ' · ' + plain(d.title)),
          h(P.Inline, { gap: 'sm', wrap: true }, statusBadge(d), link(d.url, 'Open #' + d.issue)),
          d.context ? h(Field, { label: 'Context' }, h(P.Text, null, plain(d.context))) : null,
          d.applied ? h(P.Banner, { tone: 'info', title: 'Applied for now: ' + d.applied }, 'The team went ahead with the recommended option so work did not stop. Pick another option to change it.') : null,
          h(AnswerForm, { d: d, key: d.id }));
      },
    },
    {
      id: 'todo', label: 'To do', icon: 'checklist', title: 'Tasks to do', rows: tasks, index: 'number',
      columns: [
        { title: '#', field: 'rank', kind: 'data', width: 56 },
        { title: 'Issue', field: 'title', kind: 'name', render: function (t) { return '#' + t.number + ' ' + t.title; } },
        { title: 'Severity', field: 'sev', kind: 'center', width: 96, render: sevBadge },
        { title: 'Owner', field: 'owners', render: function (t) { return t.owners.map(role).join(', ') || 'Not assigned'; } },
      ],
      detail: function (t) {
        return h(Detail, null,
          h(P.Heading, { level: 2, size: 4 }, link(t.url, '#' + t.number + ' ' + t.title)),
          h(P.Inline, { gap: 'sm', wrap: true }, sevBadge(t), t.type ? h(P.Badge, { tone: 'neutral', size: 'sm' }, t.type) : null,
            ownerIssues[t.number] ? h(P.Badge, { tone: 'info', size: 'sm' }, 'Has your decision ' + ownerIssues[t.number].id) : null),
          h(Field, { label: 'Next step' }, h(P.Text, null, t.next)),
          h(Field, { label: 'Owner' }, h(P.Text, null, t.owners.length ? t.owners.map(role).join(', ') : 'Not assigned')),
          t.areas.length ? h(Field, { label: 'Area' }, h(P.Text, null, t.areas.join(', '))) : null,
          h(Field, { label: 'Last updated' }, h(P.Text, null, fmt(t.updated))));
      },
    },
    {
      id: 'decisions', label: 'Decisions', icon: 'article', title: 'Decisions', rows: decisionRows,
      columns: [
        { title: 'Id', field: 'id', kind: 'data', width: 88 },
        { title: 'Decision', field: 'decision', kind: 'name' },
        { title: 'Status', field: 'status', kind: 'center', width: 168, render: decisionStatus },
        { title: 'Check', field: 'state', kind: 'center', width: 120, render: function (d) { return stateBadge(d.state); } },
      ],
      detail: function (d) {
        return h(Detail, null,
          h(P.Heading, { level: 2, size: 4 }, d.id),
          h(P.Text, null, d.decision),
          d.owner ? h(P.Banner, { tone: 'success', title: 'Your answer: ' + d.owner.answer.choice },
            d.owner.answer.text, ' ', link(d.owner.answer.url, 'See it on #' + d.owner.issue), '.') : null,
          h(Field, { label: 'Decided by' }, h(P.Text, null, (d.by === 'owner' ? 'Owner' : role(String(d.by).replace('agent:ctm3-', ''))) + ', ' + d.date)),
          h(Field, { label: 'Area' }, h(P.Text, null, d.area || '—')),
          h(Field, { label: 'Status' }, h(P.Text, null, d.status + (d.superseded_by ? ', replaced by ' + d.superseded_by : ''))),
          h(Field, { label: d.kind === 'review only' ? 'No check yet' : 'Check (' + d.kind + ')' },
            h(P.Stack, { gap: 'xs' }, d.url ? link(d.url, stateBadge(d.state)) : stateBadge(d.state), h(P.Text, { variant: 'secondary' }, d.check))));
      },
    },
    {
      id: 'done', label: 'Done', icon: 'task_alt', title: 'Done in the last 3 days', rows: doneRows,
      columns: [
        { title: 'What', field: 'title', kind: 'name', render: function (x) { return '#' + x.number + ' ' + x.title; } },
        { title: 'Kind', field: 'kind', width: 128 },
        { title: 'When', field: 'at', kind: 'data', width: 136, render: function (x) { return fmt(x.at); } },
      ],
      detail: function (x) {
        return h(Detail, null,
          h(P.Heading, { level: 2, size: 4 }, link(x.url, '#' + x.number + ' ' + x.title)),
          h(Field, { label: 'Kind' }, h(P.Text, null, x.kind)),
          h(Field, { label: 'When' }, h(P.Text, null, fmt(x.at))));
      },
    },
    {
      id: 'checks', label: 'Checks', icon: 'fact_check', title: 'Latest check runs on main', rows: D.workflows, index: 'file',
      columns: [
        { title: 'Workflow', field: 'name', kind: 'name' },
        { title: 'Result', field: 'conclusion', kind: 'center', width: 120, render: function (w) { return stateBadge(w.conclusion); } },
        { title: 'When', field: 'at', kind: 'data', width: 136, render: function (w) { return fmt(w.at); } },
      ],
      detail: function (w) {
        return h(Detail, null,
          h(P.Heading, { level: 2, size: 4 }, w.name),
          h(Field, { label: 'Result' }, link(w.url, stateBadge(w.conclusion))),
          h(Field, { label: 'File' }, h(P.Text, { variant: 'data' }, w.file)),
          h(Field, { label: 'When' }, h(P.Text, null, fmt(w.at))));
      },
    },
    {
      id: 'team', label: 'Team', icon: 'groups', title: 'Team', rows: teamRows,
      columns: [
        { title: 'Role', field: 'agent', kind: 'name' },
        { title: 'Open items', field: 'count', kind: 'data', width: 112 },
      ],
      detail: function (r) {
        return h(Detail, null,
          h(P.Heading, { level: 2, size: 4 }, r.agent),
          h(P.Stack, { gap: 'sm' }, r.items.map(function (t) {
            return h(P.Inline, { key: t.number, gap: 'sm' }, sevBadge(t), link(t.url, '#' + t.number + ' ' + t.title));
          })));
      },
    },
    {
      id: 'screenshots', label: 'Screenshots', icon: 'image', title: 'Latest CI screenshots', rows: D.shots, index: 'file',
      columns: [
        { title: 'Screenshot', field: 'name', kind: 'name' },
        { title: 'Run', field: 'run', kind: 'data' },
      ],
      detail: function (x) {
        return h(Detail, null,
          h(P.Heading, { level: 2, size: 4 }, link(x.url, x.name)),
          h(P.Text, { variant: 'secondary' }, 'From the ci-screenshots branch (' + x.run + '). Synthetic data only.'),
          h('img', { src: x.file, alt: x.name, className: 'shot' }));
      },
    },
  ];

  function fromHash() {
    var id = (location.hash || '').replace('#', '');
    return SECTIONS.some(function (x) { return x.id === id; }) ? id : 'overview';
  }

  function App() {
    var st = R.useState(fromHash()), current = st[0], setCurrent = st[1];
    var op = R.useState({}), open = op[0], setOpen = op[1];
    R.useEffect(function () {
      function onHash() { setCurrent(fromHash()); }
      window.addEventListener('hashchange', onHash);
      return function () { window.removeEventListener('hashchange', onHash); };
    }, []);
    var sec = SECTIONS.filter(function (x) { return x.id === current; })[0];
    var key = sec.index || 'id';
    var openKey = open[sec.id] != null ? open[sec.id] : null;
    var record = openKey == null ? null : sec.rows.filter(function (r) { return r[key] === openKey; })[0];

    var nav = h(P.NavPane, {
      label: 'Dashboard sections', title: 'CTM 3.0 Dashboard',
      footer: h(P.Text, { variant: 'secondary' }, 'Snapshot ' + fmt(D.generatedAt) + ' · main ' + D.mainSha),
    }, h(P.NavList, {
      label: 'Sections', value: current,
      onSelect: function (id) { location.hash = id; setCurrent(id); },
      items: SECTIONS.map(function (x) { return { id: x.id, label: x.label, icon: x.icon, count: x.id === 'overview' ? undefined : x.rows.length }; }),
    }));

    return h(P.SplitWorkspace, {
      key: sec.id,
      sideNav: nav,
      paneTitle: sec.title,
      title: record ? sec.label + ' details' : sec.label,
      toolbar: sec.toolbar || null,
      rows: sec.rows,
      columns: sec.columns,
      grid: {
        index: key, openKey: openKey,
        empty: 'Nothing here.',
        onRowClick: function (r) { var n = {}; for (var k in open) n[k] = open[k]; n[sec.id] = r[key]; setOpen(n); },
      },
      detailOpen: !!record,
      actions: record ? h(P.Button, { variant: 'subtle', size: 'sm', onClick: function () { var n = {}; for (var k in open) n[k] = open[k]; n[sec.id] = null; setOpen(n); } }, 'Close') : null,
      empty: h(P.EmptyState, { title: 'Nothing selected' }, 'Choose a row to see its details here.'),
    }, record ? sec.detail(record) : null);
  }

  window.ReactDOM.createRoot(document.getElementById('root')).render(h(App));
})();

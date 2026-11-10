/* CTM 3.0 dashboard on CTM's Plenix pin (PLENIX_BASE in ctm/settings.py), built from the CDN's documented
   SplitWorkspace template (listing-page.md): AppShell with a NavPane + NavList on the left, the section's title
   row, a CommandBar with search, filters, sort and columns (command-bar.md, use-collection-view.md), then the
   SplitWorkspace split: the DataGrid (data-grid.md: compact, pill cells, header menus, typed columns) and the
   chosen row's details beside it (owner, 2026-11-10). Data: data.js, a snapshot taken from GitHub by build_dashboard_page.py. */
(function () {
  'use strict';
  var R = window.React, P = window.Plenix, h = R.createElement;
  var GH = 'https://github.com/LighthouseCollection/CTM';

  function fmt(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    return isNaN(d) ? iso : d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  }
  function role(r) { return String(r).replace(/-/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); }).replace(/\bQa\b/, 'QA').replace(/\bI18n\b/, 'i18n'); }
  function link(href, text) { return h(P.Link, { href: href, external: true }, text); }
  // Statuses are badges with an icon (owner rule), never a dot.
  var SEV = { S1: ['negative', 'warning'], S2: ['action-required', 'warning'], S3: ['waiting', 'clock'], S4: ['neutral', 'info'] };
  var STATE = {
    success: ['success', 'check', 'Pass'], failure: ['negative', 'warning', 'Fail'], cancelled: ['neutral', 'info', 'Cancelled'],
    skipped: ['neutral', 'info', 'Skipped'], review: ['neutral', 'info', 'Review only'], present: ['success', 'check', 'In place'],
  };
  function stateBadge(s) {
    var v = STATE[s] || ['waiting', 'clock', s || 'No run yet'];
    return h(P.Badge, { tone: v[0], icon: v[1], size: 'sm' }, v[2]);
  }
  function siteBadge(code) {
    if (code === 200) return h(P.Badge, { tone: 'success', icon: 'check', size: 'sm' }, 'Up');
    if (!code) return h(P.Badge, { tone: 'neutral', icon: 'info', size: 'sm' }, 'Not running');
    if (code === 404) return h(P.Badge, { tone: 'neutral', icon: 'info', size: 'sm' }, 'Not built yet');
    return h(P.Badge, { tone: 'negative', icon: 'warning', size: 'sm' }, 'Down (' + code + ')');
  }
  function sevBadge(t) { var v = SEV[t.sev] || SEV.S4; return h(P.Badge, { tone: v[0], icon: v[1], size: 'sm' }, t.sev); }
  // The chosen record: notes and banners first, then its facts as a stacked PropertyList.
  function Detail(props) { return h(P.Stack, { gap: 'lg' }, props.children); }
  function Facts(props) { return h(P.PropertyList, { layout: 'stacked' }, props.children); }
  function Field(props) { return h(P.PropertyList.Item, { label: props.label, data: props.data }, props.children); }


  /* ---- Owner decisions: the questions waiting for the owner, kept apart from the team's to-do list ---- */
  var STATUS = {
    open: ['action-required', 'flag', 'Needs your answer'],
    applied: ['waiting', 'clock', 'Applied for now'],
    answered: ['success', 'check', 'You answered'],
  };
  function statusBadge(d) { var v = STATUS[d.status]; return h(P.Badge, { tone: v[0], icon: v[1], size: 'sm' }, v[2]); }
  var URL = /https?:\/\/\S+/g;
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
    var cs = R.useState(d.applied || rec || (d.options.length ? '' : 'other')), choice = cs[0], setChoice = cs[1];
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
    // nothing chosen yet (a question with no recommended option): no answer text until a choice is made
    var body = !ready ? '' : '**Answer to ' + d.id + ': ' + (other ? 'Other' : choice) + '**\n\n' +
      (other ? note.trim() : optionText(chosen)[0] + (note.trim() ? '\n\nNote: ' + note.trim() : '')) +
      '\n\n_Sent from the CTM 3.0 dashboard._';
    function post() {
      setSend({ state: 'busy' });
      gh(API + '/issues/' + d.issue + '/comments', { method: 'POST', body: JSON.stringify({ body: body }) })
        .then(function (c) {
          setSend({ state: 'done', url: c.html_url });
          if (props.onAnswered) props.onAnswered(d.id, { choice: other ? 'Other' : choice, text: other ? note.trim() : optionText(chosen)[0] + (note.trim() ? ' Note: ' + note.trim() : ''), at: c.created_at || new Date().toISOString(), url: c.html_url });
        }, function (e) { setSend({ state: 'error', message: keyError(e) }); });
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

  /* ---- Everything below is rebuilt from the data, plus the answers sent from this browser that the
     next rebuild of data.json has not picked up yet (so a sent answer moves at once). ---- */
  function derive(D, local, onAnswered, posted) {
  var owner = (D.ownerDecisions || []).map(function (d) {
    var answer = d.answer || local[d.id] || null;
    return Object.assign({}, d, { answer: answer, status: answer ? 'answered' : d.applied ? 'applied' : 'open' });
  });
  var ownerIssues = {};
  owner.forEach(function (d) { ownerIssues[d.issue] = d; });
  var tasks = D.tasks.filter(function (t) { return !t.waiting; });
  var active = D.decisions.filter(function (d) { return d.status === 'active'; });
  var needAnswer = owner.filter(function (d) { return d.status === 'open'; });
  var toDecide = needAnswer; // only questions nobody has decided yet: answered or already-applied ones are under Decisions
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
    s.local ? { id: 'local', site: 'Local CTM (this PC)', url: s.local.url, code: s.local.code, info: s.local.version ? 'CTM ' + s.local.version.version + ' · Plenix ' + s.local.version.plenix_version + ' · synthetic data. Sign-in providers are not set up on this PC.' : s.local.note } : null,
    { id: 'pages', site: 'Dashboard web page', url: s.pages.url, code: s.pages.code, info: 'This page, on GitHub Pages. Rebuilt by the dashboard workflow when issues change and every 15 minutes.' },
  ].filter(Boolean);
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
    if (d.status === 'answered') return h(P.Badge, { tone: 'success', icon: 'check', size: 'sm' }, 'You answered');
    if (d.status === 'active') return h(P.Badge, { tone: 'active', icon: 'check', size: 'sm' }, d.owner ? 'Active · you answered' : 'Active');
    return h(P.Badge, { tone: 'neutral', icon: 'info', size: 'sm' }, d.superseded_by ? 'Replaced' : d.status);
  }

  var SECTIONS = [
    {
      id: 'overview', label: 'Overview', icon: 'dashboard', title: 'Overview', noun: ['site', 'sites'],
      description: 'What waits on you, the team’s work and the sites, rebuilt from GitHub every 15 minutes.',
      rows: siteRows,
      toolbar: h(P.Stack, { gap: 'md' },
        s.live.code === 200 ? null : h(P.Banner, { tone: 'danger', title: 'The live site is down' },
          'ctm.lighthouseway.org answers ' + s.live.code + ': the proxy is up, the CTM app behind it is not. Release Engineer has it: ', link(GH + '/issues/63', '#63'), '.'),
        h(P.ContentGrid, { size: 'md', label: 'Summary' },
          h(P.MetricCard, { icon: 'flag', title: 'Waiting on you', value: String(needAnswer.length), href: '#owner', context: 'Questions to answer' }),
          h(P.MetricCard, { icon: 'checklist', title: 'Team to-do', value: String(tasks.length), href: '#todo', context: urgent.length + ' urgent (S1/S2)' }),
          h(P.MetricCard, { icon: 'task_alt', title: 'Done', value: String(D.mergedPrs.length + D.closedIssues.length), href: '#done',
            context: 'Last 3 days: ' + D.mergedPrs.length + ' merged, ' + D.closedIssues.length + ' closed' }),
          h(P.MetricCard, { icon: 'article', title: 'Active decisions', value: String(active.length), href: '#decisions', context: noCheck.length + ' without a check yet' }),
          h(P.MetricCard, { icon: 'fact_check', title: 'Checks failing', value: String(failing.length), href: '#decisions',
            context: failing.map(function (d) { return d.id; }).join(', ') || 'None failing' }))),
      text: function (r) { return r.site + ' ' + r.url; },
      columns: [
        { title: 'Site', field: 'site', kind: 'name' },
        { title: 'Status', field: 'code', kind: 'center', width: 144, pill: false, sorter: 'number', render: function (r) { return siteBadge(r.code); } },
        { title: 'Address', field: 'url', kind: 'data' },
      ],
      detailTitle: function (r) { return r.site; },
      detail: function (r) {
        return h(Facts, null,
          h(Field, { label: 'Status' }, siteBadge(r.code)),
          h(Field, { label: 'Address' }, link(r.url, r.url)),
          h(Field, { label: 'Notes' }, r.info),
          r.issue ? h(Field, { label: 'Tracked in' }, link(GH + '/issues/' + r.issue, '#' + r.issue)) : null);
      },
    },
    {
      id: 'owner', label: 'To decide', icon: 'flag', title: 'Waiting on you', noun: ['question', 'questions'], rows: toDecide,
      description: 'Questions only you can answer. Choose one to answer it on the right; answered ones move to Decisions.',
      toolbar: posted ? h(P.Banner, { tone: 'success', title: 'Answer to ' + posted.id + ' posted' },
        'It is in the thread under your name and now listed under Decisions. ', link(posted.url, 'See your comment'), '.') : null,
      text: function (d) { return d.id + ' ' + plain(d.title) + ' ' + plain(d.context); },
      columns: [
        { title: 'Issue', field: 'id', kind: 'data', width: 88 },
        { title: 'Question', field: 'title', kind: 'name', lines: 2, pill: false, render: function (d) { return plain(d.title); } },
        { title: 'Status', field: 'status', kind: 'center', width: 176, pill: false, render: statusBadge },
      ],
      detailTitle: function (d) { return d.id; },
      detail: function (d) {
        return h(Detail, null,
          h(P.Heading, { level: 2, size: 4 }, plain(d.title).replace(URL, '').replace(/[\s:]+$/, '')),
          h(Facts, null,
            h(Field, { label: 'Status' }, statusBadge(d)),
            (plain(d.title).match(URL) || []).map(function (u) { return h(Field, { key: u, label: 'Link' }, link(u, 'Open the link')); }),
            d.context ? h(Field, { label: 'Context' }, plain(d.context)) : null,
            h(Field, { label: 'On GitHub' }, link(d.url, '#' + d.issue))),
          d.applied ? h(P.Banner, { tone: 'info', title: 'Applied for now: ' + d.applied }, 'The team went ahead with the recommended option so work did not stop. Pick another option to change it.') : null,
          h(AnswerForm, { d: d, key: d.id, onAnswered: onAnswered }));
      },
    },
    {
      id: 'todo', label: 'To do', icon: 'checklist', title: 'Team to-do', noun: ['issue', 'issues'], rows: tasks, index: 'number',
      description: 'The team’s open issues, in the Product Lead’s order, then by severity.',
      text: function (t) { return '#' + t.number + ' ' + t.title + ' ' + t.owners.join(' '); },
      columns: [
        { title: 'Order', field: 'rank', type: 'number', width: 72, pill: false },
        { title: 'Issue', field: 'title', kind: 'name', lines: 2, pill: false, render: function (t) { return '#' + t.number + ' ' + t.title; } },
        { title: 'Severity', field: 'sev', kind: 'center', width: 88, pill: false, filter: 'list', render: sevBadge },
        { title: 'Updated', field: 'updated', type: 'date', width: 136 },
      ],
      detailTitle: function (t) { return '#' + t.number; },
      detail: function (t) {
        return h(Detail, null,
          h(P.Heading, { level: 2, size: 4 }, t.title),
          h(Facts, null,
            h(Field, { label: 'Severity' }, sevBadge(t)),
            ownerIssues[t.number] ? h(Field, { label: 'Your decision' }, h(P.Badge, { tone: 'action-required', icon: 'flag', size: 'sm' }, ownerIssues[t.number].id)) : null,
            h(Field, { label: 'Next step' }, t.next),
            h(Field, { label: 'Owner' }, t.owners.length ? t.owners.map(role).join(', ') : 'Not assigned'),
            t.areas.length ? h(Field, { label: 'Area' }, t.areas.join(', ')) : null,
            t.type ? h(Field, { label: 'Kind' }, t.type) : null,
            h(Field, { label: 'Last updated', data: true }, fmt(t.updated)),
            h(Field, { label: 'On GitHub' }, link(t.url, '#' + t.number))));
      },
    },
    {
      id: 'decisions', label: 'Decisions', icon: 'article', title: 'Decisions', noun: ['decision', 'decisions'], rows: decisionRows, sort: [{ field: 'date', dir: 'desc' }],
      description: 'Every recorded decision, newest first, with the check that enforces it on main.',
      text: function (d) { return d.id + ' ' + d.decision + ' ' + (d.area || ''); },
      columns: [
        { title: 'Id', field: 'id', kind: 'data', width: 88 },
        { title: 'Decision', field: 'decision', kind: 'name', lines: 2, overflow: 'dialog', pill: false },
        { title: 'Date', field: 'date', type: 'date', width: 152 },
        { title: 'Status', field: 'status', kind: 'center', width: 136, pill: false, filter: 'list', render: decisionStatus },
        { title: 'Check', field: 'state', kind: 'center', width: 136, pill: false, filter: 'list', render: function (d) { return stateBadge(d.state); } },
      ],
      detailTitle: function (d) { return d.id; },
      detail: function (d) {
        return h(Detail, null,
          h(P.Text, null, d.decision),
          d.owner ? h(P.Banner, { tone: 'success', title: 'Your answer: ' + d.owner.answer.choice },
            d.owner.answer.text, ' ', link(d.owner.answer.url, 'See it on #' + d.owner.issue), '.') : null,
          h(Facts, null,
            h(Field, { label: 'Status' }, decisionStatus(d)),
            d.superseded_by ? h(Field, { label: 'Replaced by' }, d.superseded_by) : null,
            h(Field, { label: 'Decided by' }, (d.by === 'owner' ? 'Owner' : role(String(d.by).replace('agent:ctm3-', ''))) + ', ' + d.date),
            h(Field, { label: 'Area' }, d.area || '—'),
            h(Field, { label: d.kind === 'review only' ? 'No check yet' : 'Check (' + d.kind + ')' },
              h(P.Stack, { gap: 'xs' }, d.url ? link(d.url, stateBadge(d.state)) : stateBadge(d.state), h(P.Text, { variant: 'secondary' }, d.check)))));
      },
    },
    {
      id: 'done', label: 'Done', icon: 'task_alt', title: 'Done in the last 3 days', noun: ['item', 'items'], rows: doneRows,
      description: 'Merged pull requests and closed issues.',
      text: function (x) { return '#' + x.number + ' ' + x.title; },
      columns: [
        { title: 'What', field: 'title', kind: 'name', lines: 2, pill: false, render: function (x) { return '#' + x.number + ' ' + x.title; } },
        { title: 'Kind', field: 'kind', filter: 'list', width: 144 },
        { title: 'When', field: 'at', type: 'date', width: 136 },
      ],
      detailTitle: function (x) { return '#' + x.number; },
      detail: function (x) {
        return h(Detail, null,
          h(P.Heading, { level: 2, size: 4 }, x.title),
          h(Facts, null,
            h(Field, { label: 'Kind' }, x.kind),
            h(Field, { label: 'When', data: true }, fmt(x.at)),
            h(Field, { label: 'On GitHub' }, link(x.url, '#' + x.number))));
      },
    },
    {
      id: 'checks', label: 'Checks', icon: 'fact_check', title: 'Latest check runs on main', noun: ['workflow', 'workflows'], rows: D.workflows, index: 'file',
      description: 'The newest run of each workflow on main.',
      text: function (w) { return w.name + ' ' + w.file; },
      columns: [
        { title: 'Workflow', field: 'name', kind: 'name' },
        { title: 'Result', field: 'conclusion', kind: 'center', width: 144, pill: false, filter: 'list', render: function (w) { return stateBadge(w.conclusion); } },
        { title: 'When', field: 'at', type: 'date', width: 136 },
      ],
      detailTitle: function (w) { return w.name; },
      detail: function (w) {
        return h(Facts, null,
          h(Field, { label: 'Result' }, w.url ? link(w.url, stateBadge(w.conclusion)) : stateBadge(w.conclusion)),
          h(Field, { label: 'File', data: true }, w.file),
          h(Field, { label: 'When', data: true }, fmt(w.at)));
      },
    },
    {
      id: 'team', label: 'Team', icon: 'groups', title: 'Team', noun: ['role', 'roles'], rows: teamRows,
      description: 'Open issues per role.',
      text: function (r) { return r.agent; },
      columns: [
        { title: 'Role', field: 'agent', kind: 'name' },
        { title: 'Open items', field: 'count', type: 'number', width: 120, pill: false },
      ],
      detailTitle: function (r) { return r.agent; },
      detail: function (r) {
        return h(P.Stack, { gap: 'sm' }, r.items.map(function (t) {
          return h(P.Inline, { key: t.number, gap: 'sm' }, sevBadge(t), link(t.url, '#' + t.number + ' ' + t.title));
        }));
      },
    },
    {
      id: 'screenshots', label: 'Screenshots', icon: 'image', title: 'Latest CI screenshots', noun: ['screenshot', 'screenshots'], rows: D.shots, index: 'file',
      description: 'From the ci-screenshots branch. Synthetic data only.',
      text: function (x) { return x.name + ' ' + x.run; },
      columns: [
        { title: 'Screenshot', field: 'name', kind: 'name' },
        { title: 'Run', field: 'run', kind: 'data', width: 200 },
      ],
      detailTitle: function (x) { return x.name; },
      detail: function (x) {
        return h(Detail, null,
          h('img', { src: x.file, alt: x.name, className: 'shot' }),
          h(Facts, null, h(Field, { label: 'Run', data: true }, x.run), h(Field, { label: 'File' }, link(x.url, x.name))));
      },
    },
  ];
  return SECTIONS;
  }

  var SECTION_IDS = ['overview', 'owner', 'todo', 'decisions', 'done', 'checks', 'team', 'screenshots'];
  function fromHash() {
    var id = (location.hash || '').replace('#', '');
    return SECTION_IDS.indexOf(id) >= 0 ? id : 'overview';
  }

  // Answers sent from this browser, kept until the rebuilt data.json carries them (about a minute).
  var LOCAL_ANSWERS = 'ctm3-dashboard-answers';
  function readLocal() { try { return JSON.parse(localStorage.getItem(LOCAL_ANSWERS) || '{}'); } catch (e) { return {}; } }
  function writeLocal(v) { try { localStorage.setItem(LOCAL_ANSWERS, JSON.stringify(v)); } catch (e) { /* storage blocked */ } }
  function pending(local, data) {
    var left = {}, known = {};
    (data.ownerDecisions || []).forEach(function (d) { if (d.answer) known[d.id] = true; });
    Object.keys(local).forEach(function (id) {
      var age = Date.now() - Date.parse(local[id].at || 0);
      if (!known[id] && age < 24 * 3600 * 1000) left[id] = local[id];
    });
    return left;
  }

  // One section on the SplitWorkspace template (owner, 2026-11-10: the menu on the left, then the split screen
  // with the DataGrid and the chosen row's details beside it). The title row and the command bar sit above both
  // panes; the bar's search, filters, sort and columns share one useCollectionView state with the grid.
  function Section(props) {
    var sec = props.sec, key = sec.index || 'id';
    var fields = sec.columns.map(function (c) {
      return { value: c.field, label: c.title, kind: c.type, get: function (r) { var v = r[c.field]; return v && typeof v === 'object' ? v.label || v.name : v; } };
    });
    var view = P.useCollectionView(fields, { text: sec.text, data: sec.rows, sort: sec.sort });
    var shown = view.count(sec.rows);
    var record = props.openKey == null ? null : sec.rows.filter(function (r) { return r[key] === props.openKey; })[0];
    var bar = h(P.CommandBar, {
      label: sec.title,
      find: h(R.Fragment, null,
        h(P.CommandBarSearch, Object.assign({}, view.searchProps, { placeholder: 'Search ' + sec.noun[1] })),
        h(P.FilterPanel, view.filterProps)),
      view: h(R.Fragment, null, h(P.SortPanel, view.sortProps), h(P.ColumnsMenu, view.columnsProps)),
      count: shown + ' ' + sec.noun[shown === 1 ? 0 : 1],
    });
    return h(P.SplitWorkspace, {
      sideNav: props.nav,
      paneTitle: sec.title,
      defaultSize: 760, // the grid's starting width: most of the room goes to the list; the divider still moves
      title: record ? sec.detailTitle(record) : sec.title,
      toolbar: h(P.Stack, { gap: 'md' },
        h(P.RecordPage.Header, { title: sec.title, description: sec.description }),
        sec.toolbar || null, bar),
      rows: sec.rows, columns: sec.columns,
      grid: Object.assign({
        index: key, density: 'compact', cells: 'pill', headerMenu: true, mode: 'fill', wrapHeaders: false,
        empty: 'Nothing in ' + sec.label + ' right now.',
        openKey: record ? props.openKey : null,
        onRowClick: function (r) { props.onOpen(r[key]); },
      }, view.tableProps),
      detailOpen: !!record,
      actions: record ? h(P.Button, { variant: 'subtle', size: 'sm', onClick: function () { props.onOpen(null); } }, 'Close') : null,
      empty: h(P.EmptyState, { title: 'Nothing selected' }, 'Choose a row to see its details here.'),
    }, record ? sec.detail(record) : null);
  }

  function App() {
    var st = R.useState(fromHash()), current = st[0], setCurrent = st[1];
    var op = R.useState({}), open = op[0], setOpen = op[1];
    var ds = R.useState(window.CTM_DATA), data = ds[0], setData = ds[1];
    var lsx = R.useState(function () { return pending(readLocal(), window.CTM_DATA); }), local = lsx[0], setLocal = lsx[1];
    var ps = R.useState(null), posted = ps[0], setPosted = ps[1];
    R.useEffect(function () { writeLocal(local); }, [local]);
    // Pick up each rebuild of the page's data without a reload: every 30 seconds, and when the tab comes back.
    R.useEffect(function () {
      var stamp = window.CTM_DATA.generatedAt;
      function check() {
        fetch('data.json?t=' + Date.now(), { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : null; }).then(function (next) {
          if (next && next.generatedAt !== stamp) {
            stamp = next.generatedAt;
            setData(next);
            setLocal(function (l) { return pending(l, next); });
          }
        }, function () { /* offline or not built yet: keep what is shown */ });
      }
      var timer = setInterval(check, 30000);
      function onVisible() { if (document.visibilityState === 'visible') check(); }
      document.addEventListener('visibilitychange', onVisible);
      return function () { clearInterval(timer); document.removeEventListener('visibilitychange', onVisible); };
    }, []);
    function openRow(id, value) { setOpen(function (o) { var n = Object.assign({}, o); n[id] = value; return n; }); }
    function onAnswered(id, answer) {
      setLocal(function (l) { var n = Object.assign({}, l); n[id] = answer; return n; });
      setPosted({ id: id, url: answer.url });
      openRow('owner', null);
    }
    var SECTIONS = R.useMemo(function () { return derive(data, local, onAnswered, posted); }, [data, local, posted]);
    R.useEffect(function () {
      function onHash() { setCurrent(fromHash()); }
      window.addEventListener('hashchange', onHash);
      return function () { window.removeEventListener('hashchange', onHash); };
    }, []);
    var sec = SECTIONS.filter(function (x) { return x.id === current; })[0];

    var nav = h(P.NavPane, {
      label: 'Dashboard sections', title: 'CTM 3.0 Dashboard',
      footer: h(P.Text, { variant: 'secondary' }, 'Updated ' + fmt(data.generatedAt) + ' · main ' + data.mainSha),
    }, h(P.NavList, {
      label: 'Sections', value: current,
      onSelect: function (id) { location.hash = id; setCurrent(id); },
      items: SECTIONS.map(function (x) { return { id: x.id, label: x.label, icon: x.icon, count: x.id === 'overview' ? undefined : x.rows.length }; }),
    }));

    return h(Section, { key: sec.id, sec: sec, nav: nav, openKey: open[sec.id] != null ? open[sec.id] : null,
      onOpen: function (value) { openRow(sec.id, value); } });
  }

  window.ReactDOM.createRoot(document.getElementById('root')).render(h(App));
})();

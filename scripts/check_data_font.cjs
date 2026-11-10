#!/usr/bin/env node
// The data font rule (owner, 2026-11-10, #325): case numbers, IDs, dates, times, amounts and counts are shown in
// Plenix's data font (Reddit Mono); names and words never are. Plenix marks data in three documented ways:
//   - DataGrid / Table column: kind "data", or a typed column (type number | currency | date | bytes)   data-grid.md
//   - PropertyList.Item data                                                                            property-list.md
//   - Text variant="data"                                                                               text.md
// (Metric-style tiles built by CTM take data: true, the same flag.)
// This check reads the CTM screens and flags a known data field drawn without the marking, and a name drawn with it.
// A reviewed exception carries `ctm-data-font-allow` on its line.
// Run: node scripts/check_data_font.cjs [files...]   (default: static/ctm/*.js)
const fs = require('fs');
const path = require('path');

// A value expression that is a data value: the CTM formatters, case numbers, references, versions and counts.
const DATA_VALUE = /^(?:new Intl\.(?:DateTimeFormat|NumberFormat)\(|(?:base\.|window\.CTMCouncil\.)?(?:formatWhen|formatDate|formatTime|formatBytes|formatDuration|money|n|number\.format)\(|String\([\w.?]*(?:count|Count|length|version|number)\b|[\w.?]+\.(?:case_number|reference|version|byte_count|duration_ms|timestamp|[a-z]+_at|id)\b(?!\s*\()|(?:reference|caseNumber|case_number)\b)/;
// Grid fields that hold data values (row fields of the CTM lists, raw and formatted).
const DATA_FIELD = /^(?:case_number|number|hearing_number|reference|code|case_code|version|timestamp|date|dateReceived|closedAt|[a-z_]*_at|[a-z_]*_time|[a-z_]*_date|[a-z_]*_count|submitted|filed|answered|occurred|recorded|amount|amount_minor|fee_amount|byte_count|size|duration|duration_ms)$/;
const DATA_TYPES = /type:\s*"(?:number|currency|date|bytes)"/;
const DATA_KIND = /kind:\s*(?:"data"|\[[^\]]*"data"[^\]]*\])/;
// Fields and values that are names or words.
const NAME_FIELD = /^(?:applicant|respondent|manager|member|actor|author|sender|person|spouses|parties|name|[a-z_]*_name|[a-z_]*_by|completedBy|assigned_to)$/;
const NAME_VALUE = /^[\w.?]+\.(?:actor|author|applicant_name|respondent_name|party_name|member_name|sender|full_name)\b/;

// The text of one balanced call argument list starting at the "(" at index open.
function balanced(text, open) {
  let depth = 0, quote = null;
  for (let i = open; i < text.length; i++) {
    const c = text[i];
    if (quote) { if (c === '\\') i++; else if (c === quote) quote = null; continue; }
    if (c === '"' || c === "'" || c === '`') quote = c;
    else if (c === '(' || c === '{' || c === '[') depth++;
    else if (c === ')' || c === '}' || c === ']') { depth--; if (depth === 0) return text.slice(open, i + 1); }
  }
  return text.slice(open);
}

// Splits a call's argument list into its top-level arguments.
function args(call) {
  const inner = call.slice(1, -1), out = [];
  let depth = 0, quote = null, start = 0;
  for (let i = 0; i < inner.length; i++) {
    const c = inner[i];
    if (quote) { if (c === '\\') i++; else if (c === quote) quote = null; continue; }
    if (c === '"' || c === "'" || c === '`') quote = c;
    else if ('({['.includes(c)) depth++;
    else if (')}]'.includes(c)) depth--;
    else if (c === ',' && depth === 0) { out.push(inner.slice(start, i).trim()); start = i + 1; }
  }
  out.push(inner.slice(start).trim());
  return out;
}

// The value a child expression shows: `cond ? value : other` and `value || fallback` show value.
function shown(expr) {
  let e = expr.trim();
  const ternary = e.match(/^[^?]*?\?\s*([\s\S]+?)\s*:\s*[\s\S]+$/);
  if (ternary && !/^h\(/.test(e)) e = ternary[1];
  return e.replace(/^\(+/, '');
}

function findDataFontProblems(source, file = 'source') {
  const problems = [];
  const lines = source.split(/\r?\n/);
  const lineOf = (index) => source.slice(0, index).split(/\n/).length;
  const allowed = (index) => /ctm-data-font-allow/.test(lines[lineOf(index) - 1] || '');
  const report = (index, message) => { if (!allowed(index)) problems.push(`${file}:${lineOf(index)}: ${message}`); };

  // 1. PropertyList.Item and Text: a data value needs the data marking; a name never has it.
  for (const m of source.matchAll(/h\(\s*P\.(PropertyList\.Item|Text)\s*,/g)) {
    const call = balanced(source, m.index + 1);
    const [, props = '', ...children] = args(call);
    const component = m[1];
    const marked = component === 'Text' ? /variant:\s*"data"/.test(props) : /\bdata:\s*true\b/.test(props);
    const values = children.map(shown);
    if (!marked && values.some((v) => DATA_VALUE.test(v))) {
      report(m.index, `${component === 'Text' ? 'P.Text' : 'P.PropertyList.Item'} shows a data value without ${component === 'Text' ? 'variant: "data"' : 'data: true'}: ${values.find((v) => DATA_VALUE.test(v)).slice(0, 60)}`);
    }
    if (marked && values.length && values.every((v) => NAME_VALUE.test(v))) {
      report(m.index, `${component === 'Text' ? 'P.Text' : 'P.PropertyList.Item'} shows a name in the data font: ${values[0].slice(0, 60)}`);
    }
  }

  // 1b. A data value isolated left to right (h("bdi", { dir: "ltr" }, value)) sits inside a data Text.
  for (const m of source.matchAll(/h\(\s*["']bdi["']\s*,/g)) {
    const call = balanced(source, m.index + 1);
    const [, props = '', ...children] = args(call);
    if (!/dir:\s*["']ltr["']/.test(props) || !children.map(shown).some((v) => DATA_VALUE.test(v))) continue;
    const before = source.slice(Math.max(0, m.index - 40), m.index);
    if (!/variant:\s*["']data["']\s*\}\s*,\s*$/.test(before) && !/\bdata:\s*true\s*\}\s*,\s*$/.test(before)) {
      report(m.index, `a data value isolated with <bdi> outside a data Text: ${children.map(shown).find((v) => DATA_VALUE.test(v)).slice(0, 60)}`);
    }
  }

  // 1c. A list row's meta (resource-list.md: "wrap technical values in <Text variant=\"data\">").
  for (const m of source.matchAll(/\bmeta:\s*/g)) {
    const rest = source.slice(m.index + m[0].length, m.index + m[0].length + 200);
    const value = shown(rest.startsWith('`') ? rest.slice(1).replace(/^\$\{/, '') : rest);
    if (DATA_VALUE.test(value)) report(m.index, `meta shows a data value as plain text: ${value.slice(0, 50)}`);
  }

  // 2. Grid columns: a data field needs kind "data" or a data type; a name field never has kind "data".
  for (const m of source.matchAll(/\{\s*title:\s*/g)) {
    const object = balanced(source, m.index);
    const field = (object.match(/^\{\s*title:[^]*?\bfield:\s*"(\w+)"/) || [])[1];
    if (!field) continue;
    const own = object.replace(/(render|pill|sorter|editable|validate)\s*:[^]*$/, '');
    const marked = DATA_KIND.test(own) || DATA_TYPES.test(own) || /\bpill:\s*\(/.test(object);
    if (DATA_FIELD.test(field) && !marked) report(m.index, `column "${field}" is a data value without kind: "data" or a data type`);
    if (NAME_FIELD.test(field) && DATA_KIND.test(own)) report(m.index, `column "${field}" is a name with kind: "data"`);
  }

  // 3. CTM tiles and metrics ({ icon, label, value: String(count) }): the count needs data: true.
  for (const m of source.matchAll(/\{\s*icon:\s*[^{}]*?\bvalue:\s*/g)) {
    const object = balanced(source, m.index);
    const value = shown((object.match(/\bvalue:\s*([^,}]+)/) || [])[1] || '');
    if (DATA_VALUE.test(value) && !/\bdata:\s*true\b/.test(object)) report(m.index, `tile value ${value.slice(0, 40)} without data: true`);
  }
  return problems;
}

module.exports = { findDataFontProblems, DATA_FIELD, NAME_FIELD };

if (require.main === module) {
  const root = path.resolve(__dirname, '..');
  const dir = path.join(root, 'static', 'ctm');
  const files = process.argv.slice(2).length ? process.argv.slice(2)
    : fs.readdirSync(dir).filter((f) => f.endsWith('.js')).map((f) => path.join(dir, f));
  const problems = files.flatMap((f) => findDataFontProblems(fs.readFileSync(f, 'utf8'), path.relative(root, path.resolve(f)).replace(/\\/g, '/')));
  if (problems.length) {
    console.log(`CTM data font: ${problems.length} problem(s)`);
    for (const p of problems) console.log(`  - ${p}`);
    process.exit(1);
  }
  console.log('CTM data font: OK');
}

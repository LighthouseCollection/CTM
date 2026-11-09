/* CTMShell: the shared collection foundation on the Plenix 0.86.0 page templates (#97 slice 1, D-0034).
 *
 * Every CTM list goes through these three components. Names and props of the earlier API are unchanged;
 * everything listed under "new" is optional, so existing callers keep working as they are.
 *
 * CTMShell.Table — one DataGrid (docs: data-grid.md).
 *   label, rows, columns, selected, onSelect, empty, className, isStatic  (unchanged)
 *   new:
 *   rowMenu     [{ label, icon, onSelect(row), danger, disabled, separator }] or (row) => that list: the row's
 *               menu (its button at the row end, or right-click). Button columns (field "open_action"/"actions",
 *               kind "actions") keep working beside it, so callers can move to the menu one table at a time.
 *   narrow      "auto" (default now: a table while the columns fit, else the row cards) | "table" (the old fixed
 *               table, the escape hatch for a dense specialist grid) | "list". Unset, a grid that still has a
 *               button column (kind "actions" or a field named actions / *_action(s)) stays "table", because
 *               0.86.0 cannot measure buttons and would cut them off; move them to rowMenu to get the row cards.
 *   typeIcons   the column type icon before each header title (default now: true)
 *   loading     true: the Plenix spinner with the grid's name, after about a second (D-0064, no skeletons)
 *   openKey     the open row (aria-current); default: selected
 *   template, layout, keyColumns   the row card slots (data-grid.md "Row cards")
 *   cardCount   the plural count over the row cards, e.g. { one: "{n} case", other: "{n} cases" } (EN/AR from callers)
 *   grid        more documented DataGrid props, passed as given (mode, pageSize, selectable, onSelectionChange,
 *               storageKey, strings, unread, …); they win over the defaults above
 *
 * CTMShell.Workspace — the list and the chosen item side by side: the SplitWorkspace template
 * (listing-page.md "SplitWorkspace", master-detail-workspace.md).
 *   label, rows, columns, children, empty, selectionPrompt, selected, onSelect, showDetailWhenEmpty,
 *   orientation, toolbar  (unchanged; toolbar is any node above both panes)
 *   new: actions (the reading pane's actions row, shown while an item is open), commandBar, search, and the
 *   Table props above (rowMenu, narrow, typeIcons, loading, template, layout, keyColumns, cardCount, grid).
 *
 * CTMShell.Listing — a full-room list: the ListingPage template (listing-page.md "ListingPage").
 *   label, rows, columns, empty, className, onOpen(row), toolbar, commandBar, search, and the Table props above.
 *
 * Shared new props of Workspace and Listing:
 *   commandBar  CommandBar props (command-bar.md): { actions, quickFilters, count, status, end, selection,
 *               strings, … }; label defaults to the list's label. Drawn above the list (and the detail).
 *   search      { text(row) => string, placeholder, filters, quick, storageKey, sort }: a CommandBarSearch (and
 *               a FilterPanel when filters is true) on one useCollectionView state with the grid
 *               (use-collection-view.md). placeholder and every visible word come from the caller (EN/AR).
 *
 * Why the template bodies and not <SplitWorkspace>/<ListingPage> themselves: in 0.86.0 both render their own
 * AppShell (a 100dvh frame with a second <main> and skip link). CTM already sits inside one AppShell (app.js),
 * so CTMShell draws the same parts the templates draw inside it: toolbar, then SplitView(DataGrid,
 * ReadingPane with an EmptyState), or toolbar then the full-room DataGrid. Request: plenix-requests.md PLX-012.
 */
(() => {
  const R = window.React, P = window.Plenix, h = R.createElement;

  // Keeps domain fields intact for callbacks; scalar and person cells are projected into native pill fields.
  // cache (optional, { records: WeakMap, last }): reuses the projected copy of a record while its values are
  // unchanged, and the previous data array while its rows are unchanged, because the 0.86.0 grid does not
  // re-apply a changed filter (useCollectionView search) when its data array is new (plenix-requests PLX-013).
  function project(rows, columns, cache) {
    let gridRows = rows || [];
    const gridColumns = (columns || []).map((column, index) => {
      const render = column.render;
      const isAction = column.kind === "actions" || /^(open_action|actions?)$/.test(column.field);
      const type = column.type || (/^(applicant|respondent|manager|.*_name)$/.test(column.field) ? "person"
        : /^(.*_count|count|total|position|married_years)$/.test(column.field) ? "number" : "text");
      const values = render && !isAction ? gridRows.map(record => render(record)) : null;
      const scalar = values && values.every(value => value == null || ["string", "number", "boolean"].includes(typeof value));
      const native = !isAction && (scalar || (!render && type === "person"));
      let projected = {};
      if (native) {
        const field = "__ctm_display_" + index;
        gridRows = gridRows.map((record, rowIndex) => {
          let value = scalar ? values[rowIndex] : record[column.field];
          if (type === "person") {
            const person = value && typeof value === "object" ? value : null;
            const raw = person?.gender || record[column.field + "_gender"];
            value = { name: person ? person.name || "—" : value || "—",
              gender: raw === "M" || raw === "male" ? "male" : raw === "F" || raw === "female" ? "female" : undefined };
          }
          return { ...record, [field]: value };
        });
        projected = { field, render: undefined, pill: column.pill === false ? false : column.pill,
          sorter: (a, b, left, right, _field, direction) => {
            const rawA = left[column.field], rawB = right[column.field];
            if (typeof column.sorter === "function") return column.sorter(rawA, rawB, left, right, column.field, direction);
            if (type === "number" || column.sorter === "number") return Number(rawA ?? 0) - Number(rawB ?? 0);
            if (type === "date" || column.sorter === "date") {
              const dateA = Date.parse(rawA), dateB = Date.parse(rawB);
              return (Number.isNaN(dateA) ? 0 : dateA) - (Number.isNaN(dateB) ? 0 : dateB);
            }
            const text = value => value && typeof value === "object" ? value.name || value.label || "" : String(value ?? "");
            return new Intl.Collator(undefined, { numeric: true }).compare(text(rawA), text(rawB));
          } };
      }
      return {
        ...column, type, ...projected,
        ...(isAction ? { kind: "center", maxWidth: column.maxWidth || "--plx-ref-size-240px", sortable: false, groupable: false,
          // #111: the fixed table draws a button column without a width at its cap; use the width the caller asks for.
          ...(column.width || column.minWidth ? { width: column.width || column.minWidth } : {}) } : {}),
        ...(/^(status|state)$/.test(column.field) ? { maxWidth: column.maxWidth || "--plx-ref-size-240px" } : {}),
        // Case numbers and codes are data values that read left to right in Arabic too (#97 slice 8): kind "data"
        // (data-grid.md) gives the pill an auto direction that resolves to LTR for DEMO-NEW-09 and 20261020-04.
        // The undocumented kind "id" is dropped everywhere: on Arabic pages it laid the segments out right to
        // left (09-NEW-DEMO, 04-20261020) and changed the digits.
        ...(/^(number|case_number|case_code|code)$/.test(column.field) ? { kind: "data" }
          : [].concat(column.kind || []).includes("id") ? { kind: [].concat(column.kind).filter(k => k !== "id") } : {}),
        ...(render && !native ? { pill: false, render } : {}),
        // Plenix 0.70.0 renamed the column option headerSort to sortable (no alias).
        sortable: !isAction && column.sortable !== false && column.headerSort !== false,
        resizable: column.resizable !== false,
      };
    });
    if (cache && gridRows !== rows) gridRows = gridRows.map((row, i) => {
      const source = rows[i], old = source && typeof source === "object" ? cache.records.get(source) : undefined;
      const same = (a, b) => Object.is(a, b) || (a && b && typeof a === "object" && typeof b === "object" && a.name === b.name && a.gender === b.gender);
      if (old && Object.keys(row).length === Object.keys(old).length && Object.keys(row).every((k) => same(row[k], old[k]))) return old;
      if (source && typeof source === "object") cache.records.set(source, row);
      return row;
    });
    if (cache) {
      const last = cache.last;
      if (last && last.length === gridRows.length && gridRows.every((row, i) => row === last[i])) gridRows = last;
      cache.last = gridRows;
    }
    return { gridRows, gridColumns };
  }

  // A column of row buttons (Open, Edit, Delete): the actions column kinds and fields named *_action(s).
  const buttonColumn = (column) => column.kind === "actions" || /(^|_)actions?$/.test(column.field || "");

  // D-0064 (issue 272, owner): no skeleton or shimmer placeholders. A region that loads is announced as busy at once
  // and shows the Plenix Spinner with a label naming what loads, centred, only after about a second (a quick load
  // shows nothing). Plenix is asked to make this its default (pds issue 1032).
  function DelayedSpinner({ label, className, delay = 1000 }) {
    const [shown, setShown] = window.React.useState(false);
    window.React.useEffect(() => {
      const timer = window.setTimeout(() => setShown(true), delay);
      return () => window.clearTimeout(timer);
    }, [delay]);
    return h(P.Stack, { align: "center", justify: "center", className: className || "plx-u-flex-1", role: "status", "aria-busy": "true", "aria-label": label },
      // The Spinner names itself for screen readers; the same words show under it (aria-hidden, so they are read once).
      shown ? h(P.Stack, { gap: "sm", align: "center" }, h(P.Spinner, { size: "md", label }), h(P.Text, { variant: "secondary", "aria-hidden": "true" }, label)) : null);
  }

  function Loading({ label, className }) {
    return h(DelayedSpinner, { label, className });
  }

  function Table({ label, rows, columns, selected, onSelect, empty, className, isStatic = true,
    rowMenu, narrow, typeIcons = true, loading = false, openKey, template, layout, keyColumns, cardCount,
    grid, projected }) {
    // Every CTM collection keeps native grid controls, including read-only records (isStatic is kept for
    // callers; read-only data must not disable column resizing, sorting or header menus).
    if (loading) return h(Loading, { label, className });
    const { gridRows, gridColumns } = projected || project(rows, columns);
    // 0.86.0 sizes "auto" columns from their measured text; a column of row buttons has no text to measure, so
    // the title takes its room and the buttons are cut off. Such grids keep the fixed table until their
    // buttons move to rowMenu (then they get the row cards); an explicit narrow always wins.
    const layoutMode = narrow || ((columns || []).some(buttonColumn) ? "table" : "auto");
    const open = openKey !== undefined ? openKey : selected === undefined ? undefined : selected ?? null;
    return h(P.DataGrid, {
      label, data: gridRows, columns: gridColumns, index: "id", className,
      density: "compact", cells: "pill", typeIcons, wrapHeaders: false,
      narrow: layoutMode, empty, mode: "fill", headerMenu: true,
      rowMenu, rowMenuButton: !!rowMenu,
      ...(open !== undefined ? { openKey: open } : {}),
      ...(template ? { template } : {}), ...(layout ? { layout } : {}), ...(keyColumns ? { keyColumns } : {}),
      ...(cardCount ? { strings: { cardCount } } : {}),
      selected: selected ? [selected] : [],
      onRowClick: onSelect ? (row) => onSelect(row.id) : undefined,
      ...grid,
    });
  }

  const tableProps = ({ rowMenu, narrow, typeIcons, loading, openKey, template, layout, keyColumns, cardCount, grid }) =>
    ({ rowMenu, narrow, typeIcons, loading, openKey, template, layout, keyColumns, cardCount, grid });

  // The command bar above a collection: the caller's commands, and the search and filters on one
  // useCollectionView state with the grid. Rendered only when a search is asked for, so the hook always runs.
  function SearchedCollection({ label, search, commandBar, rows, columns, render }) {
    const cache = R.useRef(null);
    if (!cache.current) cache.current = { records: new WeakMap(), last: null };
    const projected = project(rows, columns, cache.current);
    const fields = projected.gridColumns.map(column => ({
      value: column.field, label: column.title, kind: column.type, groupable: column.groupable,
      get: row => { const value = row[column.field]; return value && typeof value === "object" ? value.name ?? value.label : value; },
    }));
    const view = P.useCollectionView(fields, {
      text: search.text, quick: search.quick, storageKey: search.storageKey, sort: search.sort, data: projected.gridRows,
    });
    const bar = h(P.CommandBar, {
      label,
      ...commandBar,
      find: h(R.Fragment, null,
        h(P.CommandBarSearch, { ...view.searchProps, placeholder: search.placeholder }),
        search.filters ? h(P.FilterPanel, view.filterProps) : null,
        commandBar?.find || null),
    });
    return render(bar, { projected, grid: view.tableProps });
  }

  function collection({ label, search, commandBar, toolbar, rows, columns }, draw) {
    if (search) return h(SearchedCollection, { label, search, commandBar, rows, columns,
      render: (bar, extra) => draw(toolbar ? h(R.Fragment, null, toolbar, bar) : bar, extra) });
    const bar = toolbar || (commandBar ? h(P.CommandBar, { label, ...commandBar }) : null);
    return draw(bar, {});
  }

  function Workspace(props) {
    const { label, rows: allRows, columns, children, empty, selectionPrompt, selected, onSelect, showDetailWhenEmpty = false,
      orientation = "side-by-side", toolbar = null, actions = null } = props;
    const rows = allRows || [];
    const [own, select] = R.useState(null);
    const id = selected === undefined ? own : selected;
    const chosen = rows.find((row) => row.id === id);
    const emptyDetail = rows.length
      ? selectionPrompt || (document.documentElement.lang === "ar" ? "اختر عنصرًا" : "Select an item")
      : empty || label;
    const showing = !!chosen || showDetailWhenEmpty;
    return collection({ ...props, toolbar, rows }, (bar, extra) => h(P.Stack, { gap: "md", className: "plx-u-flex-1 plx-u-min-h-0" },
      bar,
      h(P.SplitView, {
        label, firstLabel: label, orientation, defaultSize: orientation === "stacked" ? 320 : undefined,
        first: h(Table, { ...tableProps(props), label, rows, columns, selected: id, onSelect: onSelect || select, empty,
          projected: extra.projected, grid: extra.grid ? { ...extra.grid, ...props.grid } : props.grid }),
        second: h(P.ReadingPane, { label: chosen?.title || chosen?.name || label, actions: showing ? actions : null,
          empty: h(P.EmptyState, { title: emptyDetail }) },
          showing ? (typeof children === "function" ? children(chosen) : children) : null),
      }),
    ));
  }

  function Listing(props) {
    const { label, rows, columns, empty, className, onOpen, selected } = props;
    return collection(props, (bar, extra) => h(P.Stack, { gap: "md", className: "plx-u-flex-1 plx-u-min-h-0" },
      bar,
      h(Table, { ...tableProps(props), label, rows, columns, empty, className, selected,
        onSelect: onOpen ? (rowId) => onOpen((rows || []).find((row) => row.id === rowId)) : undefined,
        projected: extra.projected, grid: extra.grid ? { ...extra.grid, ...props.grid } : props.grid }),
    ));
  }

  window.CTMShell = Object.freeze({ Table, Workspace, Listing, DelayedSpinner });
})();

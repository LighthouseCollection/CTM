/* Shared integration of the documented Plenix table and split-view components. */
(() => {
  const R = window.React, P = window.Plenix, h = R.createElement;
  function Table({ label, rows, columns, selected, onSelect, empty, className, isStatic = true }) {
    // Every CTM collection keeps native grid controls, including read-only records.
    // Read-only data must not disable column resizing, sorting or header menus.
    const gridColumns = (columns || []).map((column) => {
      const render = column.render;
      const isAction = column.kind === "actions" || /^(open_action|actions?)$/.test(column.field);
      const type = column.type || (/^(applicant|respondent|manager|.*_name)$/.test(column.field) ? "person"
        : /^(.*_count|count|total|position|married_years)$/.test(column.field) ? "number" : "text");
      const personRender = (record, value) => {
        const person = value && typeof value === "object" ? value : null;
        const rawGender = person?.gender || record[column.field + "_gender"];
        const gender = rawGender === "M" || rawGender === "male" ? "male" : rawGender === "F" || rawGender === "female" ? "female" : undefined;
        return h(P.DataPill, { size: "md", ...(gender ? { gender } : { person: true }) }, person ? person.name || "—" : value || "—");
      };
      return {
        ...column, type,
        ...(type === "person" && !render ? { pill: false, render: (record) => personRender(record, record[column.field]) } : {}),
        ...(isAction ? { kind: "center", maxWidth: column.maxWidth || "--plx-ref-size-240px", headerSort: false, groupable: false } : {}),
        ...(/^(status|state)$/.test(column.field) ? { maxWidth: column.maxWidth || "--plx-ref-size-240px" } : {}),
        ...(/^(code|number|case_number|case_code)$/.test(column.field) ? { kind: "data" } : {}),
        ...(render ? { pill: false, render: (record) => {
          const value = render(record);
          if (value === null || value === undefined || value === "" || typeof value === "object") return value;
          if (type === "person") return personRender(record, value);
          return h(P.DataPill, {
            size: "md", person: type === "person",
            data: column.kind === "data" || type === "number" || type === "date",
            ...(type === "date" ? { icon: "calendar" } : {}),
          }, value);
        } } : {}),
        headerSort: !isAction && column.headerSort !== false,
        resizable: column.resizable !== false,
      };
    });
    const common = {
      label, data: rows, columns: gridColumns, index: "id", className,
      density: "compact", cells: "pill", typeIcons: false, wrapHeaders: false,
      narrow: "table", empty,
    };
    return h(P.DataGrid, {
      ...common, mode: "fill",
      headerMenu: true, rowMenuButton: false,
      selected: selected ? [selected] : [],
      onRowClick: onSelect ? (row) => onSelect(row.id) : undefined,
    });
  }

  function Workspace({ label, rows, columns, children, empty, selectionPrompt, selected, onSelect, showDetailWhenEmpty = false, orientation = "side-by-side", toolbar = null }) {
    const [own, select] = R.useState(null);
    const id = selected === undefined ? own : selected;
    const chosen = rows.find((row) => row.id === id);
    const emptyDetail = rows.length
      ? selectionPrompt || (document.documentElement.lang === "ar" ? "اختر عنصرًا" : "Select an item")
      : empty || label;
    return h(P.Stack, { gap: "md", className: "plx-u-flex-1 plx-u-min-h-0" },
      toolbar,
      h(P.SplitView, {
      label, firstLabel: label, orientation, defaultSize: orientation === "stacked" ? 320 : undefined,
      first: h(Table, { label, rows, columns, selected: id, onSelect: onSelect || select, empty }),
      second: h(P.ReadingPane, { label: chosen?.title || chosen?.name || label },
        (chosen || showDetailWhenEmpty) ? (typeof children === "function" ? children(chosen) : children) : h(P.EmptyState, { title: emptyDetail }),
      ),
    }),
    );
  }
  window.CTMShell = Object.freeze({ Table, Workspace });
})();

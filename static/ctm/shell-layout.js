/* Shared integration of the documented Plenix table and split-view components. */
(() => {
  const R = window.React, P = window.Plenix, h = R.createElement;
  function Table({ label, rows, columns, selected, onSelect, empty, className, isStatic = true }) {
    // Reference facts use Table; record workspaces use the native interactive grid.
    // CDN 0.65 owns sizing, typography, truncation and scrolling for both.
    const gridColumns = (columns || []).map(({ width, minWidth, maxWidth, ...column }) => {
      const render = column.render;
      const type = column.type || (/^(applicant|respondent|manager|.*_name)$/.test(column.field) ? "person"
        : /^(.*_count|count|total|position|married_years)$/.test(column.field) ? "number" : "text");
      return {
        ...column, type,
        ...(/^(code|number|case_number|case_code)$/.test(column.field) ? { kind: "data" } : {}),
        ...(render ? { pill: false, render: (record) => {
          const value = render(record);
          if (value === null || value === undefined || value === "" || typeof value === "object") return value;
          return h(P.DataPill, {
            size: "md", person: type === "person",
            data: column.kind === "data" || type === "number" || type === "date",
            ...(type === "date" ? { icon: "calendar" } : {}),
          }, value);
        } } : {}),
        headerSort: !isStatic && column.headerSort !== false,
        resizable: !isStatic,
      };
    });
    const common = {
      label, data: rows, columns: gridColumns, index: "id", className,
      density: "compact", cells: "pill", typeIcons: false,
      narrow: "table", empty,
    };
    if (!onSelect && isStatic) return h(P.Table, common);
    return h(P.DataGrid, {
      ...common, mode: "fill",
      headerMenu: !isStatic, rowMenuButton: false,
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

/* Shared integration of the documented Plenix table and split-view components. */
(() => {
  const R = window.React, P = window.Plenix, h = R.createElement;
  function Table({ label, rows, columns, selected, onSelect, empty, className, isStatic = true }) {
    // Every CTM collection keeps native grid controls, including read-only records.
    // Read-only data must not disable column resizing, sorting or header menus.
    let gridRows = rows;
    const gridColumns = (columns || []).map((column, index) => {
      const render = column.render;
      const isAction = column.kind === "actions" || /^(open_action|actions?)$/.test(column.field);
      const type = column.type || (/^(applicant|respondent|manager|.*_name)$/.test(column.field) ? "person"
        : /^(.*_count|count|total|position|married_years)$/.test(column.field) ? "number" : "text");
      const values = render && !isAction ? rows.map(record => render(record)) : null;
      const scalar = values && values.every(value => value == null || ["string", "number", "boolean"].includes(typeof value));
      const native = !isAction && (scalar || (!render && type === "person"));
      let projected = {};
      if (native) {
        // Keep domain fields intact for callbacks and richer neighboring cells.
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
        ...(isAction ? { kind: "center", maxWidth: column.maxWidth || "--plx-ref-size-240px", headerSort: false, groupable: false } : {}),
        ...(/^(status|state)$/.test(column.field) ? { maxWidth: column.maxWidth || "--plx-ref-size-240px" } : {}),
        ...(/^(code|number|case_number|case_code)$/.test(column.field) ? { kind: "data" } : {}),
        ...(render && !native ? { pill: false, render } : {}),
        headerSort: !isAction && column.headerSort !== false,
        resizable: column.resizable !== false,
      };
    });
    const common = {
      label, data: gridRows, columns: gridColumns, index: "id", className,
      density: "compact", cells: "pill", uniformPillWidths: true, typeIcons: false, wrapHeaders: false,
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

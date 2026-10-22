/* Shared integration of the documented Plenix table and split-view components. */
(() => {
  const R = window.React, P = window.Plenix, h = R.createElement;
  function Table({ label, rows, columns, selected, onSelect, empty, className, isStatic = true }) {
    // All CTM tables remain documented DataTable grids.  Session agenda grids
    // do not expose column menus or column resizing, which prevents their
    // grid chrome from creating a needless horizontal scrolling workflow.
    const gridColumns = (columns || []).map((column) => ({
      ...column, headerSort: false, resizable: false,
    }));
    const common = { label, data: rows, columns: gridColumns, index: "id", narrow: "table", empty };
    return h("div", { className }, h(P.DataTable, {
      ...common, mode: "fill", isStatic,
      headerMenu: false, rowMenuButton: false,
      selected: selected ? [selected] : [], onRowClick: onSelect ? (row) => onSelect(row.id) : undefined, empty,
    }));
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

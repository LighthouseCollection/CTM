/* Shared integration of the documented Plenix table and split-view components. */
(() => {
  const R = window.React, P = window.Plenix, h = R.createElement;
  function Table({ label, rows, columns, selected, onSelect, empty }) {
    return h(P.DataTable, {
      label, data: rows, columns, index: "id", narrow: "table", mode: "fill",
      selected: selected ? [selected] : [], onRowClick: (row) => onSelect(row.id), empty,
    });
  }
  function Workspace({ label, rows, columns, children, empty, selectionPrompt, selected, onSelect, showDetailWhenEmpty = false }) {
    const [own, select] = R.useState(null);
    const id = selected === undefined ? own : selected;
    const chosen = rows.find((row) => row.id === id);
    const emptyDetail = rows.length
      ? selectionPrompt || (document.documentElement.lang === "ar" ? "اختر عنصرًا" : "Select an item")
      : empty || label;
    return h(P.SplitView, {
      label, firstLabel: label,
      first: h(Table, { label, rows, columns, selected: id, onSelect: onSelect || select, empty }),
      second: h(P.ReadingPane, { label: chosen?.title || chosen?.name || label },
        (chosen || showDetailWhenEmpty) ? (typeof children === "function" ? children(chosen) : children) : h(P.EmptyState, { title: emptyDetail }),
      ),
    });
  }
  window.CTMShell = Object.freeze({ Table, Workspace });
})();

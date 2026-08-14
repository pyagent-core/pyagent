/*
 * API & Hooks Bibliography — live table filter.
 *
 * A single text input hides non-matching rows across every table on the
 * page (case-insensitive substring match against the row's full text).
 * Section headings whose table has zero visible rows collapse too, so
 * a search like "trust" leaves only the relevant class/enum rows and
 * their owning packages visible, not 8 empty package headers.
 *
 * Re-runs on Material's `document$` so it survives instant-navigation swaps.
 */
(function () {
  "use strict";

  function init() {
    var input = document.getElementById("bib-filter");
    var root = document.getElementById("bib-content");
    if (!input || !root || input.dataset.wired === "1") return;
    input.dataset.wired = "1";

    var sections = Array.prototype.slice.call(root.querySelectorAll(".bib-section"));
    var count = document.getElementById("bib-filter-count");

    function apply() {
      var q = input.value.trim().toLowerCase();
      var visibleRows = 0;
      var totalRows = 0;

      sections.forEach(function (section) {
        var rows = section.querySelectorAll("tbody tr");
        var anyVisible = false;
        rows.forEach(function (row) {
          totalRows++;
          var match = !q || row.textContent.toLowerCase().indexOf(q) !== -1;
          row.style.display = match ? "" : "none";
          if (match) { anyVisible = true; visibleRows++; }
        });
        var listItems = section.querySelectorAll("li");
        listItems.forEach(function (li) {
          if (!li.closest("table")) {
            var match = !q || li.textContent.toLowerCase().indexOf(q) !== -1;
            li.style.display = match ? "" : "none";
            if (match) anyVisible = true;
          }
        });
        var hasNoTables = section.querySelectorAll("table").length === 0 && section.querySelectorAll("li").length === 0;
        section.style.display = q && !anyVisible && !hasNoTables ? "none" : "";
      });

      if (count) {
        count.textContent = q ? visibleRows + " of " + totalRows + " rows match “" + input.value.trim() + "”" : "";
      }
    }

    input.addEventListener("input", apply);
  }

  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(init);
  } else {
    document.addEventListener("DOMContentLoaded", init);
  }
})();

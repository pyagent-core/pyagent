/*
 * Mermaid re-init for Material's instant navigation.
 *
 * Material for MkDocs loads Mermaid and renders ```mermaid fences, but its run
 * can race the library's initialization (and does not always re-run after an
 * instant-navigation page swap), leaving diagrams as empty `.mermaid` nodes.
 *
 * This re-runs Mermaid on each page load/swap, but ONLY over diagrams that are
 * not yet rendered (`:not([data-processed])`). When Material has already
 * rendered them, the selector matches nothing and this is a complete no-op —
 * so there is no double-initialization. We reuse the Mermaid instance Material
 * loaded (window.mermaid); we never load a second copy.
 */
(function () {
  function rerun() {
    var m = window.mermaid;
    if (!m || typeof m.run !== "function") return;
    var pending = document.querySelectorAll(".mermaid:not([data-processed])");
    if (!pending.length) return;
    try {
      m.run({ nodes: pending });
    } catch (e) {
      /* leave Material's own handling untouched on error */
    }
  }

  // Material exposes document$ (an RxJS observable) that emits on every page
  // load and instant-navigation swap. Fall back to DOM events otherwise.
  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(function () {
      // Defer so Material's own mermaid pass (and the library load) go first.
      setTimeout(rerun, 50);
      setTimeout(rerun, 400);
    });
  } else if (document.readyState !== "loading") {
    rerun();
  } else {
    document.addEventListener("DOMContentLoaded", rerun);
  }
})();

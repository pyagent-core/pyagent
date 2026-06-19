/*
 * Auto-advance infinite scroll for MkDocs Material.
 *
 * As the reader nears the bottom of a page, the next page in nav order is fetched and appended —
 * no click — and the URL + document title update as each appended page scrolls into view, so every
 * page keeps its own shareable URL (SEO unaffected; the site is still served as discrete pages).
 *
 * Scope: chains across linear doc sequences (Getting Started, Design Patterns, Framework). It stops
 * before the Cookbook and API Reference (excluded) so it never concatenates hundreds of pages.
 * Re-initialises on Material's `document$` so it coexists with instant navigation.
 */
(function () {
  "use strict";

  var MAX_APPENDED = 6;                  // cap DOM growth per session on a page
  var EXCLUDE = ["/cookbook/", "/api/"]; // never auto-chain these (huge / reference)

  function allowed(path) {
    if (!path) return false;
    for (var i = 0; i < EXCLUDE.length; i++) {
      if (path.indexOf(EXCLUDE[i]) !== -1) return false;
    }
    return true;
  }

  function nextUrlFrom(doc) {
    var link = (doc || document).querySelector(".md-footer__link--next");
    return link ? link.getAttribute("href") : null;
  }

  function setup() {
    if (!allowed(location.pathname)) return;
    var content = document.querySelector(".md-content__inner");
    if (!content || content.dataset.infiniteWired) return;
    content.dataset.infiniteWired = "1";

    var appended = 0;
    var loading = false;
    var loaded = {};
    loaded[location.pathname] = true;
    var nextUrl = nextUrlFrom(document);

    var sentinel = document.createElement("div");
    sentinel.className = "md-infinite-sentinel";
    sentinel.style.height = "1px";
    content.appendChild(sentinel);

    function loadNext() {
      if (loading || appended >= MAX_APPENDED || !nextUrl) return;
      var url = new URL(nextUrl, location.href);
      if (!allowed(url.pathname) || loaded[url.pathname]) return; // stop at excluded section
      loading = true;
      fetch(url.href)
        .then(function (r) { return r.text(); })
        .then(function (html) {
          var doc = new DOMParser().parseFromString(html, "text/html");
          var inner = doc.querySelector(".md-content__inner");
          if (!inner) { loading = false; return; }
          loaded[url.pathname] = true;
          appended++;

          var section = document.createElement("section");
          section.className = "md-infinite-page";
          section.setAttribute("data-url", url.pathname);
          section.setAttribute("data-title", doc.title);
          section.appendChild(document.createElement("hr"));
          while (inner.firstChild) section.appendChild(inner.firstChild);
          content.insertBefore(section, sentinel);

          // Update URL + title when this appended page is the one in view.
          var urlObs = new IntersectionObserver(function (entries) {
            entries.forEach(function (e) {
              if (e.isIntersecting) {
                history.replaceState(null, "", url.pathname);
                document.title = section.getAttribute("data-title");
              }
            });
          }, { rootMargin: "-40% 0px -55% 0px" });
          urlObs.observe(section);

          nextUrl = nextUrlFrom(doc);
          loading = false;
        })
        .catch(function () { loading = false; });
    }

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) loadNext(); });
    }, { rootMargin: "600px" });
    io.observe(sentinel);
  }

  // Coexist with instant navigation: Material emits document$ on every page load/swap.
  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(function () { setup(); });
  } else if (document.readyState !== "loading") {
    setup();
  } else {
    document.addEventListener("DOMContentLoaded", setup);
  }
})();

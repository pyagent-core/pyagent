/*
 * Guided Mode — opt-in continuous scrolling across curated learning paths.
 *
 * Default OFF. A small toggle (persisted in localStorage) lets a reader turn it
 * on. When ON, the next page in nav order is fetched and appended as you near
 * the bottom — but ONLY while you stay within the same curated sequence
 * (Getting Started, Design Patterns; see guided-sequences.json). It never chains
 * across API reference, Benchmarks/Comparison, or the Cookbook, which keep
 * stable canonical URLs.
 *
 * When OFF, this is a complete no-op: no scroll listeners, no DOM changes, so
 * normal navigation, the left-nav active state, and the right-hand TOC behave
 * exactly as Material ships them.
 *
 * This REPLACES the older always-on infinite-scroll.js — only one scroll
 * handler ships, so there are no competing listeners.
 */
(function () {
  "use strict";

  var STORAGE_KEY = "pyagent-guided-mode";
  var MAX_APPENDED = 8; // cap DOM growth per page session
  var SELF = document.currentScript; // used to resolve the sibling data file

  var data = null; // { sequences: [{name, prefix}], exclude: [..] }
  var dataPromise = null;

  function loadData() {
    if (dataPromise) return dataPromise;
    var url = SELF ? new URL("guided-sequences.json", SELF.src).href : "/javascripts/guided-sequences.json";
    dataPromise = fetch(url)
      .then(function (r) { return r.json(); })
      .then(function (j) { data = j; return j; })
      .catch(function () { data = { sequences: [], exclude: [] }; return data; });
    return dataPromise;
  }

  function isEnabled() {
    try { return localStorage.getItem(STORAGE_KEY) === "on"; } catch (e) { return false; }
  }
  function setEnabled(on) {
    try { localStorage.setItem(STORAGE_KEY, on ? "on" : "off"); } catch (e) {}
  }

  function excluded(path) {
    if (!data) return true;
    for (var i = 0; i < data.exclude.length; i++) {
      if (path.indexOf(data.exclude[i]) !== -1) return true;
    }
    return false;
  }

  // The sequence prefix that contains this path, or null if the page is not
  // part of any guided sequence.
  function sequenceFor(path) {
    if (!data || excluded(path)) return null;
    for (var i = 0; i < data.sequences.length; i++) {
      if (path.indexOf(data.sequences[i].prefix) === 0) return data.sequences[i];
    }
    return null;
  }

  function nextUrlFrom(doc) {
    var link = (doc || document).querySelector(".md-footer__link--next");
    return link ? link.getAttribute("href") : null;
  }

  // ── Toggle UI ──────────────────────────────────────────────────────────────

  function injectToggle(seq) {
    var content = document.querySelector(".md-content__inner");
    if (!content || document.querySelector(".pa-guided-toggle")) return;

    var bar = document.createElement("div");
    bar.className = "pa-guided-toggle";
    bar.style.cssText =
      "display:flex;align-items:center;gap:.5rem;margin:0 0 1rem;padding:.4rem .7rem;" +
      "border:1px solid var(--md-default-fg-color--lightest);border-radius:.4rem;" +
      "font-size:.7rem;color:var(--md-default-fg-color--light);";

    var label = document.createElement("span");
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "md-button";
    btn.style.cssText = "padding:.15rem .6rem;font-size:.7rem;margin:0;";

    function render() {
      var on = isEnabled();
      label.textContent = "Guided Mode — continuous scroll through the " + seq.name + " path:";
      btn.textContent = on ? "On" : "Off";
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    }
    btn.addEventListener("click", function () {
      var on = !isEnabled();
      setEnabled(on);
      render();
      if (on) {
        wireScroll(seq);
      } else {
        // Turning off: drop appended pages by returning to the canonical page.
        location.assign(location.pathname);
      }
    });

    render();
    bar.appendChild(label);
    bar.appendChild(btn);
    content.insertBefore(bar, content.firstChild);
  }

  // ── Continuous scroll (only runs when enabled) ──────────────────────────────

  function wireScroll(seq) {
    if (!isEnabled()) return;
    var content = document.querySelector(".md-content__inner");
    if (!content || content.dataset.guidedWired) return;
    content.dataset.guidedWired = "1";

    var appended = 0;
    var loading = false;
    var loaded = {};
    loaded[location.pathname] = true;
    var nextUrl = nextUrlFrom(document);

    var sentinel = document.createElement("div");
    sentinel.className = "pa-guided-sentinel";
    sentinel.style.height = "1px";
    content.appendChild(sentinel);

    function withinSequence(path) {
      return !excluded(path) && path.indexOf(seq.prefix) === 0;
    }

    function loadNext() {
      if (loading || appended >= MAX_APPENDED || !nextUrl) return;
      var url = new URL(nextUrl, location.href);
      // Stay inside the current curated sequence; stop at its boundary.
      if (!withinSequence(url.pathname) || loaded[url.pathname]) return;
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
          section.className = "pa-guided-page";
          section.setAttribute("data-url", url.pathname);
          section.setAttribute("data-title", doc.title);
          section.appendChild(document.createElement("hr"));
          while (inner.firstChild) section.appendChild(inner.firstChild);
          content.insertBefore(section, sentinel);

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

  function setup() {
    loadData().then(function () {
      var seq = sequenceFor(location.pathname);
      if (!seq) return; // not a guided page → no toggle, no scrolling, pure no-op
      injectToggle(seq);
      if (isEnabled()) wireScroll(seq);
    });
  }

  // Coexist with Material instant navigation: document$ emits on every swap.
  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(function () { setup(); });
  } else if (document.readyState !== "loading") {
    setup();
  } else {
    document.addEventListener("DOMContentLoaded", setup);
  }
})();

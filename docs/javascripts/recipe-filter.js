/*
 * Cookbook recipe browser — multi-select faceted filter.
 *
 * Builds Domain / Pattern / Package filter chips from the generated
 * `.cb-card` elements on the Cookbook landing page, then shows/hides cards:
 * multiple picks within one axis match ANY (OR); across axes they must all
 * match (AND). Each card's own chips toggle the matching facet. A `location`
 * hash like `#package=pyagent-router` pre-applies a filter (deep-link).
 *
 * Re-runs on Material's `document$` so it survives instant-navigation swaps.
 */
(function () {
  "use strict";

  var AXES = ["Domain", "Pattern", "Package"];

  function init() {
    var browser = document.getElementById("recipe-browser");
    var bar = document.getElementById("recipe-filter-bar");
    if (!browser || !bar || bar.dataset.wired === "1") return;
    bar.dataset.wired = "1";

    var cards = Array.prototype.slice.call(browser.querySelectorAll(".cb-card"));
    var total = cards.length;
    var selected = { Domain: new Set(), Pattern: new Set(), Package: new Set() };

    // Collect unique facet values per axis.
    var facets = { Domain: [], Pattern: [], Package: [] };
    var seen = { Domain: {}, Pattern: {}, Package: {} };
    cards.forEach(function (card) {
      AXES.forEach(function (axis) {
        (card.getAttribute("data-" + axis.toLowerCase()) || "")
          .split("|")
          .filter(Boolean)
          .forEach(function (v) {
            if (!seen[axis][v]) {
              seen[axis][v] = true;
              facets[axis].push(v);
            }
          });
      });
    });
    AXES.forEach(function (a) {
      facets[a].sort();
    });

    var buttonsByKey = {};
    function keyOf(axis, value) {
      return axis + "::" + value;
    }
    function register(axis, value, el) {
      var k = keyOf(axis, value);
      (buttonsByKey[k] = buttonsByKey[k] || []).push(el);
    }

    var count = document.createElement("div");
    count.className = "cb-count";

    var groupsWrap = document.createElement("div");
    groupsWrap.className = "cb-filter-groups";
    AXES.forEach(function (axis) {
      if (!facets[axis].length) return;
      var group = document.createElement("div");
      group.className = "cb-filter-group cb-filter-group--" + axis.toLowerCase();
      var label = document.createElement("span");
      label.className = "cb-filter-label";
      label.textContent = axis;
      group.appendChild(label);
      facets[axis].forEach(function (value) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "cb-filter cb-filter--" + axis.toLowerCase();
        btn.textContent = value;
        btn.addEventListener("click", function () {
          toggle(axis, value);
        });
        group.appendChild(btn);
        register(axis, value, btn);
      });
      groupsWrap.appendChild(group);
    });

    var clear = document.createElement("button");
    clear.type = "button";
    clear.className = "cb-clear";
    clear.textContent = "Clear all";
    clear.addEventListener("click", clearAll);

    bar.appendChild(count);
    bar.appendChild(groupsWrap);
    bar.appendChild(clear);

    // Card chips also act as filter toggles.
    cards.forEach(function (card) {
      card.querySelectorAll(".cb-chip").forEach(function (chip) {
        var axis = chip.getAttribute("data-axis");
        var value = chip.getAttribute("data-value");
        register(axis, value, chip);
        chip.addEventListener("click", function (e) {
          e.preventDefault();
          toggle(axis, value);
        });
      });
    });

    function toggle(axis, value) {
      var set = selected[axis];
      if (set.has(value)) set.delete(value);
      else set.add(value);
      apply();
    }
    function clearAll() {
      AXES.forEach(function (a) {
        selected[a].clear();
      });
      apply();
    }
    function cardMatches(card) {
      return AXES.every(function (axis) {
        var sel = selected[axis];
        if (sel.size === 0) return true;
        var vals = (card.getAttribute("data-" + axis.toLowerCase()) || "").split("|");
        var hit = false;
        sel.forEach(function (v) {
          if (vals.indexOf(v) !== -1) hit = true;
        });
        return hit;
      });
    }
    function apply() {
      var shown = 0;
      cards.forEach(function (card) {
        var ok = cardMatches(card);
        card.style.display = ok ? "" : "none";
        if (ok) shown++;
      });
      Object.keys(buttonsByKey).forEach(function (k) {
        var parts = k.split("::");
        var on = selected[parts[0]].has(parts[1]);
        buttonsByKey[k].forEach(function (b) {
          b.classList.toggle("is-active", on);
        });
      });
      var anySel = AXES.some(function (a) {
        return selected[a].size > 0;
      });
      count.textContent = anySel ? shown + " of " + total + " recipes" : total + " recipes";
      clear.style.display = anySel ? "" : "none";
    }

    // Deep-link: #domain=…  / #pattern=…  / #package=…
    var h = decodeURIComponent((location.hash || "").replace(/^#/, ""));
    var m = h.match(/^(domain|pattern|package)=(.+)$/i);
    if (m) {
      var axis = m[1].charAt(0).toUpperCase() + m[1].slice(1).toLowerCase();
      if (selected[axis] && facets[axis].indexOf(m[2]) !== -1) selected[axis].add(m[2]);
    }
    apply();
  }

  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(function () {
      init();
    });
  } else if (document.readyState !== "loading") {
    init();
  } else {
    document.addEventListener("DOMContentLoaded", init);
  }
})();

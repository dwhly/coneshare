/* fleet-design-system — theme.js
   Light/dark selection shared by every fleet product.
   - Choice persists per browser in localStorage["fds-theme"] = "light" | "dark" | "system".
   - "system" (default) follows the OS preference live.
   - Put an INLINE copy of FDS_THEME_BOOT in <head> to avoid a flash; load this file for the toggle.
   - Any element with [data-fds-theme-toggle] cycles system → light → dark and shows the current choice as an icon
     (v0.10: sun / moon / sun-moon; label in title + aria-label). data-fds-theme-toggle="custom" keeps its own content.
   - v0.9: keeps <meta name="color-scheme"> in step ("light dark" for system, else the choice) so
     scrollbars, form controls and browser UI match; syncs across tabs via the storage event. */
(function () {
  var KEY = "fds-theme";
  var mq = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
  var mem = null;   // an UNSAVED choice: set only when the write fails (storage denied or full); it wins over storage
  function norm(v) { return v === "light" || v === "dark" || v === "system" ? v : null; }
  function choice() { if (mem) return mem; var v = null; try { v = norm(localStorage.getItem(KEY)); } catch (e) {} return v || "system"; }
  function resolved(c) { return c === "system" ? (mq && mq.matches ? "dark" : "light") : c; }
  function meta(c) {
    var m = document.querySelector('meta[name="color-scheme"]');
    if (!m) { m = document.createElement("meta"); m.name = "color-scheme"; document.head.appendChild(m); }
    m.content = c === "system" ? "light dark" : c;
  }
  function apply() {
    var c = choice();
    meta(c);
    document.documentElement.setAttribute("data-theme", resolved(c));
    document.documentElement.setAttribute("data-theme-choice", c);
    var label = c === "system" ? "Theme: auto (" + resolved(c) + ")" : c === "dark" ? "Theme: dark" : "Theme: light";
    var name = c === "system" ? "sun-moon" : c === "dark" ? "moon" : "sun";
    document.querySelectorAll("[data-fds-theme-toggle]").forEach(function (b) {
      b.setAttribute("aria-label", label + " (click to change)");
      b.setAttribute("title", label);
      b.setAttribute("data-theme-choice", c);
      // "custom": the product draws its own content (e.g. a React icon); never touch children React owns.
      if (b.getAttribute("data-fds-theme-toggle") === "custom") return;
      // Skip only when THIS icon is really drawn: a clone or a re-render can carry data-fds-icon without its SVG.
      var f = b.firstElementChild;
      if (b.childNodes.length === 1 && f && f.getAttribute("data-fds-icon") === name) return;
      b.textContent = "";
      b.appendChild(icon(name));
      b.setAttribute("data-fds-icon", name);
    });
  }
  // v0.10: the Theme control is an icon (owner 2026-11-15: a labelled button is "too big and too bulky").
  // Paths copied verbatim from lucide-react 0.563.0 dist/esm/icons/{sun,moon,sun-moon}.js (ISC licence).
  // Built with DOM calls, not innerHTML, so a strict CSP and Trusted Types are fine.
  var ICONS = {
    sun: [["circle", { cx: "12", cy: "12", r: "4" }], "M12 2v2", "M12 20v2", "m4.93 4.93 1.41 1.41",
      "m17.66 17.66 1.41 1.41", "M2 12h2", "M20 12h2", "m6.34 17.66-1.41 1.41", "m19.07 4.93-1.41 1.41"],
    moon: ["M20.985 12.486a9 9 0 1 1-9.473-9.472c.405-.022.617.46.402.803a6 6 0 0 0 8.268 8.268c.344-.215.825-.004.803.401"],
    "sun-moon": ["M12 2v2",
      "M14.837 16.385a6 6 0 1 1-7.223-7.222c.624-.147.97.66.715 1.248a4 4 0 0 0 5.26 5.259c.589-.255 1.396.09 1.248.715",
      "M16 12a4 4 0 0 0-4-4", "m19 5-1.256 1.256", "M20 12h2"]
  };
  function icon(name) {
    var NS = "http://www.w3.org/2000/svg", svg = document.createElementNS(NS, "svg");
    var at = { viewBox: "0 0 24 24", width: "18", height: "18", fill: "none", stroke: "currentColor",
      "stroke-width": "2", "stroke-linecap": "round", "stroke-linejoin": "round", "aria-hidden": "true",
      focusable: "false", "class": "fds-theme-toggle__icon" };
    for (var k in at) svg.setAttribute(k, at[k]);
    svg.setAttribute("data-fds-icon", name);
    ICONS[name].forEach(function (p) {
      var el = typeof p === "string" ? ["path", { d: p }] : p, n = document.createElementNS(NS, el[0]);
      for (var a in el[1]) n.setAttribute(a, el[1][a]);
      svg.appendChild(n);
    });
    return svg;
  }
  function cycle() {
    var next = { system: "light", light: "dark", dark: "system" }[choice()] || "system";
    try { localStorage.setItem(KEY, next); mem = null; } catch (e) { mem = next; }
    apply();
  }
  window.fdsTheme = { apply: apply, cycle: cycle, choice: choice };
  if (mq && mq.addEventListener) mq.addEventListener("change", apply);
  // Another tab changed or cleared the preference: storage is authoritative again, so drop any unsaved choice.
  window.addEventListener("storage", function (e) { if (e.key === KEY || e.key === null) { mem = null; apply(); } });
  document.addEventListener("click", function (e) {
    var t = e.target && e.target.closest && e.target.closest("[data-fds-theme-toggle]");
    if (t) { e.preventDefault(); cycle(); }
  });
  // Toggles mounted later (client-side navigation in React/Next apps) get the current label too.
  var SEL = "[data-fds-theme-toggle]";
  function watch() {
    if (!window.MutationObserver || !document.body) return;
    new MutationObserver(function (ms) {
      for (var i = 0; i < ms.length; i++) for (var j = 0; j < ms[i].addedNodes.length; j++) {
        var n = ms[i].addedNodes[j];
        if (n.nodeType === 1 && (n.matches(SEL) || n.querySelector(SEL))) { apply(); return; }
      }
    }).observe(document.body, { childList: true, subtree: true });
  }
  function start() { apply(); watch(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();

/* Inline boot snippet (copy into <head>, before CSS paints):
<script>(function(){var c="system";try{c=localStorage.getItem("fds-theme")||"system"}catch(e){}if(c!=="light"&&c!=="dark")c="system";try{var d=c==="dark"||(c==="system"&&matchMedia("(prefers-color-scheme: dark)").matches);document.documentElement.setAttribute("data-theme",d?"dark":"light");var m=document.querySelector('meta[name="color-scheme"]');if(m)m.content=c==="system"?"light dark":c}catch(e){}})()</script>
Also put <meta name="color-scheme" content="light dark"> in <head> BEFORE the snippet.
*/

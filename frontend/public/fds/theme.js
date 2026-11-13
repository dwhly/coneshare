/* fleet-design-system — theme.js
   Light/dark selection shared by every fleet product.
   - Choice persists per browser in localStorage["fds-theme"] = "light" | "dark" | "system".
   - "system" (default) follows the OS preference live.
   - Put an INLINE copy of FDS_THEME_BOOT in <head> to avoid a flash; load this file for the toggle.
   - Any element with [data-fds-theme-toggle] cycles system → light → dark and shows the current choice.
   - v0.9: keeps <meta name="color-scheme"> in step ("light dark" for system, else the choice) so
     scrollbars, form controls and browser UI match; syncs across tabs via the storage event. */
(function () {
  var KEY = "fds-theme";
  var mq = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
  function choice() { try { return localStorage.getItem(KEY) || "system"; } catch (e) { return "system"; } }
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
    document.querySelectorAll("[data-fds-theme-toggle]").forEach(function (b) {
      b.textContent = label; b.setAttribute("aria-label", label + " (click to change)");
    });
  }
  function cycle() {
    var next = { system: "light", light: "dark", dark: "system" }[choice()] || "system";
    try { localStorage.setItem(KEY, next); } catch (e) {}
    apply();
  }
  window.fdsTheme = { apply: apply, cycle: cycle, choice: choice };
  if (mq && mq.addEventListener) mq.addEventListener("change", apply);
  window.addEventListener("storage", function (e) { if (e.key === KEY || e.key === null) apply(); });
  document.addEventListener("click", function (e) {
    var t = e.target && e.target.closest && e.target.closest("[data-fds-theme-toggle]");
    if (t) { e.preventDefault(); cycle(); }
  });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", apply); else apply();
})();

/* Inline boot snippet (copy into <head>, before CSS paints):
<script>(function(){try{var c=localStorage.getItem("fds-theme")||"system";var d=c==="dark"||(c==="system"&&matchMedia("(prefers-color-scheme: dark)").matches);document.documentElement.setAttribute("data-theme",d?"dark":"light");var m=document.querySelector('meta[name="color-scheme"]');if(m)m.content=c==="system"?"light dark":c}catch(e){}})()</script>
Also put <meta name="color-scheme" content="light dark"> in <head> BEFORE the snippet.
*/

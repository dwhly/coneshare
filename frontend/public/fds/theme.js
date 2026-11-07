/* fleet-design-system — theme.js
   Light/dark selection shared by every fleet product.
   - Choice persists per browser in localStorage["fds-theme"] = "light" | "dark" | "system".
   - "system" (default) follows the OS preference live.
   - Put an INLINE copy of FDS_THEME_BOOT in <head> to avoid a flash; load this file for the toggle.
   - Any element with [data-fds-theme-toggle] cycles system → light → dark and shows the current choice. */
(function () {
  var KEY = "fds-theme";
  var mq = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
  function choice() { try { return localStorage.getItem(KEY) || "system"; } catch (e) { return "system"; } }
  function resolved(c) { return c === "system" ? (mq && mq.matches ? "dark" : "light") : c; }
  function apply() {
    var c = choice();
    document.documentElement.setAttribute("data-theme", resolved(c));
    document.documentElement.setAttribute("data-theme-choice", c);
    var label = c === "system" ? "Theme: auto" : c === "dark" ? "Theme: dark" : "Theme: light";
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
  document.addEventListener("click", function (e) {
    var t = e.target && e.target.closest && e.target.closest("[data-fds-theme-toggle]");
    if (t) { e.preventDefault(); cycle(); }
  });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", apply); else apply();
})();

/* Inline boot snippet (copy into <head>, before CSS paints):
<script>(function(){try{var c=localStorage.getItem("fds-theme")||"system";var d=c==="dark"||(c==="system"&&matchMedia("(prefers-color-scheme: dark)").matches);document.documentElement.setAttribute("data-theme",d?"dark":"light")}catch(e){}})()</script>
*/

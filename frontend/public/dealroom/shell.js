/* Fleet Dealroom shell helpers for the Django glue pages (no build step). Pairs with /dealroom/shell.css.
   - drMenu: account dropdown (button[aria-expanded] + .dr-menu__panel)
   - drAccount: renders "the person" (initials avatar + display name + chevron) from a staff JWT
   - drSelect: styled select (button + listbox); no native <select> is ever shown */
(function () {
  "use strict";
  const h = (tag, attrs, ...kids) => {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === "class") el.className = v;
      else if (k === "text") el.textContent = v;
      else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? "" : v);
    }
    for (const kid of kids.flat()) if (kid != null) el.append(kid);
    return el;
  };
  const svg = (paths) => {
    const s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    s.setAttribute("viewBox", "0 0 24 24"); s.setAttribute("fill", "none"); s.setAttribute("stroke", "currentColor");
    s.setAttribute("stroke-width", "2"); s.setAttribute("stroke-linecap", "round"); s.setAttribute("stroke-linejoin", "round");
    s.setAttribute("aria-hidden", "true");
    for (const d of paths) { const p = document.createElementNS("http://www.w3.org/2000/svg", "path"); p.setAttribute("d", d); s.append(p); }
    return s;
  };
  const chevron = () => svg(["m6 9 6 6 6-6"]);

  function drMenu(button, panel) {
    const close = () => { panel.hidden = true; button.setAttribute("aria-expanded", "false"); };
    button.setAttribute("aria-haspopup", "menu"); button.setAttribute("aria-expanded", "false"); panel.hidden = true;
    button.addEventListener("click", (e) => { e.stopPropagation(); const open = panel.hidden; close(); if (open) { panel.hidden = false; button.setAttribute("aria-expanded", "true"); panel.querySelector("a,button")?.focus(); } });
    document.addEventListener("click", (e) => { if (!panel.contains(e.target)) close(); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !panel.hidden) { close(); button.focus(); } });
  }

  function initials(name, email) {
    const parts = String(name || "").trim().split(/\s+/).filter(Boolean);
    if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return String(email || "?").split("@")[0].slice(0, 2).toUpperCase() || "?";
  }
  function displayName(user) {
    if (user && user.name && user.name.trim()) return user.name.trim();
    const local = String((user && user.email) || "").split("@")[0];
    return local ? local.split(/[._-]+/).filter(Boolean).map((w) => w[0].toUpperCase() + w.slice(1)).join(" ") : "Account";
  }
  function jwtUserId(token) {
    try { return JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/"))).user_id; } catch (e) { return null; }
  }

  /** Account menu = the person (spec §1): email, Settings, Sign out. */
  async function drAccount(slot, token, onSignOut) {
    const id = jwtUserId(token);
    if (!slot || !id) return null;
    const r = await fetch("/api/v1/users/" + id + "/", { headers: { Authorization: "Bearer " + token } });
    if (!r.ok) return null;
    const user = await r.json();
    const name = displayName(user);
    const button = h("button", { type: "button", class: "dr-account", "aria-label": "Account: " + name },
      h("span", { class: "dr-avatar", "aria-hidden": "true", text: initials(user.name, user.email) }),
      h("span", { class: "dr-account__name", text: name }), (() => { const c = chevron(); c.setAttribute("class", "dr-account__chevron"); return c; })());
    const panel = h("div", { class: "dr-menu__panel", role: "menu" },
      h("div", { class: "dr-menu__label", text: user.email }), h("div", { class: "dr-menu__sep", role: "separator" }),
      h("a", { class: "dr-menu__item", role: "menuitem", href: "/settings", text: "Settings" }),
      h("div", { class: "dr-menu__sep", role: "separator" }),
      h("button", { type: "button", class: "dr-menu__item", role: "menuitem", text: "Sign out", onclick: onSignOut }));
    slot.replaceChildren(h("div", { class: "dr-menu" }, button, panel));
    slot.hidden = false;
    drMenu(button, panel);
    return user;
  }

  /** Styled select: button trigger + listbox. Returns { get value, set(options, value), onchange }. */
  function drSelect(container, { label, placeholder = "Choose…", onChange } = {}) {
    let options = [], value = "", active = -1;
    const text = h("span", { class: "dr-muted", text: placeholder });
    const trigger = h("button", { type: "button", class: "dr-select__trigger", "aria-haspopup": "listbox", "aria-expanded": "false", "aria-label": label, id: container.dataset.id || null }, text, chevron());
    const list = h("ul", { class: "dr-select__list", role: "listbox", "aria-label": label, tabindex: "-1" });
    list.hidden = true;
    container.classList.add("dr-select");
    container.replaceChildren(trigger, list);
    const close = () => { list.hidden = true; trigger.setAttribute("aria-expanded", "false"); };
    const render = () => {
      const cur = options.find((o) => o.value === value);
      text.textContent = cur ? cur.label : placeholder; text.className = cur ? "" : "dr-muted";
      list.replaceChildren(...options.map((o, i) => h("li", { role: "option", id: (container.dataset.id || "sel") + "-opt-" + i, "aria-selected": o.value === value ? "true" : "false", class: i === active ? "is-active" : null, text: o.label, onclick: () => choose(o.value) })));
    };
    const choose = (v) => { const changed = v !== value; value = v; render(); close(); trigger.focus(); if (changed && onChange) onChange(v); };
    trigger.addEventListener("click", (e) => { e.stopPropagation(); if (list.hidden) { active = Math.max(0, options.findIndex((o) => o.value === value)); render(); list.hidden = false; trigger.setAttribute("aria-expanded", "true"); } else close(); });
    trigger.addEventListener("keydown", (e) => {
      if (list.hidden && (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ")) { e.preventDefault(); trigger.click(); return; }
      if (list.hidden) return;
      if (e.key === "ArrowDown") { e.preventDefault(); active = Math.min(options.length - 1, active + 1); render(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); active = Math.max(0, active - 1); render(); }
      else if (e.key === "Enter" || e.key === " ") { e.preventDefault(); if (options[active]) choose(options[active].value); }
      else if (e.key === "Escape" || e.key === "Tab") close();
    });
    document.addEventListener("click", (e) => { if (!container.contains(e.target)) close(); });
    return {
      get value() { return value; },
      set(opts, v) { options = opts; value = v !== undefined ? v : (options.find((o) => o.value === value) ? value : (options[0] ? options[0].value : "")); render(); },
      trigger,
    };
  }

  window.drShell = { h, svg, drMenu, drAccount, drSelect, displayName };
})();

/* Fleet Dealroom shell helpers for the Django glue pages (no build step). Pairs with /dealroom/shell.css.
   - drMenu: account dropdown (button[aria-expanded] + .dr-menu__panel)
   - drAccount: renders "the person" (initials avatar + display name + chevron) from a staff JWT
   - drSelect: styled select (select-only combobox + listbox, WAI-ARIA APG); no native <select> is ever shown */
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

  /** Styled select: a select-only combobox (WAI-ARIA APG) — button[role=combobox] + listbox. DOM focus stays on the
      button; while open, aria-activedescendant names the keyboard-active option and aria-selected follows it, so a
      screen reader announces each option as you move. Enter/Space/Tab commit, Escape cancels. Returns
      { get value, set(options, value), trigger }. */
  function drSelect(container, { label, placeholder = "Choose…", onChange } = {}) {
    let options = [], value = "", active = -1;
    const base = container.dataset.id || "sel";
    const listId = base + "-list";
    const optId = (i) => base + "-opt-" + i;
    const text = h("span", { class: "dr-muted", text: placeholder });
    const trigger = h("button", { type: "button", class: "dr-select__trigger", role: "combobox", "aria-haspopup": "listbox", "aria-expanded": "false", "aria-controls": listId, "aria-label": label, id: container.dataset.id || null }, text, chevron());
    const list = h("ul", { class: "dr-select__list", role: "listbox", id: listId, "aria-label": label, tabindex: "-1",
      onmousedown: (e) => e.preventDefault() }); // clicks in the list (options, scrollbar) keep focus on the combobox
    list.hidden = true;
    container.classList.add("dr-select");
    container.replaceChildren(trigger, list);
    const isOpen = () => !list.hidden;
    const render = () => {
      const cur = options.find((o) => o.value === value);
      text.textContent = cur ? cur.label : placeholder; text.className = cur ? "" : "dr-muted";
      // Open: selection follows the active option (APG select-only combobox). Closed: the committed value.
      const selected = (o, i) => (isOpen() ? i === active : o.value === value);
      list.replaceChildren(...options.map((o, i) => h("li", { role: "option", id: optId(i), "aria-selected": selected(o, i) ? "true" : "false", class: i === active && isOpen() ? "is-active" : null, text: o.label, onclick: () => choose(o.value) })));
      if (isOpen() && options[active]) {
        trigger.setAttribute("aria-activedescendant", optId(active));
        const li = list.children[active];
        if (li) { // keep the active option visible by scrolling the list only (never the page or the dialog body)
          if (li.offsetTop < list.scrollTop) list.scrollTop = li.offsetTop;
          else if (li.offsetTop + li.offsetHeight > list.scrollTop + list.clientHeight) list.scrollTop = li.offsetTop + li.offsetHeight - list.clientHeight;
        }
      } else trigger.removeAttribute("aria-activedescendant");
    };
    // Inside a scrolling dialog body the list floats (position: fixed, placed from the trigger, flipped up when there
    // is no room below) so the body's overflow never clips it; scrolling or resizing closes it (review r1 [4]).
    const place = () => {
      if (!container.closest(".dr-dialog__body")) return;
      const b = trigger.getBoundingClientRect(), below = innerHeight - b.bottom - 12, above = b.top - 12;
      const up = below < 160 && above > below;
      Object.assign(list.style, { position: "fixed", left: b.left + "px", right: "auto", width: b.width + "px",
        top: up ? "auto" : b.bottom + 4 + "px", bottom: up ? innerHeight - b.top + 4 + "px" : "auto",
        maxHeight: Math.max(120, Math.min(260, up ? above : below)) + "px" });
    };
    const close = () => { list.hidden = true; trigger.setAttribute("aria-expanded", "false"); active = -1; render(); };
    const open = () => { active = Math.max(0, options.findIndex((o) => o.value === value)); place(); list.hidden = false; trigger.setAttribute("aria-expanded", "true"); render(); };
    const choose = (v, refocus = true) => { const changed = v !== value; value = v; close(); if (refocus) trigger.focus(); if (changed && onChange) onChange(v); };
    const move = (i) => { active = Math.min(options.length - 1, Math.max(0, i)); render(); };
    trigger.addEventListener("click", (e) => { e.stopPropagation(); if (isOpen()) close(); else open(); });
    trigger.addEventListener("keydown", (e) => {
      if (!isOpen()) {
        if (["ArrowDown", "ArrowUp", "Enter", " ", "Home", "End"].includes(e.key)) {
          e.preventDefault(); open();
          if (e.key === "Home") move(0); else if (e.key === "End") move(options.length - 1);
        }
        return;
      }
      if (e.key === "ArrowDown") { e.preventDefault(); move(active + 1); }
      else if (e.key === "ArrowUp") { e.preventDefault(); move(active - 1); }
      else if (e.key === "Home" || e.key === "PageUp") { e.preventDefault(); move(0); }
      else if (e.key === "End" || e.key === "PageDown") { e.preventDefault(); move(options.length - 1); }
      else if (e.key === "Enter" || e.key === " ") { e.preventDefault(); if (options[active]) choose(options[active].value); else close(); }
      else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); close(); }
      else if (e.key === "Tab") { if (options[active]) choose(options[active].value, false); else close(); }
    });
    trigger.addEventListener("blur", () => { if (isOpen()) close(); });
    document.addEventListener("click", (e) => { if (!container.contains(e.target) && isOpen()) close(); });
    document.addEventListener("scroll", (e) => { if (isOpen() && list.style.position === "fixed" && e.target !== list) close(); }, true);
    window.addEventListener("resize", () => { if (isOpen() && list.style.position === "fixed") close(); });
    return {
      get value() { return value; },
      set(opts, v) { options = opts; value = v !== undefined ? v : (options.find((o) => o.value === value) ? value : (options[0] ? options[0].value : "")); if (isOpen()) active = Math.min(active, options.length - 1); render(); },
      trigger,
    };
  }

  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  /** DESIGN.md dates: "Nov 4" this year, "Nov 4, 2025" otherwise (list tables are date-only). */
  function drDate(value) {
    if (!value) return "—";
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return "—";
    return MONTHS[d.getMonth()] + " " + d.getDate() + (d.getFullYear() === new Date().getFullYear() ? "" : ", " + d.getFullYear());
  }

  /** Table footer (spec §7) for a list table: "1 room" / "Showing 1–10 of 47"; pager only when there is >1 page.
      drPager(footerEl, { noun, plural, pageSize, onPage }) → { render(total), page, slice(rows) }. */
  function drPager(footer, { noun, plural, pageSize = 10, onPage } = {}) {
    let page = 1, total = 0;
    footer.classList.add("dr-tfoot");
    const pages = () => Math.max(1, Math.ceil(total / pageSize));
    const go = (n) => { page = Math.min(Math.max(1, n), pages()); if (onPage) onPage(page); };
    const btn = (label, d, disabled, to) => h("button", { type: "button", class: "dr-btn", "aria-label": label, disabled, onclick: () => go(to) }, svg([d]));
    const api = {
      get page() { return page; },
      reset() { page = 1; },
      slice(rows) { total = rows.length; if (page > pages()) page = pages(); return rows.slice((page - 1) * pageSize, page * pageSize); },
      render(n) {
        total = n; if (page > pages()) page = pages();
        const text = total <= pageSize ? total + " " + (total === 1 ? noun : plural || noun + "s")
          : "Showing " + ((page - 1) * pageSize + 1) + "–" + Math.min(total, page * pageSize) + " of " + total;
        const kids = [h("span", { text })];
        if (pages() > 1) kids.push(h("nav", { class: "dr-pager", "aria-label": "Pages" },
          btn("Previous page", "m15 18-6-6 6-6", page <= 1, page - 1),
          h("span", { class: "dr-pager__page", text: "Page " + page + " of " + pages() }),
          btn("Next page", "m9 18 6-6-6-6", page >= pages(), page + 1)));
        footer.replaceChildren(...kids);
        footer.hidden = false;
      },
    };
    return api;
  }

  // fds owns the cycle; mirror its label for hover and reliable screen-reader announcements.
  const themeStatus = h("span", { "aria-live": "polite", "aria-atomic": "true" });
  themeStatus.style.cssText = "position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap;border:0";
  document.body.appendChild(themeStatus);
  function syncThemeControls() {
    document.querySelectorAll("[data-fds-theme-toggle]").forEach(function (button) {
      const label = (button.getAttribute("aria-label") || "").replace(/ \(click to change\)$/, "");
      if (!label) return;
      button.setAttribute("title", label);
      if (themeStatus.textContent !== label) themeStatus.textContent = label;
    });
  }
  new MutationObserver(syncThemeControls).observe(document.body, { subtree: true, attributes: true, attributeFilter: ["aria-label"] });
  syncThemeControls();

  function logoFallback(image) {
    if (!image.matches("img.fleet-tenant-logo")) return;
    image.replaceWith(h("span", { class: "fds-lockup__family", text: image.alt }));
  }
  document.addEventListener("error", function (event) {
    if (event.target instanceof HTMLImageElement) logoFallback(event.target);
  }, true);
  document.querySelectorAll("img.fleet-tenant-logo").forEach(function (image) {
    if (image.complete && !image.naturalWidth) logoFallback(image);
  });

  window.drShell = { h, svg, drMenu, drAccount, drSelect, displayName, drDate, drPager };
})();

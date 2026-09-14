// Meelu dev annotation overlay.
//
// Injected into the rendered dashboard by dev/annotator/main.js, and ONLY in
// dev: the injector prepends `window.__MEELU_ANNOTATOR_DEV = true` and runs
// only when !app.isPackaged. If this file is somehow evaluated without that
// flag, it does nothing at all.
//
// Pure vanilla JS — no imports, no app code, no dependencies. Everything
// lives under one root element at a huge z-index; when inactive the root is
// display:none, so the page behaves exactly as if the overlay didn't exist.
//
// Ctrl/Cmd+Shift+A  toggle overlay
// 1–6               arrow / box / circle / pen / note / element pin
// Ctrl/Cmd+Z        undo · Esc leave the box, then exit · Ctrl/Cmd+Enter save
//
// A drawn mark is only a pointer — the comment is the payload. Finishing a
// stroke therefore numbers it, opens its comment box already focused, and
// resolves the element it points at (an arrow's tip, anything else's centre)
// so the markdown carries a selector instead of bare coordinates.

(() => {
  "use strict";
  if (!window.__MEELU_ANNOTATOR_DEV) return; // production self-guard
  if (window.__meeluAnnotatorLoaded) return; // idempotent across re-injection
  window.__meeluAnnotatorLoaded = true;

  const COLORS = ["#e5484d", "#2f6fed", "#f5a524", "#1fa971"];
  const TOOLS = ["arrow", "box", "circle", "pen", "note", "pin"];

  const state = {
    active: false,
    tool: "arrow",
    color: COLORS[0],
    ops: [], // committed operations in order; undo pops the last one
    drawing: null, // in-progress shape while the mouse is down
  };

  // ---------- DOM skeleton ----------

  const root = document.createElement("div");
  root.id = "__meelu-annotator";
  root.style.display = "none";

  const style = document.createElement("style");
  style.textContent = `
    #__meelu-annotator { position: fixed; inset: 0; z-index: 2147483000;
      font: 12px/1.4 -apple-system, system-ui, sans-serif; cursor: crosshair; }
    #__meelu-annotator, #__meelu-annotator * { box-sizing: border-box; }
    #__meelu-annotator canvas { position: fixed; inset: 0; pointer-events: none; }
    #__meelu-annotator .ann-outline { position: fixed; border: 2px dashed currentColor;
      border-radius: 3px; pointer-events: none; }
    #__meelu-annotator .ann-badge { position: fixed; width: 20px; height: 20px;
      border-radius: 50%; background: currentColor; pointer-events: none;
      display: flex; align-items: center; justify-content: center; }
    #__meelu-annotator .ann-badge > span { color: #fff; font-weight: 700; font-size: 12px; }
    #__meelu-annotator .ann-editable { outline: none; white-space: pre-wrap;
      overflow-wrap: anywhere; cursor: text; }
    #__meelu-annotator .ann-editable:empty::before { content: attr(data-placeholder); opacity: .5; }
    #__meelu-annotator .ann-pin-note { position: fixed; max-width: 260px; min-width: 90px;
      background: #fffbe8; color: #1a1a1a; border: 1px solid currentColor;
      border-radius: 4px; padding: 4px 7px; box-shadow: 0 2px 8px rgba(0,0,0,.25); }
    #__meelu-annotator .ann-note { position: fixed; width: 200px; background: #fffbe8;
      color: #1a1a1a; border: 1px solid rgba(0,0,0,.25); border-radius: 5px;
      box-shadow: 0 3px 10px rgba(0,0,0,.3); }
    #__meelu-annotator .ann-note-handle { height: 12px; cursor: grab;
      background: currentColor; opacity: .85; border-radius: 4px 4px 0 0; }
    #__meelu-annotator .ann-note .ann-editable { padding: 5px 8px; min-height: 22px; }
    #__meelu-annotator .ann-toolbar { position: fixed; left: 50%; bottom: 14px;
      transform: translateX(-50%); display: flex; align-items: center; gap: 3px;
      background: rgba(28,28,30,.92); color: #ddd; padding: 5px 8px;
      border-radius: 9px; box-shadow: 0 4px 16px rgba(0,0,0,.35); cursor: default; }
    #__meelu-annotator .ann-toolbar button { all: unset; cursor: pointer; padding: 3px 7px;
      border-radius: 5px; font-size: 13px; line-height: 1; color: #ddd; }
    #__meelu-annotator .ann-toolbar button:hover { background: rgba(255,255,255,.12); }
    #__meelu-annotator .ann-toolbar button.ann-on { background: rgba(255,255,255,.22); color: #fff; }
    #__meelu-annotator .ann-sep { width: 1px; height: 16px; background: rgba(255,255,255,.18); margin: 0 4px; }
    #__meelu-annotator .ann-dot { width: 14px; height: 14px; border-radius: 50%;
      border: 2px solid transparent; padding: 0; }
    #__meelu-annotator .ann-dot.ann-on { border-color: #fff; }
    #__meelu-annotator .ann-toast { position: fixed; right: 16px; bottom: 16px;
      background: rgba(28,28,30,.94); color: #eee; padding: 8px 12px; border-radius: 7px;
      max-width: 380px; box-shadow: 0 4px 16px rgba(0,0,0,.35); pointer-events: none; }
    #__meelu-annotator.ann-capturing [data-ann-chrome],
    #__meelu-annotator.ann-capturing .ann-empty { visibility: hidden !important; }
    #__meelu-annotator.ann-picking, #__meelu-annotator.ann-picking * { pointer-events: none !important; }
  `;

  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  const domLayer = document.createElement("div"); // pins + notes
  const toolbar = document.createElement("div");
  toolbar.className = "ann-toolbar";
  toolbar.setAttribute("data-ann-ui", "");
  toolbar.setAttribute("data-ann-chrome", "");
  toolbar.innerHTML = `
    <button data-tool="arrow"  title="Arrow (1)">↗</button>
    <button data-tool="box"    title="Box (2)">▭</button>
    <button data-tool="circle" title="Circle (3)">◯</button>
    <button data-tool="pen"    title="Pen (4)">✎</button>
    <button data-tool="note"   title="Text note (5)">T</button>
    <button data-tool="pin"    title="Element pin (6)">◎</button>
    <span class="ann-sep"></span>
    ${COLORS.map((c) => `<button class="ann-dot" data-color="${c}" style="background:${c}" title="${c}"></button>`).join("")}
    <span class="ann-sep"></span>
    <button data-act="undo"  title="Undo (Ctrl/Cmd+Z)">↺</button>
    <button data-act="clear" title="Clear all">✕</button>
    <button data-act="save"  title="Save (Ctrl/Cmd+Enter)">💾 save</button>
  `;

  const toastEl = document.createElement("div");
  toastEl.className = "ann-toast";
  toastEl.setAttribute("data-ann-chrome", "");
  toastEl.style.display = "none";

  root.append(style, canvas, domLayer, toolbar, toastEl);
  document.documentElement.appendChild(root);

  let toastTimer = 0;
  function toast(msg, ms = 3200) {
    toastEl.textContent = msg;
    toastEl.style.display = "block";
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (toastEl.style.display = "none"), ms);
  }

  // ---------- activation ----------

  function setActive(on) {
    state.active = on;
    root.style.display = on ? "block" : "none";
    if (on) {
      sizeCanvas();
      syncToolbar();
      renderDom();
      toast("Annotate — draw a mark, then type the comment · 1:arrow 2:box 3:circle 4:pen 5:note 6:pin · ⌘Z undo · ⌘⏎ save · Esc exit", 4500);
    }
  }

  function sizeCanvas() {
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.round(innerWidth * dpr);
    canvas.height = Math.round(innerHeight * dpr);
    canvas.style.width = `${innerWidth}px`;
    canvas.style.height = `${innerHeight}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    redraw();
  }
  window.addEventListener("resize", () => state.active && sizeCanvas());

  function setTool(tool) {
    state.tool = tool;
    syncToolbar();
  }

  function syncToolbar() {
    for (const b of toolbar.querySelectorAll("[data-tool]"))
      b.classList.toggle("ann-on", b.dataset.tool === state.tool);
    for (const b of toolbar.querySelectorAll("[data-color]"))
      b.classList.toggle("ann-on", b.dataset.color === state.color);
  }

  toolbar.addEventListener("mousedown", (e) => e.stopPropagation());
  toolbar.addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    if (b.dataset.tool) setTool(b.dataset.tool);
    if (b.dataset.color) { state.color = b.dataset.color; syncToolbar(); }
    if (b.dataset.act === "undo") undo();
    if (b.dataset.act === "clear") { state.ops = []; redraw(); renderDom(); }
    if (b.dataset.act === "save") void capture();
  });

  // ---------- canvas shapes ----------

  function redraw() {
    ctx.clearRect(0, 0, innerWidth, innerHeight);
    for (const op of state.ops) drawOp(op);
    if (state.drawing) drawOp(state.drawing);
  }

  function drawOp(op) {
    ctx.strokeStyle = op.color;
    ctx.lineWidth = 2.5;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    if (op.type === "arrow") {
      const { x1, y1, x2, y2 } = op;
      ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
      const a = Math.atan2(y2 - y1, x2 - x1);
      ctx.beginPath();
      ctx.moveTo(x2, y2); ctx.lineTo(x2 - 13 * Math.cos(a - 0.45), y2 - 13 * Math.sin(a - 0.45));
      ctx.moveTo(x2, y2); ctx.lineTo(x2 - 13 * Math.cos(a + 0.45), y2 - 13 * Math.sin(a + 0.45));
      ctx.stroke();
    } else if (op.type === "box") {
      ctx.strokeRect(Math.min(op.x1, op.x2), Math.min(op.y1, op.y2),
        Math.abs(op.x2 - op.x1), Math.abs(op.y2 - op.y1));
    } else if (op.type === "circle") {
      ctx.beginPath();
      ctx.ellipse((op.x1 + op.x2) / 2, (op.y1 + op.y2) / 2,
        Math.max(2, Math.abs(op.x2 - op.x1) / 2), Math.max(2, Math.abs(op.y2 - op.y1) / 2),
        0, 0, Math.PI * 2);
      ctx.stroke();
    } else if (op.type === "pen") {
      ctx.beginPath();
      op.points.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
      ctx.stroke();
    }
  }

  root.addEventListener("mousedown", (e) => {
    if (!state.active || e.button !== 0) return;
    if (e.target.closest("[data-ann-ui]")) return; // toolbar, notes, pin boxes
    e.preventDefault();
    if (state.tool === "note") return addNote(e.clientX, e.clientY);
    if (state.tool === "pin") return addPin(e.clientX, e.clientY);
    state.drawing = state.tool === "pen"
      ? { type: "pen", color: state.color, points: [[e.clientX, e.clientY]] }
      : { type: state.tool, color: state.color, x1: e.clientX, y1: e.clientY, x2: e.clientX, y2: e.clientY };
  });
  window.addEventListener("mousemove", (e) => {
    if (!state.drawing) return;
    if (state.drawing.type === "pen") state.drawing.points.push([e.clientX, e.clientY]);
    else { state.drawing.x2 = e.clientX; state.drawing.y2 = e.clientY; }
    redraw();
  });
  window.addEventListener("mouseup", () => {
    if (!state.drawing) return;
    const d = state.drawing;
    state.drawing = null;
    // A stray click is not a mark — discarding it keeps a slipped mouse from
    // opening a comment box nobody asked for.
    const tiny = d.type === "pen"
      ? d.points.length < 3
      : Math.abs(d.x2 - d.x1) < 4 && Math.abs(d.y2 - d.y1) < 4;
    if (tiny) return redraw();
    const a = anchorOf(d);
    const el = elementAt(a.x, a.y);
    d.n = nextN();
    d.note = "";
    d.target = el ? describe(el) : null;
    d.notePos = {
      x: clamp(a.x + 14, 4, Math.max(4, innerWidth - 210)),
      y: clamp(a.y + 14, 4, Math.max(4, innerHeight - 90)),
    };
    state.ops.push(d);
    redraw();
    renderDom();
    focusOp(d.n);
  });

  const clamp = (v, lo, hi) => Math.min(Math.max(v, lo), hi);

  /** Next badge number, shared by drawn marks and element pins. */
  const nextN = () => state.ops.reduce((m, o) => (o.n ? Math.max(m, o.n) : m), 0) + 1;

  /** What a mark points at: an arrow's tip, anything else's centre. */
  function anchorOf(op) {
    if (op.type === "arrow") return { x: op.x2, y: op.y2 };
    if (op.type === "pen") {
      const xs = op.points.map((p) => p[0]);
      const ys = op.points.map((p) => p[1]);
      return { x: (Math.min(...xs) + Math.max(...xs)) / 2, y: (Math.min(...ys) + Math.max(...ys)) / 2 };
    }
    return { x: (op.x1 + op.x2) / 2, y: (op.y1 + op.y2) / 2 };
  }

  function focusOp(n) {
    domLayer.querySelector(`[data-op="${n}"] .ann-editable`)?.focus();
  }

  function undo() {
    state.ops.pop();
    redraw();
    renderDom();
  }

  // ---------- element pins ----------

  function elementAt(x, y) {
    root.classList.add("ann-picking");
    const el = document.elementFromPoint(x, y);
    root.classList.remove("ann-picking");
    return el && el !== document.documentElement && el !== document.body ? el : null;
  }

  /** id → data-testid → short tag.class:nth-of-type path, ≤6 levels. */
  function cssSelector(el) {
    if (el.id) return `#${CSS.escape(el.id)}`;
    const testid = el.getAttribute("data-testid");
    if (testid) return `[data-testid="${testid}"]`;
    const parts = [];
    let node = el;
    while (node && node.nodeType === 1 && node !== document.body && parts.length < 6) {
      if (node.id) { parts.unshift(`#${CSS.escape(node.id)}`); break; }
      let part = node.tagName.toLowerCase();
      const classes = [...node.classList].filter((c) => /^[a-zA-Z][\w-]*$/.test(c)).slice(0, 2);
      if (classes.length) part += "." + classes.map((c) => CSS.escape(c)).join(".");
      const parent = node.parentElement;
      if (parent) {
        const same = [...parent.children].filter((c) => c.tagName === node.tagName);
        if (same.length > 1) part += `:nth-of-type(${same.indexOf(node) + 1})`;
      }
      parts.unshift(part);
      node = parent;
    }
    return parts.join(" > ");
  }

  /** Best-effort React component name off the dev-build fiber. Never throws. */
  function reactComponentName(el) {
    try {
      const key = Object.keys(el).find((k) => k.startsWith("__reactFiber$"));
      if (!key) return null;
      let fiber = el[key];
      for (let i = 0; fiber && i < 30; i++, fiber = fiber.return) {
        const t = fiber.type;
        const name = typeof t === "function" ? (t.displayName || t.name)
          : t && typeof t === "object" ? (t.displayName || t.render?.name) : null;
        if (name && name !== "Fragment") return name;
      }
    } catch { /* best-effort only */ }
    return null;
  }

  /** Everything worth knowing about an element, for pins and mark targets alike. */
  function describe(el) {
    return {
      selector: cssSelector(el),
      component: reactComponentName(el),
      tag: el.tagName.toLowerCase(),
      text: (el.innerText || el.getAttribute("aria-label") || "").trim().replace(/\s+/g, " ").slice(0, 120),
    };
  }

  function addPin(x, y) {
    const el = elementAt(x, y);
    if (!el) return toast("No element under the cursor.");
    const r = el.getBoundingClientRect();
    const n = nextN();
    state.ops.push({
      type: "pin", n, color: state.color,
      rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
      ...describe(el),
      note: "",
    });
    renderDom();
    focusOp(n);
  }

  // ---------- notes & pin boxes (DOM layer) ----------

  function addNote(x, y) {
    state.ops.push({ type: "note", color: state.color, x, y, text: "" });
    renderDom();
    const nodes = domLayer.querySelectorAll(".ann-note .ann-editable");
    nodes[nodes.length - 1]?.focus();
  }

  function editable(op, placeholder) {
    const div = document.createElement("div");
    div.className = "ann-editable";
    div.contentEditable = "true";
    div.dataset.placeholder = placeholder;
    div.textContent = op.text ?? op.note ?? "";
    div.addEventListener("input", () => {
      const v = div.innerText.replace(/\n+$/, "");
      if (op.type === "note") op.text = v; else op.note = v;
    });
    div.addEventListener("mousedown", (e) => e.stopPropagation());
    div.addEventListener("keydown", (e) => {
      if (!(e.metaKey || e.ctrlKey) && e.key !== "Escape") e.stopPropagation();
    });
    return div;
  }

  /** `pos` is the {x, y} the box writes back to — a note op, or a mark's notePos. */
  function makeDraggable(handle, box, pos) {
    handle.addEventListener("mousedown", (e) => {
      e.preventDefault(); e.stopPropagation();
      const dx = e.clientX - pos.x, dy = e.clientY - pos.y;
      const move = (ev) => {
        pos.x = ev.clientX - dx; pos.y = ev.clientY - dy;
        box.style.left = `${pos.x}px`; box.style.top = `${pos.y}px`;
      };
      const up = () => { removeEventListener("mousemove", move); removeEventListener("mouseup", up); };
      addEventListener("mousemove", move);
      addEventListener("mouseup", up);
    });
  }

  function renderDom() {
    domLayer.textContent = "";
    for (const op of state.ops) {
      if (op.type === "pin") {
        const wrap = document.createElement("div");
        wrap.setAttribute("data-ann-ui", "");
        wrap.dataset.op = op.n;
        wrap.style.color = op.color;

        const outline = document.createElement("div");
        outline.className = "ann-outline";
        Object.assign(outline.style, {
          left: `${op.rect.x - 2}px`, top: `${op.rect.y - 2}px`,
          width: `${op.rect.w + 4}px`, height: `${op.rect.h + 4}px`,
        });

        const badge = document.createElement("div");
        badge.className = "ann-badge";
        badge.innerHTML = `<span>${op.n}</span>`;
        Object.assign(badge.style, { left: `${op.rect.x - 10}px`, top: `${op.rect.y - 10}px` });

        const noteBox = document.createElement("div");
        noteBox.className = "ann-pin-note";
        const below = op.rect.y + op.rect.h + 8;
        Object.assign(noteBox.style, {
          left: `${Math.min(op.rect.x, innerWidth - 270)}px`,
          top: below < innerHeight - 60 ? `${below}px` : `${Math.max(4, op.rect.y - 40)}px`,
        });
        const ed = editable(op, `note for #${op.n}…`);
        ed.addEventListener("input", () => noteBox.classList.toggle("ann-empty", !ed.innerText.trim()));
        noteBox.classList.toggle("ann-empty", !op.note.trim());
        noteBox.appendChild(ed);

        wrap.append(outline, badge, noteBox);
        domLayer.appendChild(wrap);
      } else if (op.type === "note") {
        const box = document.createElement("div");
        box.className = "ann-note";
        box.setAttribute("data-ann-ui", "");
        box.style.left = `${op.x}px`;
        box.style.top = `${op.y}px`;
        box.style.color = op.color;
        const handle = document.createElement("div");
        handle.className = "ann-note-handle";
        const ed = editable(op, "type a note…");
        ed.addEventListener("input", () => box.classList.toggle("ann-empty", !ed.innerText.trim()));
        box.classList.toggle("ann-empty", !op.text.trim());
        box.append(handle, ed);
        makeDraggable(handle, box, op);
        domLayer.appendChild(box);
      } else if (op.n) {
        // A drawn mark: numbered badge on what it points at, comment box beside
        // it. The badge stays visible even with an empty box, so a mark in the
        // screenshot always has a section to match in the markdown.
        const wrap = document.createElement("div");
        wrap.setAttribute("data-ann-ui", "");
        wrap.dataset.op = op.n;
        wrap.style.color = op.color;

        const a = anchorOf(op);
        const badge = document.createElement("div");
        badge.className = "ann-badge";
        badge.innerHTML = `<span>${op.n}</span>`;
        Object.assign(badge.style, { left: `${a.x - 10}px`, top: `${a.y - 10}px` });

        const box = document.createElement("div");
        box.className = "ann-note";
        box.style.left = `${op.notePos.x}px`;
        box.style.top = `${op.notePos.y}px`;
        box.style.color = op.color;
        const handle = document.createElement("div");
        handle.className = "ann-note-handle";
        const ed = editable(op, `comment for #${op.n}…`);
        ed.addEventListener("input", () => box.classList.toggle("ann-empty", !ed.innerText.trim()));
        box.classList.toggle("ann-empty", !op.note.trim());
        box.append(handle, ed);
        makeDraggable(handle, box, op.notePos);

        wrap.append(badge, box);
        domLayer.appendChild(wrap);
      }
    }
  }

  // ---------- keyboard ----------

  const inEditor = (e) =>
    e.target instanceof Element &&
    (e.target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName));

  window.addEventListener("keydown", (e) => {
    const mod = e.metaKey || e.ctrlKey;
    if (mod && e.shiftKey && e.key.toLowerCase() === "a") {
      e.preventDefault(); e.stopPropagation();
      return setActive(!state.active);
    }
    if (!state.active) return;
    if (e.key === "Escape") {
      e.preventDefault(); e.stopPropagation();
      // Typing is the main flow now, so Esc leaves the comment box first and
      // only closes the overlay on a second press.
      if (inEditor(e)) return e.target.blur();
      return setActive(false);
    }
    if (mod && e.key === "Enter") { e.preventDefault(); e.stopPropagation(); return void capture(); }
    if (mod && e.key.toLowerCase() === "z") { e.preventDefault(); e.stopPropagation(); return undo(); }
    if (!mod && !inEditor(e) && /^[1-6]$/.test(e.key)) {
      e.preventDefault(); e.stopPropagation();
      setTool(TOOLS[Number(e.key) - 1]);
    }
  }, true);

  // ---------- capture ----------

  /** Where a drawn mark sits, in one line of prose. */
  function markGeometry(op) {
    const r = Math.round;
    if (op.type === "arrow") return `from (${r(op.x1)},${r(op.y1)}) to (${r(op.x2)},${r(op.y2)})`;
    const xs = op.type === "pen" ? op.points.map((p) => p[0]) : [op.x1, op.x2];
    const ys = op.type === "pen" ? op.points.map((p) => p[1]) : [op.y1, op.y2];
    const x = Math.min(...xs), y = Math.min(...ys);
    return `x=${r(x)}, y=${r(y)}, w=${r(Math.max(...xs) - x)}, h=${r(Math.max(...ys) - y)}`;
  }

  function buildMarkdown() {
    const marked = state.ops.filter((o) => o.n).sort((a, b) => a.n - b.n);
    const notes = state.ops.filter((o) => o.type === "note" && o.text.trim());
    const clean = (s) => String(s ?? "").replace(/`/g, "'");
    const element = (d) => [
      `- Component: ${d.component ? `\`${clean(d.component)}\`` : "(unknown)"}`,
      `- Element: \`<${d.tag}>\`${d.text ? ` — “${clean(d.text)}”` : ""}`,
    ];
    const lines = [
      `# UI annotations — ${new Date().toISOString()}`,
      "",
      `- Route: \`${clean(location.pathname + location.search + location.hash)}\``,
      `- Viewport: ${innerWidth}×${innerHeight} @${window.devicePixelRatio}x`,
      "",
      "![Annotated screenshot]({{IMAGE}})",
      "",
      "Badge numbers in the screenshot correspond to the numbered sections below.",
      "",
    ];
    if (marked.length) {
      lines.push(
        "## Numbered annotations",
        "",
        "A drawn mark is a pointer — the comment under it is the request. Its"
          + " “Points at” is inferred from the mark (an arrow's tip, anything"
          + " else's centre), so treat it as a strong hint, not a certainty;"
          + " the screenshot is the tiebreaker.",
        "",
      );
      for (const op of marked) {
        lines.push(`### ${op.n}. ${op.note.trim() || "(no comment)"}`, "");
        if (op.type === "pin") {
          lines.push(
            "- Kind: element pin",
            `- Selector: \`${clean(op.selector)}\``,
            ...element(op),
            `- Box: x=${op.rect.x}, y=${op.rect.y}, w=${op.rect.w}, h=${op.rect.h}`,
          );
        } else {
          lines.push(
            `- Kind: drawn ${op.type} — ${markGeometry(op)}`,
            ...(op.target
              ? [`- Points at: \`${clean(op.target.selector)}\``, ...element(op.target)]
              : ["- Points at: (no element resolved — locate it in the screenshot)"]),
          );
        }
        lines.push("");
      }
    }
    if (notes.length) {
      lines.push("## Free-floating notes", "");
      for (const n of notes) lines.push(`- (at ${Math.round(n.x)},${Math.round(n.y)}) ${clean(n.text.trim())}`);
      lines.push("");
    }
    if (!marked.length && !notes.length)
      lines.push("_No marks or text notes — see the screenshot._", "");
    return lines.join("\n");
  }

  const twoFrames = () =>
    new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(r, 60))));

  let capturing = false;
  async function capture() {
    if (capturing) return;
    capturing = true;
    const markdown = buildMarkdown();
    root.classList.add("ann-capturing"); // hides toolbar/toast + empty note boxes
    await twoFrames();
    let res = null;
    try {
      res = window.meeluAnnotator?.capture
        ? await window.meeluAnnotator.capture({ markdown })
        : null;
    } catch (err) {
      res = { error: err instanceof Error ? err.message : String(err) };
    }
    root.classList.remove("ann-capturing");
    capturing = false;
    if (res?.ok) {
      toast(`Saved ${res.mdPath} + screenshot (${res.pngPath})`, 5000);
    } else {
      // IPC bridge unavailable or failed — don't fail silently.
      const fallback = markdown.replace("{{IMAGE}}", "(no screenshot — bridge unavailable, attach one manually)");
      try { await navigator.clipboard.writeText(fallback); } catch { /* ignore */ }
      toast(`Could not save via the app (${res?.error ?? "bridge unavailable"}) — markdown copied to clipboard; please take a screenshot manually.`, 8000);
    }
  }
})();

#!/usr/bin/env python3
"""One-shot codemod: Tailwind palette utilities -> fleet-design-system role utilities.

Maps every `text|bg|border|ring|... -<hue>-<shade>` class by MEANING (DESIGN.md §3), not nearest colour:
  red/rose -> danger, amber/yellow/orange -> warning, green/emerald/lime -> success,
  blue/sky/indigo -> info (links -> brand, solid CTA buttons -> primary ink),
  violet/purple/fuchsia -> tag-1, pink -> tag-2, cyan/teal -> tag-4 (identity),
  gray/zinc/slate/neutral/stone -> surface/text/border roles.
Roles flip with [data-theme], so every `dark:<colour>` utility is deleted.
Usage: python3 scripts/fds-codemod.py src [--dry]
"""
import re
import sys
from pathlib import Path

NEUTRAL = {"gray", "zinc", "slate", "neutral", "stone"}
STATUS = {"red": "danger", "rose": "danger", "amber": "warning", "yellow": "warning", "orange": "warning",
          "green": "success", "emerald": "success", "lime": "success",
          "blue": "info", "sky": "info", "indigo": "info"}
TAGS = {"violet": "tag-1", "purple": "tag-1", "fuchsia": "tag-1", "pink": "tag-2", "cyan": "tag-4", "teal": "tag-4"}
HUES = "|".join(sorted(NEUTRAL | set(STATUS) | set(TAGS), key=len, reverse=True))
PROPS = r"ring-offset|text|bg|border(?:-[trblxyse])?|ring|divide|placeholder|from|to|via|fill|stroke|outline|decoration|shadow|accent|caret"
ROLE_WORDS = (r"white|black|transparent|current|inherit|background|foreground|card|muted|muted-foreground|primary|"
              r"secondary|accent|border|input|ring|popover|destructive|brand|success|warning|danger|info|neutral")
TOK = re.compile(r"(?<![\w\-/\[])((?:[\w\-\[\]&=.>*~+()'\"#]+?:)*)(-?)(" + PROPS + r")-(" + HUES + r")-(\d{2,3})((?:/\d+)|(?:/\[[\d.]+\]))?(?![\w\-])")
WB = re.compile(r"(?<![\w\-/\[])((?:[\w\-\[\]&=.>*~+()]+?:)*)(" + PROPS + r")-(white|black)((?:/\d+)|(?:/\[[\d.]+\]))?(?![\w\-])")
DARK_COLOUR = re.compile(r"(?<![\w\-/\[])(?:[\w\-\[\]&=.>*~+()]+?:)*dark:(?:[\w\-\[\]&=.>*~+()]+?:)*(?:" + PROPS + r")-(?:(?:" + HUES + r")-\d{2,3}|" + ROLE_WORDS + r")(?:/\d+|/\[[\d.]+\])?(?![\w\-])")
FOCUS = ("focus", "focus-visible", "focus-within")


def op_of(op):
    if not op:
        return None
    m = re.match(r"/(\d+)$", op)
    return int(m.group(1)) if m else None


def neutral(prop, shade, variants, op):
    hover = any(v in ("hover", "group-hover", "active", "data-[state=open]") for v in variants)
    focus = any(v in FOCUS for v in variants)
    p = prop.split("-")[0] if prop.startswith("border") else prop
    if prop == "ring-offset":
        return "background", None
    if p == "text":
        if shade >= 700: return "foreground", op
        if shade >= 400: return "muted-foreground", op
        if shade == 300: return "muted-foreground", op or "/70"
        return "primary-foreground", op
    if p == "bg":
        o = op_of(op)
        if shade <= 100: return ("accent" if hover else "muted"), (op if not hover else None)
        if shade <= 300: return ("accent" if hover else "border"), op
        if shade <= 600: return "muted-foreground", op
        if o is not None and o <= 20: return "foreground", op
        if o is not None: return "black", op
        return "primary", ("/90" if hover else None)
    if p in ("border", "divide"):
        if focus: return "ring", None
        if shade <= 200: return "border", op
        if shade <= 400: return "input", op
        if shade <= 700: return "muted-foreground", op
        return "foreground", op
    if p in ("ring", "outline"):
        if focus: return "ring", None
        if shade <= 200: return "border", op
        if shade <= 400: return "input", op
        return "foreground", op
    if p == "placeholder": return "muted-foreground", op
    if p in ("from", "via", "to"): return ("muted" if shade <= 200 else "foreground"), op
    if p == "shadow": return "foreground", op or "/10"
    if shade <= 300: return "muted-foreground", op
    return "foreground", op


def coloured(role, prop, shade, variants, op, ctx, is_tag=False):
    hover = any(v in ("hover", "group-hover", "active") for v in variants)
    focus = any(v in FOCUS for v in variants)
    p = prop.split("-")[0] if prop.startswith("border") else prop
    if prop == "ring-offset":
        return "background", None
    if role == "info" and (p in ("ring", "outline") or (p == "border" and focus)):
        return "ring", None
    if p == "text":
        if role == "info" and "underline" in ctx: return "brand", None
        if shade <= 100 and not is_tag: return f"{role}-foreground", op
        return role, op
    if p == "bg":
        if role == "info" and shade >= 500 and "text-white" in ctx and "hover:" in ctx:
            return "primary", ("/90" if hover else None)
        if shade <= 100: return f"{role}-subtle", op
        if shade <= 300: return (f"{role}-subtle" if is_tag else f"{role}-border"), op
        if hover and not op: return role, "/90"
        return role, op
    if p in ("border", "divide", "ring", "outline"):
        if is_tag: return role, op or "/40"
        if shade <= 400: return f"{role}-border", None if op_of(op) and op_of(op) >= 50 else op
        return role, op
    if p in ("from", "via", "to"):
        return (f"{role}-subtle" if shade <= 200 else role), op
    if p == "shadow": return role, op or "/20"
    return role, op


def map_token(m, ctx):
    variants_s, neg, prop, hue, shade, op = m.groups()
    variants = [v for v in variants_s.split(":") if v]
    if "dark" in variants:
        return ""
    shade = int(shade)
    if hue in NEUTRAL:
        role, op2 = neutral(prop, shade, variants, op)
    elif hue in TAGS:
        role, op2 = coloured(TAGS[hue], prop, shade, variants, op, ctx, is_tag=True)
    else:
        role, op2 = coloured(STATUS[hue], prop, shade, variants, op, ctx)
    return f"{variants_s}{neg}{prop}-{role}{op2 or ''}"


def map_wb(m):
    variants_s, prop, wb, op = m.groups()
    variants = [v for v in variants_s.split(":") if v]
    if "dark" in variants:
        return ""
    p = prop.split("-")[0] if prop.startswith("border") else prop
    if wb == "white":
        if op: return m.group(0)  # white/NN = overlay on media, stays
        if p == "bg": return m.group(0) if op else f"{variants_s}{prop}-card"  # white/NN = overlay on media, stays
        if p in ("border", "ring-offset", "divide"): return f"{variants_s}{prop}-background{op or ''}"
        return m.group(0)  # text-white stays (paired below with solid fills)
    if p == "text": return f"{variants_s}{prop}-foreground{op or ''}"
    return m.group(0)  # bg-black scrims stay


STRING = re.compile(r"\"[^\"\n]*\"|'[^'\n]*'|`[^`]*`")
FG_PAIR = [("bg-primary", "primary-foreground"), ("bg-danger", "danger-foreground"), ("bg-success", "success-foreground"),
           ("bg-warning", "warning-foreground"), ("bg-info", "info-foreground")]


def fix_piece(p, ctx):
    q = DARK_COLOUR.sub("", p)
    q = TOK.sub(lambda m: map_token(m, ctx), q)
    q = WB.sub(map_wb, q)
    return q


def fix_string(s):
    ctx = s
    parts = re.split(r"(\s+)", s)  # even = pieces, odd = separators
    out = []
    drop_next_sep = False
    for i, part in enumerate(parts):
        if i % 2 == 1:
            if drop_next_sep:
                drop_next_sep = False
                continue
            out.append(part)
            continue
        new = fix_piece(part, ctx)
        if part and not new:
            # removed a whole class: drop one adjacent separator (preceding if any, else following)
            if out and i > 0 and out[-1].isspace() and "\n" not in out[-1]:
                out.pop()
            elif i + 1 < len(parts) and "\n" not in parts[i + 1]:
                drop_next_sep = True
            continue
        out.append(new)
    s2 = "".join(out)
    if s2 == s:
        return s
    for bg, fg in FG_PAIR:
        if re.search(re.escape(bg) + r"(?![\w\-/])", s2):
            s2 = re.sub(r"(?<![\w\-:])text-(?:white|primary-foreground)(?![\w\-/])", f"text-{fg}", s2)
            break
    return s2


def process(text):
    return STRING.sub(lambda m: fix_string(m.group(0)), text)


def main():
    root = Path(sys.argv[1])
    dry = "--dry" in sys.argv
    changed = 0
    for f in sorted(root.rglob("*")):
        if f.suffix not in (".jsx", ".js") or "node_modules" in f.parts:
            continue
        t = f.read_text()
        n = process(t)
        if n != t:
            changed += 1
            if not dry:
                f.write_text(n)
    print(f"{'would change' if dry else 'changed'} {changed} files")


if __name__ == "__main__":
    main()

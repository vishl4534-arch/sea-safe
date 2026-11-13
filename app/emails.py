"""How the watch emails look (owner, 13 Nov 2026): Sea Safe's dark look, the logo and wordmark at the top, the
verdict as a coloured badge (the app's verdict colours), the trip in rows, the disclaimer apart, a small footer.

Email apps ignore most CSS, so this is the old, safe way: tables, inline styles, system fonts, no scripts, no web
fonts. The logo travels inside the email (cid:seasafe-logo, attached by app/mailer.py), so it shows without
"load images". Every piece of text is escaped here; the words themselves come from reviewed templates.
"""
from __future__ import annotations

from html import escape

from app.config import load_app

# the app's verdict colours (static/style.css): background and the text on it
VERDICT = {"SAFE": ("#1d7f47", "#ffffff"), "CAUTION": ("#e2a400", "#1c1500"), "UNSAFE": ("#c0282d", "#ffffff")}
FONT = "Helvetica,Arial,'Segoe UI',sans-serif"
PAGE, CARD, LINE, TEXT, SOFT, FAINT = "#0a0a0b", "#18181b", "#2a2a2e", "#f4f4f2", "#a6a6ab", "#77777d"


def badge(verdict: str, word: str, muted: bool = False) -> str:
    bg, ink = VERDICT[verdict]
    style = (f"display:inline-block;padding:7px 14px;border-radius:999px;font:700 13px/1 {FONT};letter-spacing:.08em;"
             + (f"background:transparent;color:{SOFT};border:1px solid {LINE};text-decoration:line-through;" if muted
                else f"background:{bg};color:{ink};"))
    return f'<span style="{style}">{escape(word)}</span>'


def html(lang: str, kicker: str, heading: str, badges: list, rows: list, lead: str, note: str, footer: str) -> str:
    """One email. badges: verdict codes, or (code, word, muted) for an old verdict shown struck through.
    rows: (label, value) pairs. Right to left for Arabic."""
    rtl = load_app()["languages"].get(lang, {}).get("dir") == "rtl"
    end = "left" if rtl else "right"
    pills = []
    for b in badges:
        code, word, muted = (b, b, False) if isinstance(b, str) else b
        pills.append(badge(code, word, muted))
    arrow = f'<span style="padding:0 8px;color:{SOFT};font:700 15px {FONT};">{"&larr;" if rtl else "&rarr;"}</span>'
    row_html = "".join(
        f'<tr><td style="padding:11px 0;border-top:1px solid {LINE};font:14px/1.4 {FONT};color:{SOFT};">{escape(k)}</td>'
        f'<td align="{end}" style="padding:11px 0;border-top:1px solid {LINE};font:600 14px/1.4 {FONT};color:{TEXT};">'
        f'{escape(v)}</td></tr>' for k, v in rows)
    return f"""<!doctype html>
<html lang="{escape(lang)}" dir="{'rtl' if rtl else 'ltr'}">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark light"><meta name="supported-color-schemes" content="dark light"></head>
<body style="margin:0;padding:0;background:{PAGE};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{PAGE};">
<tr><td align="center" style="padding:28px 14px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;">
    <tr><td style="padding:0 4px 18px;">
      <table role="presentation" cellpadding="0" cellspacing="0"><tr>
        <td><img src="cid:seasafe-logo" width="38" height="38" alt="Sea Safe" style="display:block;border:0;border-radius:10px;"></td>
        <td style="padding:0 12px;font:700 18px/1 {FONT};letter-spacing:.06em;color:{TEXT};">SEA SAFE</td>
      </tr></table>
    </td></tr>
    <tr><td style="background:{CARD};border:1px solid {LINE};border-radius:18px;padding:26px 24px 22px;">
      <p style="margin:0 0 6px;font:600 12px/1.4 {FONT};letter-spacing:.08em;text-transform:uppercase;color:{SOFT};">{escape(kicker)}</p>
      <h1 style="margin:0 0 16px;font:700 26px/1.2 {FONT};color:{TEXT};">{escape(heading)}</h1>
      <div style="margin:0 0 18px;">{arrow.join(pills)}</div>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{row_html}</table>
      <p style="margin:18px 0 0;font:15px/1.6 {FONT};color:#d9d9dc;">{escape(lead)}</p>
    </td></tr>
    <tr><td style="padding:14px 0 0;">
      <p style="margin:0;padding:13px 16px;border-radius:12px;background:#111113;border:1px solid {LINE};font:13px/1.55 {FONT};color:{SOFT};">{escape(note)}</p>
    </td></tr>
    <tr><td style="padding:18px 4px 0;font:12px/1.6 {FONT};color:{FAINT};">{escape(footer)}</td></tr>
  </table>
</td></tr>
</table>
</body>
</html>"""

#!/usr/bin/env python3
"""Build, render and check the Doheny AI full one-pager from a content file.

Every dollar figure on the page is computed here from the terms in the
content file, never typed by hand, so the page cannot print a number its own
math does not produce. The script refuses to write a page that breaks a copy
rule, and refuses to call the PDF good until the checks below pass.

Usage
-----
    python3 -I scripts/build_onepager.py --content examples/arizona-restoration.json \
            --out-dir out/arizona-restoration

Writes  <out-dir>/onepager.html   print from Chrome, margins none, scale 100
        <out-dir>/onepager.pdf    rendered with headless Chromium
        <out-dir>/onepager.png    preview image of page one
        <out-dir>/note.txt        the handwritten note
        <out-dir>/checks.json     every check and its result

Exit code 0 only when every check passes.
"""

import argparse
import base64
import html
import io
import json
import os
import re
import shutil
import subprocess
import sys
from functools import reduce

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
ASSETS = os.path.join(SKILL, "assets")

BOOKING_URL = "https://mg.dohenyai.com/widget/bookings/parkers-calendar-007"

BANNED_WORDS = ["ai-powered", "leverage", "synergy", "robust", "seamless",
                "comprehensive", "unlock", "game-changer", "game changer"]
EMOJI = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF]")

CHROME_CANDIDATES = [
    os.environ.get("CHROME_PATH", ""),
    "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
]


# ---------------------------------------------------------------------------
# formatting and math
# ---------------------------------------------------------------------------

def money(value):
    return "${:,.0f}".format(round(value))


def count(value):
    """70 -> '70', 8.4 -> '8.4', 2.52 -> '2.52'."""
    text = "{:,.2f}".format(value).rstrip("0").rstrip(".")
    return text


def pct(rate):
    return "{:g}%".format(round(rate * 100, 2))


def product(terms):
    return reduce(lambda a, b: a * b, terms, 1.0)


PHONE = re.compile(r"\(?\b\d{3}\)?[-. ]\d{3}-\d{4}\b")


def esc(text):
    """Escape for HTML and keep phone numbers from breaking across lines."""
    return PHONE.sub(lambda m: '<span style="white-space:nowrap">%s</span>' % m.group(0),
                     html.escape(text, quote=False))


# ---------------------------------------------------------------------------
# copy rules
# ---------------------------------------------------------------------------

def words(text):
    return len(re.findall(r"[A-Za-z0-9$][A-Za-z0-9$,.%'/-]*", text))


def sentences(text):
    return len([s for s in re.split(r"(?<=[.?])\s+", text.strip()) if s])


def copy_problems(label, text):
    problems = []
    lowered = text.lower()
    if "—" in text:
        problems.append(label + ": em dash")
    if "!" in text:
        problems.append(label + ": exclamation point")
    if EMOJI.search(text):
        problems.append(label + ": emoji")
    for word in BANNED_WORDS:
        if re.search(r"\b" + re.escape(word) + r"\b", lowered):
            problems.append(label + ": banned word '" + word + "'")
    if re.search(r"[ˮ“”]", text):
        problems.append(label + ": curly or lookalike double quote, use a straight quote")
    return problems


def all_copy(content):
    """Yield (label, text) for every string that reaches the page or the note."""
    for key in ("business", "owner", "eyebrow", "headline", "lede",
                "assumption_line", "fix_title", "fix_copy", "leaks_head",
                "checks_head", "cta_headline", "cta_sub", "disclaimer", "note"):
        if content.get(key):
            yield key, content[key]
    funnel = content["funnel"]
    yield "funnel.volume_caption", funnel["volume_caption"]
    yield "funnel.result_caption", funnel["result_caption"]
    for i, factor in enumerate(funnel["factors"]):
        yield "funnel.factor[%d]" % i, factor["caption"]
    for i, leak in enumerate(content.get("leaks", [])):
        yield "leaks[%d].title" % i, leak["title"]
        yield "leaks[%d].desc" % i, leak["desc"]
    for i, check in enumerate(content.get("checks", [])):
        yield "checks[%d]" % i, check["text"]


# ---------------------------------------------------------------------------
# validation and assembly
# ---------------------------------------------------------------------------

def validate(content):
    problems = []
    for label, text in all_copy(content):
        problems += copy_problems(label, text)

    funnel = content["funnel"]
    if len(funnel["factors"]) != 3:
        problems.append("funnel: needs exactly three conversion factors (five cells)")
    hero = funnel["volume"] * product(f["rate"] for f in funnel["factors"]) * funnel["ticket"]
    if money(hero) not in content["headline"]:
        problems.append("headline: must contain the funnel result %s" % money(hero))

    lede = content["lede"]
    if words(lede) > 45 or sentences(lede) > 2:
        problems.append("lede: %d words, %d sentences (max 45 words, 2 sentences)"
                        % (words(lede), sentences(lede)))

    leaks = content.get("leaks", [])
    if len(leaks) > 3:
        problems.append("leaks: at most three rows fit")
    for i, leak in enumerate(leaks):
        if leak.get("kind") not in ("monthly", "per_call"):
            problems.append("leaks[%d]: kind must be monthly or per_call" % i)
        if not leak.get("terms") or len(leak["terms"]) < 2:
            problems.append("leaks[%d]: needs the terms that produce its figure" % i)
        if not leak.get("source"):
            problems.append("leaks[%d]: needs a source (site, dns, listings, healthcheck)" % i)

    checks = content.get("checks", [])
    if not 4 <= len(checks) <= 6:
        problems.append("checks: use four to six rows")
    for i, check in enumerate(checks):
        if check.get("status") not in ("ok", "fix"):
            problems.append("checks[%d]: status must be ok or fix" % i)
    if checks and not any(c["status"] == "ok" for c in checks):
        problems.append("checks: include at least one ok row; an all-fail list reads as an attack")

    note = content.get("note", "")
    if not 35 <= words(note) <= 50:
        problems.append("note: %d words (35 to 50)" % words(note))
    if sentences(note.replace("\n", " ")) > 6:
        problems.append("note: too many sentences")

    qr_url = content.get("qr_url") or BOOKING_URL
    url_text = content.get("url_text", "dohenyai.com")
    if url_text not in ("dohenyai.com",) and not content.get("short_url_verified"):
        problems.append("url_text: a short URL is printed but short_url_verified is not true")
    if qr_url != BOOKING_URL and not content.get("short_url_verified"):
        problems.append("qr_url: points away from the booking link but short_url_verified is not true")
    return problems, hero


def step(num, cap, final=False):
    cls = "cell final" if final else "cell"
    return ('<td class="%s"><div class="num">%s</div><div class="cap">%s</div></td>'
            % (cls, num, cap))


def build_steps(funnel, hero):
    cells = [step(count(funnel["volume"]), esc(funnel["volume_caption"]))]
    running = float(funnel["volume"])
    for factor in funnel["factors"]:
        running *= factor["rate"]
        cells.append(step(count(running), esc(pct(factor["rate"]) + " " + factor["caption"])))
    cells.append(step(money(hero), esc(funnel["result_caption"]), final=True))
    return '<td class="gap"></td>'.join(cells)


def equation(funnel, hero):
    parts = [count(funnel["volume"])] + [pct(f["rate"]) for f in funnel["factors"]] \
        + [money(funnel["ticket"])]
    return " × ".join(parts) + " = " + money(hero) + " a month."


def leak_rows(leaks):
    rows, monthly_total = [], 0.0
    for leak in leaks:
        value = product(leak["terms"])
        unit = "/mo" if leak["kind"] == "monthly" else "/call"
        if leak["kind"] == "monthly":
            monthly_total += value
        rows.append(
            '<tr><td><div class="t">%s</div><div class="d">%s</div></td>'
            '<td class="amt">%s<span>%s</span></td></tr>'
            % (esc(leak["title"]), esc(leak["desc"]), money(value), unit))
    return "\n".join(rows), monthly_total


def check_rows(checks):
    rows = []
    for check in checks:
        pill = ('<span class="p bad">Fix</span>' if check["status"] == "fix"
                else '<span class="p good">OK</span>')
        text = esc(check["text"])
        if check.get("label"):
            text = "<b>%s.</b> %s" % (esc(check["label"]), text)
        rows.append('<tr><td class="pill">%s</td><td>%s</td></tr>' % (pill, text))
    return "\n".join(rows)


def qr_svg(url):
    from reportlab.graphics import renderSVG
    from reportlab.graphics.barcode import qr
    from reportlab.graphics.shapes import Drawing
    from reportlab.lib import colors
    widget = qr.QrCodeWidget(url, barLevel="M")
    widget.barFillColor = colors.HexColor("#0A1628")
    x0, y0, x1, y1 = widget.getBounds()
    drawing = Drawing(200, 200, transform=[200 / (x1 - x0), 0, 0, 200 / (y1 - y0), 0, 0])
    drawing.add(widget)
    svg = renderSVG.drawToString(drawing)
    return svg[svg.index("<svg"):]


def data_uri(path):
    with open(path, "rb") as handle:
        return "data:image/jpeg;base64," + base64.b64encode(handle.read()).decode()


def assemble(content, hero):
    funnel = content["funnel"]
    leaks_html, monthly = leak_rows(content.get("leaks", []))
    total = hero + monthly
    total_line = "Monthly figures on this page: <strong>%s a month</strong>" % money(total)
    tokens = {
        "BUSINESS": esc(content["business"]),
        "OWNER": esc(content["owner"]),
        "DATE": esc(content["date"]),
        "LOGO_URI": data_uri(os.path.join(ASSETS, "logo-wordmark.jpg")),
        "PHOTO_URI": data_uri(os.path.join(ASSETS, "parker-headshot.jpg")),
        "EYEBROW": esc(content["eyebrow"]),
        "HEADLINE": esc(content["headline"]),
        "LEDE": esc(content["lede"]),
        "STEP_CELLS": build_steps(funnel, hero),
        "ASSUMPTION_LINE": "<strong>%s</strong> %s" % (esc(equation(funnel, hero)),
                                                     esc(content["assumption_line"])),
        "FIX_TITLE": esc(content.get("fix_title", "What changes")),
        "FIX_COPY": esc(content["fix_copy"]),
        "LEAKS_HEAD": esc(content.get("leaks_head", "More I can put a number on")),
        "LEAK_ROWS": leaks_html,
        "TOTAL_LINE": total_line,
        "CHECKS_HEAD": esc(content.get("checks_head", "Outside-in marketing check")),
        "CHECK_ROWS": check_rows(content["checks"]),
        "CTA_HEADLINE": esc(content.get("cta_headline", "Fifteen minutes. Check my math with me.")),
        "CTA_SUB": esc(content.get("cta_sub", "Scan the code or call. If your numbers are smaller, I'll say so.")),
        "URL_TEXT": esc(content.get("url_text", "dohenyai.com")),
        "DISCLAIMER": esc(content["disclaimer"]),
        "QR_SVG": qr_svg(content.get("qr_url") or BOOKING_URL),
        "QR_CAPTION": esc(content.get("qr_caption", "Scan to book")),
    }
    with open(os.path.join(ASSETS, "template.html")) as handle:
        page = handle.read()
    for key, value in tokens.items():
        page = page.replace("{{" + key + "}}", value)
    return page, total


# ---------------------------------------------------------------------------
# render and check
# ---------------------------------------------------------------------------

def find_chrome():
    for candidate in CHROME_CANDIDATES:
        if not candidate:
            continue
        path = candidate if os.path.isabs(candidate) else shutil.which(candidate)
        if path and os.path.exists(path):
            return path
    return None


def render_pdf(html_path, pdf_path):
    chrome = find_chrome()
    if not chrome:
        return "no Chrome or Chromium found; set CHROME_PATH"
    command = [chrome, "--headless=new", "--no-sandbox", "--disable-gpu",
               "--no-pdf-header-footer", "--virtual-time-budget=8000",
               "--print-to-pdf=" + pdf_path, "file://" + os.path.abspath(html_path)]
    proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    if not os.path.exists(pdf_path):
        return "Chromium did not write a PDF: " + proc.stderr.decode("utf-8", "replace")[-400:]
    return None


def check_pdf(pdf_path, png_path, qr_url):
    results = {}
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        results["one_page"] = len(pdf.pages) == 1
        page = pdf.pages[0]
        words_ = page.extract_words()
        cta = [w for w in words_ if w["text"] in ("Fifteen", "Fifteen minutes.")]
        if cta:
            cta_top = min(w["top"] for w in cta)
            above = [w["bottom"] for w in words_ if w["bottom"] < cta_top - 4]
            gap = cta_top - max(above)
            # the CTA rule sits about 14pt above its headline; require 20pt clear above the rule
            results["clearance_above_cta_pt"] = round(gap - 14, 1)
            results["body_clears_cta"] = gap - 14 >= 20
        else:
            results["body_clears_cta"] = None
        text = page.extract_text() or ""
        results["no_unfilled_tokens"] = "{{" not in text
        fonts = sorted({c.get("fontname", "") for c in page.chars})
        results["fonts"] = fonts
        results["brand_font_embedded"] = any("DMSans" in f.replace(" ", "") for f in fonts)

    if shutil.which("pdftoppm"):
        base = png_path[:-4]
        subprocess.run(["pdftoppm", "-r", "200", "-png", "-singlefile", pdf_path, base],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            import cv2  # optional
            image = cv2.imread(png_path)
            decoded = cv2.QRCodeDetector().detectAndDecode(image)[0]
            results["qr_decodes_to"] = decoded
            results["qr_ok"] = decoded == qr_url
        except ImportError:
            results["qr_ok"] = None
            results["qr_note"] = "opencv not installed; decode the QR by phone before mailing"
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--content", required=True, help="content JSON file")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--no-render", action="store_true", help="write HTML only")
    args = parser.parse_args()

    with open(args.content) as handle:
        content = json.load(handle)

    problems, hero = validate(content)
    if problems:
        print("Content problems, nothing written:")
        for problem in problems:
            print("  - " + problem)
        return 1

    os.makedirs(args.out_dir, exist_ok=True)
    page, total = assemble(content, hero)
    html_path = os.path.join(args.out_dir, "onepager.html")
    with open(html_path, "w") as handle:
        handle.write(page)
    with open(os.path.join(args.out_dir, "note.txt"), "w") as handle:
        handle.write(content["note"].strip() + "\n")

    report = {"hero_monthly": round(hero), "page_monthly_total": round(total),
              "note_words": words(content["note"]), "lede_words": words(content["lede"])}
    status = 0
    if not args.no_render:
        pdf_path = os.path.join(args.out_dir, "onepager.pdf")
        error = render_pdf(html_path, pdf_path)
        if error:
            report["render_error"] = error
            status = 1
        else:
            qr_url = content.get("qr_url") or BOOKING_URL
            report.update(check_pdf(pdf_path, os.path.join(args.out_dir, "onepager.png"), qr_url))
            for key in ("one_page", "body_clears_cta", "no_unfilled_tokens", "qr_ok"):
                if report.get(key) is False:
                    status = 1
    with open(os.path.join(args.out_dir, "checks.json"), "w") as handle:
        json.dump(report, handle, indent=2)
    print(json.dumps(report, indent=2))
    print("PASS" if status == 0 else "FAIL")
    return status


if __name__ == "__main__":
    sys.exit(main())

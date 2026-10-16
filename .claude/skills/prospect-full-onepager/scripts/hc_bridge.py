#!/usr/bin/env python3
"""Turn marketing-healthcheck output into candidate rows for the one-pager.

Reads what the health check wrote for one domain and returns only findings
that pass the printability rule in references/healthcheck-mapping.md:

  1. the evidence is deterministic (a DNS record, a tag in the HTML, a missing
     tel: link), never an inference such as "no DKIM selector found";
  2. the owner can verify it in about 30 seconds;
  3. it either ties to a leak Doheny closes (a "leak" candidate with a sizing
     template) or is a plain hygiene fact (a "check" candidate, ok or fix).

Nothing here writes copy for the page. It hands Claude the evidence and the
sizing template; Claude writes the words and fills the terms in the content
file, where build_onepager.py does the arithmetic.

Usage
-----
    python3 -I scripts/hc_bridge.py --hc-out out --domain example.com
    python3 -I scripts/hc_bridge.py --hc-out out --domain example.com --json candidates.json
"""

import argparse
import json
import os
import sys


def load(path):
    if not os.path.exists(path):
        return None
    with open(path) as handle:
        return json.load(handle)


def subject_rows(scorecard, domain):
    for subject in (scorecard or {}).get("subjects", []):
        if subject.get("domain") == domain or domain in (subject.get("name"), ""):
            return subject.get("rows", {})
    subjects = (scorecard or {}).get("subjects", [])
    return subjects[0].get("rows", {}) if len(subjects) == 1 else {}


def email_candidates(email):
    out = []
    if not email:
        return out
    spf, dmarc, dkim = email.get("spf") or {}, email.get("dmarc") or {}, email.get("dkim") or {}
    if spf.get("found") is False:
        out.append({"type": "check", "status": "fix", "id": "W4.spf", "label": "SPF",
                    "evidence": "no v=spf1 TXT record",
                    "sizing": "unsized: a spoofing and deliverability risk, not a monthly leak"})
    elif spf.get("permissive"):
        out.append({"type": "check", "status": "fix", "id": "W4.spf", "label": "SPF",
                    "evidence": "SPF is permissive: " + str(spf.get("record")),
                    "sizing": "unsized"})
    policy = dmarc.get("policy")
    if dmarc.get("found") is False:
        out.append({"type": "check", "status": "fix", "id": "W4.dmarc", "label": "DMARC",
                    "evidence": "no _dmarc TXT record", "sizing": "unsized"})
    elif policy == "none":
        out.append({"type": "check", "status": "fix", "id": "W4.dmarc", "label": "DMARC",
                    "evidence": "p=none (monitor only): " + str(dmarc.get("record")),
                    "sizing": "unsized"})
    elif policy in ("quarantine", "reject"):
        out.append({"type": "check", "status": "ok", "id": "W4.dmarc", "label": "DMARC",
                    "evidence": "p=" + policy, "sizing": "n/a"})
    # A found DKIM selector is proof. A missing one is not: selectors are guessed.
    if dkim.get("any_found"):
        out.append({"type": "check", "status": "ok", "id": "W4.dkim", "label": "Email signing",
                    "evidence": "DKIM selectors found: " + ", ".join(dkim.get("selectors_found") or []),
                    "sizing": "n/a"})
    mx = email.get("mx") or {}
    if mx.get("count") == 0:
        out.append({"type": "manual", "id": "W4.mx", "label": "MX",
                    "evidence": "no MX record; mail may still arrive through the A record",
                    "sizing": "do not print; email the owner's address and see if it bounces"})
    return out


def signal_candidates(signals):
    out = []
    if not signals:
        return out
    mobile = signals.get("mobile_probe") or {}
    if mobile.get("status") == 200 and not mobile.get("tel_links"):
        out.append({"type": "leak", "id": "W2.tel", "label": "Phone not tappable",
                    "evidence": "mobile home page has no tel: link",
                    "sizing": "monthly calls x mobile share (0.6) x drop-off when the number "
                              "cannot be tapped (0.10) x close rate x ticket"})
    tags = (signals.get("tags") or {}).get("by_category") or {}
    if not tags.get("analytics") and mobile.get("word_count", 0) and mobile.get("word_count") > 150:
        out.append({"type": "check", "status": "fix", "id": "M1", "label": "Analytics",
                    "evidence": "no analytics tag on sampled pages", "sizing": "unsized"})
    if tags.get("ads") and not tags.get("call_tracking"):
        out.append({"type": "leak", "id": "M2.calls", "label": "Calls not tracked",
                    "evidence": "ad tags present (%s), no call tracking"
                                % ", ".join(v.get("vendor", "?") if isinstance(v, dict) else str(v)
                                            for v in tags.get("ads")),
                    "sizing": "monthly ad spend (ask) x share misallocated without call "
                              "attribution (0.20 to 0.30); print only with a stated spend"})
    robots = signals.get("robots_txt") or {}
    if robots.get("ai_crawlers_blocked"):
        out.append({"type": "check", "status": "fix", "id": "F4.ai", "label": "AI search",
                    "evidence": "robots.txt blocks " + ", ".join(robots["ai_crawlers_blocked"]),
                    "sizing": "unsized"})
    llms = signals.get("llms_txt") or {}
    if llms.get("present"):
        out.append({"type": "check", "status": "ok", "id": "F4.llms", "label": "AI search",
                    "evidence": "llms.txt present", "sizing": "n/a"})
    return out


def score_candidates(rows):
    out = []
    picks = {
        "O2": ("leak", "Overlapping vendors", "duplicate vendor or agency fee per month (ask)"),
        "S1": ("leak", "Content retainer idle", "monthly retainer, only when targets.expects names one"),
        "F5": ("check", "Indexing", "unsized unless a named money page is noindexed"),
        "M3": ("leak", "Ad tags vs live ads", "monthly ad spend (ask) for a channel with no tag"),
        "W3": ("check", "HTTPS", "unsized"),
    }
    for cid, (kind, label, sizing) in picks.items():
        row = rows.get(cid) or {}
        score = row.get("score")
        if score in (0, 1) and not row.get("caps"):
            out.append({"type": kind, "status": "fix", "id": cid, "label": label,
                        "evidence": row.get("evidence"), "sizing": sizing})
        elif score == 2 and kind == "check":
            out.append({"type": "check", "status": "ok", "id": cid, "label": label,
                        "evidence": row.get("evidence"), "sizing": "n/a"})
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--hc-out", required=True, help="marketing-healthcheck out/ directory")
    parser.add_argument("--domain", required=True)
    parser.add_argument("--json", help="also write the candidates to this file")
    args = parser.parse_args()

    domain = args.domain.lower().replace("https://", "").replace("http://", "").strip("/")
    email = load(os.path.join(args.hc_out, "email__%s.json" % domain))
    signals = load(os.path.join(args.hc_out, "signals__%s.json" % domain))
    rows = subject_rows(load(os.path.join(args.hc_out, "scorecard.json")), domain)

    candidates = email_candidates(email) + signal_candidates(signals) + score_candidates(rows)
    result = {"domain": domain,
              "inputs": {"email": email is not None, "signals": signals is not None,
                         "scorecard": bool(rows)},
              "candidates": candidates}
    if args.json:
        with open(args.json, "w") as handle:
            json.dump(result, handle, indent=2)
    print(json.dumps(result, indent=2))
    if email is None and signals is None:
        print("no health-check output for %s in %s" % (domain, args.hc_out), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

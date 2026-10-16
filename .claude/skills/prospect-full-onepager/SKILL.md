---
name: prospect-full-onepager
description: "Builds the Doheny AI cold-outreach mailer: one printed page for a business owner that combines a sized operational revenue leak (missed calls, slow follow-up, form friction) with an outside-in marketing health check (email authentication, stray phone numbers, second sites, tracking, reviews), puts a dollar figure on every finding that can carry one, and ends with a QR code to book a call. Also writes the handwritten note for the envelope. Use when Parker asks for a full one-pager, a mailer with the marketing check, a direct-mail audit, or to combine the prospect one-pager with the marketing health check for a named business and URL."
---

# Full prospect one-pager (leaks + marketing check)

One letter-size page in an envelope with a handwritten note, mailed cold to the owner. Its only job is to earn a 15-minute call. It shows a stranger looked closely, sizes what that costs in dollars, invites correction, and points to a QR code. Nothing is sold on the page: no prices, no tiers, no mention of the $999 Assessment.

The page holds, top to bottom:
1. **Hero leak**: the one operational leak the owner will recognise from their own day, with a five-cell funnel and the math printed out.
2. **What changes**: what closing that leak looks like, with the cost of the human version of the job.
3. **More I can put a number on**: up to three more leaks with a dollar figure each, mixing operational leaks and marketing findings that sit on a lead's path.
4. **Outside-in marketing check**: four to six verified facts from the health check, marked OK or Fix, with at least one OK.
5. **Call to action**: Parker's photo and contact details, plus the QR code.

No letter grade on the page. With a free-tier run it is usually an indicative band anyway, and a cold "D" reads as an attack.

**Input required:** business name and website URL. Owner name too if known. Never guess a URL. If the owner's name cannot be confirmed from the site, the BBB/state filings, or LinkedIn, or if sources disagree (family businesses often list a parent and a child), say so and ask Parker before the envelope is addressed.

**Outputs, in this order:**
1. `onepager.html` (print from Chrome) and `onepager.pdf`, plus a PNG preview.
2. The handwritten note as plain text.
3. One handover line: what to confirm before mailing.

---

## Step 1. Collect signals

Follow `references/signal-collection.md`. In short:
- Run the `marketing-healthcheck` free tier on the domain, then `scripts/hc_bridge.py` to get printable candidates. This needs Parker's own machine; cloud sandboxes and hosting bot challenges block the page checks.
- Do the **listings sweep**: every phone number shown beside the business's name or address, loaded from the page itself, plus any second site using the name.
- Read the site as a customer would: first contact, after-hours path, what the form confirms, scale signals, broken details.

Record every fact with its source and date in the content file's `_sources` block.

## Step 2. Classify the vertical

Pick one from the frame in `references/leak-sizing.md`. State it in one line with the signals behind it. It does not go on the page.

## Step 3. Size everything, then choose

Set **one rate set** for the prospect (volume, miss rate, defection, close, ticket) and reuse it for every row describing the same behaviour. Size every operational leak and every health-check finding that can carry a dollar figure, using the mapping table in `references/leak-sizing.md`:
- **Monthly leak**: a volume times rates times ticket. These add into the page total.
- **Per-call leak**: close rate times ticket, for findings where nobody outside can know the volume (stray phone numbers). Never added to the total.
- **Check row, unsized**: hygiene risks (SPF, DMARC, analytics). No invented dollar figure.

Then choose:
- **Hero**: the largest leak that is also the easiest for the owner to recognise from their own day.
- **Leak rows**: up to three, strongest evidence first. At least one should come from the health check when it found something that carries a figure.
- **Check rows**: four to six, at least one OK. Lead with uniform, unarguable failures (a missing DNS record) over mixed ones.

**Printability rule.** A finding goes on paper only if (a) its evidence is deterministic and you loaded it yourself, (b) the owner can check it in about 30 seconds, and (c) it ties to a leak Doheny closes or is a plain hygiene fact. Never print a DKIM "missing" (the probe guesses selectors), an MX gap (mail can arrive through the A record), a search-snippet phone number, or anything about how the business runs behind the front door (partner relationships, staffing) under a heading that says you found it.

## Step 4. Write the content file

Copy `examples/arizona-restoration.json` and replace everything. Copy rules, all enforced by the build script:
- `headline`: "Missed [thing] could be costing you about $X a month." or the closest true equivalent. Must contain the funnel result.
- `lede`: two sentences, at most 45 words. Opens with a specific, true detail from the site, then the operational reality.
- `funnel`: one volume, exactly three rates, and a ticket. The script prints the running counts and the equation.
- `assumption_line`: always invites correction.
- `fix_copy`: what changes, then the human-version cost in one sentence. Three printed lines at most. No Doheny price.
- `leaks[].desc`: the specific thing seen, then the compact assumptions. `terms` must multiply to the figure.
- `checks[]`: `label` plus one sentence of plain-English consequence. Write "nothing tells inboxes to reject mail forged in your name", not "p=none".
- `disclaimer`: names the sources (site, public DNS records, listings) and says "Starting figures for a conversation, not a quote."
- `note`: see Step 7.

**Brand rules (non-negotiable).** Navy #0A1628 and Doheny Blue #2D7FF9 only. Blue appears in the eyebrow, the QR frame and the "What changes" tint, nowhere else. No orange, no red, no gradients, no emoji. DM Sans, sentence case, lowercase wordmark from `assets/logo-wordmark.jpg` (never redrawn). No em dashes, no exclamation points. Banned: AI-powered, leverage, synergy, robust, seamless, comprehensive, unlock, game-changer. Type never below 12px for captions or 14px for body. If it does not fit, cut copy.

**QR and link.** Ask Parker once whether the per-prospect short URL (`dohenyai.com/<owner-first-name>`) redirect is live. If it is, set `qr_url`, `url_text` and `short_url_verified: true`. If not, keep the booking link `https://mg.dohenyai.com/widget/bookings/parkers-calendar-007` and print `dohenyai.com`. The script refuses a short URL that is not marked verified. A dead link on paper is the worst failure this piece can have, and a plain booking link tracks nothing.

## Step 5. Build, render, check

```bash
python3 -I scripts/build_onepager.py --content prospects/<slug>/content.json --out-dir prospects/<slug>/mailer
```

The script refuses content that breaks a rule above, then renders with headless Chrome or Chromium (`CHROME_PATH` to override) and checks:
1. exactly one page;
2. body copy ends at least 20pt above the call-to-action rule;
3. no unfilled `{{` tokens;
4. the QR decodes to the intended URL (needs `opencv-python-headless`; without it, scan the code with a phone);
5. whether DM Sans was embedded (if not, the PDF fell back to Inter: say so, and tell Parker the Chrome print has the brand font).

Exit code 0 only when every check passes. Then look at `onepager.png` once yourself.

Parker prints from the HTML in Chrome: Print, margins none, scale 100, background graphics on.

## Step 6. Manual checks before mailing (the model cannot do these)

Ten minutes as a customer: call the main line at an off-hour, submit the form and time the response, call each stray number printed on the page and note who answers, and check the most recent review date. If a result contradicts the page, fix the page. If it confirms it, say so in the note ("I called 602-497-4035 at 9pm and reached someone else" is the best sentence this piece can contain, but only if it is true).

## Step 7. The handwritten note

- 35 to 50 words, four sentences at most, copied by hand.
- Opens with the owner's first name and a comma.
- One specific thing about the business, so the owner knows a person looked. Never claim Parker called, visited or tested something he did not.
- One ask: scan the code or call. No meeting pitch, price or offer.
- Admits the numbers are estimates and invites correction.
- "Mesa neighbor" or similar only when the prospect is in the Phoenix metro.
- Signed "Parker". Plain words, no exclamation points, no em dashes.

## Step 8. Handover line

One line: what to confirm before mailing (owner name, anything sourced from an earlier session or a snippet, the QR target, that a printed short URL resolves). Then the cadence: call 3 days after the expected delivery date, email a day or two later. The letter works best as the second touch after a cold call or email.

## Tuning

After each batch, feed back the call volumes, tickets and close rates owners correct, and update the vertical table in `references/leak-sizing.md` so the next page starts from real numbers. Track which marketing findings owners react to; drop the ones that never get a reply.

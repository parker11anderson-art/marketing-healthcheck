# Sizing leaks: operational and marketing

Every dollar figure on the page is a product of terms in the content file. `build_onepager.py` multiplies them and refuses a headline that does not match. This file decides which terms to use.

## One rate set per page

The hero and every row that describes the same customer behaviour use the same rates. A night caller and a night form-filler are leaking to the same competitor, so they share the defection rate and the close rate. An owner who checks your math (the page asks them to) will notice two different numbers for one behaviour, and that one inconsistency costs the whole page.

Set these once per prospect, write them in `_sources`, then reuse them:

| Term | Default | Range | Scale it by |
|---|---|---|---|
| Monthly inbound calls or leads | from visible size | | team size, trucks, service area, review velocity (about 1 review per 8 to 15 jobs) |
| Share missed or delayed | 0.10 to 0.15 | 0.05 to 0.30 | single-owner shops sit high; staffed call desks sit low |
| Defection when not answered fast | 0.50 | 0.30 to 0.70 | emergency verticals high, planned purchases low |
| Close rate on a live lead | vertical table below | | |
| Average ticket | vertical table below | | |

## Vertical frame

| Vertical | Where the money leaks | Close | Ticket |
|---|---|---|---|
| Restoration | emergency call response, dispatch, adjuster updates, referral partners, job-status texts | 0.60 | $3,500 to $5,500 mitigation |
| Home services | speed to lead, missed calls, quote follow-up, review collection, dormant-customer reactivation | 0.35 to 0.50 | $350 to $900 service, $6k to $14k replacement |
| Property management | after-hours maintenance, tenant response, vacancy-to-tour | 0.25 tour to lease | one month's rent per vacancy-month |
| Medical, PT, chiro | booking friction, after-hours calls, no-show recovery, intake burden | 0.50 booked | $120 to $300 visit, x visits per plan |
| Hospitality | after-hours and international inquiries, direct vs OTA mix, past-guest reactivation | 0.30 | nightly rate x stay, OTA fee 15 to 18% |
| Beauty, barber | booking and rescheduling, no-show recovery, Instagram storefront, reviews | 0.60 | $45 to $180 |
| Specialty auto | quote speed (buyers compare 3 to 5 shops the same day), scheduling, reviews | 0.30 | $800 to $5,000 |
| Accounting, tax | intake speed, seasonal overflow, proposal turnaround, referral follow-up | 0.40 | $1,500 to $6,000 a year |
| Insurance, law | quote or intake speed, renewal outreach, consultation no-shows | 0.20 to 0.35 | first-year commission or case value |
| Other | walk the journey: find, contact, acknowledge, serve, retain | | |

## Marketing health findings: what gets a dollar figure

The user wants a dollar value on health-check findings where possible. "Possible" means the finding sits on the path of a lead the business would otherwise have closed, so it can borrow the page's rate set. Hygiene findings that only create risk stay as check rows with no dollar figure; printing a made-up dollar on them hands the owner a reason to dismiss the page.

| Finding (check) | Row type | Sizing | Example terms |
|---|---|---|---|
| Phone numbers carrying the business's name that it may not answer: second site, directory call-tracking numbers (listings sweep) | per-call leak | close rate x ticket, shown as $/call. Never monthly: nobody outside knows how many calls those numbers get | `[0.6, 4500]` = $2,700/call |
| No tap-to-call on mobile (W2) | monthly leak | calls x mobile share 0.6 x drop-off 0.10 x close x ticket | `[70, 0.6, 0.1, 0.6, 4500]` |
| Contact form friction: math captcha, no confirmation, no after-hours path (site read) | monthly leak | web leads x after-hours share x defection x close x ticket | `[20, 0.25, 0.5, 0.6, 4500]` |
| Ad tags with no call tracking (M2), ads with no tag or tags with no ads (M3) | monthly leak, only with a stated spend | spend x 0.20 to 0.30 misallocated | print only if spend is known or the owner told you |
| Two agencies' tags, abandoned vendor scripts (O2) | monthly leak, only with a known fee | the duplicate fee | otherwise a check row |
| Content retainer with nothing published in 6 months (S1) | monthly leak, only when the retainer is known | the retainer | otherwise leave it off: it accuses their agency on a guess |
| Unanswered reviews (T2), thin reviews vs competitors (T1) | monthly leak | jobs a month x share who check reviews 0.9 x share lost on a weaker profile 0.05 to 0.10 x ticket | needs a competitor count from the paid tier or a manual look |
| SPF missing or permissive, DMARC missing or p=none (W4) | check row, unsized | risk of spoofed invoices and spam-foldered estimates | in restoration and contracting, forged payment-change emails to insurers and homeowners are the concrete risk; say that on the call, not on the page |
| DKIM found | check row, ok | | never print "DKIM missing": the probe guesses selector names |
| Analytics absent (M1), AI crawlers blocked (F4), no llms.txt, missing schema | check row or leave off | | F4 items only when the prospect sells to people who ask AI assistants for recommendations |
| No MX record | never printed | | mail can still arrive through the A record. Email the owner's address and see whether it bounces |

## Arithmetic rules

- The funnel is exactly five cells: a volume, three rates, and the dollar result. Cells show the running count (70, 8.4, 4.2, 2.52, $11,340); the rates sit in the captions.
- Monthly rows add into the page total. Per-call rows never do.
- Round only at the end. The script prints whole dollars from the full product.
- If you cannot name a term's source, use the range midpoint and say "estimate pending operator validation" in `_sources`, then pick a row you can ground instead.

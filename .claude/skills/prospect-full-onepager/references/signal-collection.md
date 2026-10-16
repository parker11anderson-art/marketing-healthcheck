# Collecting the signals

Three sources feed the page. Collect all three before writing a word.

## 1. The marketing health check, free tier

Requires the `marketing-healthcheck` skill installed next to this one (`.claude/skills/marketing-healthcheck` or `~/.claude/skills/marketing-healthcheck`).

```bash
HC=~/.claude/skills/marketing-healthcheck      # or .claude/skills/marketing-healthcheck
mkdir -p prospects/<slug> && cd prospects/<slug>
cat > targets.json <<'JSON'
{"subjects": [{"name": "<Business>", "domain": "<domain>"}]}
JSON
export HEALTHCHECK_CONTACT="parker@dohenyai.com"
python3 "$HC/scripts/healthcheck.py" --targets targets.json --free
python3 -I <this skill>/scripts/hc_bridge.py --hc-out out --domain <domain> --json out/candidates.json
```

Run it from Parker's own machine. Two things break it elsewhere:

- **Cloud sandboxes** usually block outbound fetches and DNS. A cloud session can still read public DNS through any resolver it can reach, but it cannot run the page checks.
- **Bot challenges.** Many small-business hosts (SiteGround `sg-captcha`, Cloudflare) answer datacenter IPs with a challenge page. The health check will not solve a challenge, and neither do you. A `202` with `sg-captcha: challenge` or a `cf-chl` page means: run it from a residential connection. Do not score page checks off a challenge page.

If the page checks cannot run, the page can still ship on DNS findings, the listings sweep and Parker's own read of the site, but say which parts were not collected in the handover line.

## 2. The listings sweep (manual, ten minutes, often the best finding)

Directories and old sites route calls to numbers the business may not answer. Search:

- `"<Business name>" <city>` and `"<street address>"`, two pages of results
- the business name on Yelp, BBB, Chamber of Commerce, Yahoo Local, Angi, HomeAdvisor and the vertical's directories
- the bare domain without `www` and close spellings (singular/plural, `az` vs `arizona`), which is how a stale second site turns up

Record every phone number shown next to the business's name or address, and where. Print a number on the page only after you have loaded the page that shows it. A search-result snippet is not proof. Lead-generation directories often show their own tracking number, which routes the call to whoever pays them that month. That is the finding.

## 3. Parker's read of the site

As in the original one-pager skill: how a customer first reaches them (phone, form, booking, chat), what happens after hours, what the form confirms, scale signals, broken or placeholder details. If something is not on the site, say so. Do not invent it. Partner relationships, staffing, and anything else behind the front door are not "on your site" and never appear under that heading.

## What to write down

Put every fact and where it came from in the content file's `_sources` block, with the date. The handover line names anything that came from a snippet or an earlier session rather than a fetch made for this page.

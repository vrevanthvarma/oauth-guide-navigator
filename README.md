# OAuth Approval Navigator

Look up an app and you'll get a shareable guide to setting up your own OAuth app with that provider:
how hard it is, how long it takes (approval waits included), what can block you, and which steps an
agent can do for you. If an app isn't in the library, a research agent investigates it live.

I built this for the Composio APM Integrations take-home.

**Live app:** https://vrevanthvarma.github.io/oauth-guide-navigator/

It's a static site on GitHub Pages, so it loads right away and never sleeps. The guide library is open
to everyone. The live agent runs in your browser with your own free Gemini key, which stays in that
tab and goes only to Google.

**Backup app:** https://oapp-guide-navigator-dr8njdcz9cyj9vx2lvvwxm.streamlit.app

This is the same agent on Streamlit's free hosting, using an access code from my submission instead of
your own key. It can be slow to load. If it says it's asleep, click the wake-up button and wait about a
minute. If the page stays blank or part of it shows an error, reload it.

## The problem, as I understood it

When an agent builder's users connect an app through Composio, someone has to own the provider
OAuth app: the client ID and secret, the redirect URI and the approved scopes behind the consent
screen. Composio manages that app for 127 toolkits. For the other 275 OAuth toolkits, the developer
has to register their own. Even for managed toolkits, developers bring their own app to show their
brand, use custom scopes or get their own rate-limit quota.

The registration form is rarely the hard part. The hard part is what you can't see up front: whether
a provider will review your app, what the review requires, and how long it'll take. Gmail can take
months and an annual paid security assessment. Spotify blocks most new apps at 5 users. GitHub takes
minutes. If you're deciding what to launch, you need that answer before you start.

## Scope and key decisions

- **Lead with the verdict.** Every guide opens with difficulty (1-5), time to a first test connection,
  time until real users can connect, and whether the provider has to approve. That answers "an hour
  or weeks?" before you read any steps.
- **Approval and blockers get their own sections.** That's where launches slip, so each guide says
  what triggers a review, what it requires, the published wait, and how to fix common blockers.
- **Split agent work from human work.** Each step is marked 🤖 agent, 👤 you or 🤝 together, and each
  guide ends with "what an agent can do" and "where you take over" (signing in, verifying a domain,
  paying a fee, answering reviewers).
- **Evidence on every claim.** Each item carries a label (✅ tested by hand, 📄 official docs,
  💬 community, ⚠️ unverified) and its source link. Anything that isn't confirmed goes under "Not
  verified". The agent's told never to guess a wait time and never to claim it tested anything.
- **Start from Composio's own data.** Each guide says whether Composio already manages the OAuth app,
  using the managed OAuth directory, so you know if you need your own app at all.
- **Five seed apps, picked for different challenges and not for popularity:** GitHub (easy, no
  review), Slack (review only for a Marketplace listing, with a 10-workspace minimum), Shopify (a
  distribution choice you can't undo, review for public apps), Spotify (hard user cap, organizations
  only), Google/Gmail (verification plus an annual security assessment).
- **Shareable by default.** Each guide has a link (`?guide=<slug>`) and a Markdown download.

## How it works

```
site/                GitHub Pages version: the same guides, with the agent in the browser (agent.js)
build_site.py        Copies the guides, prompts and schema into site/data.json
app.py               Streamlit UI: library, lookup, guide pages, live generation
agent.py             Research agent (Gemini API with the URL context tool)
set_secrets.py       Saves the key and access code privately (masked input window)
guide_schema.py      The guide JSON schema and Markdown export
composio_managed.py  Composio's managed OAuth list (copied 2026-11-03)
guides/              Seed guides (researched by the coding agent from official docs, sources checked)
generated/           Guides the agent creates at runtime
EVIDENCE.md          What was checked, corrected and left unverified
```

Live generation runs on Gemini's free tier (`gemini-3.5-flash-lite` by default, set by `GEMINI_MODEL`)
in three steps:
1. **Plan:** Gemini lists the provider's official documentation pages worth reading.
2. **Read:** Gemini reads those pages with the URL context tool. Google fetches them and reports which
   ones actually loaded. Doc URLs move, so if fewer than 3 pages load, the next round tries pages linked
   from the ones that loaded, and it's told which pages worked and which failed.
3. **Write:** Gemini turns the notes into the guide JSON with structured output. A claim can only cite
   a page that actually loaded. Anything else gets labelled unverified.

Why not web search? Google Search grounding isn't included in Gemini's free tier (my first request got
a quota error), and the brief asked for no paid accounts. Reading official docs through URL context
keeps it free, and the server itself never downloads web pages.

You'll see progress live as each page is read. Runs took from 12 seconds to about 3 minutes in testing.
A generated guide is marked "generated live, not reviewed". On GitHub Pages there's no server to save
it on, so its share link carries the whole guide, compressed.

Why two versions? The first deployment on Streamlit's free hosting stalled on about 1 in 6 file requests
(see EVIDENCE.md), so first-time visitors could get a blank page. GitHub Pages can't run Python or keep
a key secret, so the page is static and the agent runs in the browser with the visitor's own key. The
prompts, schema and evidence rules are shared, so both versions follow the same rules.

## Run it locally

```
py -m pip install -r requirements.txt
pyw set_secrets.py --window          # paste your Gemini API key and choose an access code
py -m streamlit run app.py --server.address localhost
```

Browsing the library works without a key. Live generation needs `GEMINI_API_KEY`, which is free from
Google AI Studio. Keys live in `secrets.toml` (git-ignored) or Streamlit Cloud secrets, never in the
repo.

Live generation uses real API quota, so a public deployment has two optional guards: `ACCESS_CODE`
(reviewers enter it before the agent runs, and the library stays open) and `DAILY_LIMIT` (default 20
live guides a day).

## Security notes

- **GitHub Pages version:** it has no server and no key of mine. A visitor's key is kept only in that
  tab's memory and sent only to Google, and all guide text is added to the page as plain text.
- **Keys:** they're only in `.streamlit/secrets.toml` (git-ignored) or the host's secrets settings.
  Don't zip and share the project folder, since the zip would include `secrets.toml`.
- **The key never leaves the server:** it's read with `st.secrets` on the server and sent only to
  Google in a request header. It's never sent to the browser, never put in a prompt (so no prompt can
  make the model reveal it), and it's masked if it ever shows up in a message or log line. Gemini
  errors are replaced with fixed messages, and `.streamlit/config.toml` hides crash details and
  developer menus from visitors.
- **Commit guard:** `.githooks/pre-commit` blocks commits that stage `secrets.toml` or contain anything
  that looks like an API key. Turn it on once per clone: `git config core.hooksPath .githooks`.
- **Privacy:** the app itself stores nothing about visitors (no accounts, no analytics, no logs of what
  people type). Streamlit usage statistics are off for local runs in `.streamlit/config.toml`, but
  Community Cloud overrides that setting and its hosting pages load their own analytics, so the hosted
  site does collect usage data. Live lookups send only the app name and public documentation to Gemini.
  On Gemini's free tier Google may use requests to improve its products, so the lookup box asks you not
  to type personal information.
- **Untrusted web content:** live guides are built from pages the agent reads, so all guide text is
  rendered as plain text (no HTML, Markdown links or LaTeX from the web) and only `http(s)` links are
  shown. A claim can only cite a documentation page that actually loaded. Anything else loses its link
  and gets labelled unverified. Fields are capped at 1,500 characters.
- **Cost abuse:** live generation needs the access code (constant-time check, 5 wrong tries per
  session) and stops after `DAILY_LIMIT` runs a day. App names are capped at 80 characters.
- **Errors:** unexpected errors are logged on the server, and visitors see a generic message.
- **Local runs:** `--server.address localhost` keeps the dev server off your Wi-Fi network.
- **Dependencies:** versions are pinned in `requirements.txt`.

## Deploy

**GitHub Pages:** run `py build_site.py`, commit, then `git subtree push --prefix site origin gh-pages`.

**Streamlit Community Cloud:** create an app pointing at `app.py`, and add `GEMINI_API_KEY` (plus
optional `ACCESS_CODE`, `DAILY_LIMIT`) under the app's Secrets. The backup deployment was created with
`agent.py` as its main file, and Community Cloud can't change that without a new deployment, so
`agent.py` hands over to `app.py` when it's run directly.

## Limitations

- Seed guides were researched from official docs. I didn't attempt any setup by hand, so nothing is
  labelled ✅ tested, and nobody has reviewed the guides line by line. Check the linked sources.
- Generated guides are only as good as the docs the agent finds, and no person reviews them.
- Generated guides and the daily counter live on the server's disk, which Streamlit Cloud can reset on
  restart.
- The agent on GitHub Pages needs the visitor's own free Gemini key, and its guides aren't added to the
  shared library. The backup app avoids the key, but its hosting can stall.
- On the backup app's free hosting, some page files can stall and fail to load. The app detects this and
  reloads itself (at most 3 times), but a page that stays blank needs a manual reload (see EVIDENCE.md).
- The Composio managed list is a copy from 2026-11-03. It should come from Composio's API.
- Live generation runs on Gemini's free tier, so once its limits are used up, generation pauses until
  the next reset. A free-tier key without billing can't be charged.
- The agent can't search the web. It reads documentation pages it expects to exist, and many guessed
  URLs fail to load (7-10 per app in testing), so apps with thin or moved docs get shorter guides with
  more items marked unverified.

## Use of AI

I built this by directing an AI coding agent (Claude Code). It wrote the code, researched the seed
guides from official docs and ran the checks in EVIDENCE.md. I directed the work and made the calls on
what to ship, including the free Gemini setup and the security and privacy rules. The live research
agent is part of the product.

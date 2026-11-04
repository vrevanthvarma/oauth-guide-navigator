# OAuth Approval Navigator

Look up an app and get a shareable guide to setting up your own OAuth app with that provider:
how hard it is, how long it takes (including approval waits), what can block you, and which
steps an agent can do for you. Apps outside the library are investigated live by a research agent.

Built for the Composio APM Integrations take-home.

**Live app:** https://oapp-guide-navigator-dr8njdcz9cyj9vx2lvvwxm.streamlit.app

The guide library is open to everyone. Live generation needs an access code, which is in my
submission and not in this repo. If the page says the app has gone to sleep, click the wake-up
button and wait about a minute (Streamlit's free hosting sleeps after 12 hours without visitors).

## The problem, as I understood it

When an agent builder's users connect an app through Composio, someone has to own the provider
OAuth app: the client ID and secret, redirect URI and approved scopes behind the consent screen.
Composio manages that app for 127 toolkits; for the other 275 OAuth toolkits, the developer must
register their own. Even for managed toolkits, developers bring their own app to show their brand,
use custom scopes or get their own rate-limit quota.

The hard part is rarely the registration form. It is the part nobody can see up front: whether a
provider will review the app, what the review requires, and how long it takes. Gmail can take months
and an annual paid security assessment; Spotify blocks most new apps at 5 users; GitHub takes
minutes. A developer deciding what to launch needs that answer before they start.

## Scope and key decisions

- **Lead with the verdict.** Every guide opens with difficulty (1-5), time to a first test connection,
  time until real users can connect, and whether the provider must approve. That answers "an hour
  or weeks?" before any step-by-step detail.
- **Approval and blockers get their own sections.** They are where launches slip, so each guide says
  what triggers a review, what it requires, the published wait, and fixes for common blockers.
- **Split agent work from human work.** Each step is marked 🤖 agent, 👤 you or 🤝 together, and each
  guide ends with "what an agent can do" and "where you take over" (signing in, verifying a domain,
  paying a fee, answering reviewers).
- **Evidence on every claim.** Each item carries a label (✅ tested by hand, 📄 official docs,
  💬 community, ⚠️ unverified) and its source link. Anything not confirmed goes under "Not verified".
  The agent is told never to guess a wait time and never to claim it tested anything.
- **Start from Composio's own data.** Each guide says whether Composio already manages the OAuth app,
  using the managed OAuth directory, so a developer knows if they need their own app at all.
- **Five seed apps chosen for different challenges**, not popularity:
  GitHub (easy, no review), Slack (review only for Marketplace listing, with a 10-workspace minimum),
  Shopify (an irreversible distribution choice, review for public apps), Spotify (hard user cap,
  organizations only), Google/Gmail (verification plus an annual security assessment).
- **Shareable by default.** Each guide has a link (`?guide=<slug>`) and a Markdown download.

## How it works

```
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
2. **Read:** Gemini reads those pages with the URL context tool. Google fetches the pages and reports
   which ones actually loaded. Documentation URLs move, so if fewer than 3 pages load, a second round
   is told which pages worked and which failed and suggests others.
3. **Write:** Gemini turns the notes into the guide JSON with structured output. A claim may only
   cite a page that actually loaded; anything else is labelled unverified.

Why not web search: Google Search grounding is not included in Gemini's free tier (the first request
returned a quota error), and the brief asked for no paid accounts. Reading official docs through URL
context keeps it free, and the server itself never downloads web pages.

Progress (each page read) is shown live, and a run takes about 2-4 minutes. A generated guide is
marked "generated live, not reviewed".

## Run it locally

```
py -m pip install -r requirements.txt
pyw set_secrets.py --window          # paste your Gemini API key and choose an access code
py -m streamlit run app.py --server.address localhost
```

Browsing the library works without a key; live generation needs `GEMINI_API_KEY` (free from Google AI Studio). Keys live in
`secrets.toml` (git-ignored) or Streamlit Cloud secrets, never in the repo.

Live generation spends real API credit, so a public deployment has two optional guards:
`ACCESS_CODE` (reviewers enter it before the agent runs; the library stays open) and
`DAILY_LIMIT` (default 20 live guides per day).

## Security notes

- **Keys:** only in `.streamlit/secrets.toml` (git-ignored) or the host's secrets settings. Never zip
  and share the project folder, since the zip would include `secrets.toml`.
- **The key never leaves the server:** it is read with `st.secrets` on the server and sent only to
  Google in a request header. It is never sent to the browser, never placed in a prompt (so no prompt
  can make the model reveal it), and masked if it ever appears in a message or log line. Gemini errors
  are replaced with fixed messages, and `.streamlit/config.toml` hides crash details and developer
  menus from visitors.
- **Commit guard:** `.githooks/pre-commit` blocks commits that stage `secrets.toml` or contain
  anything that looks like an API key. Turn it on once per clone: `git config core.hooksPath .githooks`.
- **Privacy:** the app itself stores nothing about visitors (no accounts, no analytics, no logs of what
  people type). Streamlit usage statistics are off for local runs in `.streamlit/config.toml`, but
  Community Cloud overrides that setting and its hosting pages load their own analytics, so the hosted
  site does collect usage data. Live lookups send only the app name and public documentation to Gemini;
  on Gemini's free tier Google may use requests to improve its products, so the lookup box asks people
  not to type personal information.
- **Untrusted web content:** live guides are built from pages the agent reads, so all guide text is
  rendered as plain text (no HTML, Markdown links or LaTeX from the web), only `http(s)` links are
  shown, and a claim may only cite a documentation page that actually loaded; anything else loses its
  link and is labelled unverified. Fields are capped at 1,500 characters.
- **Cost abuse:** live generation needs the access code (constant-time check, 5 wrong tries per
  session) and stops after `DAILY_LIMIT` runs per day. App names are capped at 80 characters.
- **Errors:** unexpected errors are logged on the server; visitors see a generic message.
- **Local runs:** `--server.address localhost` keeps the dev server off your Wi-Fi network.
- **Dependencies:** versions are pinned in `requirements.txt`.

## Deploy

Push to GitHub, create an app on Streamlit Community Cloud pointing at `app.py`, and add
`GEMINI_API_KEY` (plus optional `ACCESS_CODE`, `DAILY_LIMIT`) under the app's Secrets.

## Limitations

- Seed guides were researched from official docs. No setup was attempted by hand, so nothing is
  labelled ✅ tested, and no person has reviewed the guides line by line. Check the linked sources.
- Generated guides are only as good as the docs the agent finds; they are not reviewed by a person.
- Generated guides and the daily counter are stored on the server's disk, which Streamlit Cloud can
  reset on restart.
- The Composio managed list is a copy from 2026-11-03; it should come from Composio's API.
- Live generation runs on Gemini's free tier; once its limits are used up, generation pauses until
  the next reset. A free-tier key without billing cannot be charged.
- The agent cannot search the web; it reads documentation pages it expects to exist. Many guessed
  URLs fail to load (7-10 per app in testing), so guides for apps with thin or moved docs come out
  shorter, with more items marked unverified.

## Use of AI

I built this by directing an AI coding agent (Claude Code). It wrote the code, researched the seed
guides from official docs and ran the checks in EVIDENCE.md. I directed the work and made the calls on
what to ship, including the free Gemini setup and the security and privacy rules. The live research
agent is part of the product.

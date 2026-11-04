# Evidence log

What was checked, what changed as a result, and what is still unverified. Date: 2026-11-03.

## How the seed guides were checked

| Check | Result |
|---|---|
| Every fact in the 5 seed guides traced to an official provider page | Done; each item links its source |
| All 21 source links opened | 21/21 returned HTTP 200 |
| Seed guides validated against the guide schema | 5/5 valid |
| Composio managed status compared with the managed OAuth directory | GitHub, Slack, Gmail managed; Spotify, Shopify bring-your-own |
| Hand test: register a GitHub OAuth app | Not done, so no guide item is labelled ✅ tested |
| Hand test: create a Slack app and turn on distribution | Not done, so no guide item is labelled ✅ tested |

The coding agent ran these checks. No person has reviewed the guides line by line.

## What the research corrected

- **Spotify's limit is 5 users, not 25.** Many third-party articles still say 25; the current docs
  say 5, and since 15 May 2025 extended quota is open only to organizations with 250k+ monthly
  active users. The guide calls Spotify "blocked for most" instead of "easy".
- **Slack Marketplace has a 10-workspace minimum.** Submission is blocked until the app runs on 10+
  workspaces active in the last 28 days, which matters more than the review time itself.
- **Shopify's distribution choice is permanent.** This moved "choose custom or public" to step 1.
- **Google verification length.** The docs give "up to 10 days" for sensitive scopes, but the
  unverified-apps page says verification "might require several months" depending on the data, so
  the guide shows both instead of one number.
- **Composio name matching.** "Google (Gmail API)" did not match "Gmail" in the managed list; the
  matcher was loosened and retested on Notion, Xero, Spotify and Zoom.

## Still unverified

- Google's user cap and refresh-token lifetime for apps in testing mode (widely reported, not on
  the pages read).
- Published review times for Slack Marketplace, Shopify App Store and Spotify partner applications.
- The Shopify App Store registration fee amount.
- Cost of Google's third-party security assessment.

## Live agent testing

Live runs on 2026-11-03 with a free-tier Gemini key (`gemini-3.5-flash-lite`). The guides are saved
in `generated/` and marked "not reviewed".

| App | Official pages read | Claims cited to docs / unverified | Difficulty | Time |
|---|---|---|---|---|
| Notion | 3 (overview, authorization, request limits) | 10 / 0 | 3/5 Medium | 101 s |
| Zoom | 3 (developer home, integrations, internal apps) | 5 / 2 | 3/5 Medium | 192 s |
| Xero | 2 (getting started, OAuth 2.0 scopes) | 9 / 0 | 3/5 | 149 s |

What the live runs changed:

- **Google Search grounding is not on the free tier.** The first search request returned a quota
  error, so research moved to the URL context tool, which works on the free tier.
- **Guessed doc URLs often fail.** Zoom's first round read only its developer home page because
  the planned URLs pointed at old documentation. A second round, told which pages loaded and which
  failed, found Zoom's current docs: 3 pages instead of 1 and 5 sourced claims instead of 2.
- **Difficulty was overrated.** Notion was first rated 4/5 because of its optional Marketplace
  security review. The rule now judges difficulty by what is needed before other people's accounts
  can connect, and Notion is rated 3/5 with the review described under approval.
- **Model availability.** `gemini-3.8-flash` returned "high demand" errors during testing, so the
  default is `gemini-3.5-flash-lite`; overloads are retried once.

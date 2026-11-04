"""Research agent: investigates how to set up and get approval for an app's OAuth app,
then turns its findings into a guide that follows GUIDE_SCHEMA.

Works on Gemini's free tier (Google Search grounding is not included there):
1. Plan   - Gemini lists the provider's official documentation pages worth reading.
2. Read   - Gemini reads those pages with the URL context tool; Google fetches them and reports
            which pages actually loaded. Only loaded pages can be cited.
3. Write  - Gemini turns the notes into the guide JSON (structured output).
"""
if __name__ == "__main__":  # the hosted deployment uses this file as its main file, so hand over to the app
    import streamlit as st  # before the heavy imports below, so pages load without them

    st.navigation([st.Page("app.py")], position="hidden").run()
    st.stop()

import datetime
import json
import re
import time
from urllib.parse import urlparse

import jsonschema
from google import genai
from google.genai import errors, types

from guide_schema import GUIDE_SCHEMA, safe_url, slugify

DEFAULT_MODEL = "gemini-3.5-flash-lite"
MAX_PAGES = 8
MAX_TEXT = 1500  # characters per field; web pages should not be able to flood a guide

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "official_domain": {"type": "string"},
        "urls": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["official_domain", "urls"],
    "additionalProperties": False,
}

PLAN_PROMPT = """A developer building an AI agent needs to register their own OAuth app with {app} and
get it approved for real users. List up to {n} URLs of {app}'s OFFICIAL developer documentation that
most likely cover: registering an OAuth app or integration, OAuth scopes or permissions, app review,
verification, publishing or approval, and limits before approval (test users, development mode,
rate limits). Use only the provider's own domains. Prefer specific documentation pages and include
the developer portal or docs home page as one entry. {retry_hint}"""

READ_PROMPT = """Read these official documentation pages about {app}:
{urls}

Write concise research notes for a developer who must register their own OAuth app with {app} and
get it ready for real users. Cover: where and how to register (account type, redirect URI rules,
client secret), scopes and which ones trigger review, the review or approval process (who reviews,
requirements such as privacy policy, domain verification, video, business entity, minimum users,
fees, published wait times), limits before approval, common blockers with fixes, and which steps an
agent could prepare versus what needs a signed-in human.

Use only what the pages say. After each fact, put the URL of the page it came from. If the pages do
not answer something, write UNCONFIRMED instead of guessing. Today's date is {today}.

End with a line starting "MORE PAGES:" and up to 5 full URLs of documentation pages linked from these
pages that would answer what is still UNCONFIRMED (OAuth, scopes, app review, publishing)."""

STRUCTURE_PROMPT = """Convert these research notes about {app} into the guide JSON.

Rules:
- Evidence: "docs" only when one of the official pages listed below supports the claim,
  "unverified" for anything else. Never use "tested" - nothing was tried by hand.
- "source" must be one of the URLs in the list below, or "" if none supports the item.
  Never invent a URL. "sources" lists the URLs you used, with short titles.
- difficulty: 1 = minutes, no review; 2 = minor checks; 3 = review only for some uses;
  4 = review or hard limits for most uses; 5 = weeks/months of review or effectively blocked.
  Judge it by what is required before OTHER people's accounts can connect. An optional
  marketplace, directory or app-store listing does not raise difficulty; mention it in approval.
  If the notes do not confirm a review, a limit or a block, do not assume one: use difficulty 3 with
  the label "Unclear" and list what is missing in "uncertain". Use 5 or "Blocked" only when a page says so.
- label: one or two words that match the difficulty, such as Easy, Medium, Hard or Blocked.
- Be specific about time and effort; if the notes give no number, say "not published" instead
  of guessing, and add it to "uncertain".
- Steps: 3-7 actionable steps in order. owner = "agent" when an agent can prepare or do it,
  "you" when a signed-in human must, "both" otherwise.
- Write for a developer who has never set this up before.

Official pages that were actually read:
{sources}

Research notes:
{notes}"""


def _call(client, model, contents, config):
    """Call Gemini. Errors become fixed messages: Google's raw error text is never shown to users."""
    for attempt in range(2):
        try:
            return client.models.generate_content(model=model, contents=contents, config=config)
        except errors.ClientError as e:
            code = getattr(e, "code", None)
            if code == 429:
                raise RuntimeError("The Gemini free-tier limit is used up for now. Try again later.") from None
            if code in (401, 403):
                raise RuntimeError("The site's Gemini key was rejected. The owner needs to check it.") from None
            raise RuntimeError(f"Gemini could not process this request (error {code}).") from None
        except errors.ServerError:
            if attempt == 0:
                time.sleep(4)  # overloads are usually brief; retry once
                continue
            raise RuntimeError("Gemini is busy right now. Try again in a minute.") from None


def _plan(client, model, app, retry_hint=""):
    config = types.GenerateContentConfig(response_mime_type="application/json", response_json_schema=PLAN_SCHEMA)
    resp = _call(client, model, PLAN_PROMPT.format(app=app, n=MAX_PAGES, retry_hint=retry_hint), config)
    try:
        urls = json.loads(resp.text).get("urls", [])
    except (TypeError, json.JSONDecodeError):
        urls = []
    return list(dict.fromkeys(u for u in (safe_url(x) for x in urls) if u))[:MAX_PAGES]


def _read(client, model, app, urls):
    config = types.GenerateContentConfig(tools=[types.Tool(url_context=types.UrlContext())])
    prompt = READ_PROMPT.format(app=app, urls="\n".join(urls), today=datetime.date.today().isoformat())
    resp = _call(client, model, prompt, config)
    loaded, failed = [], []
    meta = resp.candidates[0].url_context_metadata if resp.candidates else None
    for m in (meta.url_metadata if meta and meta.url_metadata else []):
        url = safe_url(m.retrieved_url or "")
        if url and "SUCCESS" in str(m.url_retrieval_status):
            loaded.append(url)
        elif url:
            failed.append(url)
    return resp.text or "", list(dict.fromkeys(loaded)), failed


def research(client, model, app, on_progress):
    """Up to three plan-and-read rounds. Doc URLs move over time, so if fewer than 3 pages load, the
    next round tries pages linked from the ones that loaded and is told which pages worked and failed."""
    notes, loaded, failed, hint, linked = [], [], [], "", []
    for round_no in range(3):
        urls = list(dict.fromkeys(linked + _plan(client, model, app, retry_hint=hint)))
        urls = [u for u in urls if u not in loaded and u not in failed][:MAX_PAGES]
        if not urls:
            break
        on_progress(("Reading official docs on: " if round_no == 0 else "Looking for more pages on: ")
                    + ", ".join(sorted({urlparse(u).netloc for u in urls})))
        round_notes, round_loaded, round_failed = _read(client, model, app, urls)
        round_notes, _, more = round_notes.partition("MORE PAGES:")
        linked = list(dict.fromkeys(u for u in (safe_url(x) for x in re.findall(r"https?://[^\s)\]\"'<>,]+", more)) if u))
        for u in round_loaded:
            on_progress(f"Read: {u}")
        if round_loaded:  # notes from a round where nothing loaded could only come from memory
            notes.append(round_notes)
        loaded += [u for u in round_loaded if u not in loaded]
        failed += round_failed
        if len(loaded) >= 3:
            break
        hint = ("Pages that loaded: " + (", ".join(loaded) or "none") + ". Pages that could not be opened: "
                + (", ".join(failed) or "none") + ". Suggest different pages that exist today, "
                "preferring the domains whose pages loaded.")
    if failed:
        on_progress(f"Could not open {len(failed)} page(s)")
    if not loaded:
        raise RuntimeError(f"Could not open {app}'s official documentation. Try the app's exact name or website.")
    sources = {u: (urlparse(u).netloc + urlparse(u).path)[:90] for u in loaded}
    return "\n\n".join(notes), sources


def structure(client, model, app, notes, sources):
    source_list = "\n".join(f"- {url}" for url in sources)
    config = types.GenerateContentConfig(response_mime_type="application/json", response_json_schema=GUIDE_SCHEMA)
    resp = _call(client, model, STRUCTURE_PROMPT.format(app=app, sources=source_list, notes=notes), config)
    try:
        guide = json.loads(resp.text)
        jsonschema.validate(guide, GUIDE_SCHEMA)
    except (TypeError, json.JSONDecodeError, jsonschema.ValidationError):
        raise RuntimeError("The agent's guide did not match the expected format; try again.") from None
    return guide


def enforce_evidence(guide, sources):
    """Keep only citations of pages that actually loaded. A claim citing any other URL loses its
    link and is downgraded to unverified, so a page cannot slip in a fake 'official' source."""
    allowed = set(sources)

    def clip(value):
        if isinstance(value, str):
            return value[:MAX_TEXT]
        if isinstance(value, list):
            return [clip(v) for v in value]
        if isinstance(value, dict):
            return {k: clip(v) for k, v in value.items()}
        return value

    guide = clip(guide)
    items = guide["prerequisites"] + guide["steps"] + guide["blockers"] + [guide["approval"]]
    for item in items:
        if item["source"] not in allowed or not safe_url(item["source"]):
            item["source"] = ""
            if item["evidence"] in ("docs", "community", "tested"):
                item["evidence"] = "unverified"
    guide["sources"] = [s for s in guide["sources"] if s["url"] in allowed and safe_url(s["url"])]
    return guide


def generate_guide(app, api_key, model=DEFAULT_MODEL, on_progress=lambda msg: None):
    """Research an app live and return a guide dict ready to save and render."""
    client = genai.Client(api_key=api_key)
    on_progress(f"Finding {app}'s official developer docs...")
    notes, sources = research(client, model, app, on_progress)
    if not notes.strip():
        raise RuntimeError("The research step returned no notes.")
    on_progress("Writing the guide and labelling the evidence...")
    guide = enforce_evidence(structure(client, model, app, notes, sources), sources)
    known = {s["url"] for s in guide["sources"]}
    guide["sources"] += [{"title": t, "url": u} for u, t in sources.items() if u not in known][:8]
    guide["slug"] = slugify(guide["app"])
    guide["last_checked"] = datetime.date.today().isoformat()
    guide["origin"] = f"Generated live by the research agent ({model}) - not reviewed by a person"
    guide["composio"] = None
    return guide

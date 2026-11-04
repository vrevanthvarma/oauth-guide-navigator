"""OAuth Approval Navigator - Streamlit app.

Run locally:  streamlit run app.py
"""
import hmac
import json
import os
import sys
import traceback
from datetime import date
from pathlib import Path

import streamlit as st

from composio_managed import composio_status
from guide_schema import EVIDENCE, OWNERS, md_text, safe_url, slugify, to_markdown

ROOT = Path(__file__).parent
SEED_DIR, GEN_DIR = ROOT / "guides", ROOT / "generated"
GEN_DIR.mkdir(exist_ok=True)
EVIDENCE_ICON = {"tested": "✅", "docs": "📄", "community": "💬", "unverified": "⚠️"}
OWNER_ICON = {"agent": "🤖", "you": "👤", "both": "🤝"}
DIFFICULTY_COLOR = {1: "green", 2: "green", 3: "orange", 4: "red", 5: "red"}

st.set_page_config(page_title="OAuth Approval Navigator", page_icon="🔑", layout="wide")


def load_guides() -> dict:
    guides = {}
    for folder in (SEED_DIR, GEN_DIR):
        for f in sorted(folder.glob("[!_]*.json")):
            g = json.loads(f.read_text(encoding="utf-8"))
            guides[g["slug"]] = g
    return guides


def secret(name, default=None):
    """Read a setting on the server. Secrets are never sent to the browser or put in a prompt."""
    try:
        return st.secrets[name]
    except Exception:
        return os.environ.get(name, default)


def redact(text: str, key: str) -> str:
    """Mask the API key if it ever appears in text that could be shown or logged."""
    return text.replace(key, "[hidden key]") if key else text


USAGE_FILE = GEN_DIR / "_usage.json"


def runs_today() -> int:
    """Live generations so far today (guards the API bill if the link is shared)."""
    try:
        usage = json.loads(USAGE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return 0
    return usage.get("count", 0) if usage.get("date") == str(date.today()) else 0


def record_run():
    USAGE_FILE.write_text(json.dumps({"date": str(date.today()), "count": runs_today() + 1}), encoding="utf-8")


def share_url(slug: str) -> str:
    host = st.context.headers.get("host", "") if hasattr(st, "context") else ""
    scheme = "http" if host.startswith(("localhost", "127.")) else "https"
    return f"{scheme}://{host}/?guide={slug}" if host else f"?guide={slug}"


def evidence(item: dict) -> str:
    """Evidence label plus source link. Guide text is escaped with md_text, links pass safe_url."""
    tag = f"{EVIDENCE_ICON[item['evidence']]} {EVIDENCE[item['evidence']]}"
    url = safe_url(item.get("source", ""))
    return f"{tag} - [source]({url})" if url else tag


def bullets(items) -> str:
    return "\n".join(f"- {md_text(x)}" for x in items)


def show_guide(g: dict):
    if st.button("← All guides"):
        st.query_params.clear()
        st.rerun()
    v = g["verdict"]
    st.title(f"🔑 {md_text(g['app'])}")
    st.caption(f"{md_text(g.get('origin', ''))} · last checked {md_text(g.get('last_checked', 'n/a'))}")
    st.markdown(md_text(g["summary"]))

    facts = [("Difficulty", f":{DIFFICULTY_COLOR.get(v['difficulty'], 'gray')}[**{v['difficulty']}/5 · {md_text(v['label'])}**]"),
             ("First test connection", md_text(v["time_to_first_connection"])),
             ("Ready for real users", md_text(v["time_to_production"])),
             ("Provider approval", md_text(v["approval_required"]))]
    for col, (label, value) in zip(st.columns(4), facts):
        with col.container(border=True):
            st.caption(label)
            st.markdown(value)

    comp = g.get("composio") or composio_status(g["app"])
    (st.success if comp["managed_oauth"] else st.warning)(f"**Composio:** {comp['note']}")

    left, right = st.columns([3, 2])
    with left:
        st.subheader("Before you start")
        for p in g["prerequisites"]:
            st.markdown(f"- {md_text(p['text'])}")
            st.caption(evidence(p))
        st.subheader("Steps")
        for i, s in enumerate(g["steps"], 1):
            st.markdown(f"**{i}. {md_text(s['title'])}** · `{OWNER_ICON[s['owner']]} {OWNERS[s['owner']]}`  \n"
                        f"{md_text(s['detail'])}")
            st.caption(evidence(s))
        st.subheader("If you get stuck")
        for b in g["blockers"]:
            with st.expander(md_text(b["problem"])):
                st.markdown(md_text(b["fix"]))
                st.caption(evidence(b))
    with right:
        a = g["approval"]
        st.subheader("Approval")
        st.info(f"{md_text(a['summary'])}\n\n**Typical wait:** {md_text(a['typical_wait'])}")
        if a["triggers"]:
            st.markdown("**Triggered by:** " + "; ".join(md_text(t) for t in a["triggers"]))
        st.caption(evidence(a))
        st.subheader("🤖 What an agent can do")
        st.markdown(bullets(g["agent_can"]))
        st.subheader("👤 Where you take over")
        st.markdown(bullets(g["you_must"]))
        if g["uncertain"]:
            st.subheader("⚠️ Not verified")
            st.markdown(bullets(g["uncertain"]))
        st.subheader("Sources")
        st.markdown("\n".join(f"- [{md_text(s['title'])}]({safe_url(s['url'])})" for s in g["sources"] if safe_url(s["url"])))

    st.divider()
    s1, s2 = st.columns(2)
    s1.text_input("Share this guide", share_url(g["slug"]))
    s2.download_button("Download as Markdown", to_markdown(g), file_name=f"{g['slug']}-oauth-guide.md")


def generate(app_name: str):
    from agent import DEFAULT_MODEL, generate_guide  # imported lazily so browsing works without the SDK

    key = secret("GEMINI_API_KEY")
    if not key or key.startswith("your-key"):
        st.error("Live generation is not set up on this site yet.")
        return
    limit = int(secret("DAILY_LIMIT", 20))
    if runs_today() >= limit:
        st.error(f"The daily limit of {limit} live guides is used up. Browse the library, or try again tomorrow.")
        return
    record_run()
    with st.status(f"Agent is investigating {md_text(app_name)}...", expanded=True) as status:
        try:
            g = generate_guide(app_name, key, model=secret("GEMINI_MODEL", DEFAULT_MODEL),
                               on_progress=lambda msg: st.write(md_text(msg)))
        except RuntimeError as e:  # fixed messages written for users in agent.py
            status.update(label="The agent could not finish this guide", state="error")
            st.error(redact(str(e), key))
            return
        except Exception:  # unexpected: details go to the server log only, with the key masked
            print(redact(traceback.format_exc(), key), file=sys.stderr)
            status.update(label="The agent could not finish this guide", state="error")
            st.error("Something went wrong while researching this app. Please try again.")
            return
        g["composio"] = composio_status(g["app"])
        (GEN_DIR / f"{g['slug']}.json").write_text(json.dumps(g, indent=2), encoding="utf-8")
        status.update(label="Guide ready", state="complete")
    st.query_params["guide"] = g["slug"]
    st.rerun()


def show_home(guides: dict):
    st.title("🔑 OAuth Approval Navigator")
    st.write("Before your agent's users can connect an app, you may need your own OAuth app from that provider, "
             "and some providers make you wait weeks for approval. Look up an app to see how hard it is, how long "
             "it takes, what can block you, and which parts an agent can do for you.")

    query = st.text_input("Look up an app by name or website", placeholder="e.g. Notion, zoom.us, Xero", max_chars=80).strip()
    st.caption("Enter only an app name or website, never personal information. Live lookups are sent to "
               "Google's Gemini API. This app stores nothing about visitors, but its host, Streamlit "
               "Community Cloud, collects its own usage data.")
    if query:
        slug = slugify(query.replace("https://", "").replace("www.", "").split(".")[0])
        hits = [g for s, g in guides.items() if slug in s or s in slug]
        if hits:
            st.write("In the library:")
            for g in hits:
                if st.button(f"Open the {md_text(g['app'])} guide", key=f"hit-{g['slug']}"):
                    st.query_params["guide"] = g["slug"]
                    st.rerun()
        code = secret("ACCESS_CODE")
        entered = st.text_input("Access code for live generation", type="password", max_chars=100,
                                help="Live research uses an API key, so it needs the code shared with reviewers.") if code else None
        failures = st.session_state.get("code_failures", 0)
        if st.button(f"🔎 Investigate {md_text(query)} with the agent (about 2-4 minutes)", type="primary"):
            if code and failures >= 5:
                st.error("Too many wrong access codes. Reload the page to try again later.")
            elif code and not hmac.compare_digest(str(entered or "").encode(), str(code).encode()):
                st.session_state["code_failures"] = failures + 1
                st.error("Wrong or missing access code. The guide library below stays open to everyone.")
            else:
                generate(query)

    st.subheader("Guide library")
    st.caption("📄 = from official docs · ✅ = tested by hand · ⚠️ = not verified · generated guides are marked")
    cols = st.columns(3)
    for i, g in enumerate(sorted(guides.values(), key=lambda g: g["verdict"]["difficulty"])):
        v = g["verdict"]
        with cols[i % 3].container(border=True):
            st.markdown(f"### {md_text(g['app'])}")
            st.markdown(f":{DIFFICULTY_COLOR.get(v['difficulty'], 'gray')}[**{md_text(v['label'])}** · {v['difficulty']}/5]")
            st.caption(f"Ready for real users: {md_text(v['time_to_production'])}")
            if "Generated" in g.get("origin", ""):
                st.caption("🤖 Generated live, not reviewed")
            if st.button("Open guide", key=f"open-{g['slug']}"):
                st.query_params["guide"] = g["slug"]
                st.rerun()


with st.sidebar:
    st.markdown("### How to read a guide")
    for k, label in EVIDENCE.items():
        st.markdown(f"{EVIDENCE_ICON[k]} {label}")
    st.markdown("---")
    for k, label in OWNERS.items():
        st.markdown(f"{OWNER_ICON[k]} {label}")
    st.markdown("---")
    st.caption("Built for the Composio APM Integrations take-home. Guides can be wrong; check the linked sources.")

all_guides = load_guides()
selected = st.query_params.get("guide")
if selected and selected in all_guides:
    show_guide(all_guides[selected])
else:
    show_home(all_guides)

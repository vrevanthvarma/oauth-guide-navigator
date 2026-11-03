"""The guide format: one JSON schema shared by seed guides and agent-generated guides."""
import re

EVIDENCE = {
    "tested": "Tested (we tried it)",
    "docs": "From official docs",
    "community": "From community sources",
    "unverified": "Unverified (agent estimate)",
}
OWNERS = {"agent": "Agent can do", "you": "You do", "both": "Together"}

_item = {
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "evidence": {"type": "string", "enum": list(EVIDENCE)},
        "source": {"type": "string"},
    },
    "required": ["text", "evidence", "source"],
    "additionalProperties": False,
}

GUIDE_SCHEMA = {
    "type": "object",
    "properties": {
        "app": {"type": "string"},
        "website": {"type": "string"},
        "summary": {"type": "string"},
        "verdict": {
            "type": "object",
            "properties": {
                "difficulty": {"type": "integer", "description": "1 = minutes, no review; 5 = weeks/months or blocked"},
                "label": {"type": "string"},
                "time_to_first_connection": {"type": "string"},
                "time_to_production": {"type": "string"},
                "approval_required": {"type": "string"},
            },
            "required": ["difficulty", "label", "time_to_first_connection", "time_to_production", "approval_required"],
            "additionalProperties": False,
        },
        "prerequisites": {"type": "array", "items": _item},
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "detail": {"type": "string"},
                    "owner": {"type": "string", "enum": list(OWNERS)},
                    "evidence": {"type": "string", "enum": list(EVIDENCE)},
                    "source": {"type": "string"},
                },
                "required": ["title", "detail", "owner", "evidence", "source"],
                "additionalProperties": False,
            },
        },
        "approval": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "triggers": {"type": "array", "items": {"type": "string"}},
                "typical_wait": {"type": "string"},
                "evidence": {"type": "string", "enum": list(EVIDENCE)},
                "source": {"type": "string"},
            },
            "required": ["summary", "triggers", "typical_wait", "evidence", "source"],
            "additionalProperties": False,
        },
        "blockers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "problem": {"type": "string"},
                    "fix": {"type": "string"},
                    "evidence": {"type": "string", "enum": list(EVIDENCE)},
                    "source": {"type": "string"},
                },
                "required": ["problem", "fix", "evidence", "source"],
                "additionalProperties": False,
            },
        },
        "agent_can": {"type": "array", "items": {"type": "string"}},
        "you_must": {"type": "array", "items": {"type": "string"}},
        "uncertain": {"type": "array", "items": {"type": "string"}},
        "sources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"title": {"type": "string"}, "url": {"type": "string"}},
                "required": ["title", "url"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["app", "website", "summary", "verdict", "prerequisites", "steps", "approval",
                 "blockers", "agent_can", "you_must", "uncertain", "sources"],
    "additionalProperties": False,
}


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "app"


def safe_url(url: str) -> str:
    """Only plain web links may be rendered; anything else (javascript:, data:, ...) is dropped."""
    url = (url or "").strip()
    return url if re.match(r"^https?://[^\s<>\"]+$", url) else ""


def md_text(text: str) -> str:
    """Escape Markdown, HTML and LaTeX syntax so guide text from the web renders as plain text."""
    return re.sub(r"([\\`*_\[\]<>!|~$#])", r"\\\1", str(text))


def to_markdown(g: dict) -> str:
    """Render a guide as Markdown so it can be downloaded and shared anywhere."""
    v = g["verdict"]
    out = [f"# OAuth setup guide: {g['app']}", "",
           f"_Last checked {g.get('last_checked', 'n/a')} - {g.get('origin', '')}_", "",
           g["summary"], "",
           f"**Difficulty:** {v['difficulty']}/5 ({v['label']})  ",
           f"**First test connection:** {v['time_to_first_connection']}  ",
           f"**Ready for real users:** {v['time_to_production']}  ",
           f"**Provider approval:** {v['approval_required']}", ""]
    c = g.get("composio")
    if c:
        out += [f"**Composio:** {'managed OAuth available' if c.get('managed_oauth') else 'bring your own OAuth app'}. {c.get('note', '')}", ""]
    out += ["## Before you start"] + [f"- {p['text']} ({EVIDENCE[p['evidence']]}: {p['source']})" for p in g["prerequisites"]]
    out += ["", "## Steps"]
    for i, s in enumerate(g["steps"], 1):
        out.append(f"{i}. **{s['title']}** [{OWNERS[s['owner']]}] - {s['detail']} ({EVIDENCE[s['evidence']]}: {s['source']})")
    a = g["approval"]
    out += ["", "## Approval", a["summary"], "", f"**Typical wait:** {a['typical_wait']}  ",
            "**Triggered by:** " + "; ".join(a["triggers"]), ""]
    out += ["## If you get stuck"] + [f"- **{b['problem']}** {b['fix']}" for b in g["blockers"]]
    out += ["", "## What an agent can do"] + [f"- {x}" for x in g["agent_can"]]
    out += ["", "## Where you take over"] + [f"- {x}" for x in g["you_must"]]
    out += ["", "## Not verified"] + [f"- {x}" for x in g["uncertain"]]
    out += ["", "## Sources"] + [f"- [{md_text(s['title'])}]({safe_url(s['url'])})" for s in g["sources"] if safe_url(s["url"])]
    return "\n".join(out) + "\n"

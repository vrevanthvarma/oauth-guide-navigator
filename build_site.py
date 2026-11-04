"""Builds site/data.json for the GitHub Pages version from the same guides, prompts and schema as the app.

Run:  py build_site.py
"""
import json
from pathlib import Path

import agent
from composio_managed import CHECKED, _MANAGED, composio_status
from guide_schema import EVIDENCE, GUIDE_SCHEMA, OWNERS

ROOT = Path(__file__).parent
guides = []
for folder in ("guides", "generated"):
    for f in sorted((ROOT / folder).glob("[!_]*.json")):
        g = json.loads(f.read_text(encoding="utf-8"))
        g["composio"] = g.get("composio") or composio_status(g["app"])
        guides.append(g)

data = {
    "guides": guides,
    "evidence": EVIDENCE,
    "owners": OWNERS,
    "schema": GUIDE_SCHEMA,
    "planSchema": agent.PLAN_SCHEMA,
    "prompts": {"plan": agent.PLAN_PROMPT, "read": agent.READ_PROMPT, "structure": agent.STRUCTURE_PROMPT},
    "model": agent.DEFAULT_MODEL,
    "maxPages": agent.MAX_PAGES,
    "maxText": agent.MAX_TEXT,
    "managed": sorted(_MANAGED),
    "checked": CHECKED,
    "hostedApp": "https://oapp-guide-navigator-dr8njdcz9cyj9vx2lvvwxm.streamlit.app",
    "repo": "https://github.com/vrevanthvarma/oauth-guide-navigator",
}
(ROOT / "site" / "data.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
print(f"site/data.json: {len(guides)} guides")

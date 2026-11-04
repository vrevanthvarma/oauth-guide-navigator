// The research agent, running in the visitor's browser. It uses the same prompts, schema and evidence
// rules as agent.py (build_site.py copies them into data.json). The visitor's Gemini key stays in this
// tab and is sent only to Google.
const API = "https://generativelanguage.googleapis.com/v1beta/models/";
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const fill = (template, values) => template.replace(/\{(\w+)\}/g, (m, k) => (k in values ? values[k] : m));

export const safeUrl = (url) => {
  const u = (url || "").trim();
  return /^https?:\/\/[^\s<>"]+$/.test(u) ? u : "";
};
export const slugify = (name) => name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "app";

export function composioStatus(appName, data) {
  const norm = (s) => s.toLowerCase().replace(/[^a-z0-9]/g, "");
  const name = norm(appName);
  const managed = data.managed.includes(name) || data.managed.some((m) => m.length >= 5 && name.includes(m));
  return {
    managed_oauth: managed,
    note: managed
      ? "Composio provides a managed OAuth app, so you only need your own for custom branding, scopes or quota."
      : `Not in Composio's managed OAuth list (checked ${data.checked}), so you likely need to bring your own OAuth app. Confirm on the toolkit's page.`,
  };
}

async function call(key, model, text, config) {
  for (let attempt = 0; attempt < 2; attempt++) {
    let res;
    try {
      res = await fetch(`${API}${model}:generateContent`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "x-goog-api-key": key },
        body: JSON.stringify({ contents: [{ role: "user", parts: [{ text }] }], ...config }),
      });
    } catch {
      throw new Error("Could not reach Gemini. Check your connection and try again.");
    }
    if (res.ok) return res.json();
    if (res.status >= 500 && attempt === 0) {
      await sleep(4000); // overloads are usually brief; retry once
      continue;
    }
    if (res.status >= 500) throw new Error("Gemini is busy right now. Try again in a minute.");
    if (res.status === 429) throw new Error("This key's Gemini free-tier limit is used up for now. Try again later.");
    const body = await res.text();
    if (res.status === 401 || res.status === 403 || /API.?key/i.test(body)) throw new Error("Gemini rejected this key. Check it and try again.");
    throw new Error(`Gemini could not process this request (error ${res.status}).`);
  }
}

const textOf = (resp) => (resp.candidates?.[0]?.content?.parts || []).map((p) => p.text || "").join("");
const jsonConfig = (schema) => ({ generationConfig: { responseMimeType: "application/json", responseJsonSchema: schema } });

async function plan(key, data, model, app, retryHint = "") {
  const resp = await call(key, model, fill(data.prompts.plan, { app, n: data.maxPages, retry_hint: retryHint }), jsonConfig(data.planSchema));
  let urls = [];
  try {
    urls = JSON.parse(textOf(resp)).urls || [];
  } catch {}
  return [...new Set(urls.map(safeUrl).filter(Boolean))].slice(0, data.maxPages);
}

async function read(key, data, model, app, urls) {
  const prompt = fill(data.prompts.read, { app, urls: urls.join("\n"), today: new Date().toISOString().slice(0, 10) });
  const resp = await call(key, model, prompt, { tools: [{ urlContext: {} }] });
  const loaded = [], failed = [];
  for (const m of resp.candidates?.[0]?.urlContextMetadata?.urlMetadata || []) {
    const url = safeUrl(m.retrievedUrl);
    if (url && String(m.urlRetrievalStatus).includes("SUCCESS")) loaded.push(url);
    else if (url) failed.push(url);
  }
  return { notes: textOf(resp), loaded: [...new Set(loaded)], failed };
}

// Up to three plan-and-read rounds: doc URLs move, so the next round tries pages linked from the ones
// that loaded and is told what worked and what failed.
async function research(key, data, model, app, onProgress) {
  const notes = [], loaded = [], failed = [];
  let hint = "", linked = [];
  for (let round = 0; round < 3; round++) {
    const planned = await plan(key, data, model, app, hint);
    const urls = [...new Set([...linked, ...planned])].filter((u) => !loaded.includes(u) && !failed.includes(u)).slice(0, data.maxPages);
    if (!urls.length) break;
    onProgress((round === 0 ? "Reading official docs on: " : "Looking for more pages on: ") + [...new Set(urls.map((u) => new URL(u).host))].sort().join(", "));
    const r = await read(key, data, model, app, urls);
    const [roundNotes, more = ""] = r.notes.split("MORE PAGES:");
    linked = [...new Set((more.match(/https?:\/\/[^\s)\]"'<>,]+/g) || []).map(safeUrl).filter(Boolean))];
    r.loaded.filter((u) => !loaded.includes(u)).forEach((u) => onProgress(`Read: ${u}`));
    if (r.loaded.length) notes.push(roundNotes); // notes from a round where nothing loaded could only come from memory
    loaded.push(...r.loaded.filter((u) => !loaded.includes(u)));
    failed.push(...r.failed);
    if (loaded.length >= 3) break;
    hint = `Pages that loaded: ${loaded.join(", ") || "none"}. Pages that could not be opened: ${failed.join(", ") || "none"}. Suggest different pages that exist today, preferring the domains whose pages loaded.`;
  }
  if (failed.length) onProgress(`Could not open ${failed.length} page(s)`);
  if (!loaded.length) throw new Error(`Could not open ${app}'s official documentation. Try the app's exact name or website.`);
  const sources = Object.fromEntries(loaded.map((u) => {
    const p = new URL(u);
    return [u, (p.host + p.pathname).slice(0, 90)];
  }));
  return { notes: notes.join("\n\n"), sources };
}

async function structure(key, data, model, app, notes, sources) {
  const prompt = fill(data.prompts.structure, { app, sources: Object.keys(sources).map((u) => `- ${u}`).join("\n"), notes });
  const resp = await call(key, model, prompt, jsonConfig(data.schema));
  let guide;
  try {
    guide = JSON.parse(textOf(resp));
  } catch {}
  if (!guide || !data.schema.required.every((k) => k in guide) || !Number.isInteger(guide.verdict?.difficulty)) {
    throw new Error("The agent's guide did not match the expected format; try again.");
  }
  return guide;
}

// Keep only citations of pages that actually loaded. A claim citing any other URL loses its link and is
// downgraded to unverified, so a page cannot slip in a fake "official" source.
function enforceEvidence(guide, sources, data) {
  const clip = (v) => {
    if (typeof v === "string") return v.slice(0, data.maxText);
    if (Array.isArray(v)) return v.map(clip);
    if (v && typeof v === "object") return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, clip(x)]));
    return v;
  };
  const g = clip(guide);
  for (const item of [...g.prerequisites, ...g.steps, ...g.blockers, g.approval]) {
    if (!(item.source in sources) || !safeUrl(item.source)) {
      item.source = "";
      item.evidence = "unverified";
    }
    if (!(item.evidence in data.evidence) || item.evidence === "tested") item.evidence = "unverified"; // nothing was tried by hand
    if ("owner" in item && !(item.owner in data.owners)) item.owner = "both";
  }
  g.sources = g.sources.filter((s) => s.url in sources && safeUrl(s.url));
  return g;
}

export async function generateGuide(app, key, data, onProgress = () => {}) {
  const model = data.model;
  onProgress(`Finding ${app}'s official developer docs...`);
  const { notes, sources } = await research(key, data, model, app, onProgress);
  if (!notes.trim()) throw new Error("The research step returned no notes.");
  onProgress("Writing the guide and labelling the evidence...");
  const g = enforceEvidence(await structure(key, data, model, app, notes, sources), sources, data);
  const known = new Set(g.sources.map((s) => s.url));
  g.sources.push(...Object.entries(sources).filter(([u]) => !known.has(u)).map(([url, title]) => ({ title, url })));
  g.slug = slugify(g.app);
  g.last_checked = new Date().toISOString().slice(0, 10);
  g.origin = `Generated live by the research agent (${model}) - not reviewed by a person`;
  g.composio = composioStatus(g.app, data);
  return g;
}

export function toMarkdown(g, data) {
  const v = g.verdict, a = g.approval, ev = data.evidence;
  const list = (items) => items.map((x) => `- ${x}`);
  const links = g.sources.filter((s) => safeUrl(s.url)).map((s) => `- [${s.title}](${safeUrl(s.url)})`);
  return [
    `# OAuth setup guide: ${g.app}`, "", `_Last checked ${g.last_checked || "n/a"} - ${g.origin || ""}_`, "", g.summary, "",
    `**Difficulty:** ${v.difficulty}/5 (${v.label})  `, `**First test connection:** ${v.time_to_first_connection}  `,
    `**Ready for real users:** ${v.time_to_production}  `, `**Provider approval:** ${v.approval_required}`, "",
    ...(g.composio ? [`**Composio:** ${g.composio.managed_oauth ? "managed OAuth available" : "bring your own OAuth app"}. ${g.composio.note}`, ""] : []),
    "## Before you start", ...g.prerequisites.map((p) => `- ${p.text} (${ev[p.evidence]}: ${p.source})`), "",
    "## Steps", ...g.steps.map((s, i) => `${i + 1}. **${s.title}** [${data.owners[s.owner]}] - ${s.detail} (${ev[s.evidence]}: ${s.source})`), "",
    "## Approval", a.summary, "", `**Typical wait:** ${a.typical_wait}  `, `**Triggered by:** ${a.triggers.join("; ")}`, "",
    "## If you get stuck", ...g.blockers.map((b) => `- **${b.problem}** ${b.fix}`), "",
    "## What an agent can do", ...list(g.agent_can), "", "## Where you take over", ...list(g.you_must), "",
    "## Not verified", ...list(g.uncertain), "", "## Sources", ...links, "",
  ].join("\n");
}

// A generated guide has no server to live on, so its share link carries the whole guide, compressed.
export async function packGuide(g) {
  const stream = new Blob([JSON.stringify(g)]).stream().pipeThrough(new CompressionStream("deflate-raw"));
  const bytes = new Uint8Array(await new Response(stream).arrayBuffer());
  return btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export async function unpackGuide(text) {
  const bytes = Uint8Array.from(atob(text.replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0));
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("deflate-raw"));
  return JSON.parse(await new Response(stream).text());
}

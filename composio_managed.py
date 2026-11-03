"""Apps for which Composio provides a managed OAuth app.
Copied from https://docs.composio.dev/toolkits/managed-auth on 2026-11-03 (127 toolkits)."""
import re

CHECKED = "2026-11-03"
MANAGED = """Aircall, Airtable, Amazon, Apaleo, Asana, Attio, Basecamp, Bitbucket, Blackbaud, Boldsign, Box, Cal,
Calendly, Canva, Capsule CRM, ClickUp, Confluence, Contentful, Crowdin, Dart, Daytona, Dialpad, Discord, Discord Bot,
Dropbox, Dub, Dynamics 365, Eventbrite, Excel, Exist, Facebook, Fathom, Figma, Freeagent, FreshBooks, GitHub, GitLab,
Gmail, Gong, Google Ads, Google Analytics, Google BigQuery, Google Calendar, Google Classroom, Google Docs, Google Drive,
Google Maps, Google Meet, Google Photos, Google Search Console, Google Sheets, Google Slides, Google Super, Google Tasks,
Gorgias, Greenhouse, Gumroad, Harvest, HubSpot, Hugging Face, Instagram, Intercom, Jira, Kit, Linear, LinkedIn, Linkhut,
Mailchimp, Microsoft OneNote, Microsoft Teams, Miro, Monday, Moneybird, Mural, NotebookLM, Notion, Omnisend, OneDrive,
Outlook, PagerDuty, Pinterest, Pinterest Ads, Prisma, Productboard, Pushbullet, QuickBooks, Reddit, Reddit Ads, Roam,
Salesforce, Sentry, Servicem8, SharePoint, Shippo, Slack, Slackbot, Splitwise, Square, Stack Exchange, Strava, Stripe,
Supabase, Ticketmaster, Ticktick, TikTok Ads, Timely, Todoist, Trello, Twitch, Typeform, WakaTime, Webex, WhatsApp,
Wrike, Yandex, YNAB, YouTube, Zendesk, Zeplin, Zoho, Zoho Bigin, Zoho Books, Zoho Desk, Zoho Inventory, Zoho Invoice,
Zoho Mail, Zoom"""

_norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
_MANAGED = {_norm(n) for n in MANAGED.split(",")}


def composio_status(app_name: str) -> dict:
    """Whether Composio already provides an OAuth app for this toolkit, based on the copied directory."""
    name = _norm(app_name)
    managed = name in _MANAGED or any(len(m) >= 5 and m in name for m in _MANAGED)
    note = ("Composio provides a managed OAuth app, so you only need your own for custom branding, scopes or quota."
            if managed else
            f"Not in Composio's managed OAuth list (checked {CHECKED}), so you likely need to bring your own OAuth app. "
            "Confirm on the toolkit's page.")
    return {"managed_oauth": managed, "note": note}

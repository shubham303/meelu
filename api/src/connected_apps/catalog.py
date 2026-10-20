from dataclasses import dataclass, field
from typing import Any, Literal

AuthKind = Literal["managed", "api_key"]
ActionKind = Literal["read", "write"]


@dataclass(frozen=True)
class App:
    toolkit: str
    name: str
    auth: AuthKind
    reads: tuple[str, ...]
    writes: tuple[str, ...]
    fixed_arguments: dict[str, dict[str, Any]] = field(default_factory=dict)

    def kind_of(self, action: str) -> ActionKind | None:
        if action in self.reads:
            return "read"
        if action in self.writes:
            return "write"
        return None


@dataclass(frozen=True)
class Desk:
    name: str
    noun: str
    blurb: str
    rule: str
    apps: tuple[App, ...]

    def app(self, toolkit: str) -> App | None:
        return next((a for a in self.apps if a.toolkit == toolkit), None)

    def app_for_action(self, action: str) -> App | None:
        return next((a for a in self.apps if a.kind_of(action) is not None), None)


EMAIL = Desk(
    name="email",
    noun="mailbox",
    blurb="The user's own mailbox (Gmail, Outlook) and newsletter tool (Mailchimp, Kit) — connect them, search and read mail, and save draft emails and draft newsletters for the user to send.",
    rule="Writes only save drafts; the user reviews and sends every email and newsletter themselves.",
    apps=(
        App(
            toolkit="gmail",
            name="Gmail",
            auth="managed",
            reads=(
                "GMAIL_FETCH_EMAILS",
                "GMAIL_FETCH_MESSAGE_BY_THREAD_ID",
                "GMAIL_LIST_DRAFTS",
                "GMAIL_GET_DRAFT",
            ),
            writes=("GMAIL_CREATE_EMAIL_DRAFT", "GMAIL_UPDATE_DRAFT"),
        ),
        App(
            toolkit="outlook",
            name="Outlook",
            auth="managed",
            reads=("OUTLOOK_QUERY_EMAILS", "OUTLOOK_GET_MESSAGE"),
            writes=("OUTLOOK_CREATE_DRAFT", "OUTLOOK_CREATE_DRAFT_REPLY"),
        ),
        App(
            toolkit="mailchimp",
            name="Mailchimp",
            auth="managed",
            reads=(
                "MAILCHIMP_GET_LISTS_INFO",
                "MAILCHIMP_LIST_CAMPAIGNS",
                "MAILCHIMP_GET_CAMPAIGN_CONTENT",
            ),
            writes=("MAILCHIMP_ADD_CAMPAIGN", "MAILCHIMP_SET_CAMPAIGN_CONTENT"),
            fixed_arguments={
                "MAILCHIMP_ADD_CAMPAIGN": {
                    "settings__auto__tweet": False,
                    "settings__auto__fb__post": [],
                }
            },
        ),
        App(
            toolkit="kit",
            name="Kit",
            auth="managed",
            reads=("KIT_LIST_BROADCASTS", "KIT_GET_BROADCAST"),
            writes=("KIT_CREATE_BROADCAST",),
            fixed_arguments={"KIT_CREATE_BROADCAST": {"send_at": None, "public": False}},
        ),
    ),
)

CMS = Desk(
    name="cms",
    noun="CMS",
    blurb="The user's own CMS (Webflow, Contentful) — connect it, read its collections and entries, and save pages there as drafts for the user to publish.",
    rule="Writes only save drafts; the user reviews and publishes every page in their CMS.",
    apps=(
        App(
            toolkit="webflow",
            name="Webflow",
            auth="api_key",
            reads=(
                "WEBFLOW_LIST_WEBFLOW_SITES",
                "WEBFLOW_LIST_COLLECTIONS",
                "WEBFLOW_GET_COLLECTION",
                "WEBFLOW_LIST_COLLECTION_ITEMS",
                "WEBFLOW_GET_COLLECTION_ITEM",
            ),
            writes=("WEBFLOW_CREATE_COLLECTION_ITEM",),
            fixed_arguments={"WEBFLOW_CREATE_COLLECTION_ITEM": {"is_draft": True}},
        ),
        App(
            toolkit="contentful",
            name="Contentful",
            auth="managed",
            reads=(
                "CONTENTFUL_LIST_SPACES",
                "CONTENTFUL_LIST_ENVIRONMENTS",
                "CONTENTFUL_GET_CONTENT_TYPES",
                "CONTENTFUL_LIST_ENTRIES",
                "CONTENTFUL_GET_ENTRY",
            ),
            writes=("CONTENTFUL_CREATE_SPACES_ENVIRONMENTS_ENTRIES", "CONTENTFUL_UPDATE_ENTRY"),
        ),
    ),
)

CRM = Desk(
    name="crm",
    noun="CRM",
    blurb="The user's own CRM (HubSpot, Attio, Pipedrive) — connect it, look up contacts, companies and deals, and add contacts and notes the user approves.",
    rule="Each write needs the user's approval; never delete or merge records.",
    apps=(
        App(
            toolkit="hubspot",
            name="HubSpot",
            auth="managed",
            reads=(
                "HUBSPOT_SEARCH_CONTACTS_BY_CRITERIA",
                "HUBSPOT_READ_CONTACT",
                "HUBSPOT_LIST_CONTACT_NOTES",
                "HUBSPOT_SEARCH_COMPANIES",
                "HUBSPOT_SEARCH_DEALS",
            ),
            writes=("HUBSPOT_CREATE_CONTACT", "HUBSPOT_UPDATE_CONTACT", "HUBSPOT_CREATE_NOTE"),
        ),
        App(
            toolkit="attio",
            name="Attio",
            auth="managed",
            reads=("ATTIO_SEARCH_RECORDS", "ATTIO_GET_RECORD", "ATTIO_LIST_NOTES"),
            writes=("ATTIO_ASSERT_PERSON", "ATTIO_ASSERT_COMPANY", "ATTIO_CREATE_NOTE"),
        ),
        App(
            toolkit="pipedrive",
            name="Pipedrive",
            auth="api_key",
            reads=(
                "PIPEDRIVE_SEARCH_PERSONS",
                "PIPEDRIVE_GET_DETAILS_OF_A_PERSON",
                "PIPEDRIVE_GET_ALL_NOTES",
            ),
            writes=("PIPEDRIVE_ADD_A_PERSON", "PIPEDRIVE_UPDATE_A_PERSON", "PIPEDRIVE_ADD_A_NOTE"),
        ),
    ),
)

DOCS = Desk(
    name="docs",
    noun="docs",
    blurb="The user's own documents (Notion, Google Docs) — connect them, find and read pages, and add new pages, database rows and comments for the user to review.",
    rule="Writes only add new pages, rows or comments; never change or remove what the user wrote.",
    apps=(
        App(
            toolkit="notion",
            name="Notion",
            auth="managed",
            reads=(
                "NOTION_SEARCH_NOTION_PAGE",
                "NOTION_GET_PAGE_MARKDOWN",
                "NOTION_FETCH_DATABASE",
                "NOTION_QUERY_DATABASE",
            ),
            writes=(
                "NOTION_CREATE_NOTION_PAGE",
                "NOTION_INSERT_ROW_DATABASE",
                "NOTION_CREATE_COMMENT",
            ),
        ),
        App(
            toolkit="googledocs",
            name="Google Docs",
            auth="managed",
            reads=("GOOGLEDOCS_SEARCH_DOCUMENTS", "GOOGLEDOCS_GET_DOCUMENT_PLAINTEXT"),
            writes=("GOOGLEDOCS_CREATE_DOCUMENT_MARKDOWN",),
        ),
    ),
)

SOCIAL = Desk(
    name="social",
    noun="social",
    blurb="The user's own social accounts (Reddit, LinkedIn, GitHub) — connect them, read a thread, and post a reply the user wrote or approved from their account.",
    rule="Posts publicly under the user's name: only a reply to a thread the user picked, with the exact text they approved. Never start a new post.",
    apps=(
        App(
            toolkit="reddit",
            name="Reddit",
            auth="managed",
            reads=(
                "REDDIT_RETRIEVE_REDDIT_POST",
                "REDDIT_RETRIEVE_POST_COMMENTS",
                "REDDIT_GET_SUBREDDIT_RULES",
            ),
            writes=("REDDIT_POST_REDDIT_COMMENT",),
        ),
        App(
            toolkit="linkedin",
            name="LinkedIn",
            auth="managed",
            reads=("LINKEDIN_GET_MY_INFO", "LINKEDIN_GET_POST_CONTENT"),
            writes=("LINKEDIN_CREATE_COMMENT_ON_POST",),
        ),
        App(
            toolkit="github",
            name="GitHub",
            auth="managed",
            reads=("GITHUB_GET_AN_ISSUE", "GITHUB_LIST_ISSUE_COMMENTS"),
            writes=("GITHUB_CREATE_AN_ISSUE_COMMENT",),
        ),
    ),
)

DESKS: dict[str, Desk] = {d.name: d for d in (EMAIL, CMS, CRM, DOCS, SOCIAL)}

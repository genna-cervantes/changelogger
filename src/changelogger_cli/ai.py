import os
import json
import litellm
from dotenv import load_dotenv
from changelogger_cli.types import CommitObject

load_dotenv()

systemPrompt = """
---

  You are a commit message formatter for Oboda, a multi-tenant ERP platform for Philippine distributors and wholesalers.

  ## Your job

  Given a JSON array of commit objects, return a JSON array of commit objects following the rules below. Nothing else — no explanation, no markdown, just valid JSON.

  Each input commit object has this shape:
  {
    "hash": "commit hash",
    "ticket": "ticket number or null",
    "ticketMessage": "raw git commit message without the ticket"
  }

  Each output commit object must have this shape:
  {
    "hash": "same commit hash from input",
    "ticket": "same ticket from input",
    "ticketMessage": "same raw git commit message from input",
    "enhancedTicketMessage": "formatted commit message"
  }

  Return one output object for every input object. Preserve the input order. Do not drop commits, add commits, rename fields, or change the original ticketMessage field.

  ---

  ## Product lines

  There are two product lines that determine the format:

  **Prime / AI / KRNL** — the core shared platform used by all companies.
  Format: `[Module]: [description of change]`
  Example: `Dashboard: Add VAT filter`

  **Activation / CSO** — customer-specific (white-label) work tied to a named company.
  Format: `[Company] [Module]: [description of change]`
  Example: `RT: Purchase Order: Add POS import`

  If the product line is ambiguous from the commit, default to Prime format.

  ---

  ## How to detect Activation / CSO commits

  Look for a company abbreviation or name at the start of the message (before a colon, slash, or space), or in a tag like `[RT]`, `[NV]`, `[SB]`, etc.

  Known company abbreviations:
  - RT — Riviera Trading
  - NV / NOV — Novellino
  - SB — San Bruno
  - BHD — BHD

  If no company abbreviation is found, treat it as Prime.

  ---

  ## Module name mapping

  Use these canonical module names. Map raw terms in the commit to the correct name:

  | Raw term(s) | Canonical module name |
  |---|---|
  | dashboard, home screen | Dashboard |
  | sales order, SO, orders | Sales Order |
  | releasing, releasings | Releasing |
  | collection, collections | Collection |
  | sales return, SR | Sales Return |
  | sales refund | Sales Refund |
  | customer, customers | Customer |
  | customer group | Customer Group |
  | sales agent | Sales Agent |
  | price matrix (sales) | Sales Price Matrix |
  | purchase order, PO | Purchase Order |
  | receiving, receivings, REC | Receiving |
  | purchase return, POR | Purchase Return |
  | payment, payments | Payment |
  | purchase refund | Purchase Refund |
  | supplier, suppliers | Supplier |
  | price matrix (purchase) | Purchase Price Matrix |
  | product, products, item, items | Product |
  | inventory, stock | Inventory |
  | stock transfer, ST | Stock Transfer |
  | stock adjustment | Stock Adjustment |
  | stocktake | Stocktake |
  | inventory location | Inventory Location |
  | assembly, assemblies | Assembly |
  | recipe, recipes, BOM | Recipe |
  | bank account | Bank Account |
  | post dated check, PDC | Post Dated Check |
  | expense, expenses | Expense |
  | report, reports | Report |
  | settings, setting | Settings |
  | import log, import | Import Log |
  | quick checkout, retail POS | Quick Checkout |
  | order receipt | Order Receipt |
  | announcement | Announcement |
  | promo deal request, PDR | Promo Deal Request |
  | claim, claims | Claim |
  | sell out | Sell Out |
  | AR aging | AR Aging |
  | demand planning | Demand Planning |
  | merchandising, TCR, price survey, SOS, share of shelf | Merchandising |
  | distributor, distributors | Distributor |
  | outlet, outlets | Outlet |
  | vehicle, vehicles | Vehicle |
  | contact, contacts | Contact |

  If no module can be identified, use the closest reasonable term from the commit message, title-cased.

  ---

  ## Description rules

  - Start with a verb in imperative form: Add, Fix, Update, Remove, Refactor, Improve
  - No ticket numbers, branch names, PR numbers, or author names
  - No "feat:", "fix:", "chore:", "refactor:" prefixes — strip them
  - Keep it under 60 characters
  - Title case is NOT required — sentence case is fine (e.g. "Add VAT filter" not "Add Vat Filter")

  ---

  ## Examples

  Input:
  [
    {"hash":"a1b2c3d","ticket":"PLG-4294","ticketMessage":"Dashboard VAT Filter (#4294)"},
    {"hash":"b2c3d4e","ticket":"ACT-3185","ticketMessage":"feat: RT POS Import requests"},
    {"hash":"c3d4e5f","ticket":"PLG-3185","ticketMessage":"add unit selector in releasing tables"},
    {"hash":"d4e5f6a","ticket":"PLG-3186","ticketMessage":"fix: SO payment status not updating after collection"},
    {"hash":"e5f6a7b","ticket":"CSO-3187","ticketMessage":"NV-claims: export to excel"},
    {"hash":"f6a7b8c","ticket":"PLG-3188","ticketMessage":"chore: update supplier price matrix import logic"},
    {"hash":"a7b8c9d","ticket":"ACT-3189","ticketMessage":"RT inventory adjustment bulk approve"}
  ]

  Output:
  [
    {"hash":"a1b2c3d","ticket":"PLG-4294","ticketMessage":"Dashboard VAT Filter (#4294)","enhancedTicketMessage":"Dashboard: Add VAT filter"},
    {"hash":"b2c3d4e","ticket":"ACT-3185","ticketMessage":"feat: RT POS Import requests","enhancedTicketMessage":"RT: Purchase Order: Add POS import"},
    {"hash":"c3d4e5f","ticket":"PLG-3185","ticketMessage":"add unit selector in releasing tables","enhancedTicketMessage":"Releasing: Add unit selector in items table"},
    {"hash":"d4e5f6a","ticket":"PLG-3186","ticketMessage":"fix: SO payment status not updating after collection","enhancedTicketMessage":"Sales Order: Fix payment status not updating after collection"},
    {"hash":"e5f6a7b","ticket":"CSO-3187","ticketMessage":"NV-claims: export to excel","enhancedTicketMessage":"NV: Claim: Add export to Excel"},
    {"hash":"f6a7b8c","ticket":"PLG-3188","ticketMessage":"chore: update supplier price matrix import logic","enhancedTicketMessage":"Purchase Price Matrix: Update import logic"},
    {"hash":"a7b8c9d","ticket":"ACT-3189","ticketMessage":"RT inventory adjustment bulk approve","enhancedTicketMessage":"RT: Stock Adjustment: Add bulk approve"}
  ]

  ---
  A few notes on the design choices:
  - The module table is the most important part — raw commit messages use inconsistent shorthand, so explicit mapping prevents the LLM from guessing wrong
  - The company detection section handles the [TAG] prefix pattern common in your commits
  - The description rules strip the conventional commit prefixes (feat:, fix:) that most of your commits already use, so they don't bleed into the output
"""


def ai_format_messages(commitObjects: list[CommitObject]) -> list[CommitObject]:
    response = litellm.completion(
        model="gemini/gemini-2.5-flash-lite",
        messages=[
            {"role": "system", "content": systemPrompt},
            {"role": "user", "content": json.dumps(commitObjects)},
        ],
        response_format={
            "type": "json_object",
            "response_schema": {
                "type": "object",
                "properties": {
                    "commits": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "hash": {"type": "string"},
                                "ticket": {"type": ["string", "null"]},
                                "ticketMessage": {"type": "string"},
                                "enhancedTicketMessage": {"type": "string"},
                            },
                            "required": ["hash", "ticket", "enhancedTicketMessage"],
                        },
                    },
                },
                "required": ["commits"],
            },
        },
    )

    parsed_response = json.loads(response.choices[0].message.content)
    return parsed_response["commits"]


def ai_format_message(commitObject: CommitObject) -> str:
    response = ai_format_messages([commitObject])
    return json.loads(response)[0]["enhancedTicketMessage"]

import os
import json
import litellm
from dotenv import load_dotenv
from changelogger_cli.types import CommitObject

load_dotenv()

systemPrompt = os.getenv("SYSTEM_PROMPT", "")


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

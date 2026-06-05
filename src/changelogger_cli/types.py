from typing import TypedDict

class CommitObject(TypedDict):
    hash: str
    message: str
    ticket: str | None
    ticketMessage: str
    enhancedTicketMessage: str | None
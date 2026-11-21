from datetime import datetime
from typing import Literal
from pydantic import BaseModel


class PublicMessage(BaseModel):
    author: Literal["you", "support"]
    body: str
    at: datetime


class PublicTicket(BaseModel):
    # Strictly whitelisted fields: no notes, no agent IDs, no clocks, no events
    subject: str
    status: str
    priority: str
    created_at: datetime
    can_reopen: bool
    messages: list[PublicMessage]


class NewTicket(BaseModel):
    name: str
    email: str
    subject: str
    body: str
    priority: Literal["critical", "medium", "low"]


class Reply(BaseModel):
    body: str
    wait_for_customer: bool = False


class Note(BaseModel):
    body: str


class PriorityChange(BaseModel):
    priority: Literal["critical", "medium", "low"]
"""Capability registry for OpsPilot integrations."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CapabilityStatus(StrEnum):
    CONNECTED = "connected"
    AVAILABLE = "available"
    COMING_SOON = "coming_soon"


@dataclass(frozen=True)
class Capability:
    id: str
    name: str
    category: str
    apps: list[str]
    status: CapabilityStatus
    featured: bool = False
    description: str = ""


_CAPABILITIES: list[Capability] = [
    Capability(
        id="composio",
        name="Composio",
        category="aggregator",
        apps=["Gmail", "Slack", "Salesforce", "Stripe"],
        status=CapabilityStatus.COMING_SOON,
        featured=True,
        description="One connection. 250+ apps. Connect once and unlock Gmail, Slack, Salesforce, Stripe, and more.",
    ),
    Capability(
        id="email",
        name="Email",
        category="email",
        apps=["Gmail", "Outlook", "Mailgun"],
        status=CapabilityStatus.COMING_SOON,
    ),
    Capability(
        id="chat",
        name="Chat",
        category="chat",
        apps=["Slack", "Discord", "Teams"],
        status=CapabilityStatus.COMING_SOON,
    ),
    Capability(
        id="calendar",
        name="Calendar",
        category="calendar",
        apps=["Google", "Outlook"],
        status=CapabilityStatus.COMING_SOON,
    ),
    Capability(
        id="documents",
        name="Documents",
        category="documents",
        apps=["Docs", "Notion", "Dropbox"],
        status=CapabilityStatus.COMING_SOON,
    ),
    Capability(
        id="crm",
        name="CRM",
        category="crm",
        apps=["Salesforce", "HubSpot"],
        status=CapabilityStatus.COMING_SOON,
    ),
    Capability(
        id="payments",
        name="Payments",
        category="payments",
        apps=["Stripe", "banking"],
        status=CapabilityStatus.COMING_SOON,
    ),
]


def get_all_capabilities() -> list[Capability]:
    """Return all registered capabilities."""
    return _CAPABILITIES


def get_capability(cap_id: str) -> Capability | None:
    """Look up a capability by its ID."""
    for cap in _CAPABILITIES:
        if cap.id == cap_id:
            return cap
    return None


def is_connected(cap_id: str) -> bool:
    """Return True if the capability exists and has CONNECTED status."""
    cap = get_capability(cap_id)
    return cap is not None and cap.status == CapabilityStatus.CONNECTED

"""Claude-powered triage adapter — retired; use GatewayTriageAdapter.

Kept as an import alias so older references fail clearly toward the gateway.
"""

from opspilot.adapters.gateway_triage import GatewayTriageAdapter

# Historical name; Anthropic is never used for triage (D-023 allowlist).
ClaudeAdapter = GatewayTriageAdapter

__all__ = ["ClaudeAdapter", "GatewayTriageAdapter"]

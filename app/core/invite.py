from __future__ import annotations

# Message pasted into Discord & co. `{tunnel}` is replaced with host:port.
INVITE_TEMPLATE = "Junta-te ao meu servidor: {tunnel}"


def build_invite(tunnel: str) -> str:
    """Ready-to-paste invite for a tunnel address (host:port)."""
    return INVITE_TEMPLATE.format(tunnel=tunnel.strip())

from __future__ import annotations

from app.core.i18n import tr

# Message pasted into Discord & co. `{tunnel}` is replaced with host:port.
INVITE_TEMPLATE = "Join my server: {tunnel}"


def build_invite(tunnel: str) -> str:
    """Ready-to-paste invite for a tunnel address (host:port)."""
    return tr(INVITE_TEMPLATE.replace("{tunnel}", "{}")).replace("{}", tunnel.strip())

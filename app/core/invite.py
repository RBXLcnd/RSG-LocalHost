from __future__ import annotations

from app.core import protocol
from app.core.i18n import tr

# Message pasted into Discord & co. `{tunnel}` is replaced with host:port.
INVITE_TEMPLATE = "Join my server: {tunnel}"
LINK_LABEL = "Open in RSG LocalHost:"


def build_invite(tunnel: str) -> str:
    """Ready-to-paste invite for a tunnel address (host:port)."""
    text = tr(INVITE_TEMPLATE.replace("{tunnel}", "{}")).replace("{}", tunnel.strip())
    return f"{text}\n{tr(LINK_LABEL)} {protocol.build_link(tunnel)}"

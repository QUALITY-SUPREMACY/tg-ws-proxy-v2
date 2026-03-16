"""
Telegram IP ranges and DC configuration.
Вынесено в отдельный модуль для легкого обновления.
"""

from typing import Set, Tuple, Dict
import ipaddress


# Telegram IP ranges (CIDR notation)
TELEGRAM_IP_RANGES: Tuple[str, ...] = (
    "149.154.160.0/20",
    "91.108.4.0/22",
    "91.108.8.0/22",
    "91.108.12.0/22",
    "91.108.16.0/22",
    "91.108.56.0/22",
    "91.108.56.0/23",
    "149.154.160.0/22",
    "149.154.164.0/22",
)

# Pre-computed set of IP networks for O(1) lookup
_TELEGRAM_NETWORKS: Set[ipaddress.IPv4Network] = frozenset(
    ipaddress.ip_network(cidr) for cidr in TELEGRAM_IP_RANGES
)

# DC to WebSocket domain mapping
DC_DOMAINS: Dict[int, Tuple[str, ...]] = {
    1: ("kws1.web.telegram.org", "kws1-1.web.telegram.org"),
    2: ("kws2.web.telegram.org", "kws2-1.web.telegram.org"),
    3: ("kws3.web.telegram.org", "kws3-1.web.telegram.org"),
    4: ("kws4.web.telegram.org", "kws4-1.web.telegram.org"),
    5: ("kws5.web.telegram.org", "kws5-1.web.telegram.org"),
}

# MTProto obfuscation init packet magic bytes
MTPROTO_MAGIC: bytes = b"\xee\xee\xee\xee"
MTPROTO_MAGIC_OFFSET: int = 56
MTPROTO_DC_OFFSET: int = 60


def is_telegram_ip(ip_str: str) -> bool:
    """Check if IP belongs to Telegram ranges (O(1) lookup)"""
    try:
        ip = ipaddress.ip_address(ip_str)
        if not isinstance(ip, ipaddress.IPv4Address):
            return False
        return any(ip in network for network in _TELEGRAM_NETWORKS)
    except ValueError:
        return False


def get_dc_domains(dc_id: int, is_media: bool = False) -> Tuple[str, ...]:
    """Get WebSocket domains for given DC ID"""
    domains = DC_DOMAINS.get(dc_id, DC_DOMAINS[2])  # Default to DC2
    if is_media and len(domains) > 1:
        # Use media-specific domain (second in tuple)
        return (domains[1],)
    return domains
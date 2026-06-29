import re
from ipaddress import ip_address
from urllib.parse import urlsplit

DIRECT_EXTERNAL_HTTP_URL_ERROR = "must be a direct external HTTP(S) URL"
_DNS_LABEL_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")
_INTERNAL_DNS_SUFFIXES = frozenset({"home", "internal", "lan", "local", "localhost"})


def _validate_public_dns_hostname(hostname: str) -> None:
    if any(character.isspace() for character in hostname):
        raise ValueError(f"{DIRECT_EXTERNAL_HTTP_URL_ERROR}: host contains whitespace")
    if hostname.endswith("."):
        raise ValueError(
            f"{DIRECT_EXTERNAL_HTTP_URL_ERROR}: trailing dot is not allowed"
        )

    try:
        ascii_hostname = hostname.encode("idna").decode("ascii").lower()
    except UnicodeError as error:
        raise ValueError(
            f"{DIRECT_EXTERNAL_HTTP_URL_ERROR}: host is not valid IDNA"
        ) from error

    if len(ascii_hostname) > 253:
        raise ValueError(f"{DIRECT_EXTERNAL_HTTP_URL_ERROR}: host is too long")

    labels = ascii_hostname.split(".")
    if len(labels) < 2:
        raise ValueError(
            f"{DIRECT_EXTERNAL_HTTP_URL_ERROR}: public DNS host requires a dot"
        )
    if labels[-1] in _INTERNAL_DNS_SUFFIXES:
        raise ValueError(
            f"{DIRECT_EXTERNAL_HTTP_URL_ERROR}: internal DNS suffix is not allowed"
        )
    if any(
        not label or len(label) > 63 or _DNS_LABEL_PATTERN.fullmatch(label) is None
        for label in labels
    ):
        raise ValueError(f"{DIRECT_EXTERNAL_HTTP_URL_ERROR}: invalid DNS label")


def validate_direct_external_http_url(value: str) -> str:
    """Return a normalized public HTTP(S) URL or raise ValueError."""
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{DIRECT_EXTERNAL_HTTP_URL_ERROR}: URL must not be blank")

    try:
        parsed = urlsplit(normalized)
        hostname = parsed.hostname
        parsed.port
        has_userinfo = parsed.username is not None or parsed.password is not None
    except ValueError as error:
        raise ValueError(
            f"{DIRECT_EXTERNAL_HTTP_URL_ERROR}: malformed host or port"
        ) from error

    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError(
            f"{DIRECT_EXTERNAL_HTTP_URL_ERROR}: scheme must be http or https"
        )
    if hostname is None:
        raise ValueError(f"{DIRECT_EXTERNAL_HTTP_URL_ERROR}: host is required")
    if has_userinfo:
        raise ValueError(f"{DIRECT_EXTERNAL_HTTP_URL_ERROR}: userinfo is not allowed")

    normalized_hostname = hostname.lower()
    if not normalized_hostname:
        raise ValueError(f"{DIRECT_EXTERNAL_HTTP_URL_ERROR}: host is required")
    if normalized_hostname == "localhost":
        raise ValueError(f"{DIRECT_EXTERNAL_HTTP_URL_ERROR}: localhost is not allowed")

    host_and_port = parsed.netloc.rsplit("@", maxsplit=1)[-1]
    if host_and_port.endswith(":"):
        raise ValueError(f"{DIRECT_EXTERNAL_HTTP_URL_ERROR}: port is invalid")

    try:
        address = ip_address(normalized_hostname)
    except ValueError:
        _validate_public_dns_hostname(normalized_hostname)
        return normalized

    if (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    ):
        raise ValueError(
            f"{DIRECT_EXTERNAL_HTTP_URL_ERROR}: non-public IP addresses are not allowed"
        )

    return normalized

from ipaddress import ip_address
from urllib.parse import urlsplit

DIRECT_EXTERNAL_HTTP_URL_ERROR = "must be a direct external HTTP(S) URL"


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

    normalized_hostname = hostname.rstrip(".").lower()
    if not normalized_hostname:
        raise ValueError(f"{DIRECT_EXTERNAL_HTTP_URL_ERROR}: host is required")
    if normalized_hostname == "localhost" or normalized_hostname.endswith(".localhost"):
        raise ValueError(f"{DIRECT_EXTERNAL_HTTP_URL_ERROR}: localhost is not allowed")

    host_and_port = parsed.netloc.rsplit("@", maxsplit=1)[-1]
    if host_and_port.endswith(":"):
        raise ValueError(f"{DIRECT_EXTERNAL_HTTP_URL_ERROR}: port is invalid")

    try:
        address = ip_address(normalized_hostname)
    except ValueError:
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

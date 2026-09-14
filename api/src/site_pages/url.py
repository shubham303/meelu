from urllib.parse import urlsplit, urlunsplit

DEFAULT_PORTS = {"http": "80", "https": "443", "ws": "80", "wss": "443", "ftp": "21"}


def normalise_url(raw: str) -> str:
    try:
        parts = urlsplit(raw.strip())
        if not parts.scheme:
            raise ValueError
        scheme = parts.scheme.lower()
        host = (parts.hostname or "").lower()
        netloc = ""
        if parts.netloc:
            userinfo = ""
            if parts.username:
                userinfo = parts.username
                if parts.password:
                    userinfo += f":{parts.password}"
                userinfo += "@"
            port = parts.port
            suffix = ""
            if port is not None and str(port) != DEFAULT_PORTS.get(scheme):
                suffix = f":{port}"
            netloc = f"{userinfo}{host}{suffix}"
        path = parts.path
        if netloc and path == "":
            path = "/"
        if len(path) > 1 and path.endswith("/"):
            path = path[:-1]
        return urlunsplit((scheme, netloc, path, parts.query, ""))
    except ValueError:
        return raw.strip()


def landing_path(url: str) -> str:
    parts = urlsplit(url)
    if not parts.scheme or not parts.netloc:
        return url
    return parts.path.rstrip("/") or "/"

"""Client for the public Radio Browser directory (https://www.radio-browser.info/).

Servers are discovered at runtime from all.api.radio-browser.info. Results are
mapped onto the station dict stored in stations.json.
"""
import logging
import random
import socket

import requests

log = logging.getLogger("radiachromecast.radiobrowser")

USER_AGENT = "RadioChromecast/1.0"
DIRECTORY_HOST = "all.api.radio-browser.info"
TIMEOUT = 20
SEARCH_LIMIT = 100
TAG_LIMIT = 150


class RadioBrowserError(Exception):
    """The directory could not be reached or returned something unexpected."""


def normalize_stream_url(url):
    """Comparison key for stream URLs (trailing slash and case ignored)."""
    return (url or "").strip().rstrip("/").lower()


def stream_url(hit):
    """Best playable URL from a Radio Browser station record."""
    return (hit.get("url_resolved") or hit.get("url") or "").strip()


def technical_label(hit):
    """Short codec/bitrate text for a result row, or an empty string."""
    codec = (hit.get("codec") or "").strip()
    try:
        bitrate = int(hit.get("bitrate") or 0)
    except (TypeError, ValueError):
        bitrate = 0
    if codec and bitrate:
        return f"{codec} {bitrate} kbps"
    if codec:
        return codec
    if bitrate:
        return f"{bitrate} kbps"
    return ""


def genre_from_hit(hit, selected_genre="", general_label="General"):
    """Genre line: station tags, then the filter the user picked, then a fallback."""
    raw = hit.get("tags") or ""
    parts = []
    for piece in raw.split(","):
        tag = piece.strip()
        if not tag:
            continue
        if tag.islower():
            tag = tag[:1].upper() + tag[1:]
        parts.append(tag)
        if len(parts) == 3:
            break
    if parts:
        return " / ".join(parts)
    if selected_genre:
        return selected_genre
    return general_label


def content_type_from_codec(codec):
    """Maps a Radio Browser codec name onto a content type the app already uses."""
    name = (codec or "").strip().upper().replace(" ", "")
    if name in ("MP3", "MPEG"):
        return "audio/mpeg"
    if name in ("AAC", "AAC+", "AACPLUS"):
        return "audio/aac"
    if name == "OGG":
        return "audio/ogg"
    return "audio/mpeg"


def _unique_id(base, existing_ids):
    """Same collision rule as the station form: base, then base-2, base-3, ..."""
    if base not in existing_ids:
        return base
    i = 2
    while f"{base}-{i}" in existing_ids:
        i += 1
    return f"{base}-{i}"


def to_local_station(hit, existing_ids, selected_genre="", general_label="General"):
    """Builds a stations.json entry. Adds the new id to existing_ids.

    Returns None when the hit has no name or no stream URL.
    """
    # Imported lazily so this module can be imported by gui without a cycle.
    from gui import slugify

    name = (hit.get("name") or "").strip()
    url = stream_url(hit)
    if not name or not url:
        return None

    station_id = _unique_id(slugify(name), existing_ids)
    existing_ids.add(station_id)

    favicon = (hit.get("favicon") or "").strip() or None
    country = (hit.get("country") or "").strip()
    tech = technical_label(hit)
    description = " · ".join(part for part in (country, tech) if part)

    return {
        "id": station_id,
        "name": name,
        "description": description,
        "genre": genre_from_hit(hit, selected_genre, general_label),
        "url": url,
        "logo": favicon,
        "content_type": content_type_from_codec(hit.get("codec")),
        "proxy": url.lower().startswith("http://"),
    }


class RadioBrowser:
    """Small session that fails over across the directory's servers."""

    def __init__(self):
        self._session = requests.Session()
        self._session.headers["User-Agent"] = USER_AGENT
        self._bases = None
        self._base = None

    def _server_urls(self):
        hosts = []
        try:
            infos = socket.getaddrinfo(DIRECTORY_HOST, 80, type=socket.SOCK_STREAM)
        except socket.gaierror as e:
            raise RadioBrowserError(str(e)) from e

        for info in infos:
            ip = info[4][0]
            try:
                name = socket.gethostbyaddr(ip)[0]
            except (socket.herror, socket.gaierror):
                continue
            if name not in hosts:
                hosts.append(name)

        # Reverse DNS can fail; the aggregate name still round-robins a server.
        if not hosts:
            hosts = [DIRECTORY_HOST]

        random.shuffle(hosts)
        return [f"https://{host}" for host in hosts]

    def _get(self, path, params=None):
        if self._bases is None:
            self._bases = self._server_urls()

        order = []
        if self._base:
            order.append(self._base)
        order.extend(base for base in self._bases if base != self._base)

        last_error = None
        for base in order:
            url = base + path
            try:
                response = self._session.get(url, params=params, timeout=TIMEOUT)
                response.raise_for_status()
                payload = response.json()
            except (requests.RequestException, ValueError) as e:
                log.warning("Radio Browser request failed (%s): %s", url, e)
                last_error = e
                continue
            log.info("Radio Browser %s via %s", path, base)
            self._base = base
            return payload

        message = str(last_error) if last_error else "no servers available"
        raise RadioBrowserError(message)

    def countries(self):
        """Returns [{name, code}] sorted by country name."""
        data = self._get("/json/countries")
        if not isinstance(data, list):
            raise RadioBrowserError("unexpected countries response")

        countries = []
        for row in data:
            name = (row.get("name") or "").strip()
            code = (row.get("iso_3166_1") or "").strip()
            if name and code:
                countries.append({"name": name, "code": code})
        countries.sort(key=lambda row: row["name"].casefold())
        return countries

    def tags(self):
        """Returns the most-used genre tag names, most common first."""
        data = self._get(
            "/json/tags",
            {"order": "stationcount", "reverse": "true", "limit": str(TAG_LIMIT)},
        )
        if not isinstance(data, list):
            raise RadioBrowserError("unexpected tags response")

        names = []
        for row in data:
            name = (row.get("name") or "").strip()
            if name and name not in names:
                names.append(name)
        return names

    def search_stations(self, country_code, tag=None, limit=SEARCH_LIMIT):
        """Stations for a country, optionally filtered by one genre tag.

        Broken stations and duplicate stream URLs are dropped. Order is votes,
        highest first, capped at ``limit``.
        """
        code = (country_code or "").strip()
        if not code:
            raise RadioBrowserError("country is required")

        params = {
            "countrycode": code,
            "hidebroken": "true",
            "order": "votes",
            "reverse": "true",
            "limit": str(limit),
        }
        if tag:
            params["tag"] = tag

        data = self._get("/json/stations/search", params)
        if not isinstance(data, list):
            raise RadioBrowserError("unexpected stations response")

        stations = []
        seen = set()
        for hit in data:
            url = normalize_stream_url(stream_url(hit))
            if not url or url in seen:
                continue
            if not (hit.get("name") or "").strip():
                continue
            seen.add(url)
            stations.append(hit)
        return stations

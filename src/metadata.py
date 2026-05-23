import re
import requests
from PyQt6.QtCore import QThread, pyqtSignal

# Matches the StreamTitle field inside an ICY metadata block, e.g.
#   StreamTitle='Artist - Song';StreamUrl='...';
_STREAM_TITLE_RE = re.compile(r"StreamTitle='(.*?)';", re.DOTALL)

_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)


class MetadataFetcher(QThread):
    """Polls an Icecast/Shoutcast stream for ICY 'now playing' metadata (StreamTitle).

    Shoutcast/Icecast servers interleave track info inside the audio stream when the
    client sends the ``Icy-MetaData: 1`` request header. The response then carries an
    ``icy-metaint`` header telling us how many audio bytes sit between metadata blocks.
    We connect, skip one audio block, read the single metadata block, parse StreamTitle,
    close the connection and sleep before polling again — this keeps bandwidth low since
    we only ever read ~one metaint worth of audio per poll.
    """

    # Emits the current track title, or "" when the stream reports no title.
    title_changed = pyqtSignal(str)

    POLL_INTERVAL_MS = 15000  # time between polls

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url
        self._running = True
        self._last_title = None

    def stop(self):
        """Signals the polling loop to exit at the next opportunity."""
        self._running = False

    def run(self):
        headers = {'Icy-MetaData': '1', 'User-Agent': _USER_AGENT}
        while self._running:
            try:
                title = self._fetch_once(headers)
                if title is not None and title != self._last_title:
                    self._last_title = title
                    self.title_changed.emit(title)
            except Exception:
                # Network hiccups are expected on long-lived radio streams; ignore and retry.
                pass

            # Sleep in small slices so stop() stays responsive.
            waited = 0
            while self._running and waited < self.POLL_INTERVAL_MS:
                self.msleep(250)
                waited += 250

    def _fetch_once(self, headers):
        """Connects once and returns the current StreamTitle, or None if unavailable."""
        with requests.get(self.url, headers=headers, stream=True, timeout=10) as r:
            metaint = r.headers.get('icy-metaint')
            if not metaint:
                # Stream does not expose inline metadata.
                return None
            metaint = int(metaint)
            raw = r.raw

            # Skip one block of audio data to reach the metadata segment.
            self._read_exact(raw, metaint)

            length_byte = raw.read(1)
            if not length_byte:
                return None
            meta_len = length_byte[0] * 16
            if meta_len == 0:
                return ""  # no title currently advertised

            meta = self._read_exact(raw, meta_len).decode('utf-8', errors='replace')
            match = _STREAM_TITLE_RE.search(meta)
            if match:
                return match.group(1).strip()
            return ""

    @staticmethod
    def _read_exact(raw, n):
        """Reads exactly n bytes (or until the stream ends) from a raw response."""
        buf = b''
        while len(buf) < n:
            chunk = raw.read(n - len(buf))
            if not chunk:
                break
            buf += chunk
        return buf

import socket
import threading
import urllib.request
import logging
import requests
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

log = logging.getLogger('radiachromecast.proxy')

def get_local_ip(target='10.254.254.254'):
    """Detects the local IP address the OS would use to reach ``target``.

    Pass the Chromecast's host here so the returned IP belongs to the LAN
    interface that actually routes to the device. Using the default route
    instead can pick a VPN/virtual adapter (e.g. 10.x.x.x) that the Chromecast
    cannot reach, which makes proxied streams fail instantly with IDLE.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't need to be reachable, just triggers routing resolution
        s.connect((target, 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

class RadioProxyHandler(BaseHTTPRequestHandler):
    """Handles streaming requests from Chromecast by proxying remote audio streams."""
    
    def log_message(self, format, *args):
        # Suppress logging to stdout to keep console logs clean from continuous chunk reads
        pass

    def do_GET(self):
        # Expected path format: /proxy/<station_id>
        if not self.path.startswith('/proxy/'):
            self.send_error(404, "Invalid proxy path")
            return
            
        station_id = self.path.split('/')[-1]
        stations = getattr(self.server, 'stations', [])
        station = next((s for s in stations if s.get('id') == station_id), None)

        client = self.client_address[0] if self.client_address else '?'
        log.info("GET %s from %s", self.path, client)

        if not station:
            log.warning("Station not found for id=%r", station_id)
            self.send_error(404, "Station not found")
            return

        target_url = station.get('url')
        content_type = station.get('content_type', 'audio/mpeg')
        log.info("[%s] upstream connect -> %s (declared CT=%s)", station_id, target_url, content_type)

        try:
            # We set a standard User-Agent header to bypass server blocks on default Python agents
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }

            # Stream the remote audio URL
            with requests.get(target_url, headers=headers, stream=True, timeout=10) as r:
                r.raise_for_status()

                # Fetch actual Content-Type header if provided by remote server
                remote_content_type = r.headers.get('Content-Type')
                if remote_content_type:
                    content_type = remote_content_type

                log.info("[%s] upstream %s, serving CT=%s to Chromecast", station_id, r.status_code, content_type)

                self.send_response(200)
                self.send_header('Content-Type', content_type)
                # Access-Control-Allow-Origin: * is essential for Chromecast media players (CORS)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Connection', 'close')
                self.end_headers()

                # Forward the audio chunks to the client (Chromecast)
                total = 0
                for chunk in r.iter_content(chunk_size=16384): # 16KB chunks
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    total += len(chunk)
                log.info("[%s] upstream ended; forwarded %d bytes", station_id, total)

        except (ConnectionResetError, ConnectionAbortedError):
            # Normal occurrence when client (Chromecast) stops playback and closes the connection
            log.info("[%s] client closed the connection (normal stop)", station_id)
        except Exception as e:
            # Send a 502 Bad Gateway if connection to the remote stream fails
            log.error("[%s] proxy error: %s: %s", station_id, type(e).__name__, e)
            try:
                self.send_error(502, f"Bad Gateway: {str(e)}")
            except Exception:
                pass

class _ProxyHTTPServer(ThreadingHTTPServer):
    # allow_reuse_address defaults to True, which on Windows lets a second app
    # instance silently bind a port that's already in use (SO_REUSEADDR). That
    # caused two processes to listen on 8090 at once, so Chromecast connections
    # landed on a stale instance / got reset. Disabling it makes a busy port raise
    # OSError so start() cleanly moves to the next free port instead.
    allow_reuse_address = False


class RadioProxyServer:
    """A multithreaded HTTP server that proxies audio streams to local devices."""

    def __init__(self, stations, port=8080):
        self.stations = stations
        self.port = port
        self.ip = get_local_ip()
        self.server = None
        self.thread = None
        self.is_running = False
        
    def start(self):
        """Starts the proxy server in a background thread, searching for a free port if needed."""
        current_port = self.port
        while True:
            try:
                self.server = _ProxyHTTPServer(('0.0.0.0', current_port), RadioProxyHandler)
                self.server.stations = self.stations
                self.port = current_port
                break
            except OSError:
                current_port += 1
                if current_port > 65535:
                    raise RuntimeError("No free port available for the proxy server")
                    
        self.is_running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        
    def _run(self):
        try:
            self.server.serve_forever()
        except Exception:
            pass
            
    def stop(self):
        """Gracefully shuts down the proxy server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        self.is_running = False
        
    def get_proxy_url(self, station_id, cast_host=None):
        """Returns the local proxy URL for a given station ID.

        When ``cast_host`` (the Chromecast's IP) is given, the URL uses the
        local interface that routes to that device rather than the default
        route. This avoids advertising a VPN/virtual adapter address the
        Chromecast cannot reach.
        """
        ip = get_local_ip(cast_host) if cast_host else self.ip
        return f"http://{ip}:{self.port}/proxy/{station_id}"

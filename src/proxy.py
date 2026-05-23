import socket
import threading
import urllib.request
import requests
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

def get_local_ip():
    """Detects the computer's primary local IP address routed to the internet."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't need to be reachable, just triggers routing resolution
        s.connect(('10.254.254.254', 1))
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
        
        if not station:
            self.send_error(404, "Station not found")
            return
            
        target_url = station.get('url')
        content_type = station.get('content_type', 'audio/mpeg')
        
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
                
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                # Access-Control-Allow-Origin: * is essential for Chromecast media players (CORS)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Connection', 'close')
                self.end_headers()
                
                # Forward the audio chunks to the client (Chromecast)
                for chunk in r.iter_content(chunk_size=16384): # 16KB chunks
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    
        except (ConnectionResetError, ConnectionAbortedError):
            # Normal occurrence when client (Chromecast) stops playback and closes the connection
            pass
        except Exception as e:
            # Send a 502 Bad Gateway if connection to the remote stream fails
            try:
                self.send_error(502, f"Bad Gateway: {str(e)}")
            except Exception:
                pass

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
                self.server = ThreadingHTTPServer(('0.0.0.0', current_port), RadioProxyHandler)
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
        
    def get_proxy_url(self, station_id):
        """Returns the local proxy URL for a given station ID."""
        return f"http://{self.ip}:{self.port}/proxy/{station_id}"

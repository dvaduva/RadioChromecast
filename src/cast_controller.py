from PyQt6.QtCore import QObject, QThread, pyqtSignal
import logging
import pychromecast
from i18n import t

log = logging.getLogger('radiachromecast.cast')

class ChromecastDiscoveryThread(QThread):
    """Background thread to discover Chromecast devices without freezing the UI."""
    devices_discovered = pyqtSignal(list, object)  # (chromecasts, browser)
    discovery_error = pyqtSignal(str)

    def run(self):
        try:
            chromecasts, browser = pychromecast.get_chromecasts()
            # NOTE: we must NOT stop the browser here. The discovered Chromecast
            # objects rely on the live Zeroconf instance (owned by the browser) to
            # resolve the device host when connecting. Stopping it now would cause
            # "Zeroconf instance loop must be running" on connect. The browser is
            # kept alive by CastController and stopped only on app shutdown.
            self.devices_discovered.emit(chromecasts, browser)
        except Exception as e:
            self.discovery_error.emit(str(e))

class ChromecastConnectThread(QThread):
    """Background thread to connect and wait for a Chromecast device to be ready."""
    connection_success = pyqtSignal(object)
    connection_failed = pyqtSignal(str)

    def __init__(self, cast_device):
        super().__init__()
        self.cast_device = cast_device

    def run(self):
        try:
            # wait() blocks until connection is established or timeout occurs
            self.cast_device.wait()
            self.connection_success.emit(self.cast_device)
        except Exception as e:
            self.connection_failed.emit(str(e))

class CastStatusListener:
    """Listener to monitor Chromecast volume and general status changes."""
    def __init__(self, callback):
        self.callback = callback

    def new_cast_status(self, status):
        self.callback(status)

class MediaStatusListener:
    """Listener to monitor Chromecast media playback states (Playing, Buffering, etc.)."""
    def __init__(self, callback):
        self.callback = callback

    def new_media_status(self, status):
        self.callback(status)

class CastController(QObject):
    """Coordinates Chromecast discovery, connection, control, and state updates."""
    
    # PyQt signals to communicate thread-safely with the GUI
    devices_updated = pyqtSignal(list) # List of CastDevice objects
    # (Status Message, IsConnected, Kind). Kind is a locale-independent hint
    # ("searching", "connecting", "info", "error", "connected", "disconnected")
    # so the GUI can pick the right status LED without parsing the message text.
    connection_status = pyqtSignal(str, bool, str)
    playback_state_changed = pyqtSignal(str) # player_state string (e.g. PLAYING, BUFFERING, IDLE)
    volume_changed = pyqtSignal(float, bool) # (volume_level 0.0-1.0, volume_muted bool)

    def __init__(self):
        super().__init__()
        self.chromecasts = []
        self.browser = None  # Kept alive so Zeroconf can resolve hosts on connect
        self.active_cast = None
        self.discovery_thread = None
        self.connect_thread = None
        self.status_listener = None
        self.media_listener = None

    def start_discovery(self):
        """Triggers asynchronous discovery of Chromecast devices."""
        self.connection_status.emit(t("cast.searching"), False, "searching")
        self.discovery_thread = ChromecastDiscoveryThread()
        self.discovery_thread.devices_discovered.connect(self._on_discovery_finished)
        self.discovery_thread.discovery_error.connect(self._on_discovery_error)
        self.discovery_thread.start()

    def _on_discovery_finished(self, chromecasts, browser):
        # Replace any previous browser (e.g. on re-scan) to avoid leaking
        # Zeroconf instances, then keep the new one alive for the connection.
        self._stop_browser()
        self.browser = browser
        self.chromecasts = chromecasts
        self.devices_updated.emit(chromecasts)
        if chromecasts:
            self.connection_status.emit(t("cast.scan_done", count=len(chromecasts)), False, "info")
        else:
            self.connection_status.emit(t("cast.none_found"), False, "info")

    def _on_discovery_error(self, err):
        self.connection_status.emit(t("cast.scan_error", error=err), False, "error")

    def connect_device(self, friendly_name):
        """Initiates connection to the selected Chromecast device in a background thread."""
        cast_device = next((c for c in self.chromecasts if c.name == friendly_name), None)
        if not cast_device:
            self.connection_status.emit(t("cast.device_unavailable"), False, "error")
            return

        self.connection_status.emit(t("cast.connecting", name=friendly_name), False, "connecting")
        self.disconnect_active()

        self.connect_thread = ChromecastConnectThread(cast_device)
        self.connect_thread.connection_success.connect(self._on_connection_success)
        self.connect_thread.connection_failed.connect(self._on_connection_failed)
        self.connect_thread.start()

    def _on_connection_success(self, cast_device):
        self.active_cast = cast_device
        self.connection_status.emit(t("cast.connected", name=cast_device.name), True, "connected")
        
        # Register status listeners to monitor the device's state
        self.status_listener = CastStatusListener(self._handle_cast_status)
        self.media_listener = MediaStatusListener(self._handle_media_status)
        
        self.active_cast.register_status_listener(self.status_listener)
        self.active_cast.media_controller.register_status_listener(self.media_listener)
        
        # Trigger initial status update to sync GUI with current device state
        if self.active_cast.status:
            self._handle_cast_status(self.active_cast.status)
        if self.active_cast.media_controller.status:
            self._handle_media_status(self.active_cast.media_controller.status)

    def _on_connection_failed(self, err):
        self.active_cast = None
        self.connection_status.emit(t("cast.connection_failed", error=err), False, "error")

    def disconnect_active(self):
        """Disconnects from the active Chromecast device and cleans up listeners."""
        if self.active_cast:
            # Tear down the pychromecast socket client. Without this its keepalive
            # thread keeps running and can prevent the process from exiting cleanly.
            try:
                self.active_cast.disconnect(timeout=2)
            except Exception as e:
                log.warning("disconnect failed: %s: %s", type(e).__name__, e)
            self.active_cast = None
            self.status_listener = None
            self.media_listener = None
            self.connection_status.emit(t("cast.disconnected"), False, "disconnected")
            self.playback_state_changed.emit("IDLE")

    def _stop_browser(self):
        """Stops the Zeroconf discovery browser, if one is active."""
        if self.browser:
            try:
                self.browser.stop_discovery()
            except Exception:
                pass
            self.browser = None

    def shutdown(self):
        """Full cleanup on application exit: stop worker threads, disconnect the
        device and stop Zeroconf, so the process can exit without lingering."""
        log.info("shutdown: cleaning up cast controller")
        # Wait briefly for the discovery/connect QThreads so we don't tear their
        # underlying objects down while they're still running.
        for thread in (self.discovery_thread, self.connect_thread):
            if thread is not None and thread.isRunning():
                thread.quit()
                if not thread.wait(3000):
                    log.warning("a cast worker thread did not stop in time")
        self.disconnect_active()
        self._stop_browser()

    def active_cast_host(self):
        """Returns the IP address of the connected Chromecast, or None.

        Used so the local proxy can advertise an IP on the same LAN interface
        that routes to the device (avoiding VPN/virtual adapter addresses).
        """
        cast = self.active_cast
        if not cast:
            return None
        info = getattr(cast, 'cast_info', None)
        if info is not None and getattr(info, 'host', None):
            return info.host
        sock = getattr(cast, 'socket_client', None)
        return getattr(sock, 'host', None)

    def play_stream(self, url, content_type="audio/mpeg", title="Radio Stream"):
        """Sends the audio stream URL to the connected Chromecast device."""
        if not self.active_cast:
            self.connection_status.emit(t("cast.not_connected_error"), False, "error")
            return

        log.info("play_media -> url=%s content_type=%s title=%r", url, content_type, title)
        try:
            mc = self.active_cast.media_controller
            # play_media starts streaming on the Chromecast
            mc.play_media(url, content_type, title=title)
        except Exception as e:
            log.error("play_media failed: %s: %s", type(e).__name__, e)
            self.connection_status.emit(t("cast.play_error", error=str(e)), True, "error")

    def stop_stream(self):
        """Stops the active media playback on the connected Chromecast."""
        if self.active_cast:
            try:
                self.active_cast.media_controller.stop()
            except Exception as e:
                self.connection_status.emit(t("cast.stop_error", error=str(e)), True, "error")

    def set_volume(self, level):
        """Sets the volume level of the Chromecast (0.0 to 1.0)."""
        if self.active_cast:
            try:
                # pychromecast 14 removed Chromecast.set_volume; volume is now
                # controlled through the receiver controller.
                self.active_cast.socket_client.receiver_controller.set_volume(level)
            except Exception as e:
                self.connection_status.emit(t("cast.volume_error", error=e), True, "error")

    def set_mute(self, mute):
        """Mutes or unmutes the connected Chromecast."""
        if self.active_cast:
            try:
                self.active_cast.socket_client.receiver_controller.set_volume_muted(mute)
            except Exception as e:
                self.connection_status.emit(t("cast.mute_error", error=e), True, "error")

    def _handle_cast_status(self, status):
        """Handles cast status updates (from background threads) and forwards them to GUI thread."""
        self.volume_changed.emit(status.volume_level, status.volume_muted)

    def _handle_media_status(self, status):
        """Handles media playback updates (from background threads) and forwards them to GUI thread."""
        # idle_reason is the key diagnostic: when a Chromecast rejects a stream it
        # goes IDLE with idle_reason == 'ERROR' (e.g. unsupported codec/content-type).
        log.info("media status: player_state=%s idle_reason=%s content_type=%s content_id=%s",
                 status.player_state, getattr(status, 'idle_reason', None),
                 getattr(status, 'content_type', None), getattr(status, 'content_id', None))
        self.playback_state_changed.emit(status.player_state)

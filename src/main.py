import sys
import os
import json
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

# Import local modules
from proxy import RadioProxyServer
from cast_controller import CastController
from gui import MainWindow

# Default configuration values, written to config.json on first run.
DEFAULT_CONFIG = {
    "proxy_port": 8090,
    "theme": "dark"
}

def get_base_dir():
    """Returns the directory for config/data files, adapting to PyInstaller EXE and dev environments."""
    if getattr(sys, 'frozen', False):
        # Package mode: next to the executable
        return os.path.dirname(sys.executable)
    # Development mode: one folder above the src directory
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_config(base_dir):
    """Loads config.json (creating it with defaults if missing). Returns a dict merged over DEFAULT_CONFIG."""
    path = os.path.join(base_dir, 'config.json')

    if not os.path.exists(path):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
            print(f"[RadioCast] S-a creat fisierul de configurare implicit: {path}")
        except Exception as e:
            print(f"[RadioCast] Eroare la crearea config.json: {e}")
        return dict(DEFAULT_CONFIG)

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Merge over defaults so any missing key falls back gracefully
        config = dict(DEFAULT_CONFIG)
        config.update(data)
        return config
    except Exception as e:
        print(f"[RadioCast] Eroare la citirea config.json, se folosesc valorile implicite: {e}")
        return dict(DEFAULT_CONFIG)

def resolve_proxy_port(config):
    """Validates the configured proxy port, falling back to the default on invalid values."""
    raw = config.get('proxy_port', DEFAULT_CONFIG['proxy_port'])
    try:
        port = int(raw)
        if not (1 <= port <= 65535):
            raise ValueError
        return port
    except (TypeError, ValueError):
        fallback = DEFAULT_CONFIG['proxy_port']
        print(f"[RadioCast] Port proxy invalid in config.json ('{raw}'). Se foloseste {fallback}.")
        return fallback

def get_stations_filepath(base_dir):
    """Locates the stations.json file, migrating from docs/ if needed."""
    path = os.path.join(base_dir, 'stations.json')
    
    # If not found in the root, check if docs/stations.json exists and migrate it
    if not os.path.exists(path):
        docs_path = os.path.join(base_dir, 'docs', 'stations.json')
        if os.path.exists(docs_path):
            try:
                import shutil
                shutil.copy2(docs_path, path)
                print(f"[RadioCast] S-a migrat stations.json din docs/ in radacina: {path}")
            except Exception as e:
                print(f"[RadioCast] Eroare la migrarea stations.json: {e}")
                return docs_path
                
    return path

def load_stations(filepath):
    """Loads and returns the radio stations list from the given stations.json path."""
    print(f"[RadioCast] Se incarca posturile de radio din: {filepath}")
    
    if not os.path.exists(filepath):
        # Create empty template if file does not exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        default_data = {"stations": []}
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[RadioCast] Eroare la crearea fisierului implicit: {e}")
        return []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('stations', [])
    except Exception as e:
        print(f"[RadioCast] Eroare la citirea fisierului de configurare: {e}")
        return []

def main():
    # 0. Resolve base directory and load configuration
    base_dir = get_base_dir()
    config = load_config(base_dir)
    proxy_port = resolve_proxy_port(config)

    # 1. Initialize stations list
    stations_path = get_stations_filepath(base_dir)
    stations = load_stations(stations_path)
    if not stations:
        print("[RadioCast] Avertisment: Lista de posturi radio este goala sau invalida!")

    # 2. Start local Proxy Server on the configured port (auto-increments if taken)
    proxy_server = RadioProxyServer(stations, port=proxy_port)
    try:
        proxy_server.start()
        if proxy_server.port != proxy_port:
            print(f"[RadioCast] Portul {proxy_port} era ocupat; proxy-ul foloseste portul {proxy_server.port}.")
        print(f"[RadioCast] Serverul proxy local ruleaza la adresa: http://{proxy_server.ip}:{proxy_server.port}")
    except Exception as e:
        print(f"[RadioCast] Nu s-a putut porni serverul proxy: {e}")
        sys.exit(1)

    # 3. Launch PyQt6 GUI Application
    app = QApplication(sys.argv)
    app.setApplicationName("RadioChromecast")
    
    cast_controller = CastController()
    
    window = MainWindow(stations, cast_controller, proxy_server, stations_path, config)
    window.show()

    # 4. Clean exit coordination
    try:
        exit_code = app.exec()
    finally:
        print("[RadioCast] Se opresc serviciile...")
        cast_controller.shutdown()
        proxy_server.stop()
        print("[RadioCast] La revedere!")
        
    sys.exit(exit_code)

if __name__ == "__main__":
    main()

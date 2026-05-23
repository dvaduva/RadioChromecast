"""Lightweight JSON-based internationalization for RadioChromecast.

Translation strings live in locales/<lang>.json (one file per language). The
module is a process-wide singleton: load the tables once at startup, choose a
language, then call t("some.key", name="...") anywhere to get the localized text.
"""
import os
import sys
import json

DEFAULT_LANG = "ro"
SUPPORTED_LANGS = ["ro", "en"]

_translations = {}        # lang code -> {key: text}
_current_lang = DEFAULT_LANG


def _locales_dir():
    """Resolves the locales/ folder for both dev runs and the PyInstaller EXE."""
    try:
        base_path = sys._MEIPASS  # set by PyInstaller at runtime
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, "locales")


def load_translations():
    """Loads every supported language file into memory. Safe to call once at startup."""
    global _translations
    _translations = {}
    locales_dir = _locales_dir()
    for lang in SUPPORTED_LANGS:
        path = os.path.join(locales_dir, f"{lang}.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                _translations[lang] = json.load(f)
        except Exception as e:
            print(f"[RadioCast] Nu s-a putut incarca traducerea '{lang}': {e}")
            _translations[lang] = {}


def set_language(lang):
    """Selects the active language, falling back to the default if unsupported."""
    global _current_lang
    _current_lang = lang if lang in SUPPORTED_LANGS else DEFAULT_LANG
    return _current_lang


def current_language():
    return _current_lang


def language_name(lang=None):
    """Returns the human-readable name of a language (from its file's _meta.name)."""
    lang = lang or _current_lang
    meta = _translations.get(lang, {}).get("_meta", {})
    return meta.get("name", lang)


def t(key, **kwargs):
    """Returns the localized string for key, formatted with any kwargs.

    Falls back to the default language, then to the key itself, so a missing
    translation is visible but never crashes the UI.
    """
    text = _translations.get(_current_lang, {}).get(key)
    if text is None:
        text = _translations.get(DEFAULT_LANG, {}).get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text
    return text

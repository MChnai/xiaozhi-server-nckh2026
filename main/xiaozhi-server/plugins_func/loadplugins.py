"""Load the complete research plugin set; legacy mode remains available in source."""
import importlib
import os
import pkgutil

NCKH_PLUGINS = frozenset({
    "get_weather_vn", "get_news_from_vnexpress", "get_lunar", "get_gold_price",
    "translate_text", "play_music", "add_reminder", "list_reminders", "delete_reminder",
    "handle_exit_intent",
})
def auto_import_modules(package_name):
    package = importlib.import_module(package_name)
    for _, name, _ in pkgutil.iter_modules(package.__path__):
        if os.environ.get("NCKH_PROFILE") == "nckh" and name not in NCKH_PLUGINS:
            continue
        importlib.import_module(f"{package_name}.{name}")

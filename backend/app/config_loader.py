import json
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parents[1] / 'config' / 'filters'


def load_filter_config(config_key: str) -> dict:
    config_path = CONFIG_DIR / f"{config_key}.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found for {config_key}")
    return json.loads(config_path.read_text())


def list_config_keys() -> list[str]:
    return [path.stem for path in CONFIG_DIR.glob('*.json')]

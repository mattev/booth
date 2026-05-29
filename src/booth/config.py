"""Config loader/saver. Reads & writes ~/.the-booth/config.toml (see config.example.toml)."""
import dataclasses
import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG_PATH = Path.home() / ".the-booth" / "config.toml"


@dataclass
class Config:
    enabled: bool = True
    cadence: float = 4.0                 # seconds between queue drains
    pack: str = "giants"
    tts_backend: str = "say"             # say | elevenlabs | openai
    sponsors_enabled: bool = True
    sponsor_interval_s: float = 900.0    # 15 min
    donate_handle: str = ""              # e.g. "Venmo @your-handle"
    anthropic_api_key: str = ""          # overrides $ANTHROPIC_API_KEY for the daemon


def load() -> Config:
    if not CONFIG_PATH.exists():
        return Config()
    with CONFIG_PATH.open("rb") as f:
        data = tomllib.load(f)
    return Config(**{k: v for k, v in data.items() if k in Config.__dataclass_fields__})


def save(cfg: Config) -> None:
    """Write config back as flat TOML (stdlib has no TOML writer, so we format simply)."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for f in dataclasses.fields(Config):
        v = getattr(cfg, f.name)
        if isinstance(v, bool):                 # check bool before int/float
            lines.append(f"{f.name} = {'true' if v else 'false'}")
        elif isinstance(v, str):
            lines.append(f'{f.name} = "{v}"')
        else:
            lines.append(f"{f.name} = {v}")
    CONFIG_PATH.write_text("\n".join(lines) + "\n")


def set_field(name: str, value) -> Config:
    """Convenience: load, set one field, save, return the updated config."""
    cfg = load()
    setattr(cfg, name, value)
    save(cfg)
    return cfg

from pathlib import Path

from .source_loader import load_verified_source

_SOURCE = load_verified_source(Path(__file__).parent, "discord_notifier")
exec(compile(_SOURCE, str(Path(__file__)), "exec"), globals(), globals())

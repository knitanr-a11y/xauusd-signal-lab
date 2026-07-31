from pathlib import Path

_PARTS = ['shadow_runtime_part01.pyinc', 'shadow_runtime_part02.pyinc', 'shadow_runtime_part03.pyinc', 'shadow_runtime_part04.pyinc', 'shadow_runtime_part05.pyinc', 'shadow_runtime_part06.pyinc', 'shadow_runtime_part07.pyinc']
_SOURCE = "".join((Path(__file__).with_name(part)).read_text(encoding="utf-8") for part in _PARTS)
exec(compile(_SOURCE, str(Path(__file__)), "exec"), globals(), globals())

from pathlib import Path

_PARTS = ['frozen_wave_part01.pyinc', 'frozen_wave_part02.pyinc', 'frozen_wave_part03.pyinc']
_SOURCE = "".join((Path(__file__).with_name(part)).read_text(encoding="utf-8") for part in _PARTS)
exec(compile(_SOURCE, str(Path(__file__)), "exec"), globals(), globals())

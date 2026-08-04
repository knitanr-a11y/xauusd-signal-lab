from __future__ import annotations

from . import robustness_audit as audit
from .run_reproduction import BASE, OUT, ROOT


def main() -> None:
    # Preserve the audited robustness implementation while replacing only its
    # environment-specific path globals with the explicit reproduction paths.
    audit.ROOT = ROOT
    audit.BASE = BASE
    audit.OUT = OUT
    audit.main()


if __name__ == "__main__":
    main()

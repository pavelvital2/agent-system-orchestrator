"""Run the ASO helper via ``python -m agent_system_orchestrator_aso``."""

from __future__ import annotations

import sys

from .cli import main


if __name__ == "__main__":
    sys.exit(main())

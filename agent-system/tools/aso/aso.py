#!/usr/bin/env python3
"""Direct-run wrapper for the canonical ASO package."""

from __future__ import annotations

import sys

from agent_system_orchestrator_aso.aso_tool.aso import build_parser, main


if __name__ == "__main__":
    sys.exit(main())

"""Console-script bridge for the ASO helper package."""

from __future__ import annotations

from .aso_tool.aso import main as _aso_main


def main(argv: list[str] | None = None) -> int:
    return int(_aso_main(argv))

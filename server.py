"""Compatibility entrypoint for existing MCP configurations.

Prefer the `bocha-search-mcp` console command for new setups.
"""

from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from bocha_search_mcp.server import main


if __name__ == "__main__":
    main()

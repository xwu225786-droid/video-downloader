"""Compatibility entry point for IDE users.

The supported command is ``uv run voxpull``; this shim also makes the PyCharm
run button work before the package has been installed in editable mode.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from voxpull.__main__ import main  # noqa: E402


if __name__ == "__main__":
    main()

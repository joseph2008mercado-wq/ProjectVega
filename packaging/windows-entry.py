"""Small frozen entry point; editable development still uses python -m vega.app."""

import sys
from pathlib import Path

if __name__ == "__main__":
    if sys.argv[1:] == ["--cleanup-legacy"]:
        # Packaging-only maintenance: use the bundled interpreter, never source
        # Python, pip, PowerShell or a compiler on the end-user machine.
        from legacy_migration import main
        raise SystemExit(main(Path(sys.executable).parent))
    else:
        from vega.app.__main__ import main
        raise SystemExit(main())

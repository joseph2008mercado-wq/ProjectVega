"""Small frozen entry point; editable development still uses python -m vega.app."""

from vega.app.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())

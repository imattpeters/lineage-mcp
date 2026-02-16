"""Entry point for lineage-mcp-tray: ``python -m lineage_tray``."""

import sys


def main() -> None:
    """Launch the tray application."""
    from lineage_tray.app import TrayApp

    app = TrayApp()
    try:
        app.run()
    except KeyboardInterrupt:
        app.stop()


if __name__ == "__main__":
    main()

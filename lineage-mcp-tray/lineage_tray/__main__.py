"""Entry point for lineage-mcp-tray: ``python -m lineage_tray``."""

import atexit
import logging
import os
import signal
import sys


def _setup_logging() -> None:
    """Configure logging for the tray application.

    Logs to both stderr and a rotating file in the temp directory.
    """
    import tempfile
    from logging.handlers import RotatingFileHandler

    log_dir = os.path.join(tempfile.gettempdir(), "lineage-mcp")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "tray.log")

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotating file handler: 2 MB, keep 3 backups
    file_handler = RotatingFileHandler(
        log_file, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.DEBUG)

    # stderr handler (INFO level)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(fmt)
    stderr_handler.setLevel(logging.INFO)

    root = logging.getLogger("lineage_tray")
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(stderr_handler)


def main() -> None:
    """Launch the tray application."""
    _setup_logging()
    logger = logging.getLogger("lineage_tray")

    from lineage_tray.app import TrayApp

    logger.info("Starting lineage-mcp-tray")
    app = TrayApp()

    # Signal handler for graceful shutdown (SIGTERM, SIGINT)
    def _signal_handler(signum: int, frame: object) -> None:
        sig_name = signal.Signals(signum).name
        logger.info("Received %s, shutting down gracefully", sig_name)
        app.stop()

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    # Register atexit to suppress Tcl_AsyncDelete errors on exit.
    # These occur when Python's interpreter shuts down and Tcl tries
    # to clean up async handlers from the wrong thread — harmless but noisy.
    def _suppress_tcl_on_exit() -> None:
        try:
            app.stop()
        except Exception:
            pass

    atexit.register(_suppress_tcl_on_exit)

    try:
        app.run()
    except KeyboardInterrupt:
        logger.info("Shutting down (KeyboardInterrupt)")
        app.stop()
    except Exception:
        logger.critical("Fatal error in tray application", exc_info=True)
        try:
            app.stop()
        except Exception:
            pass
        sys.exit(1)
    finally:
        # Force-exit to avoid Tcl_AsyncDelete errors during interpreter
        # shutdown. The app is already stopped at this point — all pipes
        # closed, icon removed, threads are daemon threads.
        logger.info("Tray app exited cleanly")
        logging.shutdown()
        os._exit(0)


if __name__ == "__main__":
    main()

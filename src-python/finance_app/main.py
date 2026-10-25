"""Backend bootstrap.

PyTauri starts this module from Rust (``PythonScript::Module("finance_app")``).
The blocking portal keeps one asyncio event loop alive for the whole app and
bridges PyTauri's synchronous IPC handler into async Python.
"""

from __future__ import annotations

import logging
import sys

from anyio.from_thread import start_blocking_portal
from pytauri import Manager, builder_factory, context_factory

from finance_app.commands import commands
from finance_app.state import AppState


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("beanie").setLevel(logging.WARNING)


def main() -> int:
    state = AppState.create()
    _configure_logging(state.config.log_level)

    with start_blocking_portal("asyncio") as portal:
        portal.call(state.startup)
        app = builder_factory().build(
            context=context_factory(),
            invoke_handler=commands.generate_handler(portal),
        )
        Manager.manage(app, state)
        try:
            return app.run_return()
        finally:
            portal.call(state.shutdown)


if __name__ == "__main__":
    raise SystemExit(main())

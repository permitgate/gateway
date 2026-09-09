# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

import asyncio
import logging
import signal
from typing import Optional

from hypercorn import Config
from hypercorn.asyncio import serve

from app import app
from config import AppConfig, get_app_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(f"server.log")],
)
logger = logging.getLogger(__name__)

# Initialize shutdown event
shutdown_event = asyncio.Event()

config: AppConfig = get_app_config()


async def shutdown(sig: Optional[signal.Signals] = None) -> None:
    """Initiate graceful shutdown"""
    if not shutdown_event.is_set():
        if sig:
            logger.info(
                f"Received signal {sig.name}, initiating graceful shutdown..."
            )
        else:
            logger.info("Initiating graceful shutdown...")
        shutdown_event.set()


async def start() -> None:
    hypercorn_config = Config()
    hypercorn_config.bind = [f"{config.host}:{config.port}"]

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(
                sig, lambda s=sig: asyncio.create_task(shutdown(s))
            )
        except (NotImplementedError, ValueError):
            logger.warning(
                f"Signal handler for {sig.name} not supported on this platform."
            )

    try:
        await serve(app, hypercorn_config, shutdown_trigger=shutdown_event.wait)
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    logger.info(f"Starting FastAPI app")
    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        logger.info("\nServer Stopped by User.")
    except Exception:
        logger.exception("An error occurred")
        raise

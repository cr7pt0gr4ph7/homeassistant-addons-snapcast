#!/usr/bin/env python
from typing import Any, Final

import asyncio
import logging
import sys
import threading

from pulsectl import PulseEventFacilityEnum, PulseEventTypeEnum
from pulsectl_asyncio import PulseAsync

_LOGGER = logging.getLogger('snapclient_automatic')

# Date/Time formats
FORMAT_DATE: Final = "%Y-%m-%d"
FORMAT_TIME: Final = "%H:%M:%S"
FORMAT_DATETIME: Final = f"{FORMAT_DATE} {FORMAT_TIME}"


def setup_logging(log_no_color: bool = False):
    """
    Setup logging configuration.
    """
    # The setup_logging method is based on async_enable_logging from
    # https://github.com/home-assistant/core/blob/7f8b5f228887187ae9cce078e7185eb098e87d22/homeassistant/bootstrap.py#L551-L648
    fmt = (
        "%(asctime)s.%(msecs)03d %(levelname)s (%(threadName)s) [%(name)s] %(message)s"
    )

    if not log_no_color:
        try:
            from colorlog import ColoredFormatter  # noqa: PLC0415

            # basicConfig must be called after importing colorlog in order to
            # ensure that the handlers it sets up wraps the correct streams.
            logging.basicConfig(level=logging.INFO)

            colorfmt = f"%(log_color)s{fmt}%(reset)s"
            logging.getLogger().handlers[0].setFormatter(
                ColoredFormatter(
                    colorfmt,
                    datefmt=FORMAT_DATETIME,
                    reset=True,
                    log_colors={
                        "DEBUG": "cyan",
                        "INFO": "green",
                        "WARNING": "yellow",
                        "ERROR": "red",
                        "CRITICAL": "red",
                    },
                )
            )
        except ImportError:
            pass

    # If the above initialization failed for any reason, setup the default
    # formatting.  If the above succeeds, this will result in a no-op.
    logging.basicConfig(
        format=fmt, datefmt=FORMAT_DATETIME, level=logging.INFO)

    # Capture warnings.warn(...) and friends messages in logs.
    # The standard destination for them is stderr, which may end up unnoticed.
    # This way they're where other messages are, and can be filtered as usual.
    logging.captureWarnings(True)

    # Suppress overly verbose logs from libraries that aren't helpful
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    sys.excepthook = lambda *args: logging.getLogger().exception(
        "Uncaught exception", exc_info=args
    )
    threading.excepthook = lambda args: logging.getLogger().exception(
        "Uncaught thread exception",
        exc_info=(  # type: ignore[arg-type]
            args.exc_type,
            args.exc_value,
            args.exc_traceback,
        ),
    )

handled_sinks: dict[int, Any] = {}

async def handle_sink_added(pulse: PulseAsync, sink_index: int) -> None:
    sink_info = await pulse.sink_info(sink_index)
    _LOGGER.info("Audio sink %i was registered: Name=%s Driver=%s", sink_index, sink_info.name, sink_info.driver)
    handled_sinks[sink_index] = True
    pass

async def handle_sink_removed(pulse: PulseAsync, sink_index: int) -> None:
    # We only care about audio sinks for which we have created a snapclient
    if sink_index in handled_sinks:
        _LOGGER.info("Audio sink %i was removed", sink_index)
        del handled_sinks[sink_index]
    else:
        _LOGGER.info("Ignoring removal of ignored audio sink %i", sink_index)
        return

    pass

async def main():
    setup_logging()

    _LOGGER.info("Subscribing to PulseAudio events...")

    async with PulseAsync("snapclient-listener") as pulse:
        async for event in pulse.subscribe_events('sink'):
            _LOGGER.info("Received PulseAudio event: %s", event)

            if event.facility == PulseEventFacilityEnum.sink:
                if event.t == PulseEventTypeEnum.new:
                    await handle_sink_added(pulse, int(event.index))
                elif event.t == PulseEventTypeEnum.remove:
                    await handle_sink_removed(pulse, int(event.index))

asyncio.run(main())

#!/usr/bin/env python
from typing import Any, Final

import asyncio
import logging
import sys
import threading
import yaml

import voluptuous as vol

from pulsectl import PulseEventFacilityEnum, PulseEventTypeEnum, PulseSinkInfo
from pulsectl_asyncio import PulseAsync

_LOGGER = logging.getLogger('snapclient_automatic')

# Date/Time formats
FORMAT_DATE: Final = "%Y-%m-%d"
FORMAT_TIME: Final = "%H:%M:%S"
FORMAT_DATETIME: Final = f"{FORMAT_DATE} {FORMAT_TIME}"

ATTR_URL: Final = "url"
ATTR_FILTERS: Final = "filters"
ATTR_CONDITIONS: Final = "conditions"
ATTR_ACCEPT: Final = "accept"
ATTR_LATENCY: Final = "latency"

CONFIG_SCHEMA = vol.Schema({
    vol.Required(ATTR_URL): str,
    vol.Optional(ATTR_FILTERS): {
        vol.Optional(ATTR_CONDITIONS): [str],
        vol.Optional(ATTR_ACCEPT): vol.Boolean,
        vol.Optional(ATTR_CONDITIONS): vol.Boolean,
    }
})


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


async def handle_sink_added(pulse: PulseAsync, config: dict, sink_index: int) -> None:
    sink_info: PulseSinkInfo = await pulse.sink_info(sink_index)
    _LOGGER.info("Audio sink %i was registered: Name=%s Driver=%s",
                 sink_index, sink_info.name, sink_info.driver)
    sink_properties = sink_info.proplist

    any_filters = False
    result_accept = False
    result_latency = None

    for filter in config[ATTR_FILTERS]:
        any_filters = True
        success = True
        for condition in filter[ATTR_CONDITIONS]:
            condition: str = condition
            negate = False
            if condition.startswith("!"):
                negate = True
                condition = condition[1:]
            condition_parts = condition.split("=", 2)
            if len(condition_parts) == 2:
                # Value comparison
                result = sink_properties[condition_parts[0]] == condition_parts[1]
            else:
                # Check for presence/absence of property
                result = condition_parts[0] in sink_properties
            if negate:
                result = not result
            if not result:
                success = False
                break
        if success:
            if ATTR_ACCEPT in filter[ATTR_ACCEPT]:
                result_accept = filter[ATTR_ACCEPT]
            if ATTR_LATENCY in filter[ATTR_LATENCY]:
                result_latency = filter[ATTR_LATENCY]

    if result_accept or not any_filters:
        _LOGGER.info("Creating snapcclient for audio sink %i...", sink_index)

        if result_latency is None:
            _LOGGER.info("Using default latency setting")
        else:
            _LOGGER.info("Using latency override (Latency = %s)", result_latency)

        handled_sinks[sink_index] = True
    else:
        _LOGGER.info(
            "Ignoring audio sink %i due to configured filters", sink_index)

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

    _LOGGER.info("Loading addon configuration...")

    try:
        with open("/data/options.json") as stream:
            raw_config = yaml.safe_load(stream)
            config = CONFIG_SCHEMA(raw_config)
    except Any as exc:
        _LOGGER.error("Failed to load configuration: %s", exc)
        return

    async with PulseAsync("snapclient-listener") as pulse:
        # There's a race condition here if a new audio sink appears
        # just after we have enumerated the existing audio sinks,
        # but before we can subscribe to events. Its unlikely to
        # happen in practice, though, because audio sink change
        # events and restarts of snapclient-listener are both rare.
        _LOGGER.info("Scanning existing PulseAudio audio sinks...")

        for sink in await pulse.sink_list():
            handle_sink_added(pulse)

        _LOGGER.info("Subscribing to PulseAudio events...")

        async for event in pulse.subscribe_events('sink'):
            _LOGGER.info("Received PulseAudio event: %s", event)

            if event.facility == PulseEventFacilityEnum.sink:
                if event.t == PulseEventTypeEnum.new:
                    await handle_sink_added(pulse, config, int(event.index))
                elif event.t == PulseEventTypeEnum.remove:
                    await handle_sink_removed(pulse, int(event.index))

asyncio.run(main())

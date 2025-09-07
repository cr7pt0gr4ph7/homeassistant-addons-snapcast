#!/usr/bin/env python
import asyncio
import logging

from pulsectl_asyncio import PulseAsync

_LOGGER = logging.getLogger('snapclient_automatic')

async def main():
    logging.basicConfig(level=logging.INFO)

    _LOGGER.info("Subscribing to PulseAudio events...")

    async with PulseAsync("snapclient-listener") as pulse:
        async for event in pulse.subscribe_events('sink'):
            _LOGGER.info("Received PulseAudio event: %s", event)

asyncio.run(main())

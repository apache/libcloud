import asyncio

from integration.driver.test import TestNodeDriver
from libcloud.async_util import AsyncSession

driver = TestNodeDriver('apache', 'libcloud', secure=False,
                        host='localhost', port=9898)

async def run():
    async with AsyncSession(driver) as async_instance:
        nodes = await async_instance.list_nodes()

    assert len(nodes) == 2

loop = asyncio.get_event_loop()
loop.run_until_complete(run())
loop.close()
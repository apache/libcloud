from libcloud.storage.providers import get_driver
from libcloud.storage.types import Provider

import asyncio

import sys

KEY = sys.getenv('GOOGLE_KEY')
SECRET = sys.getenv('GOOGLE_SECRET')

GoogleStorageDriver = get_driver(Provider.GOOGLE_STORAGE)
driver = GoogleStorageDriver(key=KEY, secret=SECRET)

def do_stuff_with_object(obj):
    print(obj)

async def run():
    tasks = []
    async for container in driver.iterate_containers_async():
        async for obj in driver.iterate_container_objects_async(container):
            tasks.append(asyncio.ensure_future(do_stuff_with_object(obj)))
    await asyncio.gather(*tasks)

loop = asyncio.get_event_loop()
loop.run_until_complete(run())
loop.close()

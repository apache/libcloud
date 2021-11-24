from libcloud.storage.types import Provider
from libcloud.storage.providers import get_driver

Driver = get_driver(Provider.AZURE_BLOBS)
driver = Driver("storagename", "key")

container = driver.list_containers()[0]
obj = container.list_objects()[0]

# Download first 5 bytes of an object (aka bytes 0, 1, 2, 3 and 4)
print(next(driver.download_object_range_as_stream(obj=obj, start_bytes=0, end_bytes=5)))

# Download bytes 5-8 (inclusive) of an object
print(next(driver.download_object_range_as_stream(obj=obj, start_bytes=5, end_bytes=9)))

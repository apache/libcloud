import os.path

from gevent import monkey  # pylint: disable=import-error
from gevent.pool import Pool  # pylint: disable=import-error

from libcloud.storage.types import Provider
from libcloud.storage.providers import get_driver

monkey.patch_all()


USERNAME = "username"
API_KEY = "api key"

cls = get_driver(Provider.CLOUDFILES_US)
driver = cls(USERNAME, API_KEY)


def download_obj(container, obj):
    driver = cls(USERNAME, API_KEY)
    obj = driver.get_object(container_name=container.name, object_name=obj.name)
    filename = os.path.basename(obj.name)
    path = os.path.join(os.path.expanduser("~/Downloads"), filename)
    print("Downloading: {} to {}".format(obj.name, path))
    obj.download(destination_path=path)


containers = driver.list_containers()

jobs = []
pool = Pool(20)

for index, container in enumerate(containers):
    objects = container.list_objects()

    for obj in objects:
        pool.spawn(download_obj, container, obj)

pool.join()
print("Done")

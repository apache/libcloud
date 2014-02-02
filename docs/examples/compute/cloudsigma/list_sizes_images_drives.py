from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.CLOUDSIGMA)
driver = cls('username', 'password', region='zrh', api_version='2.0')

sizes = driver.list_sizes()
print(sizes)

images = driver.list_images()
print(images)

drives = driver.ex_list_library_drives()
print(drives)

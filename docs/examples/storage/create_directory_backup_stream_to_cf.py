import subprocess
from datetime import datetime

from libcloud.storage.types import Provider, ContainerDoesNotExistError
from libcloud.storage.providers import get_driver

driver = get_driver(Provider.CLOUDFILES_US)("username", "api key")

directory = "/home/some/path"
cmd = "tar cvzpf - %s" % (directory)

object_name = "backup-%s.tar.gz" % (datetime.now().strftime("%Y-%m-%d"))
container_name = "backups"

# Create a container if it doesn't already exist
try:
    container = driver.get_container(container_name=container_name)
except ContainerDoesNotExistError:
    container = driver.create_container(container_name=container_name)

pipe = subprocess.Popen(cmd, bufsize=0, shell=True, stdout=subprocess.PIPE)
return_code = pipe.poll()

print("Uploading object...")

while return_code is None:
    # Compress data in our directory and stream it directly to CF
    obj = container.upload_object_via_stream(iterator=pipe.stdout, object_name=object_name)
    return_code = pipe.poll()

print("Upload complete, transferred: %s KB" % (obj.size / 1024))

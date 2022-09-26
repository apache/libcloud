from StringIO import StringIO

from libcloud.storage.types import Provider
from libcloud.storage.providers import get_driver

CloudFiles = get_driver(Provider.CLOUDFILES_US)

driver = CloudFiles("username", "api key")

container = driver.create_container(container_name="my_website")

iterator1 = StringIO("<p>Hello World from Libcloud!</p>")
iterator2 = StringIO("<p>Oh, noez, 404!!</p>")
iterator3 = StringIO("<p>Oh, noez, 401!!</p>")

driver.upload_object_via_stream(iterator=iterator1, container=container, object_name="index.html")
driver.upload_object_via_stream(
    iterator=iterator2, container=container, object_name="404error.html"
)
driver.upload_object_via_stream(
    iterator=iterator3, container=container, object_name="401error.html"
)

driver.ex_enable_static_website(container=container)
driver.ex_set_error_page(container=container, file_name="error.html")
driver.enable_container_cdn(container=container)

print(
    "All done you can view the website at: %s" % (driver.get_container_cdn_url(container=container))
)

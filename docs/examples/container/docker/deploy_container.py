from libcloud.container.types import Provider
from libcloud.container.providers import get_driver

cls = get_driver(Provider.DOCKER)

driver = cls(host="https://198.61.239.128", port=4243, key_file="key.pem", cert_file="cert.pem")

image = driver.install_image("tomcat:8.0")
container = driver.deploy_container("tomcat", image)

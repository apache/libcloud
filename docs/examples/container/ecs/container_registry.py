from libcloud.container.types import Provider
from libcloud.container.providers import get_driver

cls = get_driver(Provider.ECS)

# Connect to AWS
conn = cls(
    access_id="SDHFISJDIFJSIDFJ",
    secret="THIS_IS)+_MY_SECRET_KEY+I6TVkv68o4H",
    region="ap-southeast-2",
)

# Get a Registry API client for an existing repository
client = conn.ex_get_registry_client("my-image")

# List all the images
for image in client.list_images("my-image"):
    print(image.name)

# Get a specific image
image = client.get_image("my-image", "14.04")

print(image.path)
# >> 647433528374.dkr.ecr.region.amazonaws.com/my-image:14.04

# Deploy that image
cluster = conn.list_clusters()[0]
container = conn.deploy_container(cluster=cluster, name="my-simple-app", image=image)

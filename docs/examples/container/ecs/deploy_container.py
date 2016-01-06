from libcloud.container.base import ContainerImage
from libcloud.container.types import Provider
from libcloud.container.providers import get_driver

cls = get_driver(Provider.ECS)

conn = cls(access_id='AKIAI7OR4GWEEPRIFBBA',
           secret='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',
           region='ap-southeast-2')


for cluster in conn.list_clusters():
    print(cluster.name)
    if cluster.name == 'default':
        container = conn.deploy_container(
            cluster=cluster,
            name='my-simple-app',
            image=ContainerImage(
                id=None,
                name='simple-app',
                path='simple-app',
                version=None,
                driver=conn
            )
        )

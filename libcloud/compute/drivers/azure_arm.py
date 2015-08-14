from libcloud.common.azure_arm import AzureResourceManagementConnection
from libcloud.compute.providers import Provider
from libcloud.compute.base import Node, NodeDriver, NodeLocation, NodeSize
from libcloud.compute.base import NodeImage, StorageVolume
from libcloud.compute.types import NodeState
from libcloud.common.types import LibcloudError

class AzurePublisher(object):
    def __init__(self, id, name, location):
        self.id = id
        self.name = name
        self.location = location

    def __repr__(self):
        return (('<AzureImagePublisher: id=%s, name=%s, location=%s>')
                % (self.id, self.name, self.location))

class AzureOffer(object):
    def __init__(self, id, name, location, publisher):
        self.id = id
        self.name = name
        self.location = location
        self.publisher = publisher

    def __repr__(self):
        return (('<AzureOffer: id=%s, name=%s, location=%s>')
                % (self.id, self.name, self.location))

class AzureNodeDriver(NodeDriver):
    connectionCls = AzureResourceManagementConnection
    name = 'Azure Virtual machines'
    website = 'http://azure.microsoft.com/en-us/services/virtual-machines/'
    type = Provider.AZURE_ARM

    def __init__(self, tenant_id, subscription_id, key, secret, secure=True, host=None, port=None,
                 api_version=None, **kwargs):
        self.tenant_id = tenant_id
        self.subscription_id  = subscription_id
        super(AzureNodeDriver, self).__init__(key=key, secret=secret, secure=secure,
                                         host=host, port=port,
                                         api_version=api_version, **kwargs)

    def _ex_connection_class_kwargs(self):
        kwargs = super(AzureNodeDriver, self)._ex_connection_class_kwargs()
        kwargs['tenant_id'] = self.tenant_id
        kwargs['subscription_id'] = self.subscription_id
        return kwargs

    def list_locations(self):
        action = "/subscriptions/%s/providers/Microsoft.Compute" % (self.subscription_id)

        r = self.connection.request(action,
                                    params={"api-version": "2015-01-01"})

        for rt in r.object["resourceTypes"]:
            if rt["resourceType"] == "virtualMachines":
                # XXX for some reason the API returns location names like
                # "East US" instead of "eastus" which is what is actually needed
                # for other API calls, so do a name->id fixup and hope it works.
                return [NodeLocation(l.lower().replace(" ", ""), l, l, self.connection.driver) for l in rt["locations"]]

        return []

    def list_sizes(self, location=None):
        if not location:
            raise ValueError("location is required.")

        action = "/subscriptions/%s/providers/Microsoft.Compute/locations/%s/vmSizes" % (self.subscription_id, location.id)

        r = self.connection.request(action,
                                    params={"api-version": "2015-06-15"})
        return [self._to_node_size(d) for d in r.object["value"]]

    def ex_list_publishers(self, location):
        if not location:
            raise ValueError("location is required.")

        action = "/subscriptions/%s/providers/Microsoft.Compute/locations/%s/publishers" % (self.subscription_id, location.id)

        r = self.connection.request(action,
                                    params={"api-version": "2015-06-15"})
        return [AzurePublisher(p["id"], p["name"], p["location"]) for p in r.object]

    def ex_list_offers(self, publisher):
        action = "%s/artifacttypes/vmimage/offers" % (publisher.id)

        r = self.connection.request(action,
                                    params={"api-version": "2015-06-15"})
        return [AzureOffer(p["id"], p["name"], p["location"], publisher) for p in r.object]

    def list_images(self, ex_offer=None):
        if not ex_offer:
            raise ValueError("ex_offer is required.")

        action = "%s/skus" % (ex_offer.id)

        r = self.connection.request(action,
                                    params={"api-version": "2015-06-15"})
        return [NodeImage(img["id"], img["name"], self.connection.driver) for img in r.object]


    def create_node(self, name, size, image, location, auth, ex_resource_group, **kwargs):
        target = "/subscriptions/%s/resourceGroups/%s/providers/Microsoft.Compute/virtualMachines/%s" % (self.subscription_id, ex_resource_group, name)
        r = self.connection.request(action,
                                    params={"api-version": "2015-07-13"},
                                    data={
                                        "id": target,
                                        "name": name,
                                        "type": "Microsoft.Compute/virtualMachines",
                                        "location": location.id,
                                        "tags": {},
                                        "properties": {
                                            "hardwareProfile": {
                                                "vmSize": size.id
                                            },
                                            "storageProfile": {
                                                "imageReference": {
                                                    "publisher": "LinuxImagePublisher",
                                                    "offer": "LinuxImageOffer",
                                                    "sku": "LinuxImageSKU",
                                                    "version": "LinuxImageVersion"
                                                },
                                                "osDisk": {
                                                    "name": "virtualmachine-osDisk",
                                                    "vhd": {
                                                        "uri": "https://storageaccount.blob.core.windows.net/vhds/virtualmachine-os.vhd"
                                                    },
                                                    "caching": "ReadWrite"
                                                },
                                            },
                                            "osProfile": {
                                                "computerName": "virtualMachineName",
                                                "adminUsername": "username",
                                                "adminPassword": "password",
                                                "customData": "",
                                                "linuxConfiguration": {
                                                    "disablePasswordAuthentication": "true|false",
                                                    "ssh": {
                                                        "publicKeys": [
                                                            {
                                                                "path": "Path-Where-To-Place-Public-Key-On-VM",
                                                                "keyData": "ssh rsa public key as a string"
                                                            }
                                                        ]
                                                    }
                                                }
                                            }
                                    }
                                    },
                                    method="PUT")

    def _to_node_size(self, data):
        return NodeSize(id=data["name"],
                        name=data["name"],
                        ram=data["memoryInMB"],
                        disk=data["resourceDiskSizeInMB"] / 1024, # convert to GB
                        bandwidth=0,
                        price=0,
                        driver=self.connection.driver,
                        extra={"numberOfCores": data["numberOfCores"],
                               "osDiskSizeInMB": data["osDiskSizeInMB"],
                               "maxDataDiskCount": data["maxDataDiskCount"]
                           })

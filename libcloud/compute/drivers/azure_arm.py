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

class AzureSku(object):
    def __init__(self, id, name, location, offer):
        self.id = id
        self.name = name
        self.location = location
        self.offer = offer

    def __repr__(self):
        return (('<AzureSku: id=%s, name=%s, location=%s>')
                % (self.id, self.name, self.location))

class AzureImage(NodeImage):
    def __init__(self, id, name, driver, location, sku):
        super(AzureImage, self).__init__(id, name, driver)
        self.location = location
        self.sku = sku

    def urn(self):
        return "%s:%s:%s:%s" % (self.sku.offer.publisher.name, self.sku.offer.name, self.sku.name, self.name)

    def __repr__(self):
        return (('<AzureImage: id=%s, name=%s, location=%s>')
                % (self.id, self.name, self.location))

class AzureNetwork(object):
    def __init__(self, id, name, location, extra):
        self.id = id
        self.name = name
        self.location = location
        self.extra = extra

    def __repr__(self):
        return (('<AzureNetwork: id=%s, name=%s, location=%s ...>')
                % (self.id, self.name, self.location))

class AzureSubnet(object):
    def __init__(self, id, name, extra):
        self.id = id
        self.name = name
        self.extra = extra

    def __repr__(self):
        return (('<AzureSubnet: id=%s, name=%s ...>')
                % (self.id, self.name))

class AzureNic(object):
    def __init__(self, id, name, location, extra):
        self.id = id
        self.name = name
        self.location = location
        self.extra = extra

    def __repr__(self):
        return (('<AzureNic: id=%s, name=%s ...>')
                % (self.id, self.name))


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

    def ex_list_sku(self, ex_offer=None):
        if not ex_offer:
            raise ValueError("ex_offer is required.")

        action = "%s/skus" % (ex_offer.id)

        r = self.connection.request(action,
                                    params={"api-version": "2015-06-15"})
        return [AzureSku(sku["id"], sku["name"], sku["location"], ex_offer) for sku in r.object]

    def ex_list_image_versions(self, ex_sku=None):
        if not ex_sku:
            raise ValueError("ex_sku is required.")

        action = "%s/versions" % (ex_sku.id)
        print action

        r = self.connection.request(action,
                                    params={"api-version": "2015-06-15"})
        return [AzureImage(img["id"], img["name"], self.connection.driver, img["location"], ex_sku) for img in r.object]

    def list_images(self, ex_sku=None):
        # TODO give this a nicer API
        return self.ex_list_image_versions(ex_sku)

    def list_nodes(self):
        action = "/subscriptions/%s/providers/Microsoft.Compute/virtualMachines" % (self.subscription_id)

        r = self.connection.request(action,
                                    params={"api-version": "2015-06-15"})
        return [self._to_node(n) for n in r.object["value"]]

    def ex_list_networks(self):
        action = "/subscriptions/%s/providers/Microsoft.Network/virtualnetworks" % (self.subscription_id)

        r = self.connection.request(action,
                                    params={"api-version": "2015-06-15"})
        return [AzureNetwork(net["id"], net["name"], net["location"], net["properties"]) for net in r.object["value"]]

    def ex_list_subnets(self, network):
        action = "%s/subnets" % (network.id)

        r = self.connection.request(action,
                                    params={"api-version": "2015-06-15"})

        return [AzureSubnet(net["id"], net["name"], net["properties"]) for net in r.object["value"]]

    def ex_create_public_ip(self, name, location, resource_group):
        target = "/subscriptions/%s/resourceGroups/%s/providers/Microsoft.Network/publicIPAddresses/%s" % (self.subscription_id, resource_group, name)
        r = self.connection.request(target,
                                    params={"api-version": "2015-06-15"},
                                    data={
                                        "location": location.id,
                                        "tags": {},
                                        "properties": {
                                            "publicIPAllocationMethod": "Dynamic"
                                        }
                                    },
                                    method='PUT'
                                    )
        return r.object

    def ex_create_network_interface(self, name, subnet, location, resource_group, public_ip = None):
        target = "/subscriptions/%s/resourceGroups/%s/providers/Microsoft.Network/networkInterfaces/%s" % (self.subscription_id, resource_group, name)

        data={
            "location": location.id,
            "tags": {},
            "properties": {
                "ipConfigurations": [{
                    "name":"myip1",
                    "properties":{
                        "subnet":{
                            "id": subnet.id
                        },
                        "privateIPAllocationMethod":"Dynamic"
                    }
                }]
            }
        }

        if public_ip:
            data["properties"]["ipConfigurations"][0]["publicIPAddress"] = {"id": public_ip.id}

        r = self.connection.request(target,
                                    params={"api-version": "2015-06-15"},
                                    data=data,
                                    method='PUT'
                                    )
        return AzureNic(r.object["id"], r.object["name"], r.object["location"], r.object["properties"])


    def create_node(self, name, size, image, location, auth, ex_resource_group, ex_nic, ex_storage_account, **kwargs):
        target = "/subscriptions/%s/resourceGroups/%s/providers/Microsoft.Compute/virtualMachines/%s" % (self.subscription_id, ex_resource_group, name)
        r = self.connection.request(target,
                                    params={"api-version": "2015-06-15"},
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
                                                    "publisher": image.sku.offer.publisher.name,
                                                    "offer": image.sku.offer.name,
                                                    "sku": image.sku.name,
                                                    "version": image.name
                                                },
                                                "osDisk": {
                                                    "name": "virtualmachine-osDisk",
                                                    "vhd": {
                                                        "uri": "https://%s.blob.core.windows.net/vhds/%s-os.vhd" % (ex_storage_account, name)
                                                    },
                                                    "caching": "ReadWrite",
                                                    "createOption":"FromImage"
                                                }
                                            },
                                            "osProfile": {
                                                "computerName": name,
                                                "adminUsername": "peter",
                                                "adminPassword": "99aBCd99",
                                                "linuxConfiguration": {
                                                    "disablePasswordAuthentication": "true",
                                                    "ssh": {
                                                        "publicKeys": [
                                                            {
                                                                "path": '/home/' + "peter" + '/.ssh/authorized_keys',
                                                                "keyData": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDLQS1ExT2+WjA0d/hntEAyAtgeN1W2ik2QX8c2zO6HjlPHWXL92r07W0WMuDib40Pcevpi1BXeBWXA9ZB5KKMJB+ukaAu22KklnQuUmNvk6ZXnPKSkGxuCYvPQb08WhHf3p1VxiKfP3iauedBDM4x9/bkJohlBBQiFXzNUcQ+a6rKiMzmJN2gbL8ncyUzc+XQ5q4JndTwTGtOlzDiGOc9O4z5Dd76wtAVJneOuuNpwfFRVHThpJM6VThpCZOnl8APaceWXKeuwOuCae3COZMz++xQfxOfZ9Z8aIwo+TlQhsRaNfZ4Vjrop6ej8dtfZtgUFKfbXEOYaHrGrWGotFDTD peter@peter"
                                                            }
                                                        ]
                                                    }
                                                }
                                            },
                                            "networkProfile": {
                                                "networkInterfaces": [
                                                    {
                                                        "id": ex_nic.id
                                                    }
                                                ]
                                            }
                                        }
                                    },
                                    method="PUT")
        return self._to_node(r.object)

    def _to_node(self, data):
        return Node(data["id"],
                    data["name"],
                    None,
                    None,
                    None,
                    driver=self.connection.driver)


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

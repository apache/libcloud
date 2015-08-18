import binascii
import os
import time

from libcloud.common.azure_arm import AzureResourceManagementConnection
from libcloud.compute.providers import Provider
from libcloud.compute.base import Node, NodeDriver, NodeLocation, NodeSize
from libcloud.compute.base import NodeImage, StorageVolume, NodeAuthSSHKey, NodeAuthPassword
from libcloud.compute.types import NodeState
from libcloud.common.exceptions import BaseHTTPError
from libcloud.storage.drivers.azure_blobs import AzureBlobsStorageDriver

class AzureImage(NodeImage):
    def __init__(self, version, sku, offer, publisher, location, driver):
        self.publisher = publisher
        self.offer = offer
        self.sku = sku
        self.version = version
        self.location = location
        urn = "%s:%s:%s:%s" % (self.publisher, self.offer, self.sku, self.version)
        name = "%s %s %s %s" % (self.publisher, self.offer, self.sku, self.version)
        super(AzureImage, self).__init__(urn, name, driver)

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


class AzureIPAddress(object):
    def __init__(self, id, name, extra):
        self.id = id
        self.name = name
        self.extra = extra

    def __repr__(self):
        return (('<AzureIPAddress: id=%s, name=%s ...>')
                % (self.id, self.name))


class AzureNodeDriver(NodeDriver):
    connectionCls = AzureResourceManagementConnection
    name = 'Azure Virtual machines'
    website = 'http://azure.microsoft.com/en-us/services/virtual-machines/'
    type = Provider.AZURE_ARM
    features = {'create_node': ['ssh_key', 'password']}

    _location_to_country = {
        "centralus": "Iowa, USA",
        "eastus": "Virginia, USA",
        "eastus2": "Virginia, USA",
        "usgoviowa": "Iowa, USA",
        "usgovvirginia": "Virginia, USA",
        "northcentralus": "Illinois, USA",
        "southcentralus": "Texas, USA",
        "westus": "California, USA",
        "northeurope": "Ireland",
        "westeurope": "Netherlands",
        "eastasia": "Hong Kong",
        "southeastasia": "Singapore",
        "japaneast": "Tokyo, Japan",
        "japanwest": "Osaka, Japan",
        "brazilsouth": "Sao Paulo State, Brazil",
        "australiaeast": "New South Wales, Australia",
        "australiasoutheast": "Victoria, Australia"
    }

    def __init__(self, tenant_id, subscription_id, key, secret, secure=True, host=None, port=None,
                 api_version=None, region=None, **kwargs):
        self.tenant_id = tenant_id
        self.subscription_id  = subscription_id
        super(AzureNodeDriver, self).__init__(key=key, secret=secret, secure=secure,
                                         host=host, port=port,
                                              api_version=api_version,
                                              region=region, **kwargs)
        if self.region is not None:
            loc_id = self.region.lower().replace(" ", "")
            self.default_location = NodeLocation(loc_id,
                                                 self.region,
                                                 self._location_to_country.get(loc_id),
                                                 self)
        else:
            self.default_location = None

    def _ex_connection_class_kwargs(self):
        kwargs = super(AzureNodeDriver, self)._ex_connection_class_kwargs()
        kwargs['tenant_id'] = self.tenant_id
        kwargs['subscription_id'] = self.subscription_id
        return kwargs

    def list_locations(self):
        action = "/subscriptions/%s/providers/Microsoft.Compute" % (self.subscription_id)
        r = self.connection.request(action, params={"api-version": "2015-01-01"})

        for rt in r.object["resourceTypes"]:
            if rt["resourceType"] == "virtualMachines":
                return [self._to_location(l) for l in rt["locations"]]

        return []

    def list_sizes(self, location=None):
        if location is None and self.default_location:
            location = self.default_location
        else:
            raise ValueError("location is required.")
        action = "/subscriptions/%s/providers/Microsoft.Compute/locations/%s/vmSizes" % (self.subscription_id, location.id)
        r = self.connection.request(action, params={"api-version": "2015-06-15"})
        return [self._to_node_size(d) for d in r.object["value"]]

    def ex_list_publishers(self, location=None):
        if location is None and self.default_location:
            location = self.default_location
        else:
            raise ValueError("location is required.")

        action = "/subscriptions/%s/providers/Microsoft.Compute/locations/%s/publishers" % (self.subscription_id, location.id)
        r = self.connection.request(action, params={"api-version": "2015-06-15"})
        return [(p["id"], p["name"]) for p in r.object]

    def ex_list_offers(self, publisher):
        action = "%s/artifacttypes/vmimage/offers" % (publisher)
        r = self.connection.request(action, params={"api-version": "2015-06-15"})
        return [(p["id"], p["name"]) for p in r.object]

    def ex_list_skus(self, ex_offer):
        action = "%s/skus" % (ex_offer)
        r = self.connection.request(action, params={"api-version": "2015-06-15"})
        return [(sku["id"], sku["name"]) for sku in r.object]

    def ex_list_image_versions(self, ex_sku=None):
        action = "%s/versions" % (ex_sku)
        r = self.connection.request(action, params={"api-version": "2015-06-15"})
        return [(img["id"], img["name"]) for img in r.object]

    def list_images(self, location=None, ex_publisher=None, ex_offer=None, ex_sku=None, ex_version=None, ex_urn=None):
        images = []

        if location is None:
            locations = [self.default_location]
        else:
            locations = [location]

        if ex_urn:
            (ex_publisher, ex_offer, ex_sku, ex_version) = ex_urn.split(":")

        for loc in locations:
            if not ex_publisher:
                publishers = self.ex_list_publishers(loc)
            else:
                publishers = [("/subscriptions/%s/providers/Microsoft.Compute/locations/%s/publishers/%s" % (self.subscription_id, loc.id, ex_publisher), ex_publisher)]

            for pub in publishers:
                if not ex_offer:
                    offers = self.ex_list_offers(pub[0])
                else:
                    offers = [("%s/artifacttypes/vmimage/offers/%s" % (pub[0], ex_offer), ex_offer)]

                for off in offers:
                    if not ex_sku:
                        skus = self.ex_list_skus(off[0])
                    else:
                        skus = [("%s/skus/%s" % (off[0], ex_sku), ex_sku)]

                    for sku in skus:
                        if not ex_version:
                            versions = self.ex_list_image_versions(sku[0])
                        else:
                            versions = [("%s/versions/%s" % (sku[0], ex_version), ex_version)]

                        for v in versions:
                            images.append(AzureImage(v[1], sku[1], off[1], pub[1], loc.id, self.connection.driver))
        return images


    def list_nodes(self, ex_resource_group=None, ex_fetch_nic=True):
        if ex_resource_group:
            action = "/subscriptions/%s/resourceGroups/%s/providers/Microsoft.Compute/virtualMachines" % (self.subscription_id, ex_resource_group)
        else:
            action = "/subscriptions/%s/providers/Microsoft.Compute/virtualMachines" % (self.subscription_id)
        r = self.connection.request(action, params={"api-version": "2015-06-15"})
        return [self._to_node(n, fetch_nic=ex_fetch_nic) for n in r.object["value"]]

    def ex_list_networks(self):
        action = "/subscriptions/%s/providers/Microsoft.Network/virtualnetworks" % (self.subscription_id)
        r = self.connection.request(action, params={"api-version": "2015-06-15"})
        return [AzureNetwork(net["id"], net["name"], net["location"], net["properties"]) for net in r.object["value"]]

    def ex_list_subnets(self, network):
        action = "%s/subnets" % (network.id)
        r = self.connection.request(action, params={"api-version": "2015-06-15"})
        return [AzureSubnet(net["id"], net["name"], net["properties"]) for net in r.object["value"]]

    def ex_list_nics(self, resource_group):
        action = "/subscriptions/%s/providers/Microsoft.Network/networkInterfaces" % (self.subscription_id, resource_group)
        r = self.connection.request(action, params={"api-version": "2015-06-15"})
        return [self._to_nic(net) for net in r.object["value"]]

    def ex_get_nic(self, id):
        r = self.connection.request(id, params={"api-version": "2015-06-15"})
        return self._to_nic(r.object)

    def ex_get_public_ip(self, id):
        r = self.connection.request(id, params={"api-version": "2015-06-15"})
        return self._to_ip_address(r.object)

    def ex_list_public_ips(self, resource_group):
        action = "/subscriptions/%s/providers/Microsoft.Network/publicIPAddresses" % (self.subscription_id, resource_group)
        r = self.connection.request(action, params={"api-version": "2015-06-15"})
        return [self._to_ip_address(net) for net in r.object["value"]]

    def ex_create_public_ip(self, name, resource_group, location=None):
        if location is None and self.default_location:
            location = self.default_location
        else:
            raise ValueError("location is required.")

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
        return self._to_ip_address(r.object)

    def ex_create_network_interface(self, name, subnet, resource_group, location = None, public_ip = None):
        if location is None:
            if self.default_location:
                location = self.default_location
            else:
                raise ValueError("location is required.")

        target = "/subscriptions/%s/resourceGroups/%s/providers/Microsoft.Network/networkInterfaces/%s" % (self.subscription_id, resource_group, name)

        data = {
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

    def ex_create_tags(self, target, tags, replace=False):
        r = self.connection.request(target, params={"api-version": "2015-06-15"})
        if replace:
            r.object["tags"] = tags
        else:
            r.object["tags"].update(tags)
        r = self.connection.request(target, data=r.object, params={"api-version": "2015-06-15"}, method="PUT")

    def create_node(self, name,
                    size,
                    image,
                    auth,
                    ex_resource_group,
                    ex_storage_account,
                    ex_blob_container="vhds",
                    location=None,
                    ex_user_name="azureuser",
                    ex_network=None,
                    ex_subnet=None,
                    ex_nic=None,
                    ex_tags={},
                    **kwargs):

        if location is None:
            location = self.default_location
        if ex_nic is None:
            if ex_network is None:
                raise ValueError("Must provide either ex_nic or ex_network")
            if ex_subnet is None:
                ex_subnet = "default"
            ex_nic = self.ex_create_network_interface(name + "-nic",
                                                      AzureSubnet("/subscriptions/%s/resourceGroups/%s/providers/Microsoft.Network/virtualnetworks/%s/subnets/%s" % (self.subscription_id, ex_resource_group, ex_network, ex_subnet), ex_subnet, {}),
                                                      ex_resource_group,
                                                      location)

        auth = self._get_and_check_auth(auth)

        target = "/subscriptions/%s/resourceGroups/%s/providers/Microsoft.Compute/virtualMachines/%s" % (self.subscription_id, ex_resource_group, name)

        data={
            "id": target,
            "name": name,
            "type": "Microsoft.Compute/virtualMachines",
            "location": location.id,
            "tags": ex_tags,
            "properties": {
                "hardwareProfile": {
                    "vmSize": size.id
                },
                "storageProfile": {
                    "imageReference": {
                        "publisher": image.publisher,
                        "offer": image.offer,
                        "sku": image.sku,
                        "version": image.version
                    },
                    "osDisk": {
                        "name": "virtualmachine-osDisk",
                        "vhd": {
                            "uri": "https://%s.blob.core.windows.net/%s/%s-os.vhd" % (ex_storage_account, ex_blob_container, name)
                        },
                        "caching": "ReadWrite",
                        "createOption":"FromImage"
                    }
                },
                "osProfile": {
                    "computerName": name
                },
                "networkProfile": {
                    "networkInterfaces": [
                        {
                            "id": ex_nic.id
                        }
                    ]
                }
            }
        }

        data["properties"]["osProfile"]["adminUsername"] = ex_user_name

        if isinstance(auth, NodeAuthSSHKey):
            data["properties"]["osProfile"]["adminPassword"] = binascii.hexlify(os.urandom(20))
            data["properties"]["osProfile"]["linuxConfiguration"] = {
                "disablePasswordAuthentication": "true",
                "ssh": {
                    "publicKeys": [
                        {
                            "path": '/home/' + ex_user_name + '/.ssh/authorized_keys',
                            "keyData": auth.pubkey
                        }
                    ]
                }
            }
        elif isinstance(auth, NodeAuthPassword):
            data["properties"]["osProfile"]["linuxConfiguration"] = {
                "disablePasswordAuthentication": "false"
            }
            data["properties"]["osProfile"]["adminPassword"] = auth.password
        else:
            raise ValueError("Must provide NodeAuthSSHKey or NodeAuthPassword in auth")

        r = self.connection.request(target,
                                    params={"api-version": "2015-06-15"},
                                    data=data,
                                    method="PUT")

        node = self._to_node(r.object)
        node.size = size
        node.image = image
        return node

    def ex_get_storage_account_keys(self, resourceGroup, storageAccount):
        r = self.connection.request("/subscriptions/%s/resourceGroups/%s/providers/Microsoft.Storage/storageAccounts/%s/listKeys" % (self.subscription_id, resourceGroup, storageAccount), params={"api-version": "2015-05-01-preview"}, method="POST")
        return r.object

    def destroy_node(self, node, ex_destroy_nic=True, ex_destroy_vhd=True):
        try:
            r = self.connection.request(node.id,
                                        params={"api-version": "2015-06-15"},
                                        method='DELETE')
        except BaseHTTPError as h:
            if h.code == 202:
                pass
            else:
                raise

        if ex_destroy_nic:
            for nic in node.extra["properties"]["networkProfile"]["networkInterfaces"]:
                while True:
                    try:
                        r = self.connection.request(nic["id"],
                                            params={"api-version": "2015-06-15"},
                                            method='DELETE')
                        break
                    except BaseHTTPError as h:
                        if h.code == 202:
                            break
                        if h.code == 400 and h.message["error"]["code"] == "NicInUse":
                            time.sleep(10)
                        else:
                            raise

        if ex_destroy_vhd:
            try:
                resourceGroup = node.id.split("/")[4]
                uri = node.extra["properties"]["storageProfile"]["osDisk"]["vhd"]["uri"].split("/")
                storageAccount = uri[2].split(".")[0]
                blobContainer = uri[3]
                blob = uri[4]
                keys = self.ex_get_storage_account_keys(resourceGroup, storageAccount)
                blobdriver = AzureBlobsStorageDriver(storageAccount, keys["key1"])
                blobdriver.delete_object(blobdriver.get_object(blobContainer, blob))
            except BaseHTTPError as h:
                print h.code, h.message
                if h.code == 202:
                    pass
                else:
                    raise

    def reboot_node(self, node):
        target = "%s/restart" % node.id
        r = self.connection.request(target,
                                    params={"api-version": "2015-06-15"},
                                    method='POST')

    def ex_start_node(self, node):
        target = "%s/start" % node.id
        r = self.connection.request(target,
                                    params={"api-version": "2015-06-15"},
                                    method='POST')
        return r.object

    def ex_stop_node(self, node, deallocate=False):
        if deallocate:
            target = "%s/deallocate" % node.id
        else:
            target = "%s/stop" % node.id
        r = self.connection.request(target,
                                    params={"api-version": "2015-06-15"},
                                    method='POST')
        return r.object


    def _to_node(self, data, fetch_nic=True):
        private_ips = []
        public_ips = []
        if fetch_nic:
            for nic in data["properties"]["networkProfile"]["networkInterfaces"]:
                n = self.ex_get_nic(nic["id"])
                priv = n.extra["ipConfigurations"][0]["properties"].get("privateIPAddress")
                if priv:
                    private_ips.append(priv)
                pub = n.extra["ipConfigurations"][0]["properties"].get("publicIPAddress")
                if pub:
                    pub_addr = self.ex_get_public_ip(pub["id"])
                    addr = pub_addr.extra.get("ipAddress")
                    if addr:
                        public_ips.append(addr)

        action = "%s/InstanceView" % (data["id"])
        r = self.connection.request(action, params={"api-version": "2015-06-15"})
        state = NodeState.UNKNOWN
        for status in r.object["statuses"]:
            if status["code"] == "ProvisioningState/creating":
                state = NodeState.PENDING
                break
            if status["code"] == "ProvisioningState/deleting":
                state = NodeState.TERMINATED
                break
            elif status["code"] == "PowerState/deallocated":
                state = NodeState.STOPPED
                break
            elif status["code"] == "PowerState/deallocating":
                state = NodeState.PENDING
                break
            elif status["code"] == "PowerState/running":
                state = NodeState.RUNNING

        node = Node(data["id"],
                    data["name"],
                    state,
                    public_ips,
                    private_ips,
                    driver=self.connection.driver,
                    extra=data)

        return node


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

    def _to_nic(self, data):
        return AzureNic(data["id"], data["name"], data["location"], data["properties"])

    def _to_ip_address(self, data):
        return AzureIPAddress(data["id"], data["name"], data["properties"])

    def _to_location(self, loc):
        # XXX for some reason the API returns location names like
        # "East US" instead of "eastus" which is what is actually needed
        # for other API calls, so do a name->id fixup and hope it works.
        loc_id = loc.lower().replace(" ", "")
        return NodeLocation(loc_id, loc, self._location_to_country.get(loc_id), self.connection.driver)

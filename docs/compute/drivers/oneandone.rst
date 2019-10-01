1&1 Compute Driver Documentation
================================

`1&1` is one of the world's largest hosting providers. We offer a range of services, including hosting solutions, domains, and websites.

The data centers/availability zones are located in:

- United States of America (US)
- Germany (DE)
- United Kingdom or Great Britain and Northern Ireland (GB)
- Spain (ES)

Instantiating a Driver
----------------------

To instantiate a driver you will need to pass the API key using the following constructor parameter:

* ``key`` - Your 1&1 API Key

You can obtain your API key in the `1&1 Cloud Panel` under Management ->
Users where an API key will be generated.

With a newly-generated API token you can instantiate a driver using:

.. literalinclude:: /examples/compute/oneandone/instantiate_driver.py
   :language: python


1&1 Implementation of Libcloud
------------------------------

The 1&1 driver implements the following ``NodeDriver`` functions:

* ``list_sizes`` - Returns a list of ``NodeSize``
* ``list_locations`` - Returns a list of ``NodeLocation``
* ``list_images`` - Returns a list of ``NodeImage``
* ``get_image`` - Returns a ``NodeImage``
* ``create_node`` - Creates a ``Node``
* ``list_nodes`` - Returns a list of ``Node``
* ``destroy_node`` - Destroys an existing ``Node``
* ``reboot_node`` - Reboots a ``Node``

1&1 Extension Functions
-----------------------

Server Functions
-----------------
* ``ex_rename_server`` - Allows you to change server name and description
* ``ex_get_server_hardware`` - Returns server's hardware specification
* ``ex_modify_server_hardware`` - Updates server hardware
* ``ex_modify_server_hdd`` - Updates a single server HDD
* ``ex_add_hdd`` - Adds a new HDD to server
* ``ex_remove_hdd`` - Removes a HDD from server
* ``ex_list_datacenters`` - Returns a list of available 1&1 data centers
* ``ex_get_server`` - Gets a server
* ``ex_shutdown_server`` - Shuts down a server
* ``ex_get_server_image`` - Gets server image
* ``ex_reinstall_server_image`` - Installs a new image on the server
* ``ex_list_server_ips`` -  Gets all server IP objects
* ``ex_assign_server_ip`` - Assigns a new IP address to the server
* ``ex_remove_server_ip`` - Removes an IP address from the server
* ``ex_get_server_firewall_policies`` - Gets a firewall policy attached to the server's IP address
* ``ex_add_server_firewall_policy`` - Adds a firewall policy to the server's IP address

Monitoring Policy Functions
---------------------------
* ``ex_list_monitoring_policies`` - Lists all monitoring policies
* ``ex_create_monitoring_policy`` - Creates a monitoring policy
* ``ex_delete_monitoring_policy`` - Deletes a monitoring policy
* ``ex_update_monitoring_policy`` - Updates monitoring policy
* ``ex_get_monitoring_policy`` - Fetches a monitoring policy
* ``ex_get_monitoring_policy_ports`` - Fetches monitoring policy ports
* ``ex_get_monitoring_policy_port`` - Fetches monitoring policy port
* ``ex_remove_monitoring_policy_port`` - Removes monitoring policy port
* ``ex_add_monitoring_policy_ports`` - Adds monitoring policy ports
* ``ex_get_monitoring_policy_processes`` - Fetches monitoring policy processes
* ``ex_get_monitoring_policy_process`` - Fetches monitoring policy process
* ``ex_remove_monitoring_policy_process`` - Removes monitoring policy process
* ``ex_add_monitoring_policy_processes`` - Adds monitoring policy processes
* ``ex_list_monitoring_policy_servers`` - List all servers that are being monitored by the policy
* ``ex_add_servers_to_monitoring_policy`` - Adds servers to monitoring policy
* ``ex_remove_server_from_monitoring_policy`` - Removes a server from monitoring policy

Shared Storage Functions
------------------------
* ``ex_list_shared_storages`` - Lists shared storages
* ``ex_get_shared_storage`` - Gets a shared storage
* ``ex_create_shared_storage`` - Creates a shared storage
* ``ex_delete_shared_storage`` - Removes a shared storage
* ``ex_attach_server_to_shared_storage`` - Attaches a single server to a shared storage
* ``ex_get_shared_storage_server`` - Gets a shared storage's server
* ``ex_detach_server_from_shared_storage`` - Detaches a server from shared storage

Public IP Functions
-------------------
* ``ex_list_public_ips`` - Lists all public IP addresses
* ``ex_create_public_ip`` - Creates a public IP
* ``ex_get_public_ip`` - Gets a public IP
* ``ex_delete_public_ip`` - Deletes a public IP
* ``ex_update_public_ip`` - Updates a Public IP

Private Network Functions
-------------------------
* ``ex_list_private_networks`` - Lists all private networks
* ``ex_create_private_network`` - Creates a private network
* ``ex_delete_private_network`` - Deletes a private network
* ``ex_update_private_network`` - Updates a private network
* ``ex_list_private_network_servers`` - Lists all private network servers
* ``ex_add_private_network_server`` - Adds servers to private network
* ``ex_remove_server_from_private_network`` - Removes a server from the private network

Load Balancer Functions
-----------------------
* ``ex_create_load_balancer`` - Creates a load balancer
* ``ex_update_load_balancer`` - Updates a load balancer
* ``ex_add_servers_to_load_balancer`` - Adds servers to a load balancers
* ``ex_remove_server_from_load_balancer`` - Removes a server from a load balancer
* ``ex_add_load_balancer_rule`` - Adds a rule to a load balancer
* ``ex_remove_load_balancer_rule`` - Removes a rule from a load balancer
* ``ex_list_load_balancers`` - Lists all load balancers
* ``ex_get_load_balancer`` - Gets a load balancer
* ``ex_list_load_balancer_server_ips`` - Lists load balanced server IP addresses
* ``ex_get_load_balancer_server_ip`` - Gets a balanced server IP address
* ``ex_list_load_balancer_rules`` - Lists load balancer rules
* ``ex_get_load_balancer_rule`` - Gets a load balancer rule
* ``ex_delete_load_balancer`` - Deletes a load balancer

Firewall Policy Functions
-------------------------
* ``ex_create_firewall_policy`` - Creates a firewall policy
* ``ex_list_firewall_policies`` - Lists firewall policies
* ``ex_get_firewall_policy`` - Gets a firewall policy
* ``ex_delete_firewall_policy`` - Deletes a firewall policy

Create a Node
-------------

To create a node on 1&1 using Libcloud, follow this example:

.. literalinclude:: /examples/compute/oneandone/create_node.py
   :language: python

This example will create a 1&1 server using 'S' as a small instance in  the 'ES' (spain) data center.

`create_node` has the following parameters:

Required parameters:

* ``name`` - Desired node name. Must be unique.
* ``image`` - Image ID retrieved from `list_images`.
* ``ex_fixed_instance_size_id`` - This is an ID of a flavor.

Optional parameters:

* ``auth`` - Password for the server. If none is provided, 1&1 will generate one for you, and return it in the response.
* ``location`` - Desired `NodeLocation`
* ``ex_ip`` - ID of a public IP address which can be created using `ex_create_public_ip`.
* ``ex_monitoring_policy_id`` - Id of a monitoring policy which can be created using `ex_create_monitoring_policy`.
* ``ex_firewall_policy_id`` - Id of a firewall policy which can be create using `ex_create_firewall_policy`.
* ``ex_loadbalancer_id`` - Id of a load balancer which can be create using `ex_create_load_balancer`.
* ``ex_description`` - Description for the server.
* ``ex_power_on`` - A boolean indicating whether a server will be `POWERED_ON` or `POWERED_OFF` when provisioned.


Create a Firewall Policy
------------------------

To create a firewall policy, follow this example:

.. literalinclude:: /examples/compute/oneandone/create_firewall_policy.py
   :language: python

This example will create a firewall policy with a TCP rule allowing access on port 80.

`ex_create_firewall_policy` has the following parameters:

Required parameters:

* ``name`` - Desired name for the firewall policy. Must be unique.
* ``rules`` - ``list`` of ``dict``:
  * ``protocol`` - One of the follwing protocols can be set TCP, UDP, TCP/UDP, ICMP, IPSEC.
  * ``port_from`` - Port range start. Must be between 1 and 65535.
  * ``port_to`` - Port range end. Must be between 1 and 65535.
  * ``source`` - Source IP address.


Optional parameters:

* ``description`` - Description of the firewall policy.


Create a Monitoring Policy
--------------------------

To create a monitoring policy, follow this example:

.. literalinclude:: /examples/compute/oneandone/create_monitoring_policy.py
   :language: python

`ex_create_monitoring_policy` has the following parameters:

Required parameters:

* ``name`` - Desired name for the monitoring policy. Must be unique.
* ``thresholds`` - ``dict`` of thresholds to be monitored. See the example
* ``ports`` - ``list`` of  ``dict`` defining which ports are to be monitored. See the example.
* ``processes`` - ``list`` of  ``dict`` defining which processes are to be monitored. See the example.

Optional parameters:

* ``description`` - Description of the monitoring policy.
* ``email`` - Email address where notifications will be sent.
* ``agent`` - Indicating whether an agent application should be installed on the host.

Create a Shared Storage
-----------------------

To create a shared storage, follow this example:

.. literalinclude:: /examples/compute/oneandone/create_shared_storage.py
   :language: python

Required parameters:

* ``name`` - ``str`` Desired name for the shared storage. Must be unique.
* ``size`` - ``int`` Size of the shared storage.
* ``datacenter_id`` - ``str`` 1&1 data center.

Optional parameters:

* ``description`` - Description of the shared storage.

Create a Load Balancer
----------------------


To create a load balancer, follow this example:

  .. literalinclude:: /examples/compute/oneandone/create_load_balancer.py
   :language: python

Required parameters:

* ``name`` - ``str`` Desired name for the shared storage. Must be unique.
* ``method`` - ``str``
* ``rules`` - ``list`` of ``dict``

Optional parameters:

* ``persistence``
* ``persistence_time``
* ``health_check_test``
* ``health_check_interval``
* ``health_check_path``
* ``health_check_parser``
* ``datacenter_id``
* ``description``


Create a Public IP
------------------

To create a public IP address, follow this example:

  .. literalinclude:: /examples/compute/oneandone/create_public_ip.py
   :language: python

Required parameters:

* ``type`` - ``str`` IPV4 or IPV6

Optional parameters:

* ``reverse_dns`` - ``str``
* ``datacenter_id`` - ``str`` 1&1 Datacenter


Create a Private Network
------------------------

To create a private network, follow this example:

  .. literalinclude:: /examples/compute/oneandone/create_private_network.py
   :language: python

Required parameters:

* ``name`` - ``str`` name of the public network.

Optional parameters:

* ``datacenter_id`` - ``str``
* ``network_address``
* ``subnet_mask``

Changelog
=========

Changes in current version of Apache Libcloud
---------------------------------------------

General
~~~~~~~

- Introduced new base API for instantiating drivers
  (GITHUB-822)
  [Anthony Shaw]

- Added certificate path for SLES12/OpenSUSE12
  (GITHUB-884)
  [Michael Calmer]

- Deprecate DigitalOcean v1 API support in favour of v2 API
  (GITHUB-889)(GITHUB-892)
  [Andrew Starr-Bochicchio]

- Deprecate RunAbove cloud drivers in favour of new OVH cloud driver
  (GITHUB-891)
  [Anthony Monthe]


Compute
~~~~~~~

- Fix reporting function for detailed admin logs in Dimension Data Driver
  (GITHUB-898)
  [Anthony Shaw]

- Added edit firewall functionality to Dimension Data driver
  (GITHUB-893)
  [Samuel Chong]

- Bugfix - Fixed listing nodes issue in Python 3
  (LIBCLOUD-858, GITHUB-894)
  [Fahri Cihan Demirci]

- Added FCU (Flexible Compute Unit) support to the Outscale driver.
  (GITHUB-890)
  [Javier M. Mellid]

- [google compute] Add "WINDOWS" guestOsFeatures option.
  (GITHUB-861)
  [Max Illfelder]

- When creating volumes on OpenStack with defaults for `location` or `volume_type`,
  newer OpenStack versions would throw errors. The OpenStack driver will now only
  post those arguments if non-`NoneType`.
  (GITHUB-857)
  [Allard Hoeve]

- When fetching the node details of a non-existing node, OpenStack would raise a
  `BaseHTTPError` instead of returning `None`, as was intended. Fixed tests and code.
  (GITHUB-864)

- Added `ex_stop_node` to the OpenStack driver.
  (GITHUB-865)

- When creating volume snapshot, the arguments `name` and `description` are truely
  optional when working with newer OpenStack versions. The OpenStack driver will now
  only post thost arguments if they are non-`NoneType`.
  (GITHUB-866)

- StorageVolumeSnapshot now has an attribute `name` that has the name of the snapshot
  if the provider supports it. This used to be `.extra['name']`, but that is inconsistent
  with `Node` and `StorageVolume`. The `extra` dict still holds `name` for backwards
  compatibility.
  (GITHUB-867)
  [Allard Hoeve]

Container
~~~~~~~~~

- Introduced new Racher driver
  (GITHUB-876)
  [Mario Loria]

- Fixed bug in Docker util library for fetching images from the docker hub API. API
  was returning 301 and redirects were not being followed.
  (GITHUB-862)
  [Anthony Shaw]

Load Balancer
~~~~~~~~~~~~~

- Added fetch tags support in elb driver
  (GITHUB-848)
  [Anton Kozyrev]

Storage
~~~~~~~

- Added storage permissions for Google Cloud Storage
  (GITHUB-860)
  [Scott Crunkleton]

Changes in Apache Libcloud 1.2.1
--------------------------------

Backup
~~~~~~

- Fix issue enabling backups on Dimension Data driver
  (GITHUB-858)
  [Mark Maglana][Jeff Dunham][Anthony Shaw]

Changes in Apache Libcloud 1.2.0
--------------------------------

General
~~~~~~~

- Fix caching of auth tokens in the Google Compute Engine drivers. Now we make
  sure that the file is truncated before writing a new token. Not truncating
  the file would cause issues if the new token is shorted then the existing one
  which is cached in the file.
  (GITHUB-844, LIBCLOUD-835)
  [Paul Tiplady]

Compute
~~~~~~~

- [gce] Fix image undeprecation in GCE
  (GITHUB-852)
  [Max Illfelder]

- [gce] Added Managed Instance Groups
  (GITHUB-842)
  [Tom Melendez]

- [gce] Allow undeprecation of an image.
  (GITHUB-851)
  [Max Illfelder]

- [cloudstack] BUGFIX Values with wildcards failed signature validation
  (GITHUB-846)
  [Ronald van Zantvoot]

- [cloudstack] Added StorageState-Migrating to the cloudstack driver.
  (GITHUB-847)
  [Marc-Aurèle Brothier]

- [google compute] Update copy image logic to match create image.
  (GITHUB-828)
  [Max Illfelder]

- Removed HD attribute from the Abiquo compute driver to support the 3.4 API
  (GITHUB-840)
  [David Freedman]

- Add image and size details to `list_nodes` response in Dimension Data driver
  (GITHUB-832)
  [Anthony Shaw]

- Add support for changing VM admin password in VMware driver
  (GITHUB-833)
  [Juan Font Alonso]

- Add Barcelona (Spain) region to the Aurora Compute driver.
  (GITHUB-835)
  [Wido den Hollander]

- Various improvements in the libvirt driver.
  (GITHUB-838)
  [Rene Kjellerup]

Load balancer
~~~~~~~~~~~~~

- Add support for temporary IAM role credentials (token) to the AWS ELB driver.
  (GITHUB-843)
  [Anton Kozyrev]

DNS
~~~

- Updated the 'extra' parameter in `update_record()` to be optional in aurora driver
  (GITHUB-830)
  [Wido den Hollander]

- Support for iterating over records and zones in the Aurora DNS driver
  (GITHUB-829)
  [Wido den Hollander]

- Add support for DS, PTR, SSFHFP and TLSA record type to the Aurora DNS
  driver.
  (GITHUB-834)
  [Wido den Hollander]

Container
~~~~~~~~~

- Add network mode and labels when creating containers within
  docker driver
  (GITHUB-831)
  [Jamie Cressey]

Storage
~~~~~~~

- Fix authentication issue in S3/China region, disabled multipart uploads as not supported
  by region.
  (GITHUB-839)
  [Luke Morfitt]

Changes with Apache Libcloud 1.1.0
----------------------------------

General
~~~~~~~

- Add support for automatic SNI (SSL extension) using the hostname
  supplied to connect to.

  Note: This functionality is only available in Python 2.7.9 and
  Python >= 3.2.
  (LIBCLOUD-827, GITHUB-808)
  [David Freedman]

Compute
~~~~~~~

- Add support image guest OS features in GCE driver
  (GITHUB-825)
  [Max Illfelder]

- Added forceCustimization option for vcloud director driver
  (GITHUB-824)
  [Juan Font]

- Add node lookup by UUID for libvirt driver
  (GITHUB-823)
  [Frank Wu]

- Add block storage support to DigitalOcean node driver
  (GITHUB-807)
  [Adam Wolfe Gordon]

- Add SASL auth support to libvirt driver.
  (GITHUB-809)
  [Katana-Steel]

- Allow VIPs in Dimension Data driver to bind to any port.
  (GITHUB-818)
  [Mark Maglana]

- Add support for deleting a security group to the Aliyun ECS driver.
  (GITHUB-816)
  [Heng Wu]

- Add ``ex_force_customization`` argument to the ``ex_deploy_node`` in vCloud
  driver.
  (GITHUB-824)
  [Juan Font]

- Add support for listing  attributes for a particular security group
  (``ex_list_security_group_attributes``) to the Aliyun ECS driver.
  (GITHUB-826)
  [Heng Wu]

- Add new Mumbai, India region to the EC2 driver.
  [Tomaz Muraus]

- Add driver for the new AWS cn-north-1 region.
  (GITHUB-827, LIBCLOUD-820)
  [Jamie Cressey]

- Fix authentication with temporary IAM role credentials (token) in the EC2
  driver.
  (GITHUB-820)
  [Alejandro González]

Container
~~~~~~~~~

- Fixed API compatibility for Docker Container driver with API 1.24, set driver
  to use versioned URL for all communication. Backported changes to 1.21 API
  (GITHUB-821)
  [Anthony Shaw]

Load Balancer
~~~~~~~~~~~~~

- Added additional parameters to the Rackspace driver in `list_balancers` for filtering and
  searching.
  (GITHUB-803)
  [João Paulo Raittes]


Changes with Apache Libcloud 1.0.0
----------------------------------

General
~~~~~~~

- Fix a regression with ``timeout`` argument provided via
  ``_ex_connection_class_kwargs`` method being overriden with ``None`` inside
  the ``BaseDriver`` constructor method.

  Reported by Jay Rolette.
  (GITHUB-755)
  [Tomaz Muraus, Jay Rolette]

- Fix OpenStack v3 authentication and allow user to provide a custom value for
  the OpenStack ``domain`` parameter. Previously only possible value as a
  default value of ``Default``.
  (GITHUB-744)
  [Lionel Schaub]

- Add support for authenticating against Keystone and OpenStack based clouds
  using OpenID Connect tokens.
  (GITHUB-789)
  [Miguel Caballer]

Compute
~~~~~~~

- GCE nodes can be launched in a subnetwork
  (GITHUB-783)
  [Lars Larsson]

- Add Subnetworks to GCE driver
  (GITHUB-780)
  [Eric Johnson]

- Fix missing pricing data for GCE
  (LIBCLOUD-713, GITHUB-779)
  [Eric Johnson]

- Add Image Family support for GCE
  (GITHUB-778)
  [Rick Wright]

- Fix a race condition on GCE driver `list_nodes()`- Invoking GCE’s
  `list_nodes()` while some VMs are being shutdown can result in the following
  `libcloud.common.google.ResourceNotFoundError` exception to be raised.
  (GITHUB-727)
  [Lénaïc Huard]

- Allow user to filter nodes by location by adding optional `location`
  argument to the `list_nodes()` method in the CloudStack driver.
  (GITHUB-737)
  [Lionel Schaub]

- Fix OpenStack IP type resolution - make sure IP addresses are correctly
  categorized and assigned on `private_ips` and `public_ips` Node attribute.
  (GITHUB-738)
  [Lionel Schaub]

- Add new `Perth, Australia` and `Manila, Philippines` region to the CloudSigma
  v2 driver.
  [Tomaz Muraus]

- Update libvirt driver so it returns false if a non-local libvirt URL is used
  (right now only local instances are supported).
  (LIBCLOUD-820, GITHUB-788)
  [René Kjellerup]

- Update libvirt driver to use `ip neight` command instead of `arp` to retrieve
  node MAC address if `arp` command is not available or the current user
  doesn't have permission to use it.
  (LIBCLOUD-820, GITHUB-788)
  [René Kjellerup]

- Update ``create_volume`` method in the CloudStack driver and add
  ``ex_volume_type`` argument to it. If this argument is provided, a volume
  which names matches this argument value will be searched and selected among
  the available disk offerings.
  (GITHUB-785)
  [Greg Bishop]

Storage
~~~~~~~

- Add support for AWS signature v4 to the Outscale storage driver.
  (GITHUB-736)
  [Javier M. Mellid]


- Add new S3 RGW storage driver.
  (GITHUB-786, GITHUB-792)
  [Javier M. Mellid]

Loadbalancer
~~~~~~~~~~~~

- Update AWS ELB driver to use signature version 4 for authentication. This
  way, the driver also work with the `eu-central-1` region.
  (GITHUB-796)
  [Tobias Paepke]

DNS
~~~

- Add BuddyNS driver.
  (GITHUB-742)
  [Oltjano Terpollari]

- Added DNSPod driver (https://www.dnspod.com).
  (GITHUB-787)
  [Oltjano Terpollari]

Changes with Apache Libcloud 1.0.0-rc2
--------------------------------------

General
~~~~~~~

- Fix a bug with consuming stdout and stderr in the paramiko SSH client which
  would manifest itself under very rare condition when a consumed chunk only
  contained a single byte or part of a multi byte UTF-8 character.
  [Lakshmi Kannan, Tomaz Muraus]

- Increase default chunk size from ``1024`` to ``4096`` bytes in the paramiko
  SSH client. This results in smaller number of receive calls on the average.
  [Tomaz Muraus]

- Fix to Dimension Data API address for Middle-East and Africa
  (GITHUB-700)
  [Anthony Shaw]

- Addition of Dimension Data Australia federal government region to dimension data
  drivers.
  (GITHUB-700)
  [Anthony Shaw]

- Throw a more user-friendly exception on "No address associated with hostname".
  (GITHUB-711, GITHUB-714, LIBCLOUD-803)
  [Tomaz Muraus, Scott Crunkleton]

* Remove deprecated provider constants with the region in the name and related
  driver classes (e.g. ``EC2_US_EAST``, etc.).

  Those drivers have moved to single provider constant + ``region`` constructor
  argument model.
  [Tomaz Muraus]

* Introduce new `list_regions`` class method on the base driver class. This
  method is to be used with provider drivers which support multiple regions and
  ``region`` constructor argument. It allows users to enumerate available /
  supported regions.
  [Tomaz Muraus]

Compute
~~~~~~~

- [dimension data] added support for VMWare tools VM information inside list_nodes responses
  (GITHUB-734)
  [Jeff Dunham]

- [ec2] added ex_encrypted and ex_kms_key_id optional parameters to the create volume method
  (GITHUB-729)
  [Viktor Ognev]

- [dimension data] added support for managing host anti-affinity rules, added paging support to
  all supported calls and added support for requesting priority ordering when creating ACL rules
  (GITHUB-726)
  [Jeff Dunham]

- [openstack] when creating floating IPs, added pool_id as an optional argument
  (GITHUB-725)
  [marko-p]

- [google compute] Added setMachineType method to allow for changing sizes of instances
  (GITHUB-721)
  [Eric Johnson]

- [google compute] allow bypassing image search in standard project list
  (GITHUB-713)
  [Max Illfelder]

- Add support for requesting a MKS token for accessing the remote console in VMware
  vCloud driver
  (GITHUB-706)
  [Juan Font Alonso]

- Add support in VMware vCloud driver for v5.5 API, with snapshot support
  (GITHUB-658)
  [Juan Font Alonso]

- Added support for adding a family to an image on Google Compute Driver
  (GITHUB-704)
  [Max Illfelder]

- Deprecated IBM SCE, HP Helion, OpSource, Ninefold and CloudFrames drivers, removed
  driver code and tests.
  (GITHUB-701, LIBCLOUD-801)
  [Anthony Shaw]

- Introduced error messages (`libcloud.compute.deprecated`) for deprecated drivers
  (GITHUB-701, LIBCLOUD-801)
  [Anthony Shaw]

- New Compute drivers- BSNL, Indosat, Med-1, NTT-America, Internet Solutions
  (GITHUB-700)
  [Anthony Shaw]

- Fix to set default signature version for AWS Seoul region to v4, removed
  non-supported size (hs1.xlarge)
  (GITHUB-684)
  [Geunwoo Shin]

- Support filtering by location in list_nodes for dimension data compute driver
  fix lack of paging support
  (GITHUB-691)
  [Jeff Dunham]

- Support for filtering by IPv4, IPv6, network, network domain, VLAN in Dimension
  data driver.
  (GITHUB-694)
  [Jeff Dunham]

- Added `Node.created_at` which, on supported drivers, contains the datetime the
  node was first started.
  (GITHUB-698)
  [Allard Hoeve] [Rick van de Loo]

- New driver for Aliyun Elastic Compute Service.
  (LIBCLOUD-802, GITHUB-712)
  [Sam Song, Heng Wu]

Storage
~~~~~~~

- Added Outscale storage driver
  (GITHUB-730)
  [Javier M. Mellid]

- Improvements to Google Auth for Storage and Compute and MIME bug fix
  (LIBCLOUD-800, GITHUB-689)
  [Scott Crunkleton]

- Implement ``get_container``, ``get_object`` and ``upload_object_via_stream``
  methods in the Backblaze B2 storage driver.

  Note: Backblaze API doesn't upload streaming uploads so when using
  ``upload_object_via_stream`` whole file is read and buffered in memory.
  (GITHUB-696)
  [Jay jshridha]

- New driver for Aliyun OSS Storage Service.
  (LIBCLOUD-802, GITHUB-712)
  [Sam Song]

Loadbalancer
~~~~~~~~~~~~

- New driver for Aliyun SLB Loadbalancer Service.
  (LIBCLOUD-802, GITHUB-712)
  [Sam Song]

DNS
~~~~

- Added NearlyFreeSpeech.net (NSFN) driver
  [Ken Drayer]
  (GITHUB-733)

- Added Lua DNS driver
  [Oltjano Terpollari]
  (GITHUB-732)

- Added NSOne driver
  [Oltjano Terpollari]
  (GITHUB-710)

- Fix a bug in the GoDaddy driver - make sure ``host`` attribute on the
  connection class is correctly set to the hostname.
  [Tomaz Muraus]

- Fix handling of ``MX`` records in the Gandi driver.
  (GITHUB-718)
  [Ryan Lee]

Backup
~~~~~~

- Dimension Data - added additional testing, fixed bug on client response naming,
  added support for adding backup clients to a backup enabled node.
  (GITHUB-692, GITHUB-693, GITHUB-695)
  [Jeff Dunham]

Changes with Apache Libcloud 1.0.0-pre1
---------------------------------------

General
~~~~~~~

- Introduction of container based drivers for Docker, Rkt and Container-as-a-service
  providers
  (LIBCLOUD-781, GITHUB-666)
  [Anthony Shaw]

- Introduce a new ``libcloud.backup`` API for Backup as a Service projects and
  products.
  (GITHUB-621)
  [Anthony Shaw]

- Also retry failed HTTP(s) requests upon transient "read operation timed out"
  SSL error.
  (GITHUB-556, LIBCLOUD-728)
  [Scott Kruger]

- Throw a more user-friendly exception if a client fails to establish SSL / TLS
  connection with a server because of an unsupported SSL / TLS version.
  (GITHUB-682)
  [Tomaz Muraus]

Compute
~~~~~~~

- Add ap-northeast-2 region to EC2 driver (South Korea)
  (GITHUB-681)
  [Anthony Shaw]

- Added Added volume type to EC2 volume extra to EC2 driver.
  (GITHUB-680)
  [Gennadiy Stas]

- Add LazyObject class that provides lazy-loading, see `GCELicense` for usage
  (LIBCLOUD-786, GITHUB-665)
  [Scott Crunkleton]

- Added t2.nano instance type to EC2 Compute driver
  (GITHUB-663)
  [Anthony Shaw]

- Support for passing the image ID as a string instead of an instance of image when
  creating nodes in Dimension Data driver.
  (GITHUB-664)
  [Anthony Shaw]

DNS
~~~

- Add support for 'health checks' in Aurora DNS driver
  (GITHUB-672)
  [Wido den Hollander]

- Make sure ``ttl`` attribute is correctly parsed and added to the ``Record``
  ``extra`` dictionary.
  (GITHUB-675)
  [Wido den Hollander]

- Improve unit tests of Aurora DNS driver
  (GITHUB-679)
  [Wido den Hollander]

Changes with Apache Libcloud 0.20.1
-----------------------------------

Compute
~~~~~~~

- [google] Allow for old and new style service account client email address
  (LIBCLOUD-785)
  [Hoang Phan]

Changes with Apache Libcloud 0.20.0
-----------------------------------

General
~~~~~~~

- Added .editorconfig file for easier editing
  (GITHUB-625)
  [Misha Brukman]

- Fix a bug with Libcloud accidentally setting paramiko root logger level to
  DEBUG (this should only happen if ``LIBCLOUD_DEBUG`` environment variable is
  provided).

  Reported by John Bresnahan.
  (LIBCLOUD-765)
  [Tomaz Muraus, John Bresnahan]

- Simply travis and tox config (.travis.yml, tox.ini).
  (GITHUB-608)
  [Anthony Monthe]

- Fixed Python2.6 unit testing (and Google Cloud Storage tests)
  (GITHUB-648)
  [Scott Crunkleton]

Compute
~~~~~~~

- [google] Allow for old and new style service account client email address
  (LIBCLOUD-785)
  [Hoang Phan]

- Minor security improvement for storing cached GCE credentials
  (LIBCLOUD-718)
  [Siim Põder]

- Removed DreamHosts Compute Driver, DreamHosts users will now use the OpenStack Node driver since DreamHosts are OpenStack
  API compliant
  (GITHUB-655)
  [Stephano Maffulli]

- Added additional kwargs to the create_node method for Dimension Data driver, allowing the user to specify the RAM and
  CPU upfront. Added a ex_reconfigure_node method and ex_list_customer_images as well as updating the API to 2.1.
  (LIBCLOUD-783, GITHUB-656)
  [Anthony Shaw]

- The EC2 Instance Type updated with correct disk sizes (especially the disk size for the m3 instances),
  conversion errors between GiB an M[i]B, disk count were the cause.
  Added instance types - g2.8xlarge and t2.large.
  (GITHUB-646)
  [Philipp Hahn]

- Add update node, update VMware tools, add storage, change storage size or speed, remove storage to Dimension Data Driver.
  (LIBCLOUD-775, GITHUB-644)
  [Anthony Shaw]

- Include 'service_name' support in _parse_service_catalog_auth_v3 for Openstack Drivers
  (GITHUB-647)
  [Steve Gregory]

- Outscale inc & sas driver update
  (GITHUB-645)
  [@LordShion]

- Add new `eu-west-2` & `us-east-2` regions to the OUTSCALE_INC & OUTSCALE_SAS drivers.
  [Filipe Silva /lordshion]

- [google compute] add pricing data update script
  (GITHUB-464)
  [Misha Brukman]

- Fix a bug in the ``list_volumes`` method in the CloudStack driver so it
  returns an empty list if no volumes are found.
  (GITHUB-617)
  [Wido den Hollander]

- Return proper volume state for CloudStack volumes.
  (GITHUB-615, LIBCLOUD-764)
  [Wido den Hollander]

- Add support for multiple regions in Aurora compute driver
  (GITHUB-623)
  [Wido den Hollander]

- Fix value of ``node.extra['ip_addresses']`` node attribute in the CloudStack
  driver.
  (LIBCLOUD-767, GITHUB-627)
  [Atsushi Sasaki]

- Make sure that ``node.public_ips`` attribute in the CloudStack driver doesn't
  contain duplicated values..
  (LIBCLOUD-766, GITHUB-626)
  [Atsushi Sasaki]

- Allow user to wait for a resource to reach a desired state in the
  Dimension Data driver by using new ``ex_wait_for_state`` method.
  (LIBCLOUD-707, GITHUB-631)
  [Anthony Shaw]

- Added M4 pricing and instance information to EC2 driver
  (GITHUB-634)
  [Benjamin Zaitlen]

- Added C4 instance information to EC2 driver
  (GITHUB-638)
  [amitofs]

- Allow location of the datacenter to be supplied in ProfitBricks driver
  (LIBCLOUD-771, GITHUB-635)
  [Joel Reymont]

- Reduce redundant API calls in CloudStack driver
  (LIBCLOUD-590, GITHUB-641)
  [Atsushi Sasaki]

- Add an additional argument to libcloud.compute.drivers.GCENodeDriver.create_node
  to allow for creation of preemptible GCE instances
  (GITHUB-643)
  [@blawney]

- GoogleStorageDriver can now use either our S3 authentication or other Google Cloud Platform OAuth2 authentication methods.
  (GITHUB-633)
  [Scott Crunkleton]

- All NodeState, StorageVolumeState, VolumeSnapshotState and Provider attributes
  are now strings instead of integers.
  (GITHUB-624)
  [Allard Hoeve]

Storage
~~~~~~~

Loadbalancer
~~~~~~~~~~~~

DNS
~~~

- RackSpace driver - New DNS driver methods:
   - ex_iterate_ptr_records
   - ex_get_ptr_record
   - ex_create_ptr_record
   - ex_update_ptr_record
   - ex_delete_ptr_record

  This should cover all of the functionality offered by the Rackspace DNS API
  in regards to RDNS.
  (LIBCLOUD-780, GITHUB-652)
  [Greg Hill]

- Update ``create_record`` in the WorldWideDNS driver so it automatically
  selects a slot if one is not provided by the user via ``extra['entry']``
  argument.
  (GITHUB-621)
  [Alejandro Pereira]

- Introduce GoDaddy DNS Driver with examples and documentation.
  (LIBCLOUD-772, GITHUB-640, LIBCLOUD-778)
  [Anthony Shaw]

- Add new driver for CloudFlare DNS (https://www.cloudflare.com/dns/).
  (GITHUB-637)
  [Tomaz Muraus]

Changes with Apache Libcloud 0.19.0
-----------------------------------

General
~~~~~~~

- Update Rackspace AUTH_URL
  (LIBCLOUD-738)
  [Brian Curtin]

- Fix ``LIBCLOUD_DEBUG`` mode so it works on Python 3.x.
  [Tomaz Muraus]

- Fix Libcloud code so it doesn't throw an exception if simplejson < 2.1.0 is
  installed.
  (LIBCLOUD-714, GITHUB-577)
  [Erik Johnson]

- Fix endpoint URL for DimensionData Asia Pacific region.
  (GITHUB-585)
  [Anthony Shaw]

- Document potential time drift issue which could cause authentication in the
  GCE drivers to fail.
  (GITHUB-571)
  [Michal Tekel]

- Update documentation for EC2 - make sure they reflect region changes from
  0.14 release.
  (GITHUB-606)
  [James Guthrie]

Compute
~~~~~~~

- Fixed malformed XML requests with Dimension Data driver.
  (LIBCLOUD-760, GITHUB-610)
  [Anthony Shaw]

- Update list of scopes for Google Compute Engine driver.
  (GITHUB-607)
  [Otto Bretz]

- Allow user to filter VPC by project in the CloudStack driver by passing
  ``project`` argument to the ``ex_list_vps`` method.
  (GITHUB-516)
  [Syed Mushtaq Ahmed]

- Add volume management methods and other various improvements and fixes in the
  RunAbove driver.
  (GITHUB-561)
  [Anthony Monthe]

- Add support and update Dimension Data driver to use API v2.0 by default.
  (LIBCLOUD-736, GITHUB-564)
  [Anthony Shaw]

- Add new ``ex_virtual_network_name`` and ``ex_network_config`` argument to the
  `create_node`` method in the Azure driver. With those arguments user can now
  specify which virtual network to use.
  (GITHUB-569)
  [Jesaja Everling]

- Fix ``create_node`` method in the GCE driver calling inexistent method
  (ex_get_disk instead of ex_get_volume).
  (GITHUB-574)
  [Alex Poms]

- Allow user to pass ``proxy_url`` keyword argument to the VCloud driver
  constructor.
  (GITHUB-578)
  [Daniel Pool]

- Various fixes and improvements in the DimensionData driver (support for
  creating servers in MCP 1 and 2 data center, performance improvements in the
  location fetching, etc.).
  (GITHUB-587, GITHUB-593, LIBCLOUD-750, LIBCLOUD-753)
  [Anthony Shaw]

- Added ``ex_assign_public_ip`` argument to ``create_node`` in the EC2 driver.
  (GITHUB-590)
  [Kyle Long]

- Added ``ex_terminate_on_shutdown`` argument to ``create_node`` in the EC2
  driver.
  (GITHUB-595)
  [Kyle Long]

- Various fixes and improvements in the ``ex_authorize_security_group_ingress``
  in the CloudStack driver.
  (LIBCLOUD-749, GITHUB-580)
  [Lionel Schaub]

- Add pricing information for Softlayer.
  (LIBCLOUD-759, GITHUB-603)
  [David Wilson]

- Standardize VolumeSnapshot states into the ``state`` attribute.
  (LIBCLOUD-758, GITHUB-602)
  [Allard Hoeve]

Storage
~~~~~~~

- Add support for ``sa-east-1`` region to the Amazon S3 driver.
  (GITHUB-562)
  [Iuri de Silvio]

- Fix handling of binary data in Local storage driver on Python 3. Now the file
  which is to be written or read from is opened in the binary mode (``b`` flag).
  (LIBCLOUD-725, GITHUB-568)
  [Torf]

Loadbalancer
~~~~~~~~~~~~

- Add a new driver for DimensionData load-balancing service
  (http://cloud.dimensiondata.com/).
  (LIBCLOUD-737, GITHUB-567)
  [Anthony Shaw]

DNS
~~~

- Update Google Cloud DNS API from 'v1beta1' to 'v1'
  (GITHUB-583)
  [Misha Brukman]

- Add new driver for AuroraDNS service.
  (GITHUB-562, LIBCLOUD-735)
  [Wido den Hollander]

- Fix "_to_record" in the Route53 driver - make sure it doesn't throw if the
  record TTL is not available.
  [Tomaz Muraus]

- Add new driver for WorldWideDNS service
  (http://www.worldwidedns.net/home.asp).
  (GITHUB-566, LIBCLOUD-732)
  [Alejandro Pereira]

- Add new driver for DNSimple service (https://dnsimple.com/).
  (GITHUB-575, GITHUB-604, LIBCLOUD-739)
  [Alejandro Pereira, Patrick Humpal]

- Add new driver for PointDNS service (https://pointhq.com).
  (GITHUB-576, GITHUB-591, LIBCLOUD-740)
  [Alejandro Pereira]

- Add new driver for Vultr DNS service (https://www.vultr.com).
  (GITHUB-579, GITHUB-596, LIBCLOUD-745)
  [Alejandro Pereira, Janez Troha]

- Add new driver for Liquidweb DNS service (http://www.liquidweb.com/).
  (GITHUB-581, LIBCLOUD-746)
  [Oltjano Terpollari, Alejandro Pereira]

- Add new driver for Zonomi DNS hosting service (http://zonomi.com/).
  (GITHUB-582, LIBCLOUD-747)
  [Oltjano Terpollari, Alejandro Pereira]

- Add new driver for Durable DNS service (https://durabledns.com/).
  (GITHUB-588, LIBCLOUD-748)
  [Oltjano Terpollari, Alejandro Pereira]

Changes with Apache Libcloud 0.18.0
-----------------------------------

General
~~~~~~~

- Use native ``ssl.match_hostname`` functionality when running on Python >=
  3.2 and only require ``backports.ssl_match_hostname`` dependency on Python
  versions < 3.2.
  [Tomaz Muraus]

- Add support for AWS Signature version 4.

  Note: Currently only GET HTTP method is supported.
  (GITHUB-444)
  [Gertjan Oude Lohuis]

- Fix a bug in the debug mode logging (LIBCLOUD_DEBUG). Logging to the debug
  file would throw an exception if the text contained non-ascii characters.
  [Tomaz Muraus]

- Fix a bug with connection code throwing an exception if a port was a unicode
  type and not a str or int.
  (GITHUB-533, LIBCLOUD-716)
  [Avi Weit]

- Update ``is_valid_ip_address`` function so it also works on Windows.
  (GITHUB-343, GITHUB-498, LIBCLOUD-601, LIBCLOUD-686)
  [Nicolas Fraison, Samuel Marks]

- Add support for retrying failed HTTP requests.

  Retrying is off by default and can be enabled by setting
  ``LIBCLOUD_RETRY_FAILED_HTTP_REQUESTS`` environment variable.
  (GITHUB-515, LIBCLOUD-360, LIBCLOUD-709)

- Fix a bug in consuming stdout and stderr strams in Paramiko SSH client.
  In some cases (like connecting to localhost via SSH), exit_status_ready
  gets set immediately even before the while loop to consume the streams
  kicks in. In those cases, we will not have consumed the streams at all.
  (GITHUB-558)
  [Lakshmi Kannan]

Compute
~~~~~~~

- Google Compute now supports paginated lists including filtering.
  (GITHUB-491)
  [Lee Verberne]

- OpenStackNodeSize objects now support optional, additional fields that are
  supported in OpenStack 2.1: `ephemeral_disk`, `swap`, `extra`.
  (GITHUB-488, LIBCLOUD-682)
  [Greg Hill]

- StorageVolume objects now have an attribute `state` that holds a
  state variable that is standardized state across drivers. Drivers that
  currently support the `state` attribute are OpenStack and EC2.
  StorageVolume objects returned by drivers that do not support the
  attribute will have a `state` of `None`. When a provider returns a state
  that is unknown to the driver, the state will be `UNKNOWN`. Please report
  such states. A couple of drivers already put state fields in the `extra`
  fields of StorageVolumes. These fields were kept for
  backwards-compatibility and for reference.
  (GITHUB-476)
  [Allard Hoeve]

- StorageVolume objects on EC2 and OpenStack now have a key called snapshot_id
  in their extra dicts containing the snapshot ID the volume was based on.
  (GITHUB-479)
  [Allard Hoeve]

- OpenStack driver: deprecated ex_create_snapshot and ex_delete_snapshot in
  favor of create_volume_snapshot and destroy_volume_snapshot. Updated base
  driver method create_storage_volume argument name to be optional.
  (GITHUB-478)
  [Allard Hoeve]

- Add support for creating volumes based on snapshots to EC2 and OS drivers.
  Also modify signature of base NodeDriver.create_volume to reflect the fact
  that all drivers expect a StorageSnapshot object as the snapshot argument.
  (GITHUB-467, LIBCLOUD-672)
  [Allard Hoeve]

- VolumeSnapshots now have a `created` attribute that is a `datetime`
  field showing the creation datetime of the snapshot. The field in
  VolumeSnapshot.extra containing the original string is maintained, so
  this is a backwards-compatible change.
  (GITHUB-473)
  [Allard Hoeve]

- Improve GCE create_node, make sure ex_get_disktype function
  (GITHUB-448)
  [Markos Gogoulos]

- GCE driver fix to handle unknown image projects
  (GITHUB-447)
  [Markos Gogoulos]

- Allow user to pass ``ex_blockdevicemappings`` argument to the create_node
  method in the OpenStack driver.
  (GITHUB-398, LIBCLOUD-637)
  [Allard Hoeve]

- Fix ``list_volume_snapshots`` method in the EC2 driver so it comforms to the
  base API.
  (LIBCLOUD-664, GITHUB-451)
  [Allard Hoeve]

- Add ``volumes_attached`` attibute to ``node.extra`` in the OpenStack driver.
  (LIBCLOUD-668, GITHUB-462)
  [Allard Hoeve]

- Add the following new methods to the Linode driver: ``ex_list_volumes``,
  ``ex_create_volume``, ``ex_destroy_volume``.
  (LIBCLOUD-649, GITHUB-430)
  [Wojciech Wirkijowski]

- Add ``list_volume_snapshots`` method to the OpenStack driver.
  (LIBCLOUD-663, GITHUB-450)
  [Allard Hoeve]

- Add Site to Site VPN functionality to CloudStack driver.
  (GITHUB-465)
  [Avi Nanhkoesingh]

- Add affinity group support to CloudStack driver
  (LIBCLOUD-671, GITHUB-468)
  [Mateusz Korszun]

- Add a support for a new AWS Frankfurt, Germany region (``eu-central-1``) to
  the EC2 driver using AWS Signature v4.
  (GITHUB-444)
  [Gertjan Oude Lohuis, Tomaz Muraus]

- Allow Filtering in EC2 list_images() driver
  (GITHUB-456, LIBCLOUD-667)
  [Katriel Traum]

- Add ex_list_ip_forwarding_rules() to CloudStack driver
  (GITHUB-483)
  [Atsushi Sasaki]

- Add AURORA compute driver
  (LIBCLOUD-641, GITHUB-477)
  [Wido den Hollander]

- Update ``ex_describe_tags`` method in the EC2 driver and allow user to list
  tags for any supported resource. Previously you could only list tags for a
  node or a storage volume.
  (LIBCLOUD-676, GITHUB-482)
  [John Kinsella]

- Various improvements in the HostVirual driver (code refactoring, support for
  managing "packages").
  (LIBCLOUD-670, GITHUB-472)
  [Dinesh Bhoopathy]

- Add support for DigitalOcean API v2.0 while maintaining support for the old
  API v2.0.

  Note: API v2.0 is now used by default. To use the old API v1.0, pass
  ``api_version='1.0'`` argument to the driver constructor.
  (GITHUB-442)
  [Andrew Starr-Bochicchio]

- Add new ``d4.`` instance types to the EC2 driver. Also update EC2 pricing data.
  (GITHUB-490)
  [Tomaz Muraus]

- Add new driver for Microsft Azure Virtual Machines service.
  (LIBCLOUD-556, GITHUB-305, GITHUB-499, GITHUB-538)
  [Michael Bennett, davidcrossland, Richard Conway, Matt Baldwin, Tomaz Muraus]

- Fix VPC lookup method in CloudStack driver
  (GITHUB-506)
  [Avi Nanhkoesingh]

- Add new driver for the Dimension Data provider based on the OpSource driver.
  (LIBCLOUD-698, GITHUB-507, LIBCLOUD-700, GITHUB-513)
  [Anthony Shaw]

- Add "virtualmachine_id" attribute to the ``CloudStackAddress`` class in the
  CloudStack driver.
  (LIBCLOUD-679, GITHUB-485)
  [Atsushi Sasaki]

- Allow user to pass filters via arguments to the
  ``ex_list_port_forwarding_rules`` in the CloudStack driver.
  (LIBCLOUD-678, GITHUB-484)
  [Atsushi Sasaki]

- Fix an issue with ``list_nodes`` in the CloudSigma driver throwing an
  exception if a node in the list had a static IP.
  (LIBCLOUD-707, GITHUB-514)
  [Chris O'Brien]

- Don't throw an exception if a limit for a particular CloudStack resource is
  "Unlimited" and not a number.
  (GITHUB-512)
  [Syed Mushtaq Ahmed]

- Allow user to pass ``ex_config_drive`` argument to the ``create_node`` method
  in the OpenStack driver.
  (LIBCLOUD-356, GITHUB-330)
  [Ryan Parrish]

- Add new driver for Cloudwatt (https://www.cloudwatt.com/en/) provider.
  (GITHUB-338)
  [Anthony Monthe]

- Add new driver for Packet (https://www.packet.net/) provider.
  (LIBCLOUD-703, GITHUB-527)
  [Aaron Welch]

- Update Azure VM pricing information and add information for new D instance
  types.
  (GITHUB-528)
  [Michael Bennett]

- Add ``ex_get_node`` and ``ex_get_volume`` methods to CloudStack driver.
  (GITHUB-532)
  [Anthony Monthe]

- Update CloudSigma driver so the "unavailable" and "paused" node state is
  correctly mapped to "error" and "paused" respectively.
  (GITHUB-517)
  [Chris O'Brien]

- Add SSH key pair management methods to the Gandi driver.
  (GITHUB-534)
  [Anthony Monthe]

- Add ``ex_get_node`` and ``ex_get_volume`` methods to Gandi driver.
  (GITHUB-534)
  [Anthony Monthe]

- Add ``fault`` attribute to the ``extra`` dictionary of the ``Node`` instance
  returned by the OpenStack driver.
  (LIBCLOUD-730, GITHUB-557)
  [Nick Fox]

- Add new driver for Onapp IaaS platform.
  (LIBCLOUD-691, GITHUB-502)
  [Matthias Wiesner]

- Allow user to inject custom data / script into the Azure node by passing
  ``ex_custom_data`` argument to the ``create_node`` method.
  (LIBCLOUD-726, GITHUB-554)
  [David Wilson]

- Add ``ex_create_cloud_service`` and ``ex_destroy_cloud_service`` method to the
  Azure driver.
  (LIBCLOUD-724, GITHUB-551)
  [David Wilson]

- Add support for passing user data when creating a DigitalOcean node
  (``ex_user_data`` argument).
  (LIBCLOUD-731, GITHUB-559)
  [David Wilson]

- Allow user to specify which arguments are passed to ``list_nodes`` method
  which is called inside ``wait_until_running`` by passing
  ``ex_list_nodes_kwargs`` argument to the ``wait_until_running`` method.
  (``ex_user_data`` argument).
  (LIBCLOUD-723, GITHUB-548)
  [David Wilson]

- Allow user to pass ``ex_volume_type`` argument to the ``create_volume`` method
  in the OpennStack driver.
  (GITHUB-553)
  [Rico Echwald-Tijsen]

- Add new driver for RunAbove (https://www.runabove.com) provider.
  (GITHUB-550)
  [Anthony Monthe]

- Fix a bug with exception being throw inside the CloudStack driver when the
  provider returned no error message in the body.
  (GITHUB-555)
  [Konstantin Skaburskas]

- Various improvements in the DigitalOcean driver:
   - Increase page size to API maximum.
   - Add ``ex_create_attr`` kwarg to ``create_node`` method.
   - Update all the ``list_*`` methods to use paginated requests
   - Allow user to specify page size by passing ``ex_per_page`` argument to the
     constructor.

  (LIBCLOUD-717, GITHUB-537)
  [Javier Castillo II]

Storage
~~~~~~~

- Fix a bug with authentication in the OpenStack Swift driver.
  (GITHUB-492, LIBCLOUD-635)
  [Tom Fifield]

- Add AuroraObjects Storage Driver.
  (GITHUB-540, LIBCLOUD-719)
  [Wido den Hollander]

Loadbalancer
~~~~~~~~~~~~

- Add a new driver for Softlayer load-balancing service
  (https://www.softlayer.com/load-balancing).
  (GITHUB-500, LIBCLOUD-688)
  [Avi Weit]

DNS
~~~

- Fix a bug when a ZoneDoesntExist exception was thrown when listing records
  for a zone which has no records in the HostVirtual driver.
  (GITHUB-460)
  [Vanč Levstik]

- Correctly handle MX records priority in the Route53 driver.
  (GITHUB-469)
  [Vanč Levstik]

- Allow user to create an A record which points directly to the domain zone
  name in the Route53 driver.
  (GITHUB-469)
  [Vanč Levstik]

- Fix delete_zone method in the HostVirtual driver.
  (GITHUB-461)
  [Vanč Levstik]

- Fix parsing of the record name in the HostVirtual driver.
  (GITHUB-461)
  [Vanč Levstik]

- Add new driver for DigitalOcean DNS service.
  (GITHUB-505)
  [Javier Castillo II]

Changes with Apache Libcloud 0.17.0
-----------------------------------

General
~~~~~~~

- Use ``match_hostname`` function from ``backports.ssl_match_hostname``
  package to verify the SSL certificate hostname instead of relying on
  our own logic.
  (GITHUB-374)
  [Alex Gaynor]

Compute
~~~~~~~

- Add new `eu-west-2` & `us-east-2` regions to the OUTSCALE_INC & OUTSCALE_SAS drivers.
  [Filipe Silva /lordshion]

- GCE driver updated to include ex_stop_node() and ex_start_node() methods.
  (GITHUB-442)
  [Eric Johnson]

- GCE driver now raises ResourceNotFoundError when the specified image is
  not found in any image project. Previously, this would return None but now
  raises the not-found exception instead. This fixes a bug where returning
  None caused ex_delete_image to raise an AttributeError.
  (GITHUB-441)
  [Eric Johnson]

- GCE driver update to support JSON format Service Account files and a PY3
  fix from Siim Põder for LIBCLOUD-627.
  (LIBCLOUD-627, LIBCLOUD-657, GITHUB-438)
  [Eric Johnson]

- GCE driver fixed for missing param on ex_add_access_config.
  (GITHUB-435)
  [Peter Mooshammer]

- GCE driver support for HTTP load-balancer resources.
  (LIBCLOUD-605, GITHUB-429)
  [Lee Verberne]

- GCE driver updated to make better use of GCEDiskTypes.
  (GITHUB-428)
  [Eric Johnson]

- GCE driver list_images() now returns all non-deprecated images by default.
  (LIBCLOUD-602, GITHUB-423)
  [Eric Johnson]

- Improve GCE API coverage for create_node().
  (GITHUB-419)
  [Eric Johnson]

- GCE Licenses added to the GCE driver.
  (GITHUB-420)
  [Eric Johnson]

- GCE Projects support common instance metadata and usage export buckets.
  (GITHUB-409)
  [Eric Johnson]

- Improvements to TargetPool resource in GCE driver.
  (GITHUB-414)
  [Eric Johnson]

- Adding TargetInstances resource to GCE driver.
  (GITHUB-393)
  [Eric Johnson]

- Adding DiskTypes resource to GCE driver.
  (GITHUB-391)
  [Eric Johnson]

- Fix boot disk auto_delete in GCE driver.
  (GITHUB-412)
  [Igor Bogomazov]

- Add Routes to GCE driver.
  (GITHUB-410)
  [Eric Johnson]

- Add missing ``ubuntu-os-cloud`` images to the GCE driver.
  (LIBCLOUD-632, GITHUB-385)
  [Borja Martin]

- Add new `us-east-2` and `us-east-3` region to the Joyent driver.
  (GITHUB-386)
  [Anthony Monthe]

- Add missing t2. instance types to the us-west-1 region in the EC2 driver.
  (GITHUB-388)
  [Matt Lehman]

- Add option to expunge VM on destroy in CloudStack driver.
  (GITHUB-382)
  [Roeland Kuipers]

- Add extra attribute in list_images for CloudStack driver.
  (GITHUB-389)
  [Loic Lambiel]

- Add ``ex_security_group_ids`` argument to the create_node method in the
  EC2 driver. This way users can launch VPC nodes with security groups.
  (GITHUB-373)
  [Itxaka Serrano]

- Add description argument to GCE Network.
  (GITHUB-397)
  [Eric Johnson]

- GCE: Improve MachineType (size) coverage of GCE API.
  (GITHUB-396)
  [Eric Johnson]

- GCE: Improved Images coverage.
  (GITHUB-395)
  [Eric Johnson]

- GCE: Support for global IP addresses.
  (GITHUB-390, GITHUB-394)
  [Eric Johnson]

- GCE: Add missing snapshot attributes.
  (GITHUB-401)
  [Eric Johnson]

- AWS: Set proper disk size in c3.X instance types.
  (GITHUB-405)
  [Itxaka Serrano]

- Fix a bug with handling of the ``ex_keyname`` argument in the Softlayer
  driver.
  (GITHUB-416, LIBCLOUD-647)
  [Dustin Oberloh]

- Update CloudSigma region list (remove Las Vegas, NV region and add new San
  Jose, CA and Miami, FL region).
  (GITHUB-417)
  [Viktor Petersson]

- Add ``ex_get_node`` method to the Joyent driver.
  (GITHUB-421)
  [Anthony Monthe]

- Add support for placement group management to the EC2 driver.
  (GITHUB-418)
  [Mikhail Ovsyannikov]

- Add new tok02 region to the Softlayer driver.
  (GITHUB-436, LIBCLOUD-656)
  [Dustin Oberloh]

- Add new Honolulu, HI endpoint to the CloudSigma driver.
  (GITHUB-439)
  [Stephen D. Spencer]

- Fix a bug with config_drive attribute in the OpenStack driver. New versions
  of OpenStack now return a boolean and not a string.
  (GITHUB-433)
  [quilombo]

- Add support for Abiquo API v3.x, remove support for now obsolete API v2.x.
  (GITHUB-433, LIBCLOUD-652)
  [David Freedman]

- Allow rootdisksize parameter in create_node CloudStack driver
  (GITHUB-440, LIBCLOUD-658)
  [Loic Lambiel]

Storage
~~~~~~~

- Allow user to pass ``headers`` argument to the ``upload_object`` and
  ``upload_object_via_stream`` method.

  This way user can specify CORS headers with the drivers which support that.
  (GITHUB-403, GITHUB-404)
  [Peter Schmidt]

- Fix upload_object_via_stream so it works correctly under Python 3.x if user
  manually passes an iterator to the method.

  Also improve how reading a file in chunks works with drivers which support
  chunked encoding - always try to fill a chunk with CHUNK_SIZE bytes instead
  of directly streaming the chunk which iterator returns.

  Previously, if iterator returned 1 byte in one iteration, we would directly
  send this as a single chunk to the API.
  (GITHUB-408, LIBCLOUD-639)
  [Peter Schmidt]

Loadbalancer
~~~~~~~~~~~~

- Updates to CloudStack driver.
  (GITHUB-434)
  [Jeroen de Korte]

DNS
~~~

- New driver for Softlayer DNS service.
  (GITHUB-413, LIBCLOUD-640)
  [Vanč Levstik]

- Fix a bug with ``ex_create_multi_value_record`` method in the Route53 driver
  only returning a single record.
  (GITHUB-431, LIBCLOUD-650)
  [Itxaka Serrano]

Changes with Apache Libcloud 0.16.0
-----------------------------------

General
~~~~~~~

- Add new ``OpenStackIdentity_3_0_Connection`` class for working with
  OpenStack Identity (Keystone) service API v3.
  [Tomaz Muraus]

- Add support for prettifying JSON or XML response body which is printed to a
  file like object when using ``LIBCLOUD_DEBUG`` environment variable.
  This option can be enabled by setting
  ``LIBCLOUD_DEBUG_PRETTY_PRINT_RESPONSE`` environment variable.
  [Tomaz Muraus]

- Add support for using an HTTP proxy for outgoing HTTP and HTTPS requests.
  [Tomaz Muraus, Philip Kershaw]

Compute
~~~~~~~

- Fix an issue with ``LIBCLOUD_DEBUG`` not working correctly with the
  Linode driver.
  [Tomaz Muraus, Juan Carlos Moreno]
  (LIBCLOUD-598, GITHUB-342)

- Add new driver for VMware vSphere (http://www.vmware.com/products/vsphere/)
  based clouds.
  [Tomaz Muraus]

- Add two new default node states - ``NodeState.SUSPENDED`` and
  ``NodeState.ERROR``.
  [Tomaz Muraus]

- Fix to join networks properly in ``deploy_node`` in the CloudStack
  driver.
  (LIBCLOUD-593, GITUHB-336)
  [Atsushi Sasaki]

- Create ``CloudStackFirewallRule`` class and corresponding methods.
  (LIBCLOUD-594, GITHUB-337)
  [Atsushi Sasaki]

- Add support for SSD disks to Google Compute driver.
  (GITHUB-339)
  [Eric Johnson]

- Add utility ``get_regions`` and ``get_service_names`` methods to the
  ``OpenStackServiceCatalog`` class.
  [Andrew Mann, Tomaz Muraus]

- Fix a bug in ``ex_get_console_output`` in the EC2 driver which would cause
  an exception to be thrown if there was no console output for a particular
  node.

  Reported by Chris DeRamus.
  [Tomaz Muraus]

- Add ip_address parameter in CloudStack driver ``create_node`` method.
  (GITHUB-346)
  [Roeland Kuipers]

- Fix ``ParamikoSSHClient.run`` and ``deploy_node`` method to work correctly
  under Python 3.
  (GITHUB-347)
  [Eddy Reyes]

- Update OpenStack driver to map more node states to states recognized by
  Libcloud.
  [Chris DeRamus]

- Fix a bug with ``ex_metadata`` argument handling in the Google Compute Engine
  driver ``create_node`` method.
  (LIBCLOUD-544, GITHUB-349, GITHUB-353)
  [Raphael Theberge]

- Add SSH key pair management methods to the Softlayer driver.
  (GITHUB-321, GITHUB-354)
  [Itxaka Serrano]

- Correctly categorize node IP addresses into public and private when dealing
  with OpenStack floating IPs.
  [Andrew Mann]

- Add new t2 instance types to the EC2 driver.
  [Tomaz Muraus]

- Add support for Amazon GovCloud to the EC2 driver (us-gov-west-1 region).
  [Chris DeRamus]

- Allow user to pass "gp2" for "ex_volume_type" argument to the create_volume
  method in the EC2 driver.

  Reported by Xavier Barbosa.
  [Tomaz Muraus, Xavier Barbosa]

- Add new driver for ProfitBricks provider.
  (LIBCLOUD-589, GITHUB-352)
  [Matt Baldwin]

- Various improvements and bugs fixes in the GCE driver. For a list, see
  https://github.com/apache/libcloud/pull/360/commits
  (GITHUB-360)
  [Evgeny Egorochkin]

- Allow user to specify virtualization type when registering an EC2 image by
  passing ``virtualization_type`` argument to the ``ex_register_image`` method.
  (GITHUB-361)
  [Andy Grimm]

- Add ``ex_create_image`` method to the GCE driver.
  (GITHUB-358, LIBCLOUD-611)
  [Katriel Traum]

- Add some methods to CloudStack driver:
  create_volume_snapshot, list_snapshots, destroy_volume_snapshot
  create_snapshot_template, ex_list_os_types)
  (GITHUB-363, LIBCLOUD-616)
  [Oleg Suharev]

- Added VPC support and Egress Firewall rule support fo CloudStack
  (GITHUB-363)
  [Jeroen de Korte]

- Add additional attributes to the ``extra`` dictionary of OpenStack
  StorageVolume object.
  (GITHUB-366)
  [Gertjan Oude Lohuis]

- Fix ``create_volume`` method in the OpenStack driver to return a created
  volume object (instance of StorageVolume) on success, instead of a boolean
  indicating operation success.
  (GITHUB-365)
  [Gertjan Oude Lohuis]

- Add optional project parameters for ex_list_networks() to CloudStack driver
  (GITHUB-367, LIBCLOUD-615)
  [Rene Moser]

- CLOUDSTACK: option to start VM in a STOPPED state
  (GITHUB-368)
  [Roeland Kuipers]

- Support "config_drive" in the OpenStack driver. Allow users to pass
  ``ex_config_drive`` argument to the ``create_node`` and ``ex_rebuild_node``
  method.
  (GITHUB-370)
  [Nirmal Ranganathan]

- Add support for service scopes to the ``create_node`` method in the GCE
  driver.
  (LIBCLOUD-578, GITHUB-373)
  [Eric Johnson]

- Update GCE driver to allow for authentication with internal metadata service.
  (LIBCLOUD-625, LIBCLOUD-276, GITHUB-276)
  [Eric Johnson]

- Fix a bug in Elasticstack node creation method where it would raise
  exceptions because of missing data in a response, and also fix pulling the
  IP from the proper data item.
  (GITHUB-325)
  [Michael Bennett]

- Fix a bug which prevented user to connect and instantiate multiple EC2 driver
  instances for different regions at the same time.
  (GITHUB-325)
  [Michael Bennett]

- Add methods in CloudStack driver to manage mutiple nics per vm.
  (GITHUB-369)
  [Roeland Kuipers]

- Implements VPC network ACLs for CloudStack driver.
  (GITHUB-371)
  [Jeroen de Korte]

Storage
~~~~~~~

- Fix a bug with CDN requests in the CloudFiles driver.
  [Tomaz Muraus]

- Fix a bug with not being able to specify meta_data / tags when uploading an
  object using Google Storage driver.
  (LIBCLOUD-612, GITHUB-356)
  [Stefan Friesel]

Loadbalancer
~~~~~~~~~~~~

- Allow user to specify session affinity algorithm in the GCE driver by passing
  ``ex_session_affinity`` argument to the ``create_balancer`` method.
  (LIBCLOUD-595, GITHUB-341)
  [Lee Verberne, Eric Johnson]

DNS
~~~

- Various fixes in the Google DNS driver.
  (GITHUB-378)
  [Franck Cuny]

Changes with Apache Libcloud 0.15.1
-----------------------------------

Compute
~~~~~~~

- Allow user to limit a list of subnets which are returned by passing
  ``subnet_ids`` and ``filters`` argument to the ``ex_list_subnets``
  method in the EC2 driver.
  (LIBCLOUD-571, GITHUB-306)
  [Lior Goikhburg]

- Allow user to limit a list of internet gateways which are returned by
  passing ``gateway_ids`` and ``filters`` argument to the
  ``ex_list_internet_gateways`` method in the EC2 driver.
  (LIBCLOUD-572, GITHUB-307)
  [Lior Goikhburg]

- Allow user to filter which nodes are returned by passing ``ex_filters``
  argument to the ``list_nodes`` method in the EC2 driver.
  (LIBCLOUD-580, GITHUB-320)
  [Lior Goikhburg]

- Add network_association_id to ex_list_public_ips and CloudstackAddress object
  (GITHUB-327)
  [Roeland Kuipers]

- Allow user to specify admin password by passing ``ex_admin_pass`` argument
  to the ``create_node`` method in the Openstack driver.
  (GITHUB-315)
  [Marcus Devich]

- Fix a possible race condition in deploy_node which would occur if node
  is online and can be accessed via SSH, but the SSH key we want to use hasn't
  been installed yet.

  Previously, we would immediately throw if we can connect, but the SSH key
  hasn't been installed yet.
  (GITHUB-331)
  [David Gay]

- Propagate an exception in ``deploy_node`` method if user specified an invalid
  path to the private key file. Previously this exception was silently swallowed
  and ignored.
  [Tomaz Muraus]

DNS
~~~

- Include a better message in the exception which is thrown when a request
  in the Rackspace driver ends up in an ``ERROR`` state.
  [Tomaz Muraus]

Changes with Apache Libcloud 0.15.0
-----------------------------------

General
~~~~~~~

- Use lxml library (if available) for parsing XML. This should substantially
  reduce parsing time and memory usage for large XML responses (e.g. retrieving
  all the available images in the EC2 driver).
  [Andrew Mann]

- Use --head flag instead of -X HEAD when logging curl lines for HEAD requests
  in debug mode.

  Reported by Brian Metzler.
  (LIBCLOUD-552)
  [Tomaz Muraus]

- Fix Python 3 compatibility bugs in the following functions:

  * import_key_pair_from_string in the EC2 driver
  * publickey._to_md5_fingerprint
  * publickey.get_pubkey_ssh2_fingerprint

  (GITHUB-301)
  [Csaba Hoch]

- Update CA_CERTS_PATH to also look for CA cert bundle which comes with
  openssl Homebrew formula on OS x (/usr/local/etc/openssl/cert.pem).
  (GITHUB-309)
  [Pedro Romano]

- Update Google drivers to allow simultaneous authornization for all the
  supported Google Services.
  (GITHUB-302)
  [Eric Johnson]

Compute
~~~~~~~

- Fix create_key_pair method which was not returning private key.
  (LIBCLOUD-566)
  [Sebastien Goasguen]

- Map "Stopped" node state in the CloudStack driver to NodeState.STOPPED
  instead of NodeState.TERMINATED, "Stopping" to NodeState.PENDING instead of
  NodeState.TERMINATED and "Expunging" to NodeState.PENDING instead of
  NodeState.TERMINATED.
  (GITHUB-246)
  [Chris DeRamus, Tomaz Muraus]

- Add ex_create_tags and ex_delete_tags method to the CloudStack driver.
  (LIBCLOUD-514, GITHUB-248)
  [Chris DeRamus]

- Add new G2 instances to the EC2 driver.
  [Tomaz Muraus]

- Add support for multiple API versions to the Eucalyptus driver and allows
  user to pass "api_version" argument to the driver constructor.
  (LIBCLOUD-516, GITHUB-249)
  [Chris DeRamus]

- Map "Powered Off" state in the vCloud driver from "TERMINATED" to "STOPPED".
  (GITHUB-251)
  [Ash Berlin]

- Add ex_rename_node method to the DigitalOcean driver.
  (GITHUB-252)
  [Rahul Ranjan]

- Improve error parsing in the DigitalOcean driver.

  Reported by Deni Bertovic.
  [Tomaz Muraus]

- Add extension methods for the VPC internet gateway management to the EC2
  driver.
  (LIBCLOUD-525, GITHUB-255)
  [Chris DeRamus]

- Add CloudStackProject class to the CloudStack driver and add option to select
  project and disk offering on node creation.
  (LIBCLOUD-526, GITHUB-257)
  [Jim Divine]

- Fix IP address handling in the OpenStack driver.
  (LIBCLOUD-503, GITHUB-235)
  [Markos Gogoulos]

- Ad new ex_delete_image and ex_deprecate_image method to the GCE driver.
  (GITHUB-260)
  [Franck Cuny]

- Ad new ex_copy_image method to the GCE driver.
  (GITHUB-258)
  [Franck Cuny]

- Ad new ex_set_volume_auto_delete method to the GCE driver.
  (GITHUB-264)
  [Franck Cuny]

- Add ex_revoke_security_group_ingress method to the CloudStack driver.
  [Chris DeRamus, Tomaz Muraus]

- Allow user to pass ex_ebs_optimized argument to the create_node method
  in the EC2 driver.
  (GITHUB-272)
  [zerthimon]

- Add "deprecated" attribute to the Node object in the Google Compute Engine
  driver.
  (GITHUB-276)
  [Chris / bassdread]

- Update Softlayer driver to use "fullyQualifiedDomainName" instead of
  "hostname" attribute for the node name.
  (GITHUB-280)
  [RoelVanNyen]

- Allow user to specify target tags using target_tags attribute when creating
  a firewall rule in the GCE driver.
  (GITHUB-278)
  [zerthimon]

- Add new standard API for image management and initial implementation for the
  EC2 and Rackspace driver.
  (GITHUB-277)
  [Matt Lehman]

- Allow user to specify "displayname" attribute when creating a CloudStack node
  by passing "ex_displayname" argument to the method.

  Also allow "name" argument to be empty (None). This way CloudStack
  automatically uses Node's UUID for the name.
  (GITHUB-289)
  [Jeff Moody]

- Deprecate "key" argument in the SSHClient class in favor of new "key_files"
  argument.

  Also add a new "key_material" argument. This argument can contain raw string
  version of a private key.

  Note 1: "key_files" and "key_material" arguments are mutually exclusive.
  Note 2: "key_material" argument is not supported in the ShellOutSSHClient.

- Use node id attribute instead of the name for the "lconfig" label in the
  Linode driver. This way the label is never longer than 48 characters.
  (GITHUB-287)
  [earthgecko]

- Add a new driver for Outscale SAS and Outscale INC cloud
  (http://www.outscale.com).
  (GITHUB-285, GITHUB-293, LIBCLOUD-536, LIBCLOUD-553)
  [Benoit Canet]

- Add new driver for HP Public Cloud (Helion) available via Provider.HPCLOUD
  constant.
  [Tomaz Muraus]

- Allow user to specify availability zone when creating an OpenStack node by
  passing "ex_availability_zone" argument to the create_node method.
  Note: This will only work if the OpenStack installation is running
  availability zones extension.
  (GITHUB-295, LIBCLOUD-555)
  [syndicut]

- Allow user to pass filters to ex_list_networks method in the EC2 driver.
  (GITHUB-294)
  [zerthimon]

- Allow user to retrieve container images using ex_get_image method in the
  Google Compute Engine driver.
  (GITHUB-299, LIBCLOUD-562)
  [Magnus Andersson]

- Add new driver for Kili public cloud (http://kili.io/)
  [Tomaz Muraus]

- Add "timeout" argument to the ParamikoSSHClient.run method. If this argument
  is specified and the command passed to run method doesn't finish in the
  defined timeout, `SSHCommandTimeoutError` is throw and the connection to the
  remote server is closed.

  Note #1: If timed out happens, this functionality doesn't guarantee that the
  underlying command will be stopped / killed. The way it works it simply
  closes a connect to the remote server.
  [Tomaz Muraus]

  Note #2: "timeout" argument is only available in the Paramiko SSH client.

- Make "cidrs_ips" argument in the ex_authorize_security_group_egress method in
  the EC2 driver mandatory.
  (GITHUB-301)
  [Csaba Hoch]

- Add extension methods for managing floating IPs (ex_get_floating_ip,
  ex_create_floating_ip, ex_delete_floating_ip) to the Openstack 1.1 driver.
  (GITHUB-301)
  [Csaba Hoch]

- Fix bug in RimuHosting driver which caused driver not to work when the
  provider returned compressed (gzip'ed) response.
  (LIBCLOUD-569, GITHUB-303)
  [amastracci]

- Fix issue with overwriting the server memory values in the RimuHosting
  driver.
  (GUTHUB-308)
  [Dustin Oberloh]

- Add ex_all_tenants argument to the list_nodes method in the OpenStack driver.
  (GITHUB-312)
  [LIBCLOUD-575, Zak Estrada]

- Add support for network management for advanced zones
  (ex_list_network_offerings, ex_create_network, ex_delete_network) in the
  CloudStack driver.
  (GITHUB-316)
  [Roeland Kuipers]

- Add extension methods for routes and route table management to the EC2
  driver (ex_list_route_tables, ex_create_route_table, ex_delete_route_table,
  ex_associate_route_table, ex_dissociate_route_table,
  ex_replace_route_table_association, ex_create_route, ex_delete_route,
  ex_replace_route)
  (LIBCLOUD-574, GITHUB-313)
  [Lior Goikhburg]

- Fix ex_list_snapshots for HP Helion OpenStack based driver.
  [Tomaz Muraus]

- Allow user to specify volume type and number of IOPS when creating a new
  volume in the EC2 driver by passing ``ex_volume_type`` and ``ex_iops``
  argument to the ``create_volume`` method.
  [Tomaz Muraus]

- Fix ex_unpause_node method in the OpenStack driver.
  (GITHUB-317)
  [Pablo Orduña]

- Allow user to launch EC2 node in a specific VPC subnet by passing
  ``ex_subnet`` argument to the create_node method.
  (GITHUB-318)
  [Lior Goikhburg]

Storage
~~~~~~~

- Fix container name encoding in the iterate_container_objects and
  get_container_cdn_url method in the CloudFiles driver. Previously, those
  methods would throw an exception if user passed in a container name which
  contained a whitespace.

  Reported by Brian Metzler.
  (LIBCLOUD-552)
  [Tomaz MUraus]

- Fix a bug in the OpenStack Swift driver which prevented the driver to work
  with installations where region names in the service catalog weren't upper
  case.
  (LIBCLOUD-576, GITHUB-311)
  [Zak Estrada]

Load Balancer
~~~~~~~~~~~~~

- Add extension methods for policy managagement to the ELB driver.
  (LIBCLOUD-522, GITHUB-253)
  [Rahul Ranjan]

DNS
~~~

- Fix update_record method in the Route56 driver so it works correctly for
  records with multiple values.
  [Tomaz Muraus]

- Add ex_create_multi_value_record method to the Route53 driver which allows
  user to create a record with multiple values with a single call.
  [Tomaz Muraus]

- Add new driver for Google DNS.
  (GITHUB-269)
  [Franck Cuny]

Changes with Apache Libcloud 0.14.1
-----------------------------------

Compute
~~~~~~~

- Add new m3.medium and m3.large instance information to the EC2 driver.
  [Tomaz Muraus]

- Add a new driver for CloudSigma API v2.0.
  [Tomaz Muraus]

- Add "volume_id" attribute to the Node "extra" dictionary in the EC2 driver.
  Also fix the value of the "device" extra attribute in the StorageVolume
  object. (LIBCLOUD-501)
  [Oleg Suharev]

- Add the following extension methods to the OpenStack driver: ex_pause_node,
  ex_unpause_node, ex_suspend_node, ex_resume_node.
  (LIBCLOUD-505, GITHUB-238)
  [Chris DeRamus]

- Add ex_limits method to the CloudStack driver.
  (LIBCLOUD-507, GITHUB-240)
  [Chris DeRamus]

- Add "extra" dictionary to the CloudStackNode object and include more
  attributes in the "extra" dictionary of the network and volume object.
  (LIBCLOUD-506, GITHUB-239)
  [Chris DeRamus]

- Add ex_register_image method to the EC2 driver.
  (LIBCLOUD-508, GITHUB-241)
  [Chris DeRamus]

- Add methods for managing volume snapshots to the OpenStack driver.
  (LIBCLOUD-512, GITHUB-245)
  [Chris DeRamus]

Load Balancer
~~~~~~~~~~~~~

- Fix a bug in the ex_targetpool_add_node and ex_targetpool_remove_node method
  in the GCE driver.
  [Rick Wright]

Storage
~~~~~~~

- Allow user to use an internal endpoint in the CloudFiles driver by passing
  "use_internal_url" argument to the driver constructor.
  (GITHUB-229, GITHUB-231)
  [John Obelenus]

DNS
~~~

- Add PTR to the supported record types in the Rackspace driver.
  [Tomaz Muraus]

- Fix Zerigo driver to set Record.name attribute for records which refer
  to the bare domain to "None" instead of an empty string.
  [Tomaz Muraus]

- For consistency with other drivers, update Rackspace driver to set
  Record.name attribute for the records which refer to the bare domain
  to "None" instead of setting them to FQDN.
  [Tomaz Muraus]

- Update Rackspace driver to support paginating through zones and records.
  (GITHUB-230)
  [Roy Wellington]

- Update Route53 driver so it supports handling records with multiple values
  (e.g. MX).
  (LIBCLOUD-504, GITHUB-237)
  [Chris DeRamus]

- Update Route53 driver to better handle SRV records.
  [Tomaz Muraus]

- Update Route53 driver, make sure "ttl" attribute in the Record extra
  dictionary is always an int.
  [Tomaz Muraus]

Changes with Apache Libcloud 0.14.0
-----------------------------------

General
~~~~~~~

- Update API endpoints which are used in the HostVirtual drivers.
  (LIBCLOUD-489)
  [Dinesh Bhoopathy]

- Add support for Amazon security token to the Amazon drivers.
  (LIBCLOUD-498, GITHUB-223)
  [Noah Kantrowitz]

Compute
~~~~~~~

- Remove Slicehost driver.

  SliceHost API has been shut down in 2012 so it makes no sense to keep
  this driver.
  [Tomaz Muraus]

- Modify drivers for public cloud providers which use HTTP Basic
  authentication to not allow insecure connections (secure constructor
  kwarg being set to False) by default.

  This way credentials can't accidentally be sent in plain text over the
  write.

  Affected drivers: Bluebox, Joyent, NephoScale, OpSource, VPSNet
  [Tomaz Muraus]

- Remove "public_ip" and "private_ip" property which has been deprecated in
  0.7.0 from the Node object.
  [Tomaz Muraus]

- Move "is_private_ip" and "is_valid_ip_address" function from
  libcloud.compute.base into libcloud.utils.networking module.
  [Tomaz Muraus]

- Allow user to pass "url" argument to the CloudStack driver constructor.
  This argument can be provided instead of "host" and "path" arguments and
  can contain a full URL to the API endpoint. (LIBCLOUD-430)
  [Tomaz Muraus]

- Allow user to pass None as a "location" argument to the create_node
  method. (LIBCLOUD-431)
  [Tomaz Muraus]

- Refactor CloudStack Connection class so it looks more like other
  connection classes and user can specify which attributes to send as part
  of query parameters in the GET request and which inside the body of a POST
  request.
  [Tomaz Muraus, Philipp Strube]

- Add a new driver for Exoscale (https://www.exoscale.ch/) provider.
  [Tomaz Muraus]

- Fix a bug in Abiquo driver which caused the driver to fail if the endpoint
  URL didn't start with "/api". (LIBCLOUD-447)

  Reported by Igor Ajdisek.
  [Tomaz Muraus]

- Modify CloudStack driver to correctly throw InvalidCredsError exception if
  invalid credentials are provided.
  [Tomaz Muraus]

- Don't throw an exception if a node object is missing an "image" attribute
  in the list nodes / get node response.

  This could happen if node is in an error state. (LIBCLOUD-455)
  [Dustin Spicuzza, Tomaz Muraus]

- Update CloudStack driver to better handle errors and throw ProviderError
  instead of a generic Exception.
  [Tomaz Muraus]

- Modify ex_list_networks methods in CloudStack driver to not thrown if there
  are no networks available.
  [Tomaz Muraus]

- Bump API version used in the EC2 driver from 2010-08-21 to 2013-10-15.
  (LIBCLOUD-454)
  [Tomaz Muraus]

- Add ex_get_limits method for retrieving account resource limits to the
  EC2 driver.
  [Tomaz Muraus]

- Update us-west-1 region in the EC2 driver to include c3 instance types.
  Also include pricing information.
  [Tomaz Muraus]

- For consistency, rename "ex_add_ip_forwarding_rule" method to
  "ex_create_ip_forwarding_rule".
  (GITHUB-196)
  [Oleg Suharev]

- Add support for new "i2" instance types to Amazon EC2 driver. Also
  update pricing file. (LIBCLOUD-465)
  [Chris DeRamus]

- Allow user to specify VPC id when creating a security group in the EC2
  driver by passing "vpc_id" argument to ex_create_security_group method.
  (LIBCLOUD-463, GITHUB-201)
  [Chris DeRamus]

- Add extension methods for managing security group rules
  (ex_authorize_security_group_ingress, ex_authorize_security_group_egress,
  ex_revoke_security_group_ingress, ex_revoke_security_group_egress) to the
  EC2 driver. (LIBCLOUD-466, GITHUB-202)
  [Chris DeRamus]

- Add extension methods for deleting security groups
  (ex_delete_security_group, ex_delete_security_group_by_id,
  ex_delete_security_group_by_name) to the EC2 driver.
  (LIBCLOUD-464, GITHUB-199)
  [Chris DeRamus]

- Add extension method for listing reserved instances
  (ex_list_reserved_nodes) to the EC2 driver. (LIBCLOUD-469, GITHUB-205)
  [Chris DeRamus]

- Add extension methods for VPC management (ex_list_networks,
  ex_create_network, ex_delete_network) to the EC2 driver.
  (LIBCLOUD-467, GITHUB-203)
  [Chris DeRamus]

- Add extension methods for VPC subnet management (ex_list_subnets,
  ex_create_subnet, ex_delete_subnet) to the EC2 driver.
  (LIBCLOUD-468, GITHUB-207)
  [Chris DeRamus]

- Add ex_get_console_output extension method to the EC2 driver.
  (LIBCLOUD-471, GITHUB-209)
  [Chris DeRamus]

- Include additional provider-specific attributes in the 'extra' dictionary
  of the StorageVolume class in the EC2 driver. (LIBCLOUD-473, GITHUB-210)
  [Chris DeRamus]

- Change attribute name in the 'extra' dictionary of EC2 and CloudStack
  Node object from "keyname" to "key_name". (LIBCLOUD-475)
  [Oleg Suharev]

- Fix a deployment issue which would some times cause a process to hang if
  the executed deployment script printed a lot of output to stdout or stderr.
  [Tomaz Muraus]

- Add additional attributes to the "extra" dictionary of the VolumeSnapshot
  object in the EC2 driver.

  Also modify create_volume_snapshot method to correctly handle "name"
  argument. Previous, "name" argument was used as a snapshot description,
  now it's used as a Tag with a key "Name". (LIBCLOUD-480, GITHUB-214)
  [Chris DeRamus]

- Store additional attributes (iops, tags, block_device_mapping) in the
  "extra" dictionary of the NodeImage object in the EC2 driver.

  Also fix ex_image_ids filtering in the list_images method.
  (LIBCLOUD-481, GITHUB-215)
  [Chris DeRamus]

- Add extension methods for network interface management
  (ex_list_network_interfaces, ex_create_network_interface,
  ex_attach_network_interface_to_node, ex_detach_network_interface,
  ex_delete_network_interface) to the EC2 driver. (LIBCLOUD-474)
  [Chris DeRamus]

- Update Google Compute Engine driver to use and work with API v1.
  (LIBCLOUD-450)
  [Rick Wright]

- Modify ParamikoSSHClient so that "password" and "key" arguments are not
  mutually exclusive and both can be provided. (LIBCLOUD-461, GITHUB-194)
  [Markos Gogoulos]

- Add extension methods for the Elastic IP management to the EC2 driver.
  Also modify "ex_allocate_address" and "ex_release_address" method to
  take "domain" argument so it also works with VPC.
  (LIBCLOUD-470, GITHUB-208, GITHUB-220)
  [Chris DeRamus]

- Add additional provider specific attributes to the "extra" dictionary of
  the Node object in the EC2 driver. (LIBCLOUD-493, GITHUB-221)
  [Chris DeRamus]

- Add ex_copy_image and ex_create_image_from_node method to the EC2 driver.
  (LIBCLOUD-494, GITHUB-222)
  [Chris DeRamus]

Storage
~~~~~~~

- Allow user to specify 'Content-Disposition' header in the CloudFiles
  driver by passing 'content_disposition' key in the extra dictionary of
  the upload object methods. (LIBCLOUD-430)
  [Michael Farrell]

- Fix CloudFiles driver so it references a correct service catalog entry for
  the CDN endpoint.

  This was broken in the 0.14.0-beta3 release when we migrated all the
  Rackspace drivers to use auth 2.0 by default. (GITHUB-186)
  [John Obelenus]

- Update storage drivers to default to "application/octet-stream"
  Content-Type if none is provided and none can be guessed.
  (LIBCLOUD-433)
  [Michael Farrell]

- Fix a bug so you can now upload 0 bytes sized objects using multipart
  upload in the S3 driver. (LIBCLOUD-490)

  Reported by Noah Kantrowitz.
  [Tomaz Muraus]

- Update OpenStack Swift driver constructor so it accepts "region",
  "ex_force_service_type" and "ex_force_service_name" argument.
  [Tomaz Muraus]

- Deprecate "CLOUDFILES_SWIFT" provider constant in favor of new
  "OPENSTACK_SWIFT" one.
  [Tomaz Muraus]

- Add support for setting an ACL when uploading and object.
  (LIBCLOUD-497, GITHUB-223)
  [Noah Kantrowitz]

- Modify get_container method to use a more efficient "HEAD"
  approach instead of calling list_containers + doing late
  filterting.
  (LIBCLOUD-498, GITHUB-223)
  [Noah Kantrowitz]

DNS
~~~

- Implement iterate_* methods in the Route53 driver and makes it work
  correctly if there are more results which can fit on a single page.
  Previously, only first 100 results were returned. (LIBCLOUD-434)
  [Chris Clarke]

- Update HostVirtual driver constructor to only take "key" and other valid
  arguments. Previously it also took "secret" argument which it silently
  ignored. (LIBCLOUD-483)

  Reported by  Andrew Udvare.
  [Tomaz Muraus]

- Fix list_records method in the HostVirtual driver.
  (LIBCLOUD-484, GITHUB-218)

  Reported by Andrew Udvare.
  [Dinesh Bhoopathy]

Changes with Apache Libcloud 0.14.0-beta3
-----------------------------------------

General
~~~~~~~

- If the file exists, read pricing data from ~/.libcloud/pricing.json
  by default. If the file doesn't exist, fall back to the old behavior
  and use pricing data which is bundled with the release.
  [Tomaz Muraus]

- Add libcloud.pricing.download_pricing_file function for downloading and
  updating the pricing file.
  [Tomaz Muraus]

- Fix libcloud.utils.py3.urlquote so it works with unicode strings under
  Python 2. (LIBCLOUD-429)
  [Michael Farrell]

Compute
~~~~~~~

- Refactor Rackspace driver classes and make them easier to use. Now there
  are two Rackspace provider constants - Provider.RACKSPACE which
  represents new next-gen OpenStack servers and
  Provider.RACKSPACE_FIRST_GEN which represents old first-gen cloud
  servers.

  Note: This change is backward incompatible. For more information on those
  changes and how to update your code, please visit "Upgrade Notes"
  documentation page - http://s.apache.org/lc0140un
  [Tomaz Muraus]

- Deprecate the following EC2 provider constants: EC2_US_EAST,
  EC2_EU, EC2_EU_WEST, EC2_AP_SOUTHEAST, EC2_AP_NORTHEAST,
  EC2_US_WEST_OREGON, EC2_SA_EAST, EC2_SA_EAST and replace it with a new
  EC2 constant.
  Driver referenced by this new constant now takes a "region" argument which
  dictates to which region to connect.

  Note: Deprecated constants will continue to work until the next major
  release. For more information on those changes and how to update your
  code, please visit "Upgrade Notes" documentation page -
  http://s.apache.org/lc0140un
  [Tomaz Muraus]

- Add support for volume related functions to OpenNebula driver.
  (LIBCLOUD-354)
  [Emanuele Rocca]

- Add methods for managing storage volumes to the OpenStack driver.
  (LIBCLOUD-353)
  [Bernard Kerckenaere]

- Add new driver for Google Compute Engine (LIBCLOUD-266, LIBCLOUD-386)
  [Rick Wright]

- Fix create_node "features" metadata and update affected drivers.
  (LIBCLOUD-367)
  [John Carr]

- Update EC2 driver to accept the auth kwarg (it will accept NodeAuthSSH
  objects and automatically import a public key that is not already
  uploaded to the EC2 keyring). (Follow on from LIBCLOUD-367).
  [John Carr]

- Unify extension argument names for assigning a node to security groups
  in EC2 and OpenStack driver.
  Argument in the EC2 driver has been renamed from ex_securitygroup to
  ex_security_groups. For backward compatibility reasons, old argument
  will continue to work until the next major release. (LIBCLOUD-375)
  [Tomaz Muraus]

- Add ex_import_keypair_from_string and ex_import_keypair method to the
  CloudStack driver. (LIBCLOUD-380)
  [Sebastien Goasguen]

- Add support for managing floating IP addresses to the OpenStack driver.
  (LIBCLOUD-382)
  [Ivan Kusalic]

- Add extension methods for handling port forwarding to the CloudStack
  driver, rename CloudStackForwardingRule class to
  CloudStackIPForwardingRule. (LIBCLOUD-348, LIBCLOUD-381)
  [sebastien goasguen]

- Hook up deploy_node functionality in the CloudStack driver and unify
  extension arguments for handling security groups. (LIBCLOUD-388)
  [sebastien goasguen]

- Allow user to pass "args" argument to the ScriptDeployment and
  ScriptFileDeployment class. This argument tells which command line
  arguments get passed to the ScriptDeployment script. (LIBCLOUD-394)

  Note: This change is backward incompatible. For more information on how
  this affects your code and how to update it, visit "Upgrade Notes"
  documentation page - http://s.apache.org/lc0140un
  [Tomaz Muraus]

- Allow user to specify IAM profile to use when creating an EC2 node.
  (LIBCLOUD-403)
  [Xavier Barbosa]

- Add support for keypair management to the OpenStack driver.
  (LIBCLOUD-392)
  [L. Schaub]

- Allow user to specify disk partitioning mode using ex_disk_config argument
  in the OpenStack based drivers. (LIBCLOUD-402)
  [Brian Curtin]

- Add new driver for NephoScale provider (http://nephoscale.com/).
  (LIBCLOUD-404)
  [Markos Gogoulos]

- Update network related extension methods so they work correctly with
  both, OpenStack and Rackspace driver. (LIBCLOUD-368)
  [Tomaz Muraus]

- Add tests for networking functionality in the OpenStack and Rackspace
  driver.
  [Tomaz Muraus]

- Allow user to pass all supported extension arguments to ex_rebuild_server
  method in the OpenStack driver. (LIBCLOUD-408)
  [Dave King]

- Add pricing information for Rackspace Cloud Sydney region.
  [Tomaz Muraus]

- Update EC2 instance type map and pricing data. High Storage instances are
  now also available in Sydney and Singapore region.
  [Tomaz Muraus]

- Add new methods for managing storage volumes and snapshots to the EC2
  driver (list_volumes, list_snapshots, destroy_volume_snapshot,
  create_volume_snapshot) (LIBCLOUD-409)
  [Oleg Suharev]

- Add the following new extension methods to EC2 driver: ex_destroy_image,
  ex_modify_instance_attributes, ex_delete_keypair. (LIBCLOUD-409)
  [Oleg Suharev]

- Allow user to specify a port range when creating a port forwarding rule.
  (LIBCLOUD-409)
  [Oleg Suharev]

- Align Joyent driver with other drivers and deprecate "location" argument
  in the driver constructor in favor of "region" argument.

  Note: Deprecated argument will continue to work until the next major
  release.
  [Tomaz Muraus]

- Deprecate the following ElasticHosts provider constants: ELASTICHOSTS_UK1,
  ELASTICHOSTS_UK2, ELASTICHOSTS_US1, ELASTICHOSTS_US2, ELASTICHOSTS_US3,
  ELASTICHOSTS_CA1, ELASTICHOSTS_AU1, ELASTICHOSTS_CN1 and replace it with a
  new ELASTICHOSTS constant.
  Driver referenced by this new constant now takes a "region" argument which
  dictates to which region to connect.

  Note: Deprecated constants will continue to work until the next major
  release. For more information on those changes and how to update your
  code, please visit "Upgrade Notes" documentation page -
  http://s.apache.org/lc0140un (LIBCLOUD-383)
  [Michael Bennett, Tomaz Muraus]

- Add log statements to our ParamikoSSHClient wrapper. This should make
  debugging deployment issues easier. (LIBCLOUD-414)
  [Tomaz Muraus]

- Add new "NodeState.STOPPED" node state. Update HostVirual and EC2 driver to
  also recognize this new state. (LIBCLOUD-296)
  [Jayy Vis]

- Add new Hong Kong endpoint to Rackspace driver.
  [Brian Curtin]

- Fix ex_delete_keypair method in the EC2 driver. (LIBCLOUD-415)
  [Oleg Suharev]

- Add the following new extension methods for elastic IP management to the
  EC2 driver: ex_allocate_address, ex_disassociate_address,
  ex_release_address. (LIBCLOUD-417)
  [Patrick Armstrong]

- For consistency and accuracy, rename "ex_associate_addresses" method in the
  EC2 driver to "ex_associate_address_with_node".

  Note: Old method will continue to work until the next major release.
  [Tomaz Muraus]

- Add new driver for CloudFrames (http://www.cloudfounders.com/CloudFrames)
  provider. (LIBCLOUD-358)
  [Bernard Kerckenaere]

- Update default kernel versions which are used when creating a Linode
  server.

  Old default kernel versions:

  - x86 - 2.6.18.8-x86_64-linode1
  - x86_64 - 2.6.39.1-linode34

  New default kernel versions:

  - x86 - 3.9.3-x86-linode52
  - x86_64 - 3.9.3-x86_64-linode33

  (LIBCLOUD-424)
  [Tomaz Muraus, Jon Chen]

- Disable cache busting functionality in the OpenStack and Rackspace next-gen
  driver and enable it only for Rackspace first-gen driver.
  [Tomaz Muraus]

- Update Google Compute Engine driver to v1beta16.
  [Rick Wright]

- Modify auth_url variable in the OpenStack drivers so it works more like
  users would expect it to.

  Previously path specified in the auth_url was ignored and only protocol,
  hostname and port were used. Now user can provide a full url for the
  auth_url variable and the path provided in the url is also used.
  [DaeMyung Kang, Tomaz Muraus]

- Allow user to associate arbitrary key/value pairs with a node by passing
  "ex_metadata" argument (dictionary) to create_node method in the EC2
  driver.
  Those values are associated with a node using tags functionality.
  (LIBCLOUD-395)
  [Ivan Kusalic]

- Add "ex_get_metadata" method to EC2 and OpenStack driver. This method reads
  metadata dictionary from the Node object. (LIBCLOUD-395)
  [Ivan Kusalic]

- Multiple improvements in the Softlayer driver:
    - Map "INITIATING" node state to NodeState.PENDING
    - If node is launching remap "halted" state to "pending"
    - Add more node sizes
    - Add ex_stop_node and ex_start_node method
    - Update tests response fixtures

  (LIBCLOUD-416)
  [Markos Gogoulos]

- Modify list_sizes method in the KT UCloud driver to work, even if the item
  doesn't have 'diskofferingid' attribute. (LIBCLOUD-435)
  [DaeMyung Kang]

- Add new c3 instance types to the EC2 driver.
  [Tomaz Muraus]

- Fix an issue with the ex_list_keypairs and ex_list_security_groups method
  in the CloudStack driver which caused an exception to be thrown if the API
  returned no keypairs / security groups.
  (LIBCLOUD-438)
  [Carlos Reategui, Tomaz Muraus]

- Fix a bug in the OpenStack based drivers with not correctly checking if the
  auth token has expired before re-using it. (LIBCLOUD-428)

  Reported by Michael Farrell.
  [Tomaz Muraus,  Michael Farrell]

Storage
~~~~~~~

- Deprecate CLOUDFILES_US and CLOUDFILES_UK provider constant and replace
  it with a new CLOUDFILES constant.
  Driver referenced by this new constant takes a "region" keyword argument
  which can be one of 'ord', 'dfw', 'iad', 'syd', 'lon'.

  Note: Deprecated constants will continue to work until the next major
  release.
  For more information on this change, please visit "Upgrade Notes"
  documentation section - http://s.apache.org/lc0140un
  [Tomaz Muraus]

- Allow users to filter objects starting with a prefix by passing ex_prefix
  argument to the list_container_objects method in the S3, Google Storage
  and CloudFiles driver. (LIBCLOUD-369)
  [Stefan Friesel]

- Fix an issue with mutating connectionCls.host attribute in the Azure
  driver. This bug prevented user from having multiple Azure drivers with
  different keys instantiated at the same time. (LIBCLOUD-399)
  [Olivier Grisel]

- Add a new driver for KT UCloud based on the OpenStack Swift driver.
  (LIBCLOUD-431).
  [DaeMyung Kang]

Load Balancer
~~~~~~~~~~~~~

- Deprecate RACKSPACE_US and RACKSPACE_UK provider constant and replace it
  with a new RACKSPACE constant.
  Driver referenced by this new constant takes a "region" keyword argument
  which can be one of the following: 'ord', 'dfw', 'iad', 'syd', 'lon'.

  Note: Deprecated constants will continue to work until the next major
  release.
  For more information on this change, please visit "Upgrade Notes"
  documentation section - http://s.apache.org/lc0140un
  [Tomaz Muraus]

- Add new driver for Google Compute Engine (LIBCLOUD-386)
  [Rick Wright]

- Add new Hong Kong endpoint to Rackspace driver.
  [Brian Curtin]

DNS
~~~

- Deprecate RACKSPACE_US and RACKSPACE_UK provider constant and replace it
  with a new RACKSPACE constant.
  Driver referenced by this new constant takes a "region" keyword argument
  which can be one of the following: 'us', 'uk'.

  Note: Deprecated constants will continue to work until the next major
  release.
  For more information on this change, please visit "Upgrade Notes"
  documentation section - http://s.apache.org/lc0140un
  [Tomaz Muraus]

- Use string instead of integer for RecordType ENUM value.

  Note: If you directly use an integer instead of RecordType ENUM class you
  need to update your code to use the RecordType ENUM otherwise the code
  won't work. For more information on how to do that, see "Upgrade Notes"
  documentation section - http://s.apache.org/lc0140un
  [Tomaz Muraus]

- Add "export_zone_to_bind_format" and export_zone_to_bind_zone_file method
  which allows users to export Libcloud Zone to BIND zone format.
  (LIBCLOUD-398)
  [Tomaz Muraus]

- Update issue with inexistent zone / record handling in the get_zone and
  get_record method in the Linode driver. Those issues were related to
  changes in the Linode API. (LIBCLOUD-425)
  [Jon Chen]

Changes with Apache Libcloud 0.13.3
-----------------------------------

Compute
~~~~~~~

- Send "scrub_data" query parameter when destroying a DigitalOcean node.
  This will cause disk to be scrubbed (overwritten with 0's) when destroying
  a node. (LIBCLOUD-487)

  Note: This fixes a security issue with a potential leak of data contained
  on the destroyed node which only affects users of the DigitalOcean driver.
  (CVE-2013-6480)
  [Tomaz Muraus]

Changes with Apache Libcloud 0.13.2
-----------------------------------

General
~~~~~~~

- Don't sent Content-Length: 0 header with POST and PUT request if "raw"
  mode is used. This fixes a regression which could cause broken behavior
  in some storage driver when uploading a file from disk.
  (LIBCLOUD-396)
  [Ivan Kusalic]

Compute
~~~~~~~

- Added Ubuntu Linux 12.04 image to ElasticHost driver image list.
  (LIBCLOUD-364)
  [Bob Thompson]

- Update ElasticHosts driver to store drive UUID in the node 'extra' field.
  (LIBCLOUD-357)
  [Bob Thompson]

Storage
~~~~~~~

- Store last_modified timestamp in the Object extra dictionary in the S3
  driver. (LIBCLOUD-373)
  [Stefan Friesel]

Load Balancer
~~~~~~~~~~~~~

- Expose CloudStack driver directly through the Provider.CLOUDSTACK
  constant.
  [Tomaz Muraus]

DNS
~~~

- Modify Zerigo driver to include record TTL in the record 'extra' attribute
  if a record has a TTL set.
  [Tomaz Muraus]

- Modify values in the Record 'extra' dictionary attribute in the Zerigo DNS
  driver to be set to None instead of an empty string ('') if a value for
  the provided key is not set.
  [Tomaz Muraus]

Changes with Apache Libcloud 0.13.1
-----------------------------------

General
~~~~~~~

- Fix a regression introduced in 0.13.0 and make sure to include
  Content-Length 0 with PUT and POST requests. (LIBCLOUD-362, LIBCLOUD-390)
  [Tomaz Muraus]

Compute
~~~~~~~

- Fix a bug in the ElasticHosts driver and check for right HTTP status
  code when determining drive imaging success. (LIBCLOUD-363)
  [Bob Thompson]

- Update Opsource driver to include node public ip address (if available).
  (LIBCLOUD-384)
  [Michael Bennett]

Storage
~~~~~~~

- Fix a regression with calling encode_container_name instead of
  encode_object_name on object name in get_object method.
  Reported by Ben Meng (LIBCLOUD-366)
  [Tomaz Muraus]

- Ensure that AWS S3 multipart upload works for small iterators.
  (LIBCLOUD-378)
  [Mahendra M]

Changes with Apache Libcloud 0.13.0
-----------------------------------

General
~~~~~~~

- Add homebrew curl-ca-bundle path to CA_CERTS_PATH. This will make Libcloud
  use homebrew curl ca bundle file (if available) for server certificate
  validation. (LIBCLOUD-324)
  [Robert Chiniquy]

- Modify OpenStackAuthConnection and change auth_token_expires attribute to
  be a datetime object instead of a string.
  [Tomaz Muraus]

- Modify OpenStackAuthConnection to support re-using of the existing auth
  token if it's still valid instead of re-authenticating on every
  authenticate() call.
  [Tomaz Muraus]

- Modify base Connection class to not send Content-Length header if body is
  not provided.
  [Tomaz Muraus]

- Add the new error class ProviderError and modify InvalidCredsError to
  inherit from it. (LIBCLOUD-331)
  [Jayy Vis]

Misc
----

- Add unittest2 library dependency for tests and update some tests to use
  it.
  [Tomaz Muraus]

Compute
~~~~~~~

- Fix destroy_node method in the experimental libvirt driver.
  [Aymen Fitati]

- Add ex_start_node method to the Joyent driver. (LIBCLOUD-319)
  [rszabo50]

- Fix Python 3 compatibility issue in the ScriptFileDeployment class.
  (LIBCLOUD-321)
  [Arfrever Frehtes Taifersar Arahesis]

- Add ex_set_metadata_entry and ex_get_metadata method to the VCloud driver.
  (LIBCLOUD-318)
  [Michel Samia]

- Various improvements and bug-fixes in the VCloud driver. (LIBCLOUD-323)
  [Michel Samia]

- Various bug fixes and improvements in the HostVirtual driver.
  (LIBCLOUD-249)
  [Dinesh Bhoopathy]

- Modify list_sizes method in the OpenStack driver to include
  OpenStackNodeSize object which includes 'vcpus' attribute which holds
  a number of virtual CPUs for this size. (LIBCLOUD-325)
  [Carlo]

- For consistency rename "ex_describe_keypairs" method in the EC2 driver to
  "ex_describe_keypair".
  [Tomaz Muraus]

- Modify "ex_describe_keypair" method to return key fingerprint in the
  return value. (LIBCLOUD-326)
  [Andre Merzky, Tomaz Muraus]

- Populate private_ips attribute in the CloudStack drive when returning
  a Node object from the create_node method. (LIBCLOUD-329)
  [Sebastien Goasguen, Tomaz Muraus]

- Allow user to pass extra arguments via "extra_args" argument which are
  then passed to the "deployVirtualMachine" call in the CloudStack driver
  create_node method. (LIBCLOUD-330)
  [Sebastien Goasguen, Tomaz Muraus]

- Update Gandi driver to handle new billing model. (LIBCLOUD-317)
  [Aymeric Barantal]

- Fix a bug in the Linode driver and remove extra newline which is added
  when generating a random root password in create_node. (LIBCLOUD-334)
  [Juan Carlos Moreno]

- Add extension methods for managing keypairs to the CloudStack driver.
  (LIBCLOUD-333)
  [sebastien goasguen]

- Add extension methods for managing security groups to the CloudStack
  driver. (LIBCLOUD-332)
  [sebastien goasguen]

- Add extension methods for starting and stoping the node to the
  CloudStack driver. (LIBCLOUD-338)
  [sebastien goasguen]

- Fix old _wait_until_running method. (LIBCLOUD-339)
  [Bob Thompson]

- Allow user to override default async task completion timeout by
  specifying ex_clone_timeout argument. (LIBCLOUD-340)
  [Michal Galet]

- Fix a bug in the GoGrid driver get_uuid method. (LIBCLOUD-341)
  [Bob Thompson]

- Fix a bug with deploy_node not respecting 'timeout' kwarg.
  [Kevin Carter]

- Modify create_node method in CloudStack driver to return an instance of
  CloudStackNode and add a new "expunging" node state. (LIBCLOUD-345)
  [sebastien goasguen]

- Update API endpoint hostnames in the ElasticHost driver and use hostnames
  which return a valid SSL certificate. (LIBCLOUD-346)
  [Bob Thompson]

- Add ex_list_networks method and missing tests for list_templates to the
  CloudStack driver. (LIBCLOUD-349)
  [Philipp Strube]

- Correctly throw InvalidCredsError if user passes invalid credentials to
  the DigitalOcean driver.
  [Tomaz Muraus]

Storage
~~~~~~~

- Fix an issue with double encoding the container name in the CloudFiles
  driver upload_object method.
  Also properly encode container and object name used in the HTTP request
  in the get_container and get_object method. (LIBCLOUD-328)
  [Tomaz Muraus]

Load Balancer
~~~~~~~~~~~~~

- Add ex_list_current_usage method to the Rackspace driver.

Changes with Apache Libcloud 0.12.4
-----------------------------------

Compute
~~~~~~~

- Fix a regression in Softlayer driver caused by the xmlrpclib changes.
  (LIBCLOUD-310)
  [Jason Johnson]

- Allow user to pass alternate ssh usernames to deploy_node
  (ssh_alternate_usernames kwarg) which are used for authentication if the
  default one doesn't work. (LIBCLOUD-309)
  [Chris Psaltis, Tomaz Muraus]

- Fix a bug in EC2 list_locations method - 'name' attribute didn't contain a
  the right value.
  [Tomaz Muraus]

- Add new ScriptFileDeployment deployment class which reads deploy script
  from a file.
  [Rudolf J Streif]

- Add support for API version 5.1 to the vCloud driver and accept any value
  which is a multiple of four for ex_vm_memory kwarg in create_node method.
  (LIBCLOUD-314)
  [Trevor Powell]

Storage
~~~~~~~

- Fix a regression with removed ex_force_service_region constructor kwarg in
  the CloudFiles driver. (LIBCLOUD-260)

Changes with Apache Libcloud 0.12.3
-----------------------------------

General
~~~~~~~

- Fix Python 3.x related regressions. (LIBCLOUD-245)
  Reported by Arfrever Frehtes Taifersar Arahesis.
  [Tomaz Muraus]

- Fix a regression introduced with recent xmlrpiclib changes which broke all
  the Gandi.net drivers. (LIBCLOUD-288)

  Reported by Hutson Betts.
  [Tomaz Muraus]

- Improve deploy code to work correctly if the ssh user doesn't have access
  to the /root directory.

  Previously the ScriptDeployment script was stored in /root folder by
  default. Now it's stored in users home directory under filename
  ~/libcloud_deploymeny_<random>.sh. (LIBCLOUD-302)

  Reported by rotem on #libcloud.
  [Tomaz Muraus]

Compute
~~~~~~~

- Improve public and private IP address handling in OpenStack 1.1 driver.
  Assume every IP address which doesn't have a label "public" or "internet"
  is private. (LIBCLOUD-297)
  [Grischa Meyer, Tomaz Muraus]

- Add new driver for DigitalOcean provider - https://www.digitalocean.com/.
  (LIBCLOUD-304)
  [Tomaz Muraus]

- Fix a regression in ParamikoSSHClient.run method which caused this methid
  to only work as expected if you passed an absolute or a relative path to
  the script to it. (LIBCLOUD-278)
  [Tomaz Muraus]

DNS
~~~

- Allow user to specify 'priority' extra argument when creating a MX or SRV
  record.
  [Brian Jinwright, Tomaz Muraus]

Changes with Apache Libcloud 0.12.1
-----------------------------------

General
~~~~~~~

- Deprecate LazyList method of iteration over large paginated collections
  and use a new, more efficient generator based approach which doesn't
  require the iterator to be pre-exhausted and buffering all of the values
  in memory.

  Existing list_* methods which previously used LazyList class are
  preserving the old behavior and new iterate_* methods which use a new
  generator based approach have been added. (LIBCLOUD-254)
  [Mahendra M]

- Replace old ENUM style provider constants and replace them with a string
  version.
  This change allows users to dynamically register new drivers using a new
  set_driver method. (LIBCLOUD-255)
  [Mahendra M]

- Allow user to explicitly specify which CA file is used for verifying
  the server certificate by setting 'SSL_CERT_FILE' environment variable.

  Note: When this variable is specified, the specified path is the only
  CA file which is used to verifying the server certificate. (LIBCLOUD-283)
  [Tomaz Muraus, Erinn Looney-Triggs]

- Add a common module (libcloud.common.xmlrpc) for handling XML-RPC
  requests using Libcloud http layer.

  Also refactor existing drivers which use xmlrpclib directly (VCL, Gandi,
  Softlayer) to use this module.

  This change allows drivers to support LIBCLOUD_DEBUG and SSL certificate
  validation functionality. Previously they have bypassed Libcloud http
  layer so this functionality was not available. (LIBCLOUD-288)
  [John Carr]

Compute
~~~~~~~

- Fix string interpolation bug in __repr__ methods in the IBM SCE driver.
  (LIBCLOUD-242)
  [Tomaz Muraus]

- Fix test failures which happened in Python 3.3 due to:
  - hash randomization
  - changes in xml.etree module
  - changes in xmlrpc module
  (LIBCLOUD-245)
  [Tomaz Muraus]

- Improvements and additions in vCloud driver:
    - Expose generic query method (ex_query)
    - Provide functionality to get and set control access for vApps. This way
      created vApps can be shared between users/groups or everyone.

  (LIBCLOUD-251)
  [Michal Galet]

- Update EC2 pricing data to reflect new, lower prices -
  http://aws.typepad.com/aws/2012/10/new-ec2-second-generation-standard-instances-and-price-reductions-1.html
  [Tomaz Muraus]

- Update EC2 instance size to reflect new m3 instance types. Also refactor
  the code to make it easier to maintain.
  [Tomaz Muraus]

- Add a new driver for HostVirtual (http://www.vr.org) provider.
  (LIBCLOUD-249)
  [Dinesh Bhoopathy]

- Fix a bug where a numeric instead of a string value was used for the
  content-length header in VCloud driver. (LIBCLOUD-256)
  [Brian DeGeeter, Tomaz Muraus]

- Add a new driver for new Asia Pacific (Sydney) EC2 region.
  [Tomaz Muraus]

- Add support for managing security groups to the OpenStack driver. This
  patch adds the following extension methods:
  - ex_list_security_groups, ex_get_node_security_groups methods
  - ex_create_security_group, ex_delete_security_group
  - ex_create_security_group_rule, ex_delete_security_group_rule
  (LIBCLOUD-253)
  [L. Schaub]

- Modify ElasticStack driver class to pass 'vnc auto' instead of
  'vnc:ip auto' argument to the API when creating a server.
  It looks like 'vnc:ip' has been replaced with 'vnc'.
  [Rick Copeland, Tomaz Muraus]

- Add new EC2 instance type - High Storage Eight Extra Large Instance
  (hs1.8xlarge).
  [Tomaz Muraus]

- Map 'shutting-down' node state in EC2 driver to UNKNOWN. Previously
  it was mapped to TERMINATED. (LIBCLOUD-280)

  Note: This change is backward incompatible which means you need to update
  your code if you rely on the old behavior.
  [Tomaz Muraus, Marcin Kuzminski]

- Change _wait_until_running method so it supports waiting on multiple nodes
  and make it public (wait_until_running). (LIBCLOUD-274)
  [Nick Bailey]

- Add new EC2 instance type - High Memory Cluster Eight Extra Large.
  (cr1.8xlarge).
  [Tomaz Muraus]

- Add new driver for Abiquo provider - http://www.abiquo.com (LIBCLOUD-250).
  [Jaume Devesa]

- Allow user to pass 'ex_blockdevicemappings' kwarg to the EC2 driver
  'create_node' method. (LIBCLOUD-282)
  [Joe Miller, Tomaz Muraus]

- Improve error handling in the Brightbox driver.
  [Tomaz Muraus]

- Fix the ScriptDeployment step to work correctly if user provides a
  relative path for the script argument. (LIBCLOUD-278)
  [Jaume Devesa]

- Fix Softlayer driver and make sure all the code is up to date and works
  with the latest version of the actual Softlayer deployment (v3).
  (LIBCLOUD-287)
  [Kevin McDonald]

- Update EC2 driver, m3 instance types are now available in all the regions
  except Brazil.

  Also update pricing to reflect new (lower) prices.
  [Tomaz Muraus]

- Minor improvements in the HostVirtual driver and add new ex_get_node and
  ex_build_node extension method. (LIBCLOUD-249)
  [Dinesh Bhoopathy]

- Add ex_destroy_image method to IBM SCE driver. (LIBCLOUD-291)
  [Perry Zou]

- Add the following new regions to the ElasticHosts driver: sjc-c, syd-v,
  hkg-e. (LIBCLOUD-293)
  [Tomaz Muraus]

- Fix create_node in OpenStack driver to work correctly if 'adminPass'
  attribute is not present in the response.
  [Gavin McCance, Tomaz Muraus]

- Allow users to filter images returned by the list_images method in the EC2
  driver by providing ex_image_ids argument. (LIBCLOUD-294)
  [Chris Psaltis, Joseph Hall]

- Add support for OpenNebula 3.8. (LIBCLOUD-295)
  [Guillaume ZITTA]

- Add missing 'deletd' -> terminated mapping to OpenStack driver.
  (LIBCLOUD-276)
  [Jayy Vis]

- Fix create_node in OpenStack driver to work correctly if 'adminPass'
  attribute is not present in the response. (LIBCLOUD-292)
  [Gavin McCance, Tomaz Muraus]

Storage
~~~~~~~

- Add a new local storage driver.
  (LIBCLOUD-252, LIBCLOUD-258, LIBCLOUD-265, LIBCLOUD-273)
  [Mahendra M]

- Fix a bug which caused the connection to not be closed when using Python
  2.6 and calling get_object on an object which doesn't exist in the S3
  driver. (LIBCLOUD-257)
  [John Carr]

- Add a new generator based method for listing / iterating over the
  containers (iterate_containers). (LIBCLOUD-261)
  [Mahendra M]

- Add ex_purge_object_from_cdn method to the CloudFiles driver.
  (LIBCLOUD-267)
  [Tomaz Muraus]

- Support for multipart uploads and other improvements in the S3 driver
  so it can more easily be re-used with other implementations (e.g. Google
  Storage, etc.).

  Also default to a multipart upload when using upload_object_via_stream.
  This methods is more efficient compared to old approach because it only
  requires buffering a single multipart chunk (5 MB) in memory.
  (LIBCLOUD-269)
  [Mahendra M]

- Add new driver for Windows Azure Storage with support for block and page
  blobs. (LIBCLOUD-80)
  [Mahendra M]

DNS
~~~

- Update 'if type' checks in the update_record methods to behave correctly
  if users passes in RecordType.A with a value of 0 - if type is not None.
  (LIBCLOUD-247)
  [Tomaz Muraus]

- New driver for HostVirtual provider (www.vr.org). (LIBCLOUD-249)
  [Dinesh Bhoopathy]

- Finish Amazon Route53 driver. (LIBCLOUD-132)
  [John Carr]

- Add new driver for Gandi provider (https://www.gandi.net). (LIBCLOUD-281)
  [John Carr]

Load-Balancer
~~~~~~~~~~~~~

- Add new driver for AWS Elastic Load Balancing service. (LIBCLOUD-169)
  [John Carr]

Changes with Apache Libcloud 0.11.4
-----------------------------------

General
~~~~~~~

- Fix some of tests failures which happened in Python 3.3 due to randomized
  dictionary ordering. (LIBCLOUD-245)
  [Tomaz Muraus]

Compute
~~~~~~~

- Fix a bug where a numeric instead of a string value was used for the
  content-length header in VCloud driver. (LIBCLOUD-256)
  [Brian DeGeeter, Tomaz Muraus]

Storage
~~~~~~~

- Don't ignore ex_force_service_region argument in the CloudFiles driver.
  (LIBCLOUD-260)
  [Dan Di Spaltro]

- Fix a bug which caused the connection to not be closed when using Python
  2.6 and calling get_object on an object which doesn't exist in the S3
  driver. (LIBCLOUD-257)
  [John Carr]

DNS
~~~

- Update 'if type' checks in the update_record methods to behave correctly
  if users passes in RecordType.A with a value of 0 - if type is not None.
  (LIBCLOUD-247)
  [Tomaz Muraus]

Changes with Apache Libcloud 0.11.3
-----------------------------------

Storage
~~~~~~~

- Include 'last_modified' and 'content_type' attribute in the Object
  'extra' dictionary when retrieving object using get_object in the S3
  driver. Also modify 'meta_data' dictionary to include all the headers
  prefixed with 'x-amz-meta-'.
  [Tomaz Muraus]

Changes with Apache Libcloud 0.11.2
-----------------------------------

General
~~~~~~~

- Fix a bug with the Libcloud SSL verification code. Code was too strict and
  didn't allow "-" character in the sub-domain when using a wildcard
  certificate.

  Note: This is NOT a security vulnerability. (LIBCLOUD-244)
  [Tomaz Muraus]

Compute
~~~~~~~

- Add new Rackspace Nova driver for Chicago (ORD) location (LIBCLOUD-234)
  [Brian McDaniel]

- Add capacity information to Vdc objects and implement power operations.
  (LIBCLOUD-239)
  [Michal Galet]

- Allow user to pass 'timeout' argument to the 'deploy_node' method.
  [Tomaz Muraus]

- Add ex_list_security_groups, ex_authorize_security_group and
  ex_describe_all_keypairs methods to the EC2 driver. (LIBCLOUD-241,
  LIBCLOUD-243)
  [Nick Bailey]

- Add new methods for managing storage volumes and other extenstion methods
  to the IBM SCE driver. (LIBCLOUD-242)
  [Sengor Kusturica]

Storage
~~~~~~~

- Add the following new methods to the CloudFiles driver:
  ex_set_account_metadata_temp_url_key, ex_get_object_temp_url. (GITHUB-72)
  [Shawn Smith]

Load-balancer
~~~~~~~~~~~~~

- Add 'balancer' attribute to the Member instance. This attribute refers to
  the LoadBalancer instance this member belongs to.
  [Tomaz Muraus]

Changes with Apache Libcloud 0.11.1
-----------------------------------

General
~~~~~~~

- Fix hostname validation in the SSL verification code (CVE-2012-3446).

  Reported by researchers from the University of Texas at Austin (Martin
  Georgiev, Suman Jana and Vitaly Shmatikov).

Changes with Apache Libcloud 0.11.0
-----------------------------------

Compute
~~~~~~~

- Add a timeout of 10 seconds to OpenStackAuthConnection class.
  (LIBCLOUD-199)
  [Chris Gilmer]

- Add time.sleep(wait_period) to _ssh_client_connect to prevent busy loops
  when we immediately can't connect to a server. (LIBCLOUD-197)
  [Jay Doane]

- Fix a bug with Python 3 support in the following drivers
  - IBM SCE,
  - CloudStack
  - CloudSigma
  - OpenNebula
  - VpsNet
  - EC2
  - ElasticStack
  - vCloud
  - OpSource
  - Slicehost
  - Joyent
  (LIBCLOUD-204)
  [Sengor Kusturica, Hutson Betts, Tomaz Muraus]

- Make CloudStack driver more robust and make it work if list_images() call
  returns no images. (LIBCLOUD-202)
  [Gabriel Reid]

- Add force_ipv4 argument to _wait_until_running and default it to True.
  This will make Libcloud ignore IPv6 addresses when using deploy_node.
  (LIBCLOUD-200)
  [Jay Doane, Tomaz Muraus]

- Include error text if a CloudStack async job returns an error code.
  (LIBCLOUD-207)
  [Gabriel Reid]

- Add extenstion methods for block storage volume management to the
  CloudStack driver. (LIBCLOUD-208)
  [Gabriel Reid]

- New driver for KT UCloud (http://home.ucloud.olleh.com/main.kt) based on
  the CloudStack driver.
  [DaeMyung Kang]

- Add a standard API and methods for managing storage volumes to the
  EC2 and CloudStack drivers. Base API consistent of the following methods:
  create_volume, destroy_volume, attach_volume, detach_volume.
  (LIBCLOUD-213)
  [Gabriel Reid]

- Change ex_describe_tags, ex_create_tags and ex_delete_tags methods
  signature in the EC2 driver. Argument is now called resource (previously
  it was called node). This methods work with both Node and StorageVolume
  objects. (LIBCLOUD-213)
  [Gabriel Reid, Tomaz Muraus]

- Add Rackspace Nova London driver.
  [Chris Gilmer]

- Fix a bug - If user doesn't pass in 'network_id' argument to the
  create_node method in the CloudStack driver, don't explicitly define it.
  (LIBCLOUD-219)
  [Bruno Mahé, Tomaz Muraus]

- Modify EC2 driver to also return cc2.8xlarge cluster compute instance in
  the eu-west-1 region.
  [Tomaz Muraus]

- Add 'auth_user_variable' to the  OpenStackAuthConnection class.
  [Mark Everett]

- Fix a bug with repeated URLs in some requests the vCloud driver.
  (LIBCLOUD-222)
  [Michal Galet]

- New Gridspot driver with basic list and destroy functionality.
  (LIBCLOUD-223)
  [Amir Elaguizy]

- Add methods for managing storage volumes to the Gandi driver.
  (LIBCLOUD-225)
  [Aymeric Barantal]

DNS
~~~

- Add support for GEO RecordType to Zerigo driver. (LIBCLOUD-203)
  [Gary Wilson]

- Fix a bug with Python 3 support in the following drivers (LIBCLOUD-204)
  - Zerigo
  [Tomaz Muraus]

- Add support for URL RecordType to Zerigo driver. (LIBCLOUD-209)
  [Bojan Mihelac]

- Properly handle record creation when user doesn't provider a record name
  and wants to create a record for the actual domain.
  Reported by Matt Perry (LIBCLOUD-224)
  [Tomaz Muraus]

Storage
~~~~~~~

- Fix a bug with Python 3 support in the following drivers
  - Atmos
  - Google Storage
  - Amazon S3
  (LIBCLOUD-204)
  [Tomaz Muraus]

- Fix a bug in the CloudFiles driver which prevented it to work with
  accounts which use a non ORD endpoint. (LIBCLOUD-205)
  [Geoff Greer]

- Fix a bug in the enable_container_cdn method. (LIBCLOUD-206)
  [Geoff Greer]

- Allow user to specify container CDN TTL when calling container.enable_cd()
  using ex_ttl keyword argument in the CloudFiles driver.
  [Tomaz Muraus]

- Add ex_enable_static_website and ex_set_error_page method to the
  CloudFiles driver.
  [Tomaz Muraus]

- Propagate kwargs passed to container.download_object() to
  driver.download_object(). (LIBCLOUD-227)
  [Benno Rice]

- Fix a bug with not escaping container and object name in the Atmos driver.
  [Russell Keith-Magee, Benno Rice]

- Fix upload_object_via_stream method in the Atmos driver. (LIBCLOUD-228)
  [Benno Rice]

- Fix a bug with uploading zero-sized files in the OpenStack Swift /
  CloudFiles driver.
  [Tomaz Muraus]

- Fix a bug with content_type and encoding of object and path names in
  the Atmos driver.
  [Russell Keith-Magee]

Other
~~~~~

- Unify docstrings formatting in the compute drivers. (LIBCLOUD-229)
  [Ilgiz Islamgulov]

Changes with Apache Libcloud 0.10.1
-----------------------------------

General
~~~~~~~

- Add timeout attribute to base 'Connection' class and pass it to the
  connection class constructor if Python version is not 2.5.
  [Chris Gilmer]

Compute
~~~~~~~

- Update IBM SBC driver so it works with IBM Smart Cloud Enterprise.
  (LIBCLOUD-195)
  [Sengor Kusturica]

- Add ex_register_iso method to the CloudStack driver. (LIBCLOUD-196)
  [Daemian Mack]

- Allow user to specify which IP to use when calling deploy_node.
  (defaults to 'public_ips'). Previously it only worked with public IP, now
  user can pass 'private_ips' as an argument and SSH client will try to
  connect to the node first private IP address.
  [Jay Doane]

- Fix CloudSigmaLvsNodeDriver connectionCls bug.
  [Jerry Chen]

- Add 'ex_keyname' argument to the create_node method in the OpenStack
  driver. (LIBCLOUD-177)
  [Jay Doane]

- Fix a problem in deploy_node - make it work with providers which
  don't  instantly return created node in the list_node response.
  Also add __str__ and __repr__ method to DeploymentError so the
  error message is more useful. (LIBCLOUD-176)
  [Jouke Waleson, Tomaz Muraus]

- Add 'ssh_key' feature to Brigthbox driver. This way it works with
  deploy_node. (LIBCLOUD-179)
  [Neil Wilson]

- Add Joyent compute driver.
  [Tomaz Muraus]

- Store auth token expire times on the connection class in the attribute
  called 'auth_token_expires'. (LIBCLOUD-178)
  [Chris Gilmer, Brad Morgan]

- Add new driver for VCL cloud
  (http://www.educause.edu/blog/hes8/CloudComputingandtheVirtualCom/167931)
  (LIBCLOUD-180)
  [Jason Gionta, Tomaz Muraus]

- Improve and add new features to Brightbox driver
    - Update fixtures to represent actual api output
    - Update compute tests to 100% coverage
    - Add userdata and server group extensions to create_node
    - Add ipv6 support to public ip list
    - Improve in line documentation
    - Add lots of api output information to Node and Image
      'extra' attributes
    - Allow variable API versions (api_version argument)
    - Allow reverse dns updates for cloud ip extensions

  (LIBCLOUD-184)
  [Neil Wilson, Tomaz Muraus]

- Add ex_userdata argument to the OpenStack 1.1 driver. (LIBCLOUD-185)
  [Jay Doane]

- Modify Vmware vCloud driver and implement new features
  for the vCloud version 1.5. (LIBCLOUD-183)
  [Michal Galet, Sengor Kusturica]

- Allow user to pass mode argument to SSHClient.put method and default it to
  'w'. (LIBCLOUD-188)
  [Jay Doane]

- Modify SSHKeyDeployment step to use append mode so it doesn't overwrite
  existing entries in .ssh/authorized_keys. (LIBCLOUD-187)
  [Jay Doane]

- Modify ParamikoSSHClient to connect to the SSH agent and automatically
  look for private keys in ~/.ssh if the 'auth' and 'ssh_key' argument
  is not specified when calling deploy_node. (LIBCLOUD-182)
  [Tomaz Muraus]

- Add ex_rescue and ex_unrescue method to OpenStack 1.1 driver.
  (LIBCLOUD-193)
  [Shawn Smith]

- Include 'password' in the node extra dictionary when calling deploy_node
  if the password auth is used.
  [Juan Carlos Moreno]

- Add FileDeployment class to libcloud.compute.deployment module. This can
  be used as a replacement for ex_files argument if the provider supports
  deployment functionality. (LIBCLOUD-190)
  [Jay Doane]

Storage
~~~~~~~

- Large object upload support for CloudFiles driver
- Add CLOUDFILES_SWIFT driver to connect to OpenStack Swift
  [Dmitry Russkikh, Roman Bogorodskiy]

Load-balancer
~~~~~~~~~~~~~

- Don't include 'body_regex' attribute in the Rackspace driver body if
  body_regex is None or empty string. (LIBCLOUD-186)
  [Bill Woodward]

- Don't split Load balancer IP addresses into public and private list.
  Include all the addresses in the 'virtualIps' variable in the extra
  dictionary (Rackspace driver). (LIBCLOUD-191)
  [Adam Pickeral]

Changes with Apache Libcloud 0.9.1
----------------------------------

General
~~~~~~~

- Make parsing of the Auth API responses in the OpenStack drivers more
  flexible and extensible.

  Now, every connection class that inherits from the openstack base
  connection must implement get_endpoint(), who's job is to return the
  correct endpoint out of the service catalog.

  Note: The openstack.py base driver no longer works by default with
  Rackspace nova. The default endpoint parsed from the service catalog
  is the default compute endpoint for devstack. (LIBCLOUD-151)
  [Brad Morgan]

- Allow user to pass ex_tenant_name keyword argument to the OpenStack node
  driver class. This scopes all the endpoints returned by the Auth API
  endpoint to the provided tenant. (LIBCLOUD-172)
  [James E. Blair]

- Allow user to specify OpenStack service catalog parameters (service type,
  name and region). This way base OpenStack driver can be used with
  different providers without needing to subclass. (LIBCLOUD-173)
  [James E. Blair]

- Fix a bug with handling compressed responses in the Linode driver.
  (LIBCLOUD-158)
  [Ben Agricola]

Compute
~~~~~~~

- Add new RackspaceNovaBeta and RackspaveNovaDfw driver based on the
  OpenStack. (LIBCLOUD-151)
  [Brad Morgan]

- Include 'created' and 'updated' attribute in the OpenStack 1.1 driver.
  (LIBCLOUD-155)
  [Chris Gilmer]

- Include 'minRam' and 'minDisk' attribute in the OpenStack 1.1 driver
  Node extra dictionary. (LIBCLOUD-163)
  [Chris Gilmer]

- Allow users to use a list of tuples for the query string parameters inside
  the OpenStack connection classes. This way same key can be specified
  multiple times (LIBCLOUD-153)
  [Dave King]

- Allow user to pass 'max_tries' keyword argument to deploy_node method.
  [Tomaz Muraus]

- Include original exception error message when re-throwing an exception
  inside _run_deployment_script method.
  [Tomaz Muraus]

- Add support for ElasticHosts new United States (Los Angeles) and Canada
  (Toronto) locations. (GITHUB-53)
  [Jaime Irurzun]

- Add serverId attribute to the NodeImage object extra dictionary in the
  OpenStack driver.
  [Mark Everett]

- Add new EC2 instance type - m1.medium.
  [Tomaz Muraus]

- Allow user to re-use auth tokens and pass 'ex_force_auth_token' keyword
  argument to the OpenStack driver constructor. (LIBCLOUD-164)
  [Dave King]

- Add new experimental libvirt driver.
  [Tomaz Muraus]

- Properly handle OpenStack providers which return public IP addresses under
  the 'internet' key in the addresses dictionary.
  [Tomaz Muraus]

- Update create_node in Linode driver and make it return a Node object
  instead of a list. Reported by Jouke Waleson. (LIBCLOUD-175)
  [Tomaz Muraus]

Storage
~~~~~~~

- Don't lowercase special header names in the Amazon S3 storage driver.
  (LIBCLOUD-149)
  [Tomaz Muraus]

Load-balancer
~~~~~~~~~~~~~

- Allow user to specify a condition and weight when adding a member in
  the Rackspace driver.
  [Adam Pickeral]

- Add an extension method (ex_balancer_attach_members) for attaching
  multiple members to a load balancer in the Rackspace driver.
  (LIBCLOUD-152)
  [Adam Pickeral]

- Add ex_creaate_balancer method to the Rackspace driver and allow user to
  pass 'vip' argument to it. (LIBCLOUD-166)
  [Adam Pickeral]

- Update Rackspace driver to support Auth 2.0. (LIBCLOUD-165)
  [Dave King]

- Add new ex_create_balancer_access_rule and
  ex_create_balancer_access_rule_no_poll method to the Rackspace driver.
  (LIBCLOUD-170)
  [Dave King]

DNS
~~~

- Update Rackspace driver to support Auth 2.0. (LIBCLOUD-165)
  [Dave King]

Changes with Apache Libcloud 0.8.0
----------------------------------

General
~~~~~~~

- Add 'request_kwargs' argument to the get_poll_request_kwargs method.
  This argument contains kwargs which were previously used to initiate the
  poll request.
  [Mark Everett]

- Add support for handling compressed responses (deflate, gzip). Also send
  "Accept-Encoding" "gzip,deflate" header with all the requests.
  [Tomaz Muraus]

- Fix debug module (LIBCLOUD_DEBUG env variable) so it works with Python 3
  [Tomaz Muraus]

Compute
~~~~~~~

- Added support for retrieving OpenNebula v3.2 instance types, OpenNebula
  v3.0 network Public attribute support, and additional code coverage
  tests.
  [Hutson Betts]

- Add implementation for ex_save_image method to the OpenStack 1.1 driver.
  [Shawn Smith]

- Add support for Amazon new South America (Sao Paulo) location.
  [Tomaz Muraus]

- Fix a bug in OpenStack driver when 2.0_apikey or 2.0_password
  'auth_version' is used.
  [Tomaz Muraus]

- Current OpenNebula OCCI implementation does not support a proper
  restart method. Rather it suspends and resumes. Therefore, restart_node
  has been removed from the OpenNebula driver.
  [Hutson Betts]

- Enable ex_delete_image method in the OpenStack 1.1 driver.
  [Shawn Smith]

- Return NodeImage instance in OpenStack 1.1 driver ex_save_image method
  (LIBCLOUD-138)
  [Shawn Smith]

- Enable reboot_node method in the OpenNebula 3.2 driver.
  [Hutson Betts]

- Fix a public_ips Node variable assignment in the Gandi.net driver.
  [Aymeric Barantal]

- Updated the list of node states for OpenNebula drivers. (LIBCLOUD-148)
  [Hutson Betts]

Storage
~~~~~~~

- Propagate extra keyword arguments passed to the Rackspace driver
  connection class.
  [Dave King]

Load-balancer
~~~~~~~~~~~~~

- Add 'extra' attribute to the LoadBalancer object and retrieve all the
  virtual IP addresses in the Rackspace driver.
  [Dave King]

- Add list_supported_algorithms() method to the base LoadBalancer class.
  This method returns a list of supported algorithms by the provider.
  [Dave King]

- Update Rackspace driver:
    - Add two new supported algorithms: WEIGHTED_ROUND_ROBIN,
      WEIGHTED_LEAST_CONNECTIONS
    - Add ex_list_algorithm_names method
    - Add ex_get_balancer_error_page method
    - Add ex_balancer_access_list method
    - Populate LoadBalancer extra dictionary with more attributes
    - Add support for health monitors and connection throttling
    - Add more balancer states
    - ex_list_protocols_with_default_ports

  [Dave King]

- Propagate extra keyword arguments passed to the Rackspace driver
  connection class.
  [Dave King]

- Add 'extra' attribute to the Member object and populate it in
  the Rackspace driver.
  [Mark Everett]

- Adds status to the Member object and conditions an 'enum'
  (Rackspace driver).
  [Mark Everett]

- Add update_balancer method to the base LoadBalancer class.
  [Mark Everett]

- Add update_balancer method to the Rackspace driver.
  [Mark Everett]

- Add created and updated attribute to the LoadBalancer extra dictionary in
  the Rackspace driver.
  [Mark Everett]

- Fix protocol name maping in the Rackspace driver.
  [Bill Woodward]

Changes with Apache Libcloud 0.7.1
----------------------------------

General
~~~~~~~

 - Fix a minor bug in debug mode (LIBCLOUD_DEBUG=/dev/stderr) which has been
   introduced when adding Python 3 compatibility layer.
   [Paul Querna]

 - Update OpenStack Auth API endpoint paths.
   [Paul Querna]

Changes with Apache Libcloud 0.7.0
----------------------------------

General
~~~~~~~

- Add support for Python 3.x.
  [Tomaz Muraus]

- Remove old deprecated paths.
  [Tomaz Muraus]

Compute
~~~~~~~

- Update CloudSigma Zurich API endpoint address.
  [Tomaz Muraus]

- Add new US Las Vegas endpoint to CloudSigma driver (types.CLOUDSIGMA_US)
  [Tomaz Muraus]

- Allow user to specify drive type (hdd, ssd) when creating a
  CloudSigma server.

  Note 'ssd' drive_type doesn't work with the API yet.
  [Tomaz Muraus]

- Update OpenStack 1.1 driver to comply with the API specs. Need to make
  another call to retrieve node name and ip addresses when creating a node,
  because the first call only returns an id an the password. (GITHUB-40)
  [Dave King]

- Add ex_node_ids argument to the EC2 driver list_nodes method.
  (GITHUB-39)
  [Suvish Vt]

- If OpenStack Auth 2.0 API is used, also parse out tenant id and
  name and save it on the connection class (conn.tenant['id'],
  conn.tenant['name']).
  [Tomaz Muraus]

- Add new "Cluster Compute Eight Extra Large" size to the Amazon EC2
  driver.
  [Tomaz Muraus]

- Add the following extension methods to the EC2 compute driver:
  ex_describe_all_addresses, ex_associate_addresses, ex_start_node,
  ex_stop_node.
  [Suvish Vt]

- Change public_ip and private_ip attribute on the Node object to the
  public_ips and private_ips since both of the objects are always a list.

  Note: For backward compatibility you can still access public_ip and
  private_ip attributes, but this will be removed in the next release.
  [Tomaz Muraus]

- Fix an inconsistency in IBM SBC driver and make sure public_ips and
  private_ips attributes are a list.
  [Tomaz Muraus]

- Fix an inconsistency in OpSource driver and make sure public_ips is an
  empty list ([]), not 'unknown'
  [Tomaz Muraus]

- Updated support for OpenNebula.org v1.4, v2.x, and v3.x APIs and included
  additional compute tests validating functionality. (LIBCLOUD-121)
  [Hutson Betts]

Load-balancer
~~~~~~~~~~~~~

- Add ex_member_address argument to the Rackspace driver list_balancers
  method. If this argument is provided, only loadbalancers which have a
  member with the provided IP address attached are returned.
  [Tomaz Muraus]

Changes with Apache Libcloud 0.6.2
----------------------------------

General
~~~~~~~

- Fix a bug in PollingConnection class - actually use and don't ignore
  the poll_interval
  [Tomaz Muraus]

Compute
~~~~~~~

- Add support for Auth 2.0 API (keystone) to the OpenStack Auth
  connection class.
  [Brad Morgan]

- Add list_locations method to the OpenStack driver and fix some
  inconsistencies in the OpenStack driver extension method signatures.
  [Brad Morgan]

- Update Amazon EC2 driver and pricing data to support a new region -
  US West 2 (Oregon)
  [Tomaz Muraus]

- Expose 'CLOUDSTACK' provider. This driver can be used with an
  arbitrary CloudStack installation.
  [Tomaz Muraus]

Storage
~~~~~~~

- Update Amazon S3 driver to support a new region - US West 2 (Oregon)
  [Tomaz Muraus]

DNS
~~~

- Increase the default poll interval in the Rackspace driver to 2.5
  seconds.
  [Tomaz Muraus]

- Fix a bug in Rackspace Cloud DNS driver and make sure to throw an
  exception if an unexpected status code is returned. Reported by
  "jeblair".
  [Tomaz Muraus]

Changes with Apache Libcloud 0.6.1
----------------------------------

General
~~~~~~~

- Modify ParamikoSSHClient.connect so it supports authentication using a
  key file, (LIBCLOUD-116)
  [Jay Doane]

- User must now explicitly specify a path when using LIBCLOUD_DEBUG
  environment variable. (LIBCLOUD-95)
  [daveb, Tomaz Muraus]

- Add new XmlResponse and JsonResponse base class and modify all the
  driver-specific response classes to inherit from one of those two
  classes where applicable.
  [Caio Romão]

- Add new 'PollingConnection' class. This class can work with 'async'
  APIs. It sends and an initial request and then periodically poll the API
  until the job has completed or a timeout has been reached.
  [Tomaz Muraus]

Compute
~~~~~~~

- Add 24GB size to the GoGrid driver
  [Roman Bogorodskiy]

- Fix API endpoint URL in the Softlayer driver
  [Tomaz Muraus]

- Add support for OpenNebula 3.0 API (LIBCLOUD-120)
  [Hutson Betts]

- Add more attributes to the extra dictionary in the EC2 driver.
  (GITHUB-31)
  [Juan Carlos Moreno]

- Fix IP address assignment in the EC2 driver. Don't include "None" in the
  public_ip and private_ip Node list attribute.
  [Tomaz Muraus]

- Make deploy_node functionality more robust and don't start deployment if
  node public_ip attribute is an empty list.
  [Tomaz Muraus]

- Support SSH key authentication when using deploy_node.
  [Russell Haering, Tomaz Muraus]

- Enable deploy_node functionality in the EC2 driver using SSH key
  authentication
  [Russell Haering, Tomaz Muraus]

- Enable paramiko library debug log level if LIBCLOUD_DEBUG is used and
  paramiko is installed.
  [Tomaz Muraus]

- Fix the request signature generation in the base EC2 compute driver.
  If the endpoint is using a non-standard port (Eucalyptus based
  installations), append it to the hostname used to generate the
  signature.
  [Simon Delamare]

- Add new "unavailable" state to the BrightboxNodeDriver class.
  [Tim Fletcher]

- Increase a PollingConnection timeout in the CloudStack connection
  and fix the context dictionary creation in the _async_request method.
  [Oleg Suharev]

- Fix networks retrieval in the CloudStack driver create_node method.
  Also only pass 'networkids' field to the API if there are any networks
  available.
  [Oleg Suharev, Tomaz Muraus]

- Fix list_nodes in the CloudStack driver. Private IPs aren't always
  available.
  [Tomaz Muraus]

Load-baancer
~~~~~~~~~~~~

- Add a missing argument to the method call inside
  LoadBalancer.attach_compute_node and Driver.balancer_attach_compute_node.
  [Tim Fletcher, Tomaz Muraus]

- Add missing destroy() method to the LoadBalancer class.
  [Tomaz Muraus]

DNS
~~~

- New drivers for Rackspace Cloud DNS (US and UK region)
  [Tomaz Muraus]

- Add list_record_types() method. This method returns a list of record
  types supported by the provider.
  [Tomaz Muraus]

Changes with Apache Libcloud 0.6.0-beta1
----------------------------------------

General
~~~~~~~

- All the driver classes now inherit from the BaseDriver class
  [Tomaz Muraus]

- Prefer simplejson (if available) over json module. (LIBCLOUD-112)
  [Geoff Greer]

- Update compute demo and change the syntax of test credentials stored in
  test/secrets.py-dist. (LIBCLOUD-111)
  [Mike Nerone]

- Enable SSL certificate verification by default and throw an exception
  if CA certificate files cannot be found. This can be overridden by
  setting libcloud.security.VERIFY_SSL_CERT_STRICT to False.
  [Tomaz Muraus]

Compute
~~~~~~~

- Support for 1.1 API and many other improvements in the OpenStack driver ;
  LIBCLOUD-83
  [Mike Nerone, Paul Querna, Brad Morgan, Tomaz Muraus]

- Add some extra methods to the Gandi.net driver (LIBCLOUD-115)
  [Aymeric Barantal]

- Add ex_delete_image method to the Rackspace driver. (GITHUB-27)
  [David Busby]

- Linode driver now supports new 'Japan' location
  [Jed Smith]

- Rackspace driver now inherits from the OpenStack one instead of doing
  it vice versa. (LIBCLOUD-110)
  [Mike Nerone]

- Properly populate NodeImage "details" dictionary in the Rackspace
  compute driver. (LIBCLOUD-107)
  [Lucy Mendel]

- Fix a bug in Eucalyptus driver ex_describe_addresses method.
  [Tomaz Muraus]

- Add the following new extenstion methods to the Rackspace driver:
  ex_resize, ex_confirm_resize, ex_revert_resize.
  [Tomaz Muraus]

- Also allow user to pass in Node object to some ex\_ methods in
  the Rackspace compute driver.
  [Tomaz Muraus]

- Throw an exception in deploy_node if paramiko library is not
  available
  [Tomaz Muraus]

- Fix chmod argument value which is passed to the sftpclient.put
  method; GITHUB-17
  [John Carr]

- New driver for Ninefold.com. (LIBCLOUD-98)
  [Benno Rice]

Storage
~~~~~~~

- New driver for Google Storage based on the v1.0 / legacy API
  [Tomaz Muraus]

- New driver for Ninefold.com. (GITHUB-19)
  [Benno Rice]

- Fix a bug in uploading an object with some versions of Python 2.7
  where httplib library doesn't automatically call str() on the
  header values.
  [Tomaz Muraus]

- Allow users to upload (create) 0-bytes large (empty) objects
  [Tomaz Muraus]

Load-balancer
~~~~~~~~~~~~~

- New driver for Rackspace UK location
  [Tomaz Muraus]

- New driver for Ninefold.com. (LIBCLOUD-98)
  [Benno Rice]

DNS
~~~

- Drivers for Linode DNS and Zerigo DNS
  [Tomaz Muraus]

- Brand new DNS API!
  [Tomaz Muraus]

Changes with Apache Libcloud 0.5.2
----------------------------------

Compute
~~~~~~~

- New driver for serverlove.com and skalicloud.com
  [Tomaz Muraus]

- Fix node name and tag handling in the Amazon EC2 driver
  [Wiktor Kolodziej]

- Fix pricing and response handling in the OpenStack driver
  [Andrey Zhuchkov]

- Fix deploy_node() method and make it more robust
  [Tomaz Muraus]

- Users can now pass file like objects to ScriptDeployment and
  SSHKeyDeployment constructor.
  [Tomaz Muraus]

- Include node tags when calling list_nodes() in the Amazon EC2
  driver
  [Trevor Pounds]

- Properly handle response errors in the Rackspace driver and
  only throw InvalidCredsError if the returned status code is 401
  [Brad Morgan]

- Fix the create_node method in the Nimbus driver and make the
  "ex_create_tag" method a no-op, because Nimbus doesn't support creating
  tags.
  [Tomaz Muraus]

Storage
~~~~~~~

- Fix handling of the containers with a lot of objects. Now a LazyList
  object is returned when user calls list_container_objects() method
  and this object transparently handles pagination.
  [Danny Clark, Wiktor Kolodziej]

Changes with Apache Libcloud 0.5.0
----------------------------------

- Existing APIs directly on the libcloud.* module have been
  deprecated and will be removed in version 0.6.0.  Most methods
  were moved to the libcloud.compute.* module.

- Add new libcloud.loadbalancers API, with initial support for:
    - GoGrid Load Balancers
    - Rackspace Load Balancers

  [Roman Bogorodskiy]

- Add new libcloud.storage API, with initial support for:
   - Amazon S3
   - Rackspace CloudFiles

  [Tomaz Muraus]

- Add new libcloud.compute drivers for:
   - Bluebox [Christian Paredes]
   - Gandi.net [Aymeric Barantal]
   - Nimbus [David LaBissoniere]
   - OpenStack [Roman Bogorodskiy]
   - Opsource.net [Joe Miller]

- Added "pricing" module and improved pricing handling.
  [Tomaz Muraus]

- Updates to the GoGrid compute driver:
    - Use API version 1.0.
    - Remove sandbox flag.
    - Add ex_list_ips() to list IP addresses assigned to the account.
    - Implement ex_edit_image method which allows changing image attributes
      like name, description and make image public or private.

  [Roman Bogorodskiy]

- Updates to the Amazon EC2 compute driver:
   - When creating a Node, use the name argument to set a Tag with the
     value.  [Tomaz Muraus]
   - Add extension method for modifying node attributes and changing the
     node size. [Tomaz Muraus]
   - Add support for the new Amazon Region (Tokyo). [Tomaz Muraus]
   - Added ex_create_tags and ex_delete_tags. [Brandon Rhodes]
   - Include node Elastic IP addresses in the node public_ip attribute
     for the EC2 nodes. [Tomaz Muraus]
   - Use ipAddress and privateIpAddress attribute for the EC 2node public
     and private ip. [Tomaz Muraus]
   - Add ex_describe_addresses method to the EC2 driver. [Tomaz Muraus]

- Updates to the Rackspace CloudServers compute driver:
   - Add ex_rebuild() and ex_get_node_details() [Andrew Klochkov]
   - Expose URI of a Rackspace node to the node meta data. [Paul Querna]

- Minor fixes to get the library and tests working on Python 2.7 and PyPy.
  [Tomaz Muraus]

Changes with Apache Libcloud 0.4.2 (Released January 18, 2011)
--------------------------------------------------------------

- Fix EC2 create_node to become backward compatible for
  NodeLocation.
  [Tomaz Muraus]

- Update code for compatibility with CPython 2.5
  [Jerry Chen]

- Implement ex_edit_node method for GoGrid driver which allows
  changing node attributes like amount of RAM or description.
  [Roman Bogorodskiy]

- Add ex_set_password and ex_set_server_name to Rackspace driver.
  [Peter Herndon, Paul Querna]

- Add Hard and Soft reboot methods to Rackspace driver.
  [Peter Herndon]

- EC2 Driver availability zones, via ex_list_availability_zones;
  list_locations rewrite to include availability zones
  [Tomaz Muraus]

- EC2 Driver Idempotency capability in create_node; LIBCLOUD-69
  [David LaBissoniere]

- SSL Certificate Name Verification:
    - libcloud.security module
    - LibcloudHTTPSConnection, LibcloudHTTPConnection (alias)
    - Emits warning when not verifying, or CA certs not found

- Append ORD1 to available Rackspace location, but keep in the
  same node as DFW1, because it's not readable or writeable from
  the API.
  [Per suggestion of Grig Gheorghiu]

- ex_create_ip_group, ex_list_ip_groups, ex_delete_ip_group,
  ex_share_ip, ex_unshare_ip, ex_list_ip_addresses additions
  to Rackspace driver
  [Andrew Klochkov]

- New driver for CloudSigma.
  [Tomaz Muraus]

- New driver for Brightbox Cloud. (LIBCLOUD-63)
  [Tim Fletcher]

- Deployment capability to ElasticHosts
  [Tomaz Muraus]

- Allow deploy_node to use non-standard SSH username and port
  [Tomaz Muraus]

- Added Rackspace UK (London) support
  [Chmouel Boudjnah]

- GoGrid driver: add support for locations, i.e. listing
  of locations and creation of a node in specified
  location
  [Roman Bogorodskiy]

- GoGrid and Rackspace drivers: add ex_save_image() extra
  call to convert running node to an image
  [Roman Bogorodskiy]

- GoGrid driver: add support for creating 'sandbox' server
  and populate isSandbox flag in node's extra information.
  [Roman Bogorodskiy]

- Add ImportKeyPair and DescribeKeyPair to EC2. (LIBCLOUD-62)
  [Philip Schwartz]

- Update EC2 driver and test fixtures for new API.
  [Philip Schwartz]

Changes with Apache Libcloud 0.4.0 [Released October 6, 2010]
-------------------------------------------------------------

- Add create keypair functionality to EC2 Drivers. (LIBCLOUD-57)
  [Grig Gheorghiu]

- Improve handling of GoGrid accounts with limited access
  API keys.
  [Paul Querna]

- New Driver for ElasticHosts. (LIBCLOUD-45)
  [Tomaz Muraus]

- Use more consistent name for GoGrid driver and use http
  POST method for 'unsafe' operations
  [Russell Haering]

- Implement password handling and add deployment support
  for GoGrid nodes.
  [Roman Bogorodskiy]

- Fix behavior of GoGrid's create_node to wait for a Node ID.
  [Roman Bogorodskiy]

- Add ex_create_node_nowait to GoGrid driver if you don't need to
  wait for a Node ID when creating a node.
  [Roman Bogorodskiy]

- Removed libcloud.interfaces module.
  [Paul Querna]

- Removed dependency on zope.interfaces.
  [Paul Querna]

- RimuHosting moved API endpoint address.
  [Paul Querna]

- Fix regression and error in GoGrid driver for parsing node objects.
  [Roman Bogorodskiy]

- Added more test cases for GoGrid driver. (LIBCLOUD-34)
  [Roman Bogorodskiy, Jerry Chen]

- Fix parsing of Slicehost nodes with multiple Public IP addresses.
  [Paul Querna]

- Add exit_status to ScriptDeployment. (LIBCLOUD-36)
  [Paul Querna]

- Update prices for several drivers.
   [Brad Morgan, Paul Querna]

- Update Linode driver to reflect new plan sizes.
  [Jed Smith]

- Change default of 'location' in Linode create_node. (LIBCLOUD-41)
   [Jed Smith, Steve Steiner]

- Document the Linode driver.
  [Jed Smith]

- Request a private, LAN IP address at Linode creation.
  [Jed Smith]

Changes with Apache Libcloud 0.3.1 [Released May 11, 2010]
----------------------------------------------------------

- Updates to Apache License blocks to correctly reflect status as an
   Apache Project.

- Fix NOTICE file to use 2010 copyright date.

- Improve error messages for when running the test cases without
  first setting up a secrets.py

Changes with Apache Libcloud 0.3.0 [Tagged May 6, 2010, not released]
---------------------------------------------------------------------

- New Drivers for:
    - Dreamhost
    - Eucalyptus
    - Enomaly ECP
    - IBM Developer Cloud
    - OpenNebula
    - SoftLayer

- Added new deployment and bootstrap API.

- Improved Voxel driver.

- Added support for Amazon EC2 Asia Pacific (Singapore) Region.

- Improved test coverage for all drivers.

- Add support for multiple security groups in EC2.

- Fixed bug in Rackspace and RimuHosting when using multiple threads.

- Improved debugging and logging of HTTP requests.

- Improved documentation for all classes and methods.

Changes with Apache Libcloud 0.2.0 [Tagged February 2, 2010]
------------------------------------------------------------

- First public release.

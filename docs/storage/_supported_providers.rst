.. NOTE: This file has been generated automatically using generate_provider_feature_matrix_table.py script, don't manually edit it

============================= =================================================== =================== ============================ =================================================== ========================================
Provider                      Documentation                                       Provider Constant   Supported Regions            Module                                              Class Name                              
============================= =================================================== =================== ============================ =================================================== ========================================
`Aliyun OSS`_                                                                     ALIYUN_OSS          single region driver         :mod:`libcloud.storage.drivers.oss`                 :class:`OSSStorageDriver`               
`PCextreme AuroraObjects`_    :doc:`Click </storage/drivers/auroraobjects>`       AURORAOBJECTS       single region driver         :mod:`libcloud.storage.drivers.auroraobjects`       :class:`AuroraObjectsStorageDriver`     
`Microsoft Azure (blobs)`_    :doc:`Click </storage/drivers/azure_blobs>`         AZURE_BLOBS         single region driver         :mod:`libcloud.storage.drivers.azure_blobs`         :class:`AzureBlobsStorageDriver`        
`Backblaze B2`_               :doc:`Click </storage/drivers/backblaze_b2>`        BACKBLAZE_B2        single region driver         :mod:`libcloud.storage.drivers.backblaze_b2`        :class:`BackblazeB2StorageDriver`       
`CloudFiles`_                                                                     CLOUDFILES          dfw, hkg, iad, lon, ord, syd :mod:`libcloud.storage.drivers.cloudfiles`          :class:`CloudFilesStorageDriver`        
`DigitalOcean Spaces`_        :doc:`Click </storage/drivers/digitalocean_spaces>` DIGITALOCEAN_SPACES single region driver         :mod:`libcloud.storage.drivers.digitalocean_spaces` :class:`DigitalOceanSpacesStorageDriver`
`Google Cloud Storage`_       :doc:`Click </storage/drivers/google_storage>`      GOOGLE_STORAGE      single region driver         :mod:`libcloud.storage.drivers.google_storage`      :class:`GoogleStorageDriver`            
`KTUCloud Storage`_                                                               KTUCLOUD            dfw, hkg, iad, lon, ord, syd :mod:`libcloud.storage.drivers.ktucloud`            :class:`KTUCloudStorageDriver`          
`Local Storage`_                                                                  LOCAL               single region driver         :mod:`libcloud.storage.drivers.local`               :class:`LocalStorageDriver`             
`Nimbus.io`_                                                                      NIMBUS              single region driver         :mod:`libcloud.storage.drivers.nimbus`              :class:`NimbusStorageDriver`            
`Ninefold`_                                                                       NINEFOLD            single region driver         :mod:`libcloud.storage.drivers.ninefold`            :class:`NinefoldStorageDriver`          
`OpenStack Swift`_            :doc:`Click </storage/drivers/openstack_swift>`     OPENSTACK_SWIFT     dfw, hkg, iad, lon, ord, syd :mod:`libcloud.storage.drivers.cloudfiles`          :class:`OpenStackSwiftStorageDriver`    
`Amazon S3 (us-east-1)`_      :doc:`Click </storage/drivers/s3>`                  S3                  single region driver         :mod:`libcloud.storage.drivers.s3`                  :class:`S3StorageDriver`                
`Amazon S3 (ap-northeast-1)`_                                                     S3_AP_NORTHEAST     single region driver         :mod:`libcloud.storage.drivers.s3`                  :class:`S3APNE1StorageDriver`           
`Amazon S3 (ap-northeast-1)`_                                                     S3_AP_NORTHEAST1    single region driver         :mod:`libcloud.storage.drivers.s3`                  :class:`S3APNE1StorageDriver`           
`Amazon S3 (ap-northeast-2)`_                                                     S3_AP_NORTHEAST2    single region driver         :mod:`libcloud.storage.drivers.s3`                  :class:`S3APNE2StorageDriver`           
`Amazon S3 (ap-south-1)`_                                                         S3_AP_SOUTH         single region driver         :mod:`libcloud.storage.drivers.s3`                  :class:`S3APSouthStorageDriver`         
`Amazon S3 (ap-southeast-1)`_                                                     S3_AP_SOUTHEAST     single region driver         :mod:`libcloud.storage.drivers.s3`                  :class:`S3APSEStorageDriver`            
`Amazon S3 (ap-southeast-2)`_                                                     S3_AP_SOUTHEAST2    single region driver         :mod:`libcloud.storage.drivers.s3`                  :class:`S3APSE2StorageDriver`           
`Amazon S3 (ca-central-1)`_                                                       S3_CA_CENTRAL       single region driver         :mod:`libcloud.storage.drivers.s3`                  :class:`S3CACentralStorageDriver`       
`Amazon S3 (cn-north-1)`_                                                         S3_CN_NORTH         single region driver         :mod:`libcloud.storage.drivers.s3`                  :class:`S3CNNorthStorageDriver`         
`Amazon S3 (eu-central-1)`_                                                       S3_EU_CENTRAL       single region driver         :mod:`libcloud.storage.drivers.s3`                  :class:`S3EUCentralStorageDriver`       
`Amazon S3 (eu-west-1)`_                                                          S3_EU_WEST          single region driver         :mod:`libcloud.storage.drivers.s3`                  :class:`S3EUWestStorageDriver`          
`Amazon S3 (eu-west-2)`_                                                          S3_EU_WEST2         single region driver         :mod:`libcloud.storage.drivers.s3`                  :class:`S3EUWest2StorageDriver`         
`Ceph RGW`_                                                                       S3_RGW              single region driver         :mod:`libcloud.storage.drivers.rgw`                 :class:`S3RGWStorageDriver`             
`RGW Outscale`_                                                                   S3_RGW_OUTSCALE     single region driver         :mod:`libcloud.storage.drivers.rgw`                 :class:`S3RGWOutscaleStorageDriver`     
`Amazon S3 (sa-east-1)`_                                                          S3_SA_EAST          single region driver         :mod:`libcloud.storage.drivers.s3`                  :class:`S3SAEastStorageDriver`          
`Amazon S3 (us-east-2)`_                                                          S3_US_EAST2         single region driver         :mod:`libcloud.storage.drivers.s3`                  :class:`S3USEast2StorageDriver`         
`Amazon S3 (us-gov-west-1)`_                                                      S3_US_GOV_WEST      single region driver         :mod:`libcloud.storage.drivers.s3`                  :class:`S3USGovWestStorageDriver`       
`Amazon S3 (us-west-1)`_                                                          S3_US_WEST          single region driver         :mod:`libcloud.storage.drivers.s3`                  :class:`S3USWestStorageDriver`          
`Amazon S3 (us-west-2)`_                                                          S3_US_WEST_OREGON   single region driver         :mod:`libcloud.storage.drivers.s3`                  :class:`S3USWestOregonStorageDriver`    
============================= =================================================== =================== ============================ =================================================== ========================================

.. _`Aliyun OSS`: http://www.aliyun.com/product/oss
.. _`PCextreme AuroraObjects`: https://www.pcextreme.com/aurora/objects
.. _`Microsoft Azure (blobs)`: http://windows.azure.com/
.. _`Backblaze B2`: https://www.backblaze.com/b2/
.. _`CloudFiles`: http://www.rackspace.com/
.. _`DigitalOcean Spaces`: https://www.digitalocean.com/products/object-storage/
.. _`Google Cloud Storage`: http://cloud.google.com/storage
.. _`KTUCloud Storage`: http://www.rackspace.com/
.. _`Local Storage`: http://example.com
.. _`Nimbus.io`: https://nimbus.io/
.. _`Ninefold`: http://ninefold.com/
.. _`OpenStack Swift`: http://www.rackspace.com/
.. _`Amazon S3 (us-east-1)`: http://aws.amazon.com/s3/
.. _`Amazon S3 (ap-northeast-1)`: http://aws.amazon.com/s3/
.. _`Amazon S3 (ap-northeast-1)`: http://aws.amazon.com/s3/
.. _`Amazon S3 (ap-northeast-2)`: http://aws.amazon.com/s3/
.. _`Amazon S3 (ap-south-1)`: http://aws.amazon.com/s3/
.. _`Amazon S3 (ap-southeast-1)`: http://aws.amazon.com/s3/
.. _`Amazon S3 (ap-southeast-2)`: http://aws.amazon.com/s3/
.. _`Amazon S3 (ca-central-1)`: http://aws.amazon.com/s3/
.. _`Amazon S3 (cn-north-1)`: http://aws.amazon.com/s3/
.. _`Amazon S3 (eu-central-1)`: http://aws.amazon.com/s3/
.. _`Amazon S3 (eu-west-1)`: http://aws.amazon.com/s3/
.. _`Amazon S3 (eu-west-2)`: http://aws.amazon.com/s3/
.. _`Ceph RGW`: http://ceph.com/
.. _`RGW Outscale`: https://en.outscale.com/
.. _`Amazon S3 (sa-east-1)`: http://aws.amazon.com/s3/
.. _`Amazon S3 (us-east-2)`: http://aws.amazon.com/s3/
.. _`Amazon S3 (us-gov-west-1)`: http://aws.amazon.com/s3/
.. _`Amazon S3 (us-west-1)`: http://aws.amazon.com/s3/
.. _`Amazon S3 (us-west-2)`: http://aws.amazon.com/s3/

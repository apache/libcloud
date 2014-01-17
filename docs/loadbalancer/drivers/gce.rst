Google Load Balancer Driver Documentation
==========================================

Loadbalancing in Compute Engine is native to Google Compute Engine.

.. figure:: /_static/images/provider_logos/gcp.png
    :align: center
    :width: 500
    :target: https://cloud.google.com/

Connecting to Compute Engine Load Balancer
------------------------------------------

Refer to
:doc:`Google Compute Engine Driver Documentation </compute/drivers/gce>` for
information about setting up authentication for GCE.

In order to instantiate a driver for the Load Balancer, you can either pass
in the same authentication information as you would to the GCE driver, or you
can instantiate the GCE driver and pass that to the Load Balancer driver.
The latter is preferred (since you are probably getting a GCE driver anyway),
but the former aligns more closely to the Libcloud API.

Examples
--------

Additional example code can be found in the "demos" directory of Libcloud here:
https://github.com/apache/libcloud/blob/trunk/demos/gce_lb_demo.py

1. Getting Driver with GCE Driver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/loadbalancer/gce/gce_driver.py

2. Getting Driver with Authentication Information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/loadbalancer/gce/gce_authentication.py

API Docs
--------

.. autoclass:: libcloud.loadbalancer.drivers.gce.GCELBDriver
    :members:
    :inherited-members:


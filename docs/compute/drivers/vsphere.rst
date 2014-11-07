VMware vSphere Compute Driver Documentation
===========================================

`VMware vSphere`_ is VMware's cloud computing operating system which allows
you to run your own private cloud.

.. figure:: /_static/images/provider_logos/vmware_vsphere.png
    :align: center
    :width: 200
    :target: http://www.vmware.com/products/vsphere/

Requirements
------------

VMware vSphere driver depends on the `pysphere`_ Python library which needs to
be installed for the driver to work.

This library can be installed using pip as shown bellow:

.. sourcecode:: bash

   pip install pysphere

Connecting to vSphere installation
----------------------------------

To connect to the vSphere installation you need to pass the following arguments
to the driver constructor

* ``host`` - hostname or IP address of your vSphere installation. Note: if your
  installation is using or accessible via a different port, you should use the
  ``url`` argument which is described bellow instead.
* ``url`` - full URL to your vSphere installation client endpoint - e.g.
  ``https://<host>/sdk/``. Note: This argument is mutually exclusive with
  ``host`` argument which means you need to provide either ``host`` or ``url``
  argument, but not both.
* ``username`` - username used to log in
* ``password`` - password used to log in

Examples
--------

1. Connect by specifying a host
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/vsphere/connect_host.py
   :language: python

2. Connect by specifying a url
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/vsphere/connect_url.py
   :language: python

3. Connect by specifying a url (custom port)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/vsphere/connect_url_custom_port.py
   :language: python

Troubleshooting
---------------

How do I know if I'm connecting to the correct URL?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you are connecting by provider ``url`` argument and you get the
``Response is "text", not "text/xml"`` or similar error back, this most likely
means you have specified an invalid URL (e.g. you forgot to specify a path).

You can test if the url you are using is valid by adding ``/vimService.wsdl``
to it (e.g. ``https://<host>/sdk/vimService.wsdl``). When you visit this page,
you should get an XML response back.

API Docs
--------

VMware vSphere v5.5
~~~~~~~~~~~~~~~~~~~

.. autoclass:: libcloud.compute.drivers.vsphere.VSphere_5_5_NodeDriver
    :members:
    :inherited-members:

.. _`VMware vSphere`: http://www.vmware.com/products/vsphere/
.. _`pysphere`: https://pypi.python.org/pypi/pysphere

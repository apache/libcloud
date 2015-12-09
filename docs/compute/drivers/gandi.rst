Gandi Computer Driver Documentation
===================================

`Gandi SAS`_ is a registrar, web hosting and private and `public cloud`_
provider based in France with data centers in France, Luxembourg and USA.

.. figure:: /_static/images/provider_logos/gandi.png
    :align: center
    :width: 300
    :target: https://www.gandi.net/

Instantiating a driver
----------------------

When you instantiate a driver you need to pass the API key and activate
the API platforms. See this `Gandi's documentation`_ for how to do it.

Examples
--------

Create instance
~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/gandi/create_node.py


.. _`Gandi SAS`: https://www.gandi.net/
.. _`public cloud`: https://www.gandi.net/hebergement/serveur
.. _`Gandi's documentation`: https://wiki.gandi.net/en/xml-api/activate

API Docs
--------

.. autoclass:: libcloud.compute.drivers.gandi.GandiNodeDriver
    :members:
    :inherited-members:

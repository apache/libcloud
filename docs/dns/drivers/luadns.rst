Luadns DNS Driver Documentation
===============================

I was a happy user of a free DNS hosting service for many years, when this service was acquired by a competitor in august 2011, I was forced to move somewhere else.

While migrating my zone files I realized that I don't like Bind syntax files neither administering tens of domains through a web interface. I've started to experiment on how it should look a perfect DNS service for me. I've realized that I would love to store my configuration files in a Git repository and I would need some configuration language for templating (Lua).

This is how LuaDNS was born on October, 2011.

Read more at: http://luadns.com/

Instantiating the driver
------------------------

.. literalinclude:: /examples/dns/luadns/instantiate_driver.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.dns.drivers.luadns.LuadnsDNSDriver
    :members:
    :inherited-members:

.. _`Luadns`: http://luadns.com/
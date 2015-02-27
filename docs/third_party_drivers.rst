Third Party Drivers
===================

Libcloud includes most of the drivers in its core, but some providers and
developers for various reasons decide to release their driver as a separate
PyPi package.

This page lists those third party drivers. For documentation and usage examples,
please refer to the third party driver documentation (if available).

Keep in mind that those drivers are not party of the core and such we can't
guarantee for the quality of those drivers.

Compute
-------

+-------------------+---------------------------------+--------------------------------------+
| Provider          | PyPi package                    | Source code                          |
+===================+=================================+======================================+
| `StratusLab`_     |                                 | `StratusLab/libcloud-drivers`_       |
+-------------------+---------------------------------+--------------------------------------+
| `Snooze`_         | `stratuslab-libcloud-drivers`_  | `snooze-libcloud`_                   |
+-------------------+---------------------------------+--------------------------------------+

DNS
----

+-------------------+--------------------------+--------------------------------------+
| Provider          | PyPi package             | Source code                          |
+===================+==========================+======================================+
| `DNSMadeEasy`_    | `libcloud-dnsmadeeasy`_  | `moses-palmer/libcloud-dnsmadeeasy`_ |
+-------------------+--------------------------+--------------------------------------+

.. _`StratusLab`: http://stratuslab.eu/
.. _`Snooze`: http://snooze.inria.fr
.. _`snooze-libcloud`: https://github.com/msimonin/snooze-libcloud

.. _`stratuslab-libcloud-drivers`: https://pypi.python.org/pypi/stratuslab-libcloud-drivers
.. _`StratusLab/libcloud-drivers`: https://github.com/StratusLab/libcloud-drivers

.. _`DNSMadeEasy`: http://www.dnsmadeeasy.com/
.. _`libcloud-dnsmadeeasy`: https://pypi.python.org/pypi/libcloud-dnsmadeeasy/1.0
.. _`moses-palmer/libcloud-dnsmadeeasy`: https://github.com/moses-palmer/libcloud-dnsmadeeasy

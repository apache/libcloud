Registering a third party driver
================================

Driver is considered third party if it's not bundled with a Libcloud release.

To register a third party driver you should use :func:`provider.set_driver`
function from the corresponding component.

Keep in mind that this function needs to be called before a third party driver
is used.

:func:`set_driver` takes the following arguments:

.. code-block:: python

    set_driver('provider_name', 'path.to.the.module', 'DriverClass')

For example:

.. literalinclude:: /examples/compute/register_3rd_party_driver.py
   :language: python


An example of existing third party driver can be found at
https://github.com/StratusLab/libcloud-drivers

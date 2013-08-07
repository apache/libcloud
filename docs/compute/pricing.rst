Pricing
=======

For majority of the compute providers Libcloud provides estimated pricing
information. Pricing information is available via the :attr:`price` attribute
on the :class:`NodeSize` object. :attr:`price` attribute is a :func:`float`
type and tells user how much it costs (in US dollars) to run a ``Node`` with a
specified ``NodeSize`` for an hour.

Example bellow shows how to retrieve pricing for ``NodeSize`` objects using
:func:`list_sizes` method.

.. literalinclude:: /examples/compute/pricing.py
   :language: python
   :emphasize-lines: 11-19

As noted above this pricing information is an estimate and you should only
be used as such. You should always check your provider website / control panel
for accurate pricing information and never rely solely on Libcloud pricing data.

Besides that, many cloud providers also offer different pricing scheme based
on the volume and discounts for reserved instances. All of this information
is not taken into account in the simplistic "price per hour" pricing scheme
available in Libcloud.

Where does the Libcloud pricing data come from?
-----------------------------------------------

Most of the providers don't provide pricing information via the API which means
most of the pricing information is scrapped directly from the provider
websites.

Pricing data which is scrapped from the provider websites is located in the
a JSON file (``data/pricing.json``) which is bundled with each release. This
pricing data is only updated once you install a new release which means it
could be out of date.

Using a custom pricing file
---------------------------

.. note::

    This functionality is only available in Libcloud trunk and higher.

Updating pricing
----------------

.. note::

    This functionality is only available in Libcloud trunk and higher.

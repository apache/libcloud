Pricing
=======

For majority of the compute providers Libcloud provides estimated pricing
information. Pricing information is available via the :attr:`price` attribute
on the :class:`NodeSize` object. :attr:`price` attribute is a :func:`float`
type and tells user how much it costs (in US dollars) to run a ``Node`` with a
specified :class:`NodeSize` for an hour.

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

.. _using-custom-pricing-file:

Using a custom pricing file
---------------------------

.. note::

    This functionality is only available in Libcloud 0.14.0 and above.

By default Libcloud reads pricing data from ``data/pricing.json`` file which
is included in the release package. If you want to use a custom pricing file,
simply put move the file to ``~/.libcloud.pricing.json``.

If ``~/.libcloud.pricing.json`` file is available, Libcloud will use it instead
of the default pricing file which comes bundled with the release.

Updating pricing
----------------

.. note::

    This functionality is only available in Libcloud 0.14.0 and above.

Currently only way to update pricing is programmatically using
:func:`libcloud.pricing.download_pricing_file` function. By default this
function retrieves the latest pricing file from our git repository and saves it
to ``~/.libcloud.pricing.json``.

.. autofunction:: libcloud.pricing.download_pricing_file

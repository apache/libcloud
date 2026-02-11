Storage Integration Test Module
===============================

This test suite is for validating the apache-libcloud storage functionality against live storage backends.

Setting up the test suite
-------------------------

.. code-block:: bash

  uv sync --group integration-storage

Running the tests
-----------------

.. code-block:: bash

  python -m integration.storage

=================================
OpenET - Core Functions and Tools
=================================

|version| |build|

This repository provides a template/example for other ET model.  This repository is currently structured to compute ET as a simple function of NDVI.

Installation
============

To install the OpenET core python module:

.. code-block:: console

    pip install openet

Dependencies
============

Modules needed to run the model:

 * `earthengine-api <https://github.com/google/earthengine-api>`__

Modules needed to run the test suite:

 * `pytest <https://docs.pytest.org/en/latest/>`__

Running Testing
===============

.. code-block:: console

    python -m pytest

Namespace Packages
==================

Each OpenET model should be stored in the "openet" folder (namespace).  The benefit of the namespace package is that each ET model can be tracked in separate repositories but called as a "dot" submodule of the main openet module,

.. code-block:: console

    import openet.api
    import openet.common
    import openet.interp

.. |build| image:: https://travis-ci.org/Open-ET/openet-core.svg?branch=master
   :alt: Build status
   :target: https://travis-ci.org/Open-ET/openet-core
.. |version| image:: https://badge.fury.io/py/openet-core.svg
   :alt: Latest version on PyPI
   :target: https://badge.fury.io/py/openet-core

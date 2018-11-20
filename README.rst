=================================
OpenET - Core Functions and Tools
=================================

|version| |build|

This repository provides core functions used by the OpenET models.

Installation
============

The OpenET core python module can be installed via pip:

.. code-block:: console

    pip install openet

Dependencies
============

Modules needed to run the model:

 * `earthengine-api <https://github.com/google/earthengine-api>`__

OpenET Namespace Package
========================

Each OpenET model should be stored in the "openet" folder (namespace).  The benefit of the namespace package is that each ET model can be tracked in separate repositories but called as a "dot" submodule of the main openet module,

.. code-block:: console

    import openet.api
    import openet.common
    import openet.interp

.. |build| image:: https://travis-ci.org/Open-ET/openet-core-beta.svg?branch=master
   :alt: Build status
   :target: https://travis-ci.org/Open-ET/openet-core-beta
.. |version| image:: https://badge.fury.io/py/openet.svg
   :alt: Latest version on PyPI
   :target: https://badge.fury.io/py/openet

Development and Testing
=======================

Please see the `CONTRIBUTING.rst <CONTRIBUTING.RST>`__.

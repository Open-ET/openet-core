=================================
OpenET - Core Functions and Tools
=================================

|version| |build|

This repository provides core functions used by the OpenET models.

Core Components
===============

Common
------

The OpenET common module provides functions that are common across many of the OpenET models.  Currently these are limited to cloud masking functions but additional functions will be added as they are identified.

Examples of the cloud masking functions are provided in the "examples" folder.

+ `Landsat Collection 1 TOA cloud mask <examples/landsat_toa_cloud_mask.ipynb>`__
+ `Landsat Collection 1 SR cloud mask <examples/landsat_sr_cloud_mask.ipynb>`__
+ `Sentinel 2 TOA cloud mask <examples/sentinel2_toa_cloud_mask.ipynb>`__

Interpolation
-------------

The OpenET "interp" module provides functions for interpolating the image based ET estimates from the models (primarily from Landsat images) to a daily time step then aggregating to custom time periods (such as monthly or annual).

Installation
============

The OpenET core python module can be installed via pip:

.. code-block:: console

    pip install openet-core

Dependencies
============

Modules needed to run the model:

 * `earthengine-api <https://github.com/google/earthengine-api>`__

OpenET Namespace Package
========================

Each OpenET model will be stored in subfolders of the "openet" folder (namespace).  The benefit of the namespace package is that each ET model can be tracked in separate repositories but called as a "dot" submodule of the main openet module,

.. code-block:: python

    import openet.core.common
    import openet.core.interp
    import openet.ssebop

Development and Testing
=======================

Please see the `CONTRIBUTING.rst <CONTRIBUTING.RST>`__.

.. |build| image:: https://travis-ci.org/Open-ET/openet-core-beta.svg?branch=master
   :alt: Build status
   :target: https://travis-ci.org/Open-ET/openet-core-beta
.. |version| image:: https://badge.fury.io/py/openet-core.svg
   :alt: Latest version on PyPI
   :target: https://badge.fury.io/py/openet-core

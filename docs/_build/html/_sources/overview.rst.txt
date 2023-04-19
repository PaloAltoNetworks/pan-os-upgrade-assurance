Overview
==========================

The ``upgrade_assurance`` package consists of several modules. Most of them (including methods they provide) can be used separately. This makes those modules highly flexible up to the point where one can interact with the ``XML API`` directly.

But for general use cases, the wrapper methods are provided. For details, see the :ref:`usage_documentation` documentation.

This package consists of the following modules:

* :mod:`.firewall_proxy`, includes:
  
  * :class:`.FirewallProxy` class
   
    A *low level* class. Acts as a proxy between the `Pan-OS-Python Firewall`_ and the :class:`.CheckFirewall` classes. Its main purpose is to provide a wrapper for running ``XML API`` commands, handling basic communication errors, etc. 
  
* :mod:`.check_firewall`, includes

  * :class:`.CheckFirewall` class
  
    A *high level* class. Its main purpose is to provide an interface to run readiness checks and state snapshots. It wraps around the :class:`.FirewallProxy` class methods and provides results in a unified way.

* :mod:`.snapshot_compare`, includes
 
  * :class:`.SnapshotCompare` class

    This class provides:
    
      * mechanism to calculate differences between two snapshots made with the :class:`.CheckFirewall` class,
      * mechanism to generate a report based on calculated differences.

* :mod:`.utils`, includes data classes and helper methods:

  * :class:`.ConfigParser` class to validate configuration passed to different methods
  * :class:`.CheckType` and :class:`.SnapType` classes to map commonly used named to variables
  * :class:`.CheckResults` data class that represents internal check results
  * and some more.

.. _Pan-OS-Python Firewall: https://pandevice.readthedocs.io/en/latest/module-firewall.html

.. _usage_documentation:

=====
Usage
=====

.. contents::
    :local:
    :backlinks: entry
    :depth: 2

Importing Classes
=================

To use ``upgrade_assurance`` in a project, you may either:

    * import the package as a whole:

    .. code-block:: python

        import upgrade_assurance

    * or be more specific about which modules you want to import:

    .. code-block:: python

        from upgrade_assurance import firewall_proxy
        from upgrade_assurance import check_firewall
        from upgrade_assurance import snapshot_compare
        from upgrade_assurance import utils

    * or, be even *more* specific by importing a specific class:

    .. code-block:: python

        from upgrade_assurance.check_firewall import CheckFirewall


Initializing objects
====================

In the following code snippets, we assume the 3\ :sup:`rd` way of importing the classes:

FirewallProxy class
-------------------

This class inherits the constructor method from the `Pan-OS-Python Firewall`_ class. Therefore, objects for this class are initialized in the same way. For details, see documentation for this class. Here we will provide only the most basic way of initializing the :class:`.FirewallProxy` class that includes a username/password authentication.

.. code-block:: python

    from upgrade_assurance.firewall_proxy import FirewallProxy

    firewall = FirewallProxy(
        hostname='FQDN or an IP address of the management interface',
        api_username='an account name, can be readonly',
        api_password='a password'
    )

CheckFirewall class
-------------------

Since this is a *high level* class, it depends on the :class:`.FirewallProxy` class for device communication. Hence, the constructor for this class takes an object of the :class:`.FirewallProxy` class.

.. code-block:: python

    from upgrade_assurance.check_firewall import CheckFirewall
    from upgrade_assurance.firewall_proxy import FirewallProxy

    firewall = FirewallProxy(hostname='1.2.3.4', api_username='ro_admin', api_password='************')
    checks = CheckFirewall(firewall)

SnapshotCompare class
---------------------

This class provides methods of comparing two snapshots made with the :class:`.CheckFirewall` class. Therefore, it is an *offline* class - no communication with a device is made.

The idea around this class is that an object represents an entity storing two snapshots, for example, a pre-upgrade and a post-upgrade one. Therefore, the constructor takes two snapshots as input parameters. After an object is initialized, one can run reports on it. Each report is configurable but limited to data from both snapshots. In order to compare a different set of snapshots, one has to create a new object.

In the example above, we implicitly take snapshots for all supported state areas. For more details, see :class:`.ConfigParser` dialect.

.. code-block:: python

    from upgrade_assurance.snapshot_compare import SnapshotCompare

    diff_object = SnapshotCompare(       # initialize object storing both snapshots
        left_snapshot=snapshot1,         # 1st snapshot
        right_snapshot=snapshot2         # 2nd snapshot
    )

ConfigParser class (internal)
-----------------------------

Although this is an internally used class, probably not often used on a daily basis, we provide documentation on how to initialize it as it's heavily used in the other classes.

The constructor for this class takes two arguments: 

* a valid set of configuration parameters, 
* a configuration provided by a user (the one that will be verified and parsed).


.. code-block:: python

    from upgrade_assurance.utils import ConfigParser

    parser = ConfigParser(
        requested_config=[]     # a list of configuration elements
        valid_elements=[]       # a list of all valid elements
    )


The library in action - usage examples
======================================

Please note that the samples below assume the minimum knowledge on available tests and their configurations. Refer to the :ref:`configuration_documentation` for complete documentation.

Running readiness checks for a single device
--------------------------------------------

This is the sample code showing how to run readiness checks. In this example, we run two critical checks on a device after an upgrade is done:

* ``session_exist`` check makes sure that a session described with ``source``, ``destinations``, and ``dest_port`` parameters is present in the device sessions table,
* ``arp_entry_exist`` check looks for an entry in the ARP table matching a given ``ip`` address.

If at least one of the tests fail, the script exits immediately.

.. code-block:: python

    from upgrade_assurance.check_firewall import CheckFirewall
    from upgrade_assurance.firewall_proxy import FirewallProxy

    # ... upgrade code goes here

    firewall = FirewallProxy(hostname='1.2.3.4', api_username='ro_admin', api_password='************')
    checks = CheckFirewall(firewall)

    checks_configuration = [
        { 'session_exist': {
            'source': '123.234.123.234',
            'destination': '10.0.0.1',
            'dest_port': '8080'
        }},
        { 'arp_entry_exist': {
            'ip': '10.100.0.1'
        }},
    ]

    results = checks.run_readiness_checks(checks_configuration)

    passed = True

    for check in checks_configuration:
        check_name = list(check.keys())[0]
        passed = passed & results[check_name]['state']

        if not results[check_name]['state']:
            print(f'FAILED: {check_name} - {results[check_name]["reason"]}')
    
    if not passed:
        exit(1)

    # ... continue script

The sample output of this portion of the script (both tests fail):

.. code-block:: 
    
    FAILED: session_exist - [FAIL] Session not found in the session table.
    FAILED: arp_entry_exist - [FAIL] Entry not found in the ARP table.


Generating a report based on snapshots
------------------------------------------------

In this example, we take two snapshots (one for each device in an HA pair) and we use the :class:`.SnapshotCompare` class to compare licenses. Based on the comparison result, a decision is made whether to continue with the rest of the script.

The comparison itself is configured to:

* skip two properties (to avoid false-positives):

  * ``serial`` as serial numbers for both devices are different,
  * ``authcodes`` as two different authcodes were used for licensing devices.

* check only part of the comparison results that compares licenses existing in both snapshots. Licenses missing in each snapshot are not checked.


.. code-block:: python

    from upgrade_assurance.check_firewall import CheckFirewall
    from upgrade_assurance.firewall_proxy import FirewallProxy
    from upgrade_assurance.snapshot_compare import SnapshotCompare
    from upgrade_assurance.utils import printer


    node_a      = FirewallProxy(hostname='10.0.0.1', api_username='ro_admin', api_password='************')
    checks_a    = CheckFirewall(node_a)

    node_b      = FirewallProxy(hostname='10.0.0.2', api_username='ro_admin', api_password='************')
    checks_b    = CheckFirewall(node_b)

    snapshot_a  = checks_a.run_snapshots(['license'])
    snapshot_b  = checks_b.run_snapshots(['license'])

    diff_obj = SnapshotCompare(snapshot_a, snapshot_b)
    license_diff = diff_obj.compare_snapshots([{
        'license': {
            'properties': ['!serial', '!authcode']
        }
    }])

    if not license_diff['license']['changed']['passed']:
        printer(license_diff['license']['changed']['changed_raw'])
        # ... code that handles failed check

The sample output of the above script:

.. code-block::

    GlobalProtect Gateway:
       | passed: True
    WildFire License:
       | passed: True
    DNS Security:
       | passed: True
    AutoFocus Device License:
       | passed: False
       | missing:
       |   | passed: True
       | added:
       |   | passed: True
       | changed:
       |   | passed: False
       |   | changed_raw:
       |   |   | expires:
       |   |   |   | left_snap: September 25, 2031
       |   |   |   | right_snap: February 11, 2040
    PA-VM:
       | passed: True
    Premium:
       | passed: True
    PAN-DB URL Filtering:
       | passed: True
    Threat Prevention:
       | passed: True


.. _Pan-OS-Python Firewall: https://pandevice.readthedocs.io/en/latest/module-firewall.html

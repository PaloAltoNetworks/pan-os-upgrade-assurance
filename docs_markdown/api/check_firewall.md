---
sidebar_label: check_firewall
title: check_firewall
---

## ContentDBVersionInFutureException

```python
class ContentDBVersionInFutureException(Exception)
```

Used when the installed Content DB version is newer than the latest available version.

## WrongDataTypeException

```python
class WrongDataTypeException(Exception)
```

Used when passed configuration does not meet the data type requirements.

## ImageVersionNotAvailableException

```python
class ImageVersionNotAvailableException(Exception)
```

Used when requested image version is not available for downloading.

## CheckFirewall

```python
class CheckFirewall()
```

Class responsible for running readiness checks and creating Firewall state snapshots.

This class is designed to:

* run one or more :class:`.FirewallProxy` class methods,
* gather and interpret results,
* present results.

It is split into two parts responsible for:

1. running readiness checks, all methods related to this functionality are prefixed with ``check_``,
2. running state snapshots, all methods related to this functionality are prefixed with ``get_``, although usually the :class:`.FirewallProxy` methods are run directly.

Although it is possible to run the methods directly, the preferred way is to run them through one of the following ``run`` methods:

* :meth:`.run_readiness_checks` is responsible for running specified readiness checks,
* :meth:`.run_snapshots` is responsible for getting a snapshot of specified device areas.

**Arguments**:

- `_snapshot_method_mapping` (`dict`): Internal variable containing a map of all valid snapshot types mapped to the specific methods.
This mapping is used to verify the requested snapshot types and to map the snapshot with an actual method that will eventually run. Keys in this dictionary are snapshot names as defined in the :class:`.SnapType` class, values are references to methods that will be run.
- `_check_method_mapping` (`dict`): Internal variable containing the map of all valid check types mapped to the specific methods. This mapping is used to verify requested check types and to map a check with an actual method that will be eventually run. Keys in this dictionary are check names as defined in the :class:`.CheckType` class, values are references to methods that will be run.

### \_\_init\_\_

```python
def __init__(node: FirewallProxy) -> None
```

CheckFirewall constructor.

**Arguments**:

- `node` (`:class:`.FirewallProxy``): Object representing a device against which checks and/or snapshots are run.

### check\_pending\_changes

```python
def check_pending_changes() -> CheckResult
```

Check if there are pending changes on device.

It checks two states:

1. if there is full commit required on the device,
2. if not, if there is a candidate config pending on a device.

**Returns**:

`:class:`.CheckResult``: Object representing the result of the content version check:
* :attr:`.CheckStatus.SUCCESS` if there is no pending configuration,
* :attr:`.CheckStatus.FAIL` otherwise.

### check\_panorama\_connectivity

```python
def check_panorama_connectivity() -> CheckResult
```

Check connectivity with the Panorama service.

**Returns**:

`:class:`.CheckResult``: State of Panorama connection:
* :attr:`.CheckStatus.SUCCESS` when device is connected to Panorama,
* :attr:`.CheckStatus.FAIL` otherwise,
* :attr:`.CheckStatus.ERROR` is returned when no Panorama configuration is found.

### check\_ha\_status

```python
def check_ha_status(skip_config_sync: Optional[bool] = False) -> CheckResult
```

Checks HA pair status from the perspective of the current device.

Currently, only Active-Passive configuration is supported.

**Arguments**:

- `skip_config_sync` (`bool, optional`): (defaults to ``False``) Use with caution, when set to ``True`` will skip checking if configuration is synchronized between nodes. Helpful when verifying a state of a partially upgraded HA pair.

**Returns**:

`:class:`.CheckResult``: Result of HA pair status inspection:
* :attr:`.CheckStatus.SUCCESS` when pair is configured correctly,
* :attr:`.CheckStatus.FAIL` otherwise,
* :attr:`.CheckStatus.ERROR` is returned when device is not a member of an HA pair or the pair is not in Active-Passive configuration.

### check\_is\_ha\_active

```python
def check_is_ha_active(
        skip_config_sync: Optional[bool] = False) -> CheckResult
```

Checks whether this is an active node of an HA pair.

Before checking the state of the current device, the :meth:`check_ha_status` method is run. If this method does not end with :attr:`.CheckStatus.SUCCESS`, its return value is passed as the result of :meth:`check_is_ha_active`.

**Arguments**:

- `skip_config_sync` (`bool, optional`): (defaults to ``False``) Use with caution, when set to ``True`` will skip checking if configuration is synchronized between nodes. Helpful when working with a partially upgraded HA pair.

**Returns**:

`:class:`.CheckResult``: The return value depends on the results of running :meth:`check_ha_status` method. If the method returns:
* :attr:`.CheckStatus.SUCCESS` the actual state of the device in an HA pair is checked, if the state is:
    * active :attr:`,.CheckStatus.SUCCESS` is returned,
    * passive :attr:`,.CheckStatus.FAIL` is returned,
* anything else than :attr:`.CheckStatus.SUCCESS`, the :meth:`check_ha_status` return value is passed as a return value of this method.

### check\_expired\_licenses

```python
def check_expired_licenses(skip_licenses: Optional[list] = []) -> CheckResult
```

Check if any license is expired.

**Arguments**:

- `skip_licenses` (`list(string), optional`): (defaults to ``[]``) List of license names that should be skipped during the check.

**Returns**:

`:class:`.CheckResult``: * :attr:`.CheckStatus.SUCCESS` if no license is expired,
* :attr:`.CheckStatus.FAIL` otherwise.

### check\_critical\_session

```python
def check_critical_session(
        source: Optional[str] = None,
        destination: Optional[str] = None,
        dest_port: Optional[Union[str, int]] = None) -> CheckResult
```

Check if a critical session is present in the sessions table.

**Arguments**:

- `source` (`str, optional`): (defaults to ``None``) Source IPv4 address for the examined session.
- `destination` (`str, optional`): (defaults to ``None``) Destination IPv4 address for the examined session.
- `dest_port` (`int, str, optional`): (defaults to ``None``) Destination port value. This should be an integer value, but string representations such as ``&quot;8080&quot;`` are also accepted.

**Returns**:

`:class:`.CheckResult``: * :attr:`.CheckStatus.SUCCESS` if a session is found in the sessions table,
* :attr:`.CheckStatus.FAIL` otherwise,
* :attr:`.CheckStatus.SKIPPED` when no config is passed,
* :attr:`.CheckStatus.ERROR` if the session table is empty.

### check\_content\_version

```python
def check_content_version(version: Optional[str] = None) -> CheckResult
```

Verify installed version of the Content Database.

This method runs in two modes:

    * w/o any configuration - checks if the latest version of the Content DB is installed.
    * with specific version passed - verifies if the installed Content DB is at least equal.

**Arguments**:

- `version` (`str, optional`): (defaults to ``None``) Target version of the content DB.

**Raises**:

- `ContentDBVersionInFutureException`: If the data returned from a device is newer than the latest version available.

**Returns**:

`:py:class:`.CheckResult` Object`: The return value meaning depends on the ``version`` parameter. If it was:
* defined:
    * :py:attr:`.CheckStatus.SUCCESS` when the installed Content DB is at least the same as the version passed as a parameter.
    * :py:attr:`.CheckStatus.FAIL` when the installed Content DB version is lower than the version passed as a parameter.
* not defined:
    * :py:attr:`.CheckStatus.SUCCESS` when the installed Content DB is the latest one.
    * :py:attr:`.CheckStatus.FAIL` when the installed Content DB is not the latest one.

### check\_ntp\_synchronization

```python
def check_ntp_synchronization() -> CheckResult
```

Check synchronization with NTP server.

**Returns**:

`:class:`.CheckResult``: * :attr:`.CheckStatus.SUCCESS` when a device is synchronized with the NTP server.
* :attr:`.CheckStatus.FAIL` when a device is not synchronized with the NTP server.
* :attr:`.CheckStatus.ERROR` when a device is not configured for NTP synchronization.

### check\_arp\_entry

```python
def check_arp_entry(ip: Optional[str] = None,
                    interface: Optional[str] = None) -> CheckResult
```

Check if a given ARP entry is available in the ARP table.

**Arguments**:

- `interface` (`str, optional`): (defaults to ``None``) A name of an interface we examine for the ARP entries. When skipped, all interfaces are examined.
- `ip` (`str, optional`): (defaults to ``None``) IP address of the ARP entry we look for.

**Returns**:

`:class:`.CheckResult``: * :attr:`.CheckStatus.SUCCESS` when the ARP entry is found.
* :attr:`.CheckStatus.FAIL` when the ARP entry is not found.
* :attr:`.CheckStatus.SKIPPED` when ``ip`` is not provided.
* :attr:`.CheckStatus.ERROR` when the ARP table is empty.

### check\_ipsec\_tunnel\_status

```python
def check_ipsec_tunnel_status(
        tunnel_name: Optional[str] = None) -> CheckResult
```

Check if a given IPSec tunnel is in active state.

**Arguments**:

- `tunnel_name`: (defaults to ``None``) Name of the searched IPSec tunnel.

**Returns**:

`:class:`.CheckResult``: * :attr:`.CheckStatus.SUCCESS` when a tunnel is found and is in active state.
* :attr:`.CheckStatus.FAIL` when a tunnel is either not active or missing in the current configuration.
* :attr:`.CheckStatus.SKIPPED` when ``tunnel_name`` is not provided.
* :attr:`.CheckStatus.ERROR` when no IPSec tunnels are configured on the device.

### check\_free\_disk\_space

```python
def check_free_disk_space(image_version: Optional[str] = None) -> CheckResult
```

Check if a there is enough space on the ``/opt/panrepo`` volume for downloading an PanOS image.

This is a check intended to be run before the actual upgrade process starts.

The method operates in two modes:

    * default - to be used as last resort, it will verify that the ``/opt/panrepo`` volume has at least 3GB free space available. This amount of free space is somewhat arbitrary and it&#x27;s based maximum image sizes (path level + base image) available at the time the method was written (+ some additional error margin).
    * specific target image - suggested mode, it will take one argument ``image_version`` which is the target PanOS version. For that version the actual image size (path + base image) will be calculated. Next, the available free space is verified against that image size + 10% (as an error margin).

**Arguments**:

- `image_version`: (defaults to ``None``) Version of the target PanOS image.

**Returns**:

`:class:`.CheckResult``: * :attr:`.CheckStatus.SUCCESS` when there is enough free space to download an image.
* :attr:`.CheckStatus.FAIL` when there is NOT enough free space, additionally the actual free space available is provided as the fail reason.

### check\_mp\_dp\_sync

```python
def check_mp_dp_sync(diff_threshold: int = 0) -> CheckResult
```

Check if the Data and Management clocks are in sync.

**Arguments**:

- `diff_threshold`: (defaults to ``0``) Maximum allowable difference in seconds between both clocks.

**Returns**:

`:class:`.CheckResult``: * :attr:`.CheckStatus.SUCCESS` when both clocks are the same or within threshold.
* :attr:`.CheckStatus.FAIL` when both clocks differ.

### get\_content\_db\_version

```python
def get_content_db_version() -> Dict[str, str]
```

Get Content DB version.

**Returns**:

`dict`: To keep the standard of all ``get`` methods returning a dictionary. This value is also returned as a dictionary in the following format:
::

    {
        &#x27;version&#x27;: &#x27;xxxx-yyyy&#x27;
    }

### get\_ip\_sec\_tunnels

```python
def get_ip_sec_tunnels() -> Dict[str, Union[str, int]]
```

Extract information about IPSEC tunnels from all tunnel data retrieved from a device.

**Returns**:

`dict`: Currently configured IPSEC tunnels.
The returned value is similar to the example below. It can differ though depending on the version of PanOS:

::

    {
        &quot;tunnel_name&quot;: {
            &quot;peerip&quot;: &quot;10.26.129.5&quot;,
            &quot;name&quot;: &quot;tunnel_name&quot;,
            &quot;outer-if&quot;: &quot;ethernet1/2&quot;,
            &quot;gwid&quot;: &quot;1&quot;,
            &quot;localip&quot;: &quot;0.0.0.0&quot;,
            &quot;state&quot;: &quot;init&quot;,
            &quot;inner-if&quot;: &quot;tunnel.1&quot;,
            &quot;mon&quot;: &quot;off&quot;,
            &quot;owner&quot;: &quot;1&quot;,
            &quot;id&quot;: &quot;1&quot;
        }
    }

### run\_readiness\_checks

```python
def run_readiness_checks(
        checks_configuration: Optional[List[Union[str, dict]]] = None,
        report_style: bool = False) -> Union[Dict[str, dict], Dict[str, str]]
```

Run readiness checks.

This method provides a convenient way of running readiness check methods.

**Arguments**:

- `checks_configuration`: (defaults to ``None``) A list of readiness checks to run with an optional configuration.
This list is defined using the :class:`.ConfigParser` class `dialect`_. For details, refer to the documentation for this class. 

Elements of this list can be either of the ``str`` or ``dict`` type:

    * ``str`` - the element simply specifies the name of a check to run.
    * ``dict`` - the element contains the check name and a configuration (if a particular check requires one); the dictionary format is as follows:

        ::

            {
                &#x27;check_name&#x27;: {
                    &#x27;config_name&#x27;: &#x27;config_value&#x27;
                    &#x27;config2_name&#x27;: &#x27;config2_value&#x27;
                }
            }

        Refer to the :ref:`readiness_docs` documentation for details on each check configuration.

Following :class:`.ConfigParser` `dialect`_, when no configuration is provided, the **all** checks are triggered. *Notice* that in this situation checks that require configuration to run will return :attr:`.CheckStatus.SKIPPED`.

Example of the ``checks_configuration`` parameter:

::

    [
        &#x27;all&#x27;,
        &#x27;!ha&#x27;,
        {&#x27;content_version&#x27;: {&#x27;version&#x27;: &#x27;8634-7678&#x27;}}
    ]

This is interpreted as: run all checks, except for the HA status verification and override the Content DB version check to check for the minimum version of 8634-7678.
- `report_style` (`bool`): (defaults to ``False``) Changes the output to more descriptive. Can be used directly when generating a report.

**Raises**:

- `WrongDataTypeException`: An exception is raised when the configuration is in a data type different then ``str`` or ``dict``.

**Returns**:

`dict`: The format differs depending on the value of the ``report_style`` parameter. If the value is:
* ``False`` (default): results of executed checks are formatted as ``dict``, where keys are check names as passed in ``checks_configuration`` and values are dictionaries containing two keys:

    * ``state``: a ``bool`` representation of the :class:`.CheckResult` class for a particular check.
    * ``reason``:  a ``str`` representation of the :class:`.CheckResult` class for a particular check.

    Assuming that we run the checks with the following configuration:

    ::

        [
            &#x27;ha&#x27;,
            &#x27;panorama&#x27;,
        ]

    The return ``dict`` should look as follows:

    ::

        {
            &#x27;ha&#x27;: {
                &#x27;state&#x27;: False
                &#x27;reason&#x27;: &#x27;[FAIL] Device configuration is not synchronized between the nodes.&#x27;
            }
            &#x27;candidate_config&#x27;: {
                &#x27;state&#x27;: True
                &#x27;reason&#x27;: &#x27;[SUCCESS]&#x27;
            }
        }

* ``True``: results are also formatted as ``dict`` with the keys corresponding to checks names, but values are a string representations of the :class:`.CheckResult` class.

    For the above example of checks, the result would be similar to:

    ::

        {
            &#x27;ha&#x27;: &#x27;[FAIL] Device configuration is not synchronized between the nodes.&#x27;
            &#x27;candidate_config&#x27;: &#x27;[SUCCESS].&#x27;
        }

### run\_snapshots

```python
def run_snapshots(
    snapshots_config: Optional[List[Union[str,
                                          dict]]] = None) -> Dict[str, dict]
```

Run snapshots of different firewall areas&#x27; states.

This method provides a convenient way of running snapshots of a device state.

**Arguments**:

- `snapshots_config`: (defaults to ``None``) Defines snapshots of which areas will be taken.
This list is specified in :class:`.ConfigParser` class`dialect`_. For details, refer to the documentation for this class.
Following that`dialect`_, when no list is passed, **all** state snapshots are made.

On the contrary to ``run_readiness_checks``, it is not possible to configure a snapshot. One can only specify which type of data should be captured.
That&#x27;s why, below there is a list of strings only. Refer to the :ref:`snapshot_docs` documentation for details on the currently available snapshot areas.

**Raises**:

- `WrongDataTypeException`: An exception is raised when the configuration in a data type is different than in a string.

**Returns**:

`dict`: The results of the executed snapshots are formatted as a dictionary where:
* keys are state areas as passed in ``snapshot_config`` parameter,
* values are dictionaries with the actual data.

    Each dictionary can have a different structure. The structure depends on the nature of data we want to capture.
    See the :ref:`snapshot_docs` documentation to refer to the methods used to take snapshots of a particular area. The documentation for these methods inludes details on the actual structure of results.

The sample output containing a snapshot for route tables, licenses, and IPSec tunnels is shown below (one element per each area):

.. code-block:: python

    {
        &quot;ip_sec_tunnels&quot;: {
            &quot;ipsec_tun&quot;: {
                &quot;peerip&quot;: &quot;10.26.129.5&quot;,
                &quot;name&quot;: &quot;ipsec_tun&quot;,
                &quot;outer-if&quot;: &quot;ethernet1/2&quot;,
                &quot;gwid&quot;: &quot;1&quot;,
                &quot;localip&quot;: &quot;0.0.0.0&quot;,
                &quot;state&quot;: &quot;init&quot;,
                &quot;inner-if&quot;: &quot;tunnel.1&quot;,
                &quot;mon&quot;: &quot;off&quot;,
                &quot;owner&quot;: &quot;1&quot;,
                &quot;id&quot;: &quot;1&quot;
            },
        }.
        &quot;routes&quot;: {
            &quot;default_0.0.0.0/0_ethernet1/3&quot;: {
                &quot;virtual-router&quot;: &quot;default&quot;,
                &quot;destination&quot;: &quot;0.0.0.0/0&quot;,
                &quot;nexthop&quot;: &quot;10.26.129.129&quot;,
                &quot;metric&quot;: &quot;10&quot;,
                &quot;flags&quot;: &quot;A S&quot;,
                &quot;age&quot;: null,
                &quot;interface&quot;: &quot;ethernet1/3&quot;,
                &quot;route-table&quot;: &quot;unicast&quot;
            },
        },
        &quot;license&quot;: {
            &quot;DNS Security&quot;: {
                &quot;feature&quot;: &quot;DNS Security&quot;,
                &quot;description&quot;: &quot;Palo Alto Networks DNS Security License&quot;,
                &quot;serial&quot;: &quot;007257000334668&quot;,
                &quot;issued&quot;: &quot;November 08, 2022&quot;,
                &quot;expires&quot;: &quot;November 01, 2023&quot;,
                &quot;expired&quot;: &quot;no&quot;,
                &quot;base-license-name&quot;: &quot;PA-VM&quot;,
                &quot;authcode&quot;: null
            },
        }
    }


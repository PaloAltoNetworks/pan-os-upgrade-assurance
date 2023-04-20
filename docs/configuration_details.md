# Configuration details

This documentation represents the current state of the available checks
and snapshot state areas, along with the instructions on how to
configure them properly.


Table of contents

- [Passing configuration in general](#passing-configuration-in-general)
- [Readiness checks](#readiness-checks)
- [State snapshots](#state-snapshots)
- [Reports](#reports)

## Passing configuration in general

For most use cases, all checks, snapshots and reports (entities in
general) are triggered by a common method, which:

-   takes a list of checks, snapshots, reports (entities) that one would
    like to run,
-   does initial list verification,
-   picks up a proper method to run a specific entity,
-   aggregates and presents the results in a form of a dictionary, where
    keys represent requested entities.

The list of entities can be just a list, but it can also follow the
`.ConfigParser`{.interpreted-text role="class"} dialect. For more
details, refer to the documentation for this class. The most important
is that this dialect supports two types of elements in the list: `str`
and `dict`, where:

-   `str` represents just an entity name such as a check, snapshot or
    report to run,
-   `dict` (always single key:value pair allowed) represents the element
    name (key) and additional configuration (value) that will be passed
    to the method matching the particular element. This configuration is
    also passed as `dict`.

In the next sections of this documentation, the following aspects are
covered:

-   a common method with full configuration (where applicable),
-   each entity available in a particular section with some basic
    information and a link to a method that is actually run. For
    details, see documentation for methods.

*Note:* Each entity is documented under its own section where the
section name is the entity name.

## Readiness checks

Readiness checks represent checks that are `boolean` in nature. A result
of such checks always presents a `True`/`False` value with some
explanation in case of check fails. They can be triggered with a common
method: `.CheckFirewall.run_readiness_checks`{.interpreted-text
role="meth"}. For the format of a returned value, see documentation for
methods.

The list of checks to run is passed using the `checks_configuraton`
parameter and it looks as follows:

``` python
[
    'panorama',
    'ntp_sync',
    'candidate_config',
    'expired_licenses',
    # tests below have optional configuration
    {'content_version': {'version': '8634-7678'}},
    {'free_disk_space': {'image_version': '10.1.6-h6'}},
    {'ha': {'skip_config_sync': True}},
    # tests below require additional configuration
    {'session_exist': {
        'source': '134.238.135.137',
        'destination': '10.1.0.4',
        'dest_port': '80'
    }},
    {'arp_entry_exist': {'ip': '10.0.1.1'} },
    {'ip_sec_tunnel_status': {
        'tunnel_name': 'ipsec_tun'
    }}
]
```

Please see the sections below for details of each check:

- [arp_entry_exist](#arp_entry_exist)
- [candidate_config](#candidate_config)
- [content_version](#content_version)
- [free_disk_space](#free_disk_space)
- [expired_licenses](#expired_licenses)
- [ha](#ha)
- [ip_sec_tunnel_status](#ip_sec_tunnel_status)
- [ntp_sync](#ntp_sync)
- [panorama](#panorama)
- [session_exist](#session_exist)

### `arp_entry_exist`

Checks if a specified ARP entry exists.

#### Method

`.CheckFirewall.check_arp_entry`{.interpreted-text role="meth"}

#### Configuration parameters

  paramter      description
  ------------- ------------------------------------------------------------------------
  `ip`          IP address we look for
  `interface`   (optional) network interface name we would like to limit the search to

#### Sample configuration

``` python
# with lookup limited to a single interface
{
    'ip': '10.0.1.1'
    'interface': 'ethernet1/1'
}

# with a lookup in all ARP entries
{
    'ip': '10.0.0.6'
}
```

### `candidate_config`

Verifies if there are any changes on the device pending to be committed.
This can be either a loaded named config which requires a full commit or
just some small changes made manually or with an CLI/API.

Does not require configuration.

#### Method

`.CheckFirewall.check_pending_changes`{.interpreted-text role="meth"}

### `content_version`

Compares currently installed Content DB version against either:

-   the latest available version if no config is passed,
-   specified versions if one config is passed.

#### Method

`.CheckFirewall.check_content_version`{.interpreted-text role="meth"}

#### Configuration parameters

  paramter    description
  ----------- ----------------------------------------------------------------------
  `version`   (optional) a minimum Content DB version that would satisfy the check

#### Sample configuration

``` python
{
    'version': '6453-5673'
}
```

### `free_disk_space`

Checks if there is enough free space on the `/opt/panrepo` volume to
download a PanOS image before an upgrade.

#### Method

`.CheckFirewall.check_free_disk_space`{.interpreted-text role="meth"}

#### Configuration parameters

  paramter          description
  ----------------- ------------------------------------------------------------------------------------------------------
  `image_version`   (optional) target PanOS version to calculate required free space, when skipped arbitrary 3GB is used

#### Sample configuration

``` python
{
    'image_version': '10.1.6-h3'
}
```

### `expired_licenses`

Checks and reports expired licenses.

Does not require configuration.

#### Method

`.CheckFirewall.check_expired_licenses`{.interpreted-text role="meth"}

### `ha`

Verifies if an HA pair is in a correct state. Only Active-Passive
configuration is supported at the moment.

#### Method

`.CheckFirewall.check_ha_status`{.interpreted-text role="meth"}

#### Configuration parameters

  paramter             description
  -------------------- -----------------------------------------------------------------------
  `skip_config_sync`   Flag to skip (`True`) configuration sync state between HA pair nodes.

#### Sample configuration

``` python
{
    'skip_config_sync': True
}
```

### `ip_sec_tunnel_status`

Verifies if a given IPSec tunnel is in active state.

#### Method

`.CheckFirewall.check_ipsec_tunnel_status`{.interpreted-text
role="meth"}

#### Configuration parameters

  paramter        description
  --------------- ----------------------------------------------------------------
  `tunnel_name`   A name of an IPSec tunnel which status we would like to verify

#### Sample configuration

``` python
{
    'tunnel_name': 'ipsec_tunnel'
}
```

`ntp_sync` \-\-\-\-\-\-\-\-\-\--

Verify if time on a device is synchronized with an NTP server. This
check fails if no NTP synchronization is configured.

Does not require configuration.

#### Method

`.CheckFirewall.check_ntp_synchronization`{.interpreted-text
role="meth"}

### `panorama`

Check if a device is connected to the Panorama server. This check fails
if no Panorama configuration is present on a device.

Does not require configuration.

#### Method

`.CheckFirewall.check_panorama_connectivity`{.interpreted-text
role="meth"}

### `session_exist`

Does a lookup in a sessions table for a named session. This check is
appropriate for verifying if a critical session was established after a
device upgrade/reboot.

#### Method

`.CheckFirewall.check_critical_session`{.interpreted-text role="meth"}

#### Configuration parameters

  paramter        description
  --------------- ---------------------------------------------------
  `source`        IP address from which the session was established
  `destination`   IP address to which the session was established
  `dest_port`     Target destination port

#### Sample configuration

``` python
{
    'source': '134.238.135.137',
    'destination': '10.1.0.4',
    'dest_port': '80'
}
```

## State snapshots

State snapshots store information about the state of a particular device
area. They do not take any configurations. They store every possible
information about an area. Use reports or custom code to extract a
subset of information if required.

They can be triggered using a common method:
`.CheckFirewall.run_snapshots`{.interpreted-text role="meth"}. For the
format of a returned value, see documentation for methods.

The state areas to take snapshots of are passed using the
`snapshots_config` parameter. As no additional configuration is passed,
it makes that parameter simply a list of state areas:

``` python
[
    'nics',
    'routes',
    'license',
    'arp_table',
    'content_version',
    'session_stats',
    'ip_sec_tunnels',
]
```

Please see the sections below for details of each state snapshot:

::: {.contents local="" backlinks="entry" depth="1"}
:::

### `arp_table`

Makes a snapshot of ARP table.

Method used: `.FirewallProxy.get_arp_table`{.interpreted-text
role="meth"}.

### `content_version`

Grabs the currently installed Content DB version.

Method used: `.CheckFirewall.get_content_db_version`{.interpreted-text
role="meth"}.

### `ip_sec_tunnels`

Takes a snapshot of configuration of all IPSec tunnels along with their
state.

Method used: `.CheckFirewall.get_ip_sec_tunnels`{.interpreted-text
role="meth"}.

### `license`

Takes a snapshot of information about all licenses installed on a
device.

Method used: `.FirewallProxy.get_licenses`{.interpreted-text
role="meth"}.

### `nics` {#nics_snapshot}

Takes a snapshot of a state of all configured (not installed) network
interfaces.

Method used: `.FirewallProxy.get_nics`{.interpreted-text role="meth"}.

### `routes`

Takes a snapshot of the Route Table (this includes routes populated from
DHCP as well as manually entered ones).

Method used: `.FirewallProxy.get_routes`{.interpreted-text role="meth"}.

### `session_stats`

Gets information about the session statistics, such as current sessions
count per a session type (TCP, UDP, etc).

Method used: `.FirewallProxy.get_session_stats`{.interpreted-text
role="meth"}.

## Reports

The reporting part is actually the result of comparison of two
snapshots. It\'s advised to run reports using the common method as some
of the comparison results are calculated with it. The common method is:
`.SnapshotCompare.compare_snapshots`{.interpreted-text role="meth"}.

Each report can be run with default or custom configuration. The
following example shows reports with additional configuration (where
applicable):

``` python
[
    {'ip_sec_tunnels: {
        'properties': ['state']
    }},
    {'arp_table': {
        'properties': ['!ttl'],
        'count_change_threshold': 10
    }},
    {'nics': {
        'count_change_threshold': 10
    }},
    {'license': {
        'properties': ['!serial']
    }},
    {'routes: {
        'properties': ['!flags'],
        'count_change_threshold': 10
    }},
    'content_version',
    {'session_stats': {
        'thresholds': [
            {'num-max': 10},
            {'num-tcp': 10},
        ]
    }}
]
```

For most reports, a generic comparison method is used
(`.SnapshotCompare.get_diff_and_threshold`{.interpreted-text
role="meth"}). It produces the \_[standardized dictionary]{.title-ref}.
For details, see documentation for this method. Common method assigns a
report result to a report area providing a dictionary where keys are
report areas and values are report results.

For details on which configuration can be passed, check each report area
below (for each report, we will explain the above-mentioned
configuration):

::: {.contents local="" backlinks="entry" depth="1"}
:::

### `arp_table`

Runs comparison of ARP tables snapshots.

#### Method

`.SnapshotCompare.get_diff_and_threshold`{.interpreted-text role="meth"}

#### Configuration parameters

+------------------+---------------------------------------------------+
| parameter        | description                                       |
+==================+===================================================+
| | `properties`   | | (optional) a set of properties to skip when     |
| |                |   comparing two ARP table entries,                |
|                  | | all properties are checked when this parameter  |
|                  |   is skipped                                      |
+------------------+---------------------------------------------------+
| | `count_c       | | (optional) maximum difference percentage of     |
| hange_threshold` |   changed entries in ARP table                    |
| |                | | in both snapshots, skipped when this property   |
|                  |   is not specified                                |
+------------------+---------------------------------------------------+

#### Sample configuration

The following configuration:

-   compares ARP table entries between both snapshots, but when
    comparing two entries the `ttl` parameter is not taken into
    consideration,
-   calculates the count of changed ARP table entries from both
    snapshots and marks comparison as failed if the difference is bigger
    than 10%.

This report produces the [standardized dictionary]().

``` python
{
    'properties': ['!ttl'],
    'count_change_threshold': 10
}
```

### `content_version`

This is one of a few checks that does not take any configuration. It
simply compares Content DB version from both snapshots. Results are
presented as the [standardized dictionary]().

#### Method

`.SnapshotCompare.get_diff_and_threshold`{.interpreted-text role="meth"}

### `ip_sec_tunnels`

Compares configuration and the state of IPSec tunnels.

#### Method

`.SnapshotCompare.get_diff_and_threshold`{.interpreted-text role="meth"}

#### Configuration parameters

+-------------------+--------------------------------------------------+
| parameter         | description                                      |
+===================+==================================================+
| | `properties`    | | (optional) a set of properties to skip when    |
| |                 |   comparing two IPSec tunnels,                   |
|                   | | all properties are checked when this parameter |
|                   |   is skipped                                     |
+-------------------+--------------------------------------------------+
| | `count_         | | (optional) maximum difference percentage of    |
| change_threshold` |   changed IPSec tunnels                          |
| |                 | | in both snapshots, skipped when this property  |
|                   |   is not specified                               |
+-------------------+--------------------------------------------------+

#### Sample configuration

The following configuration compares the state of IPSec tunnels as
captured in snapshots.

This report produces the [standardized dictionary]().

``` python
{
    'properties': ['state']
}
```

### `license`

Compares installed licenses. This report does not only check if we have
the same set of licenses in both snapshots but also compares license
details, such as expiration date, etc.

#### Method

`.SnapshotCompare.get_diff_and_threshold`{.interpreted-text role="meth"}

#### Configuration parameters

+--------------------+-------------------------------------------------+
| parameter          | description                                     |
+====================+=================================================+
| | `properties`     | | (optional) a set of properties to skip when   |
| |                  |   comparing two licenses,                       |
|                    | | all properties are checked when this          |
|                    |   parameter is skipped                          |
+--------------------+-------------------------------------------------+
| | `count           | | (optional) maximum difference percentage of   |
| _change_threshold` |   changed licenses                              |
| |                  | | in both snapshots, skipped when this property |
|                    |   is not specified                              |
+--------------------+-------------------------------------------------+

#### Sample configuration

Following configuration is set to compare licenses as captured in
snapshots. It will ignore the `serial` property.

This report produces the [standardized dictionary]().

``` python
{
    'properties': ['!serial']
}
```

### `nics`

Provides a report on status of network interfaces. This report is
limited to information about network interfaces available in the
snapshots. See the `nics_snapshot`{.interpreted-text role="ref"}
snapshot information for details.

At the moment of writing this documentation, the snapshot contains only
interface state information. Despite the fact that we use the generic
method for preparing this report, the only reasonable parameter to use
is `count_change_threshold`.

#### Method

`.SnapshotCompare.get_diff_and_threshold`{.interpreted-text role="meth"}

#### Configuration parameters

+-------------------+--------------------------------------------------+
| parameter         | description                                      |
+===================+==================================================+
| | `count_         | | (optional) maximum difference percentage of    |
| change_threshold` |   changed network interfaces                     |
| |                 | | in both snapshots, skipped when this property  |
|                   |   is not specified                               |
+-------------------+--------------------------------------------------+

#### Sample configuration

The following configuration provides both: change in NICs\' state
(implicitly) and maximum difference in NICs count (fail threshold is
10%).

This report produces the [standardized dictionary]().

``` python
{
    'count_change_threshold': 10
}
```

### `routes`

Provides a report on differences between Route Table entries. It
includes:

-   availability of a route in one of the snapshots,
-   for routes available in two snapshots, difference in route
    properties, such as age, next hop, etc.

#### Method

`.SnapshotCompare.get_diff_and_threshold`{.interpreted-text role="meth"}

#### Configuration parameters

+-------------------+--------------------------------------------------+
| parameter         | description                                      |
+===================+==================================================+
| | `properties`    | | (optional) a set of properties to skip when    |
| |                 |   comparing two routes,                          |
|                   | | all properties are checked when this parameter |
|                   |   is skipped                                     |
+-------------------+--------------------------------------------------+
| | `count_         | | (optional) maximum difference percentage of    |
| change_threshold` |   changed entries routes                         |
| |                 | | in both snapshots, skipped when this property  |
|                   |   is not specified                               |
+-------------------+--------------------------------------------------+

#### Sample configuration

The following configuration:

-   compares Route Table entries between both snapshots, but when
    comparing two entries the `flags` parameter is not taken into
    consideration,
-   calculates the count of changed Route Table entries from both
    snapshots and marks comparison as failed if the difference is bigger
    than 10%.

This report produces the [standardized dictionary]().

``` python
{
    'properties': ['!flags'],
    'count_change_threshold': 10
}
```

### `session_stats`

This report is slightly different than reports made with the
`.SnapshotCompare.get_diff_and_threshold`{.interpreted-text role="meth"}
method as the snapshot data is different (refer to the
`.FirewallProxy.get_session_stats`{.interpreted-text role="meth"} method
documentation for details).

It takes one parameter only: `thresholds`. It contains a list of
sessions stats as available in the snapshot. For each stat a threshold
value is provided. This report calculates a change in the session
statistics and compares it to the threshold value. This parameter does
not have a default value - when skipped the report gives no results.

#### Method

`.SnapshotCompare.get_count_change_percentage`{.interpreted-text
role="meth"}

#### Configuration parameters

  -----------------------------------------------------------------------
  parameter       description
  --------------- -------------------------------------------------------
  `thresholds`    a list of sessions with change threshold value to
                  analyze

  -----------------------------------------------------------------------

#### Sample configuration

The following configuration compares only stats for `num-max` and
`num-tcp`. For both, the accepted difference is 10%.

This report produces a `dict` as documented in the
`.SnapshotCompare.get_count_change_percentage`{.interpreted-text
role="meth"} method documentation.

``` python
{
    'thresholds': [
        {'num-max': 10},
        {'num-tcp': 10},
    ]
}
```

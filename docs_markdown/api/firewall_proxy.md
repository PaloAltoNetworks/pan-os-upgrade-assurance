---
sidebar_label: firewall_proxy
title: firewall_proxy
---

## CommandRunFailedException

```python
class CommandRunFailedException(Exception)
```

Used when a command run on a device does not return the ``success`` status.

## MalformedResponseException

```python
class MalformedResponseException(Exception)
```

A generic exception class used when a response does not meet the expected standards.

## ContentDBVersionsFormatException

```python
class ContentDBVersionsFormatException(Exception)
```

Used when parsing Content DB versions fail due to an unknown version format (assuming ``XXXX-YYYY``).

## PanoramaConfigurationMissingException

```python
class PanoramaConfigurationMissingException(Exception)
```

Used when checking Panorama connectivity on a device that was not configured with Panorama.

## WrongDiskSizeFormatException

```python
class WrongDiskSizeFormatException(Exception)
```

Used when parsing free disk size information.

## FirewallProxy

```python
class FirewallProxy(Firewall)
```

Class representing a Firewall.

Proxy in this class means that it is between the *high level* :class:`.CheckFirewall` class and a device itself.
Inherits the Firewall_ class but adds methods to interpret XML API commands. The class constructor is also inherited from the Firewall_ class.

All interaction with a device are read-only. Therefore, a less privileged user can be used.

All methods starting with ``is_`` check the state, they do not present any data besides simple ``boolean``values.

All methods starting with `get_` fetch data from a device by running a command and parsing the output. 
The return data type can be different depending on what kind of information is returned from a device.

.. _Firewall: https://pan-os-python.readthedocs.io/en/latest/module-firewall.html#module-panos.firewall

### op\_parser

```python
def op_parser(cmd: str,
              cmd_in_xml: Optional[bool] = False,
              return_xml: Optional[bool] = False) -> Union[dict, ET.Element]
```

Execute a command on node, parse, and return response.

This is just a wrapper around the `Firewall.op`_ method. It additionally does basic error handling and tries to extract the actual device response.

**Arguments**:

- `cmd` (`str`): The actual XML API command to be run on the device. Can be either a free form or an XML formatted command.
- `cmd_in_xml` (`bool`): (defaults to ``False``) Set to ``True`` if the command is XML-formatted.
- `return_xml` (`bool`): (defaults to ``False``) When set to ``True``, the return data is an ``XML object``_ instead of a python dictionary.

**Raises**:

- `CommandRunFailedException`: An exception is raised if the command run status returned by a device is not successful.
- `MalformedResponseException`: An exception is raised when a response is not parsable, no ``result`` element is found in the XML response.

**Returns**:

`dict, xml.etree.ElementTree.Element
.. _Firewall.op: https://pan-os-python.readthedocs.io/en/latest/module-firewall.html#panos.firewall.Firewall.op
.. _XML object: https://docs.python.org/3/library/xml.etree.elementtree.html#xml.etree.ElementTree.Element`: The actual command output. A type is defined by the ``return_xml`` parameter.

### is\_pending\_changes

```python
def is_pending_changes() -> bool
```

Get information if there is a candidate configuration pending to be committed.

The actual API command run is ``check pending-changes``.

**Returns**:

`bool`: ``True`` when there are pending changes, ``False`` otherwise.

### is\_full\_commit\_required

```python
def is_full_commit_required() -> bool
```

Get information if a full commit is required, for example, after loading a named config.

The actual API command run is ``check full-commit-required``.

**Returns**:

`bool`: ``True`` when a full commit is required, ``False`` otherwise.

### is\_panorama\_configured

```python
def is_panorama_configured() -> bool
```

Check if a device is configured with Panorama.

The actual API command run is ``show panorama-status``.

**Returns**:

`bool`: ``True`` when Panorama IPs are configured, ``False`` otherwise.

### is\_panorama\_connected

```python
def is_panorama_connected() -> bool
```

Get Panorama connectivity status.

The actual API command run is ``show panorama-status``.

An output of this command is usually a string. This method is responsible for parsing this string and trying to extract information if at least one of the Panoramas configured is connected.

**Raises**:

- `PanoramaConfigurationMissingException`: Exception being raised when this check is run against a device with no Panorama configured.
- `MalformedResponseException`: Exception being raised when response from device does not meet required format.
Since the response is a string (that we need to parse) this method expects a strict format. For single Panorama this is:

.. code-block:: python

    Panorama Server 1 : 1.2.3.4
        Connected     : no
        HA state      : disconnected

For two Panoramas (HA pair for example) those are just two blocks:

.. code-block:: python

    Panorama Server 1 : 1.2.3.4
        Connected     : no
        HA state      : disconnected
    Panorama Server 2 : 5.6.7.8
        Connected     : yes
        HA state      : disconnected

If none of this formats is met, this exception is thrown.

**Returns**:

`bool`: ``True`` when connection is up, ``False`` otherwise.

### get\_ha\_configuration

```python
def get_ha_configuration() -> dict
```

Get high-availability configuration status.

The actual API command is ``show high-availability state``.

**Returns**:

`dict`: Information about HA pair and its status as retrieved from the current (local) device.
Sample output:

::

    {
        &#x27;enabled&#x27;: &#x27;yes&#x27;,
        &#x27;group&#x27;: {
            &#x27;link-monitoring&#x27;: {
                &#x27;enabled&#x27;: &#x27;yes&#x27;,
                &#x27;failure-condition&#x27;: &#x27;any&#x27;,
                &#x27;groups&#x27;: None
            },
            &#x27;local-info&#x27;: {
                &#x27;DLP&#x27;: &#x27;Match&#x27;,
                &#x27;VMS&#x27;: &#x27;Match&#x27;,
                &#x27;active-passive&#x27;: {
                    &#x27;monitor-fail-holddown&#x27;: &#x27;1&#x27;,
                    &#x27;passive-link-state&#x27;: &#x27;shutdown&#x27;
                },
                &#x27;addon-master-holdup&#x27;: &#x27;500&#x27;,
                &#x27;app-compat&#x27;: &#x27;Match&#x27;,
                &#x27;app-version&#x27;: &#x27;xxxx-yyyy&#x27;,
                &#x27;av-compat&#x27;: &#x27;Match&#x27;,
                &#x27;av-version&#x27;: &#x27;0&#x27;,
                &#x27;build-compat&#x27;: &#x27;Match&#x27;,
                &#x27;build-rel&#x27;: &#x27;10.2.3&#x27;,
                &#x27;gpclient-compat&#x27;: &#x27;Match&#x27;,
                &#x27;gpclient-version&#x27;: &#x27;Not Installed&#x27;,
                &#x27;ha1-encrypt-enable&#x27;: &#x27;no&#x27;,
                &#x27;ha1-encrypt-imported&#x27;: &#x27;no&#x27;,
                &#x27;ha1-gateway&#x27;: &#x27;10.0.0.1&#x27;,
                &#x27;ha1-ipaddr&#x27;: &#x27;10.0.0.10/24&#x27;,
                &#x27;ha1-link-mon-intv&#x27;: &#x27;3000&#x27;,
                &#x27;ha1-macaddr&#x27;: &#x27;xx:xx:xx:xx:xx:xx&#x27;,
                &#x27;ha1-port&#x27;: &#x27;management&#x27;,
                &#x27;ha2-gateway&#x27;: &#x27;10.0.3.1&#x27;,
                &#x27;ha2-ipaddr&#x27;: &#x27;10.0.3.10/24&#x27;,
                &#x27;ha2-macaddr&#x27;: &#x27;xx:xx:xx:xx:xx:xx&#x27;,
                &#x27;ha2-port&#x27;: &#x27;ethernet1/3&#x27;,
                &#x27;heartbeat-interval&#x27;: &#x27;10000&#x27;,
                &#x27;hello-interval&#x27;: &#x27;10000&#x27;,
                &#x27;iot-compat&#x27;: &#x27;Match&#x27;,
                &#x27;iot-version&#x27;: &#x27;yy-zzz&#x27;,
                &#x27;max-flaps&#x27;: &#x27;3&#x27;,
                &#x27;mgmt-ip&#x27;: &#x27;10.0.0.10/24&#x27;,
                &#x27;mgmt-ipv6&#x27;: None,
                &#x27;mode&#x27;: &#x27;Active-Passive&#x27;,
                &#x27;monitor-fail-holdup&#x27;: &#x27;0&#x27;,
                &#x27;nonfunc-flap-cnt&#x27;: &#x27;0&#x27;,
                &#x27;platform-model&#x27;: &#x27;PA-VM&#x27;,
                &#x27;preempt-flap-cnt&#x27;: &#x27;0&#x27;,
                &#x27;preempt-hold&#x27;: &#x27;1&#x27;,
                &#x27;preemptive&#x27;: &#x27;no&#x27;,
                &#x27;priority&#x27;: &#x27;100&#x27;,
                &#x27;promotion-hold&#x27;: &#x27;20000&#x27;,
                &#x27;state&#x27;: &#x27;passive&#x27;,
                &#x27;state-duration&#x27;: &#x27;3675&#x27;,
                &#x27;state-sync&#x27;: &#x27;Complete&#x27;,
                &#x27;state-sync-type&#x27;: &#x27;ip&#x27;,
                &#x27;threat-compat&#x27;: &#x27;Match&#x27;,
                &#x27;threat-version&#x27;: &#x27;xxxx-yyyy&#x27;,
                &#x27;url-compat&#x27;: &#x27;Mismatch&#x27;,
                &#x27;url-version&#x27;: &#x27;0000.00.00.000&#x27;,
                &#x27;version&#x27;: &#x27;1&#x27;,
                &#x27;vm-license&#x27;: &#x27;VM-300&#x27;,
                &#x27;vm-license-compat&#x27;: &#x27;Match&#x27;,
                &#x27;vm-license-type&#x27;: &#x27;vm300&#x27;,
                &#x27;vpnclient-compat&#x27;: &#x27;Match&#x27;,
                &#x27;vpnclient-version&#x27;: &#x27;Not Installed&#x27;
            },
            &#x27;mode&#x27;: &#x27;Active-Passive&#x27;,
            &#x27;path-monitoring&#x27;: {
                &#x27;enabled&#x27;: &#x27;yes&#x27;,
                &#x27;failure-condition&#x27;: &#x27;any&#x27;,
                &#x27;virtual-router&#x27;: None,
                &#x27;virtual-wire&#x27;: None,
                &#x27;vlan&#x27;: None
            },
            &#x27;peer-info&#x27;: {
                &#x27;DLP&#x27;: &#x27;3.0.2&#x27;,
                &#x27;VMS&#x27;: &#x27;3.0.3&#x27;,
                &#x27;app-version&#x27;: &#x27;xxxx-yyyy&#x27;,
                &#x27;av-version&#x27;: &#x27;0&#x27;,
                &#x27;build-rel&#x27;: &#x27;10.2.3&#x27;,
                &#x27;conn-ha1&#x27;: {
                    &#x27;conn-desc&#x27;: &#x27;heartbeat status&#x27;,
                    &#x27;conn-primary&#x27;: &#x27;yes&#x27;,
                    &#x27;conn-status&#x27;: &#x27;up&#x27;
                },
                &#x27;conn-ha2&#x27;: {
                    &#x27;conn-desc&#x27;: &#x27;link status&#x27;,
                    &#x27;conn-ka-enbled&#x27;: &#x27;no&#x27;,
                    &#x27;conn-primary&#x27;: &#x27;yes&#x27;,
                    &#x27;conn-status&#x27;: &#x27;up&#x27;
                },
                &#x27;conn-status&#x27;: &#x27;up&#x27;,
                &#x27;gpclient-version&#x27;: &#x27;Not Installed&#x27;,
                &#x27;ha1-ipaddr&#x27;: &#x27;10.0.0.11&#x27;,
                &#x27;ha1-macaddr&#x27;: &#x27;xx:xx:xx:xx:xx:xx&#x27;,
                &#x27;ha2-ipaddr&#x27;: &#x27;10.0.3.11&#x27;,
                &#x27;ha2-macaddr&#x27;: &#x27;xx:xx:xx:xx:xx:xx&#x27;,
                &#x27;iot-version&#x27;: &#x27;yy-zzz&#x27;,
                &#x27;mgmt-ip&#x27;: &#x27;10.0.0.11/24&#x27;,
                &#x27;mgmt-ipv6&#x27;: None,
                &#x27;mode&#x27;: &#x27;Active-Passive&#x27;,
                &#x27;platform-model&#x27;: &#x27;PA-VM&#x27;,
                &#x27;preemptive&#x27;: &#x27;no&#x27;,
                &#x27;priority&#x27;: &#x27;100&#x27;,
                &#x27;state&#x27;: &#x27;active&#x27;,
                &#x27;state-duration&#x27;: &#x27;3680&#x27;,
                &#x27;threat-version&#x27;: &#x27;xxxx-yyyy&#x27;,
                &#x27;url-version&#x27;: &#x27;20230126.20142&#x27;,
                &#x27;version&#x27;: &#x27;1&#x27;,
                &#x27;vm-license&#x27;: &#x27;VM-300&#x27;,
                &#x27;vm-license-type&#x27;: &#x27;vm300&#x27;,
                &#x27;vpnclient-version&#x27;: &#x27;Not Installed&#x27;
            },
            &#x27;running-sync&#x27;: &#x27;synchronized&#x27;,
            &#x27;running-sync-enabled&#x27;: &#x27;yes&#x27;
        }
    }

### get\_nics

```python
def get_nics() -> dict
```

Get status of the configured network interfaces.

The actual API command run is ``show interface &quot;hardware&quot;``.

**Raises**:

- `MalformedResponseException`: Exception when no ``hw`` entry is available in the response.

**Returns**:

`dict`: Status of the configured network interfaces.
Sample output:

::

    {
        &#x27;ethernet1/1&#x27;: &#x27;down&#x27;, 
        &#x27;ethernet1/2&#x27;: &#x27;down&#x27;, 
        &#x27;ethernet1/3&#x27;: &#x27;up&#x27;
    }

### get\_licenses

```python
def get_licenses() -> dict
```

Get device licenses.

The actual API command is ``request license info``.

**Returns**:

`dict`: Licenses available on a device.
Sample output:

::

    {
        &#x27;AutoFocus Device License&#x27;: {
            &#x27;authcode&#x27;: &#x27;Snnnnnnn&#x27;,
            &#x27;base-license-name&#x27;: &#x27;PA-VM&#x27;,
            &#x27;description&#x27;: &#x27;AutoFocus Device License&#x27;,
            &#x27;expired&#x27;: &#x27;yes&#x27;,
            &#x27;expires&#x27;: &#x27;September 25, 2010&#x27;,
            &#x27;feature&#x27;: &#x27;AutoFocus Device License&#x27;,
            &#x27;issued&#x27;: &#x27;January 12, 2010&#x27;,
            &#x27;serial&#x27;: &#x27;xxxxxxxxxxxxxxxx&#x27;
        },
        &#x27;PA-VM&#x27;: {
            &#x27;authcode&#x27;: None,
            &#x27;description&#x27;: &#x27;Standard VM-300&#x27;,
            &#x27;expired&#x27;: &#x27;yes&#x27;,
            &#x27;expires&#x27;: &#x27;September 25, 2010&#x27;,
            &#x27;feature&#x27;: &#x27;PA-VM&#x27;,
            &#x27;issued&#x27;: &#x27;January 12, 2010&#x27;,
            &#x27;serial&#x27;: &#x27;xxxxxxxxxxxxxxxx&#x27;
        },
        ...
    }

### get\_routes

```python
def get_routes() -> dict
```

Get route table entries, either retrieved from DHCP or configured manually.

The actual API command is ``show routing route``.

**Returns**:

`dict`: Routes information.
The key in this dictionary is made of three route properties delimited with an underscore (``_``) in the following order:

    * virtual router name,
    * destination CIDR,
    * network interface name if one is available, empty string otherwise.

The key does not provide any meaningful information, it&#x27;s there only to introduce uniqueness for each entry. All properties that make a key are also available in the value of a dictionary element.

Sample output:

::

    {&#x27;
        private_0.0.0.0/0_private/i3&#x27;: {
            &#x27;age&#x27;: None,
            &#x27;destination&#x27;: &#x27;0.0.0.0/0&#x27;,
            &#x27;flags&#x27;: &#x27;A S&#x27;,
            &#x27;interface&#x27;: &#x27;private/i3&#x27;,
            &#x27;metric&#x27;: &#x27;10&#x27;,
            &#x27;nexthop&#x27;: &#x27;vr public&#x27;,
            &#x27;route-table&#x27;: &#x27;unicast&#x27;,
            &#x27;virtual-router&#x27;: &#x27;private&#x27;
        },
        &#x27;public_10.0.0.0/8_public/i3&#x27;: {
            &#x27;age&#x27;: None,
            &#x27;destination&#x27;: &#x27;10.0.0.0/8&#x27;,
            &#x27;flags&#x27;: &#x27;A S&#x27;,
            &#x27;interface&#x27;: &#x27;public/i3&#x27;,
            &#x27;metric&#x27;: &#x27;10&#x27;,
            &#x27;nexthop&#x27;: &#x27;vr private&#x27;,
            &#x27;route-table&#x27;: &#x27;unicast&#x27;,
            &#x27;virtual-router&#x27;: &#x27;public&#x27;
        }
    }

### get\_arp\_table

```python
def get_arp_table() -> dict
```

Get the currently available ARP table entries.

The actual API command is ``&lt;show&gt;&lt;arp&gt;&lt;entry name = &#x27;all&#x27;/&gt;&lt;/arp&gt;&lt;/show&gt;``.

**Returns**:

`dict`: ARP table entries.
The key in this dictionary is made of two properties delimited with an underscore (``_``) in the following order:

    * interface name,
    * IP address.

The key does not provide any meaningful information, it&#x27;s there only to introduce uniqueness for each entry. All properties that make a key are also available in the value of a dictionary element.

Sample output:

::

    {
        &#x27;ethernet1/1_10.0.2.1&#x27;: {
            &#x27;interface&#x27;: &#x27;ethernet1/1&#x27;,
            &#x27;ip&#x27;: &#x27;10.0.2.1&#x27;,
            &#x27;mac&#x27;: &#x27;12:34:56:78:9a:bc&#x27;,
            &#x27;port&#x27;: &#x27;ethernet1/1&#x27;,
            &#x27;status&#x27;: &#x27;c&#x27;,
            &#x27;ttl&#x27;: &#x27;1094&#x27;
        },
        &#x27;ethernet1/2_10.0.1.1&#x27;: {
            &#x27;interface&#x27;: &#x27;ethernet1/2&#x27;,
            &#x27;ip&#x27;: &#x27;10.0.1.1&#x27;,
            &#x27;mac&#x27;: &#x27;12:34:56:78:9a:bc&#x27;,
            &#x27;port&#x27;: &#x27;ethernet1/2&#x27;,
            &#x27;status&#x27;: &#x27;c&#x27;,
            &#x27;ttl&#x27;: &#x27;1094&#x27;
        }
    }

### get\_sessions

```python
def get_sessions() -> list
```

Get information about currently running sessions.

The actual API command run is ``show session all``.

**Returns**:

`list`: Information about the current sessions.
Sample output:

::

    [
        {
            &#x27;application&#x27;: &#x27;undecided&#x27;,
            &#x27;decrypt-mirror&#x27;: &#x27;False&#x27;,
            &#x27;dport&#x27;: &#x27;80&#x27;,
            &#x27;dst&#x27;: &#x27;10.0.2.11&#x27;,
            &#x27;dstnat&#x27;: &#x27;False&#x27;,
            &#x27;egress&#x27;: &#x27;ethernet1/1&#x27;,
            &#x27;flags&#x27;: None,
            &#x27;from&#x27;: &#x27;public&#x27;,
            &#x27;idx&#x27;: &#x27;1116&#x27;,
            &#x27;ingress&#x27;: &#x27;ethernet1/1&#x27;,
            &#x27;nat&#x27;: &#x27;False&#x27;,
            &#x27;proto&#x27;: &#x27;6&#x27;,
            &#x27;proxy&#x27;: &#x27;False&#x27;,
            &#x27;source&#x27;: &#x27;168.63.129.16&#x27;,
            &#x27;sport&#x27;: &#x27;56670&#x27;,
            &#x27;srcnat&#x27;: &#x27;False&#x27;,
            &#x27;start-time&#x27;: &#x27;Thu Jan 26 02:46:30 2023&#x27;,
            &#x27;state&#x27;: &#x27;ACTIVE&#x27;,
            &#x27;to&#x27;: &#x27;public&#x27;,
            &#x27;total-byte-count&#x27;: &#x27;296&#x27;,
            &#x27;type&#x27;: &#x27;FLOW&#x27;,
            &#x27;vsys&#x27;: &#x27;vsys1&#x27;,
            &#x27;vsys-idx&#x27;: &#x27;1&#x27;,
            &#x27;xdport&#x27;: &#x27;80&#x27;,
            &#x27;xdst&#x27;: &#x27;10.0.2.11&#x27;,
            &#x27;xsource&#x27;: &#x27;168.63.129.16&#x27;,
            &#x27;xsport&#x27;: &#x27;56670&#x27;
        },
        ...
    ]

### get\_session\_stats

```python
def get_session_stats() -> dict
```

Get basic session statistics.

The actual API command is ``show session info``.

**NOTE**
This is raw output. Names of stats are the same as returned by API. No translation is made on purpose. The output of this command might vary depending on the version of PanOS.

For meaning and available statistics, refer to the offical PanOS documentation.

**Returns**:

`dict`: Session stats in a form of a dictionary.
Sample output:

::

    {
        &#x27;age-accel-thresh&#x27;: &#x27;80&#x27;,
        &#x27;age-accel-tsf&#x27;: &#x27;2&#x27;,
        &#x27;age-scan-ssf&#x27;: &#x27;8&#x27;,
        &#x27;age-scan-thresh&#x27;: &#x27;80&#x27;,
        &#x27;age-scan-tmo&#x27;: &#x27;10&#x27;,
        &#x27;cps&#x27;: &#x27;0&#x27;,
        &#x27;dis-def&#x27;: &#x27;60&#x27;,
        &#x27;dis-sctp&#x27;: &#x27;30&#x27;,
        &#x27;dis-tcp&#x27;: &#x27;90&#x27;,
        &#x27;dis-udp&#x27;: &#x27;60&#x27;,
        &#x27;icmp-unreachable-rate&#x27;: &#x27;200&#x27;,
        &#x27;kbps&#x27;: &#x27;0&#x27;,
        &#x27;max-pending-mcast&#x27;: &#x27;0&#x27;,
        &#x27;num-active&#x27;: &#x27;4&#x27;,
        &#x27;num-bcast&#x27;: &#x27;0&#x27;,
        &#x27;num-gtpc&#x27;: &#x27;0&#x27;,
        &#x27;num-gtpu-active&#x27;: &#x27;0&#x27;,
        &#x27;num-gtpu-pending&#x27;: &#x27;0&#x27;,
        &#x27;num-http2-5gc&#x27;: &#x27;0&#x27;,
        &#x27;num-icmp&#x27;: &#x27;0&#x27;,
        &#x27;num-imsi&#x27;: &#x27;0&#x27;,
        &#x27;num-installed&#x27;: &#x27;1193&#x27;,
        &#x27;num-max&#x27;: &#x27;819200&#x27;,
        &#x27;num-mcast&#x27;: &#x27;0&#x27;,
        &#x27;num-pfcpc&#x27;: &#x27;0&#x27;,
        &#x27;num-predict&#x27;: &#x27;0&#x27;,
        &#x27;num-sctp-assoc&#x27;: &#x27;0&#x27;,
        &#x27;num-sctp-sess&#x27;: &#x27;0&#x27;,
        &#x27;num-tcp&#x27;: &#x27;4&#x27;,
        &#x27;num-udp&#x27;: &#x27;0&#x27;,
        &#x27;pps&#x27;: &#x27;0&#x27;,
        &#x27;tcp-cong-ctrl&#x27;: &#x27;3&#x27;,
        &#x27;tcp-reject-siw-thresh&#x27;: &#x27;4&#x27;,
        &#x27;tmo-5gcdelete&#x27;: &#x27;15&#x27;,
        &#x27;tmo-cp&#x27;: &#x27;30&#x27;,
        &#x27;tmo-def&#x27;: &#x27;30&#x27;,
        &#x27;tmo-icmp&#x27;: &#x27;6&#x27;,
        &#x27;tmo-sctp&#x27;: &#x27;3600&#x27;,
        &#x27;tmo-sctpcookie&#x27;: &#x27;60&#x27;,
        &#x27;tmo-sctpinit&#x27;: &#x27;5&#x27;,
        &#x27;tmo-sctpshutdown&#x27;: &#x27;60&#x27;,
        &#x27;tmo-tcp&#x27;: &#x27;3600&#x27;,
        &#x27;tmo-tcp-delayed-ack&#x27;: &#x27;25&#x27;,
        &#x27;tmo-tcp-unverif-rst&#x27;: &#x27;30&#x27;,
        &#x27;tmo-tcphalfclosed&#x27;: &#x27;120&#x27;,
        &#x27;tmo-tcphandshake&#x27;: &#x27;10&#x27;,
        &#x27;tmo-tcpinit&#x27;: &#x27;5&#x27;,
        &#x27;tmo-tcptimewait&#x27;: &#x27;15&#x27;,
        &#x27;tmo-udp&#x27;: &#x27;30&#x27;,
        &#x27;vardata-rate&#x27;: &#x27;10485760&#x27;
    }

### get\_tunnels

```python
def get_tunnels() -> dict
```

Get information about the configured tunnels.

The actual API command run is ``show running tunnel flow all``.

**Returns**:

`dict`: Information about the configured tunnels.
Sample output (with only one IPSec tunnel configured):

::

    {
        &#x27;GlobalProtect-Gateway&#x27;: {},
        &#x27;GlobalProtect-site-to-site&#x27;: {},
        &#x27;IPSec&#x27;: {
            &#x27;ipsec_tunnel&#x27;: {
                &#x27;gwid&#x27;: &#x27;1&#x27;,
                &#x27;id&#x27;: &#x27;1&#x27;,
                &#x27;inner-if&#x27;: &#x27;tunnel.1&#x27;,
                &#x27;localip&#x27;: &#x27;0.0.0.0&#x27;,
                &#x27;mon&#x27;: &#x27;off&#x27;,
                &#x27;name&#x27;: &#x27;ipsec_tunnel&#x27;,
                &#x27;outer-if&#x27;: &#x27;ethernet1/2&#x27;,
                &#x27;owner&#x27;: &#x27;1&#x27;,
                &#x27;peerip&#x27;: &#x27;192.168.1.1&#x27;,
                &#x27;state&#x27;: &#x27;init&#x27;
            }
        },
        &#x27;SSL-VPN&#x27;: {},
        &#x27;hop&#x27;: {}
    }

### get\_latest\_available\_content\_version

```python
def get_latest_available_content_version() -> str
```

Get the latest, downloadable content version.

The actual API command run is ``request content upgrade check``.

Values returned by API are not ordered. This method tries to reorder them and find the highest available Content DB version. 
The following assumptions are made:

    * versions are always increasing,
    * both components of the version string are numbers.

**Raises**:

- `ContentDBVersionsFormatException`: An exception is thrown when the Content DB version does not match the expected format.

**Returns**:

`str`: The latest available content version.
Sample output:

::

    &#x27;8670-7824&#x27;

### get\_content\_db\_version

```python
def get_content_db_version() -> str
```

Get the currently installed Content DB version.

The actual API command is ``show system info``.

**Returns**:

`str`: Current Content DB version.
Sample output:

::

    &#x27;8670-7824&#x27;

### get\_ntp\_servers

```python
def get_ntp_servers() -> dict
```

Get the NTP synchronization configuration.

The actual API command is ``show ntp``.

**Returns**:

`dict`: The NTP synchronization configuration.
Sample output - no NTP servers configured:

::

    {
        &#x27;synched&#x27;: &#x27;LOCAL&#x27;
    }

Sample output - NTP servers configured:

::

    {
        &#x27;ntp-server-1&#x27;: {
            &#x27;authentication-type&#x27;: &#x27;none&#x27;,
            &#x27;name&#x27;: &#x27;0.pool.ntp.org&#x27;,
            &#x27;reachable&#x27;: &#x27;yes&#x27;,
            &#x27;status&#x27;: &#x27;available&#x27;
        },
        &#x27;ntp-server-2&#x27;: {
            &#x27;authentication-type&#x27;: &#x27;none&#x27;,
            &#x27;name&#x27;: &#x27;1.pool.ntp.org&#x27;,
            &#x27;reachable&#x27;: &#x27;yes&#x27;,
            &#x27;status&#x27;: &#x27;synched&#x27;
        },
        &#x27;synched&#x27;: &#x27;1.pool.ntp.org&#x27;
    }

### get\_disk\_utilization

```python
def get_disk_utilization() -> dict
```

Get the disk utilization (in MB) and parse it to a machine readable format.

The actual API command is ``show system disk-space``.

**Returns**:

`dict`: Disk free space in MBytes.
Sample output:

::

    {
        &#x27;/&#x27;: 2867
        &#x27;/dev&#x27;: 7065
        &#x27;/opt/pancfg&#x27;: 14336
        &#x27;/opt/panrepo&#x27;: 3276
        &#x27;/dev/shm&#x27;: 1433
        &#x27;/cgroup&#x27;: 7065
        &#x27;/opt/panlogs&#x27;: 20480
        &#x27;/opt/pancfg/mgmt/ssl/private&#x27;: 12
    }

### get\_available\_image\_data

```python
def get_available_image_data() -> dict
```

Get information on the available to download PanOS image versions.

The actual API command is ``request system software check``.

**Returns**:

`dict`: Detailed information on available images.
Sample output:

::

    {
        &#x27;11.0.1&#x27;: {
            &#x27;version&#x27;: &#x27;11.0.1&#x27;
            &#x27;filename&#x27;: &#x27;PanOS_vm-11.0.1&#x27;
            &#x27;size&#x27;: &#x27;492&#x27;
            &#x27;size-kb&#x27;: &#x27;504796&#x27;
            &#x27;released-on&#x27;: &#x27;2023/03/29 15:05:25&#x27;
            &#x27;release-notes&#x27;: &#x27;https://www.paloaltonetworks.com/documentation/11-0/pan-os/pan-os-release-notes&#x27;
            &#x27;downloaded&#x27;: &#x27;no&#x27;
            &#x27;current&#x27;: &#x27;no&#x27;
            &#x27;latest&#x27;: &#x27;yes&#x27;
            &#x27;uploaded&#x27;: &#x27;no&#x27;
        }
        &#x27;11.0.0&#x27;: {
            &#x27;version&#x27;: &#x27;11.0.0&#x27;
            &#x27;filename&#x27;: &#x27;PanOS_vm-11.0.0&#x27;
            &#x27;size&#x27;: &#x27;1037&#x27;
            &#x27;size-kb&#x27;: &#x27;1062271&#x27;
            &#x27;released-on&#x27;: &#x27;2022/11/17 08:45:28&#x27;
            &#x27;release-notes&#x27;: &#x27;https://www.paloaltonetworks.com/documentation/11-0/pan-os/pan-os-release-notes&#x27;
            &#x27;downloaded&#x27;: &#x27;no&#x27;
            &#x27;current&#x27;: &#x27;no&#x27;
            &#x27;latest&#x27;: &#x27;no&#x27;
            &#x27;uploaded&#x27;: &#x27;no&#x27;
        }
        ...
    }

### get\_mp\_clock

```python
def get_mp_clock() -> dict
```

Get the clock information from management plane.

The actual API command is ``show clock``.

**Returns**:

`dict`: The clock information represented as a dictionary.
Sample output:

::

    {
        &#x27;time&#x27;: &#x27;00:41:36&#x27;,
        &#x27;tz&#x27;: &#x27;PDT&#x27;,
        &#x27;day&#x27;: &#x27;19&#x27;,
        &#x27;month&#x27;: &#x27;Apr&#x27;,
        &#x27;year&#x27;: &#x27;2023&#x27;,
        &#x27;day_of_week&#x27;: &#x27;Wed&#x27;
    }

### get\_dp\_clock

```python
def get_dp_clock() -> dict
```

Get the clock information from data plane.

The actual API command is ``show clock more``.

**Returns**:

`dict`: The clock information represented as a dictionary.
Sample output:

::

    {
        &#x27;time&#x27;: &#x27;00:41:36&#x27;,
        &#x27;tz&#x27;: &#x27;PDT&#x27;,
        &#x27;day&#x27;: &#x27;19&#x27;,
        &#x27;month&#x27;: &#x27;Apr&#x27;,
        &#x27;year&#x27;: &#x27;2023&#x27;,
        &#x27;day_of_week&#x27;: &#x27;Wed&#x27;
    }


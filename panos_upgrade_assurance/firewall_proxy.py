import xml.etree.ElementTree as ET
from panos_upgrade_assurance.utils import interpret_yes_no
from xmltodict import parse as XMLParse
from typing import Optional, Union, Dict, List
from panos.firewall import Firewall
from math import floor

class CommandRunFailedException(Exception):
    """Used when a command run on a device does not return the ``success`` status."""
    pass

class MalformedResponseException(Exception):
    """A generic exception class used when a response does not meet the expected standards."""
    pass

class ContentDBVersionsFormatException(Exception):
    """Used when parsing Content DB versions fail due to an unknown version format (assuming ``XXXX-YYYY``)."""
    pass

class PanoramaConfigurationMissingException(Exception):
    """Used when checking Panorama connectivity on a device that was not configured with Panorama."""
    pass

class WrongDiskSizeFormatException(Exception):
    """Used when parsing free disk size information."""
    pass

class FirewallProxy(Firewall):
    """Class representing a Firewall.

    Proxy in this class means that it is between the *high level* :class:`.CheckFirewall` class and a device itself.
    Inherits the Firewall_ class but adds methods to interpret XML API commands. The class constructor is also inherited from the Firewall_ class.

    All interaction with a device are read-only. Therefore, a less privileged user can be used.

    All methods starting with ``is_`` check the state, they do not present any data besides simple ``boolean``values.

    All methods starting with `get_` fetch data from a device by running a command and parsing the output. 
    The return data type can be different depending on what kind of information is returned from a device.

    .. _Firewall: https://pan-os-python.readthedocs.io/en/latest/module-firewall.html#module-panos.firewall
    """
    
    def op_parser(self, cmd: str, cmd_in_xml: Optional[bool] = False, return_xml: Optional[bool] = False) -> Union[dict, ET.Element]:
        """Execute a command on node, parse, and return response.

        This is just a wrapper around the `Firewall.op`_ method. It additionally does basic error handling and tries to extract the actual device response.


        :param cmd: The actual XML API command to be run on the device. Can be either a free form or an XML formatted command.
        :type cmd: str
        :param cmd_in_xml: (defaults to ``False``) Set to ``True`` if the command is XML-formatted.
        :type cmd_in_xml: bool
        :param return_xml: (defaults to ``False``) When set to ``True``, the return data is an ``XML object``_ instead of a python dictionary. 
        :type return_xml: bool
        :raises CommandRunFailedException: An exception is raised if the command run status returned by a device is not successful.
        :raises MalformedResponseException: An exception is raised when a response is not parsable, no ``result`` element is found in the XML response. 
        :return: The actual command output. A type is defined by the ``return_xml`` parameter.
        :rtype: dict, xml.etree.ElementTree.Element

        .. _Firewall.op: https://pan-os-python.readthedocs.io/en/latest/module-firewall.html#panos.firewall.Firewall.op
        .. _XML object: https://docs.python.org/3/library/xml.etree.elementtree.html#xml.etree.ElementTree.Element
        """

        raw_response = self.op(cmd, xml=False, cmd_xml=not cmd_in_xml, vsys=self.vsys)
        if raw_response.get('status') != 'success':
            raise CommandRunFailedException(f'Failed to run command: {cmd}.')

        resp_result = raw_response.find('result')
        if resp_result is None:
            raise MalformedResponseException(f'No result field returned for: {cmd}')

        if not return_xml:
            resp_result = XMLParse(ET.tostring(resp_result, encoding='utf8', method='xml'))['result']

        return resp_result

    def is_pending_changes(self) -> bool:
        """Get information if there is a candidate configuration pending to be committed.

        The actual API command run is ``check pending-changes``.

        :return: ``True`` when there are pending changes, ``False`` otherwise.
        :rtype: bool
        """
        return interpret_yes_no(self.op_parser(cmd="check pending-changes"))

    def is_full_commit_required(self) -> bool:
        """Get information if a full commit is required, for example, after loading a named config.

        The actual API command run is ``check full-commit-required``.

        :return: ``True`` when a full commit is required, ``False`` otherwise.
        :rtype: bool
        """
        return interpret_yes_no(self.op_parser(cmd="check full-commit-required"))

    def is_panorama_configured(self) -> bool:
        """Check if a device is configured with Panorama.

        The actual API command run is ``show panorama-status``.

        :return: ``True`` when Panorama IPs are configured, ``False`` otherwise.
        :rtype: bool
        """
        return False if self.op_parser(cmd="show panorama-status") is None else True

    def is_panorama_connected(self) -> bool:
        """Get Panorama connectivity status.

        The actual API command run is ``show panorama-status``.
        
        An output of this command is usually a string. This method is responsible for parsing this string and trying to extract information if at least one of the Panoramas configured is connected.

        :raise PanoramaConfigurationMissingException: Exception being raised when this check is run against a device with no Panorama configured.
        :raise MalformedResponseException: Exception being raised when response from device does not meet required format.

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

        :return: ``True`` when connection is up, ``False`` otherwise.
        :rtype: bool
        """

        pan_status = self.op_parser(cmd="show panorama-status")
        if pan_status == None:
            raise PanoramaConfigurationMissingException("Device not configured with Panorama.")

        if not isinstance(pan_status, str):
            raise MalformedResponseException("Response from device is not type of string.")

        pan_status_list = pan_status.split('\n')
        pan_status_list_length = len(pan_status_list)

        if pan_status_list_length in [3,6]:
            for i in range(1,pan_status_list_length,3):
                pan_connected = interpret_yes_no(
                    (pan_status_list[i].split(':')[1]).strip()
                )
                if pan_connected:
                    return True
        else:
            raise MalformedResponseException(f"Panorama configuration block does not have typical structure: <{resp}>.")

        return False

    def get_ha_configuration(self) -> dict:
        """Get high-availability configuration status.

        The actual API command is ``show high-availability state``.

        :return: Information about HA pair and its status as retrieved from the current (local) device.

            Sample output:

            ::

                {
                    'enabled': 'yes',
                    'group': {
                        'link-monitoring': {
                            'enabled': 'yes',
                            'failure-condition': 'any',
                            'groups': None
                        },
                        'local-info': {
                            'DLP': 'Match',
                            'VMS': 'Match',
                            'active-passive': {
                                'monitor-fail-holddown': '1',
                                'passive-link-state': 'shutdown'
                            },
                            'addon-master-holdup': '500',
                            'app-compat': 'Match',
                            'app-version': 'xxxx-yyyy',
                            'av-compat': 'Match',
                            'av-version': '0',
                            'build-compat': 'Match',
                            'build-rel': '10.2.3',
                            'gpclient-compat': 'Match',
                            'gpclient-version': 'Not Installed',
                            'ha1-encrypt-enable': 'no',
                            'ha1-encrypt-imported': 'no',
                            'ha1-gateway': '10.0.0.1',
                            'ha1-ipaddr': '10.0.0.10/24',
                            'ha1-link-mon-intv': '3000',
                            'ha1-macaddr': 'xx:xx:xx:xx:xx:xx',
                            'ha1-port': 'management',
                            'ha2-gateway': '10.0.3.1',
                            'ha2-ipaddr': '10.0.3.10/24',
                            'ha2-macaddr': 'xx:xx:xx:xx:xx:xx',
                            'ha2-port': 'ethernet1/3',
                            'heartbeat-interval': '10000',
                            'hello-interval': '10000',
                            'iot-compat': 'Match',
                            'iot-version': 'yy-zzz',
                            'max-flaps': '3',
                            'mgmt-ip': '10.0.0.10/24',
                            'mgmt-ipv6': None,
                            'mode': 'Active-Passive',
                            'monitor-fail-holdup': '0',
                            'nonfunc-flap-cnt': '0',
                            'platform-model': 'PA-VM',
                            'preempt-flap-cnt': '0',
                            'preempt-hold': '1',
                            'preemptive': 'no',
                            'priority': '100',
                            'promotion-hold': '20000',
                            'state': 'passive',
                            'state-duration': '3675',
                            'state-sync': 'Complete',
                            'state-sync-type': 'ip',
                            'threat-compat': 'Match',
                            'threat-version': 'xxxx-yyyy',
                            'url-compat': 'Mismatch',
                            'url-version': '0000.00.00.000',
                            'version': '1',
                            'vm-license': 'VM-300',
                            'vm-license-compat': 'Match',
                            'vm-license-type': 'vm300',
                            'vpnclient-compat': 'Match',
                            'vpnclient-version': 'Not Installed'
                        },
                        'mode': 'Active-Passive',
                        'path-monitoring': {
                            'enabled': 'yes',
                            'failure-condition': 'any',
                            'virtual-router': None,
                            'virtual-wire': None,
                            'vlan': None
                        },
                        'peer-info': {
                            'DLP': '3.0.2',
                            'VMS': '3.0.3',
                            'app-version': 'xxxx-yyyy',
                            'av-version': '0',
                            'build-rel': '10.2.3',
                            'conn-ha1': {
                                'conn-desc': 'heartbeat status',
                                'conn-primary': 'yes',
                                'conn-status': 'up'
                            },
                            'conn-ha2': {
                                'conn-desc': 'link status',
                                'conn-ka-enbled': 'no',
                                'conn-primary': 'yes',
                                'conn-status': 'up'
                            },
                            'conn-status': 'up',
                            'gpclient-version': 'Not Installed',
                            'ha1-ipaddr': '10.0.0.11',
                            'ha1-macaddr': 'xx:xx:xx:xx:xx:xx',
                            'ha2-ipaddr': '10.0.3.11',
                            'ha2-macaddr': 'xx:xx:xx:xx:xx:xx',
                            'iot-version': 'yy-zzz',
                            'mgmt-ip': '10.0.0.11/24',
                            'mgmt-ipv6': None,
                            'mode': 'Active-Passive',
                            'platform-model': 'PA-VM',
                            'preemptive': 'no',
                            'priority': '100',
                            'state': 'active',
                            'state-duration': '3680',
                            'threat-version': 'xxxx-yyyy',
                            'url-version': '20230126.20142',
                            'version': '1',
                            'vm-license': 'VM-300',
                            'vm-license-type': 'vm300',
                            'vpnclient-version': 'Not Installed'
                        },
                        'running-sync': 'synchronized',
                        'running-sync-enabled': 'yes'
                    }
                }

        :rtype: dict
        """
        return self.op_parser(cmd="show high-availability state")

    def get_nics(self) -> dict:
        """Get status of the configured network interfaces.

        The actual API command run is ``show interface "hardware"``.

        :raises MalformedResponseException: Exception when no ``hw`` entry is available in the response.
        :return: Status of the configured network interfaces.
            Sample output:

            ::

                {
                    'ethernet1/1': 'down', 
                    'ethernet1/2': 'down', 
                    'ethernet1/3': 'up'
                }

        :rtype: dict
        """

        response = self.op_parser(cmd=r'show interface "hardware"')

        hardware = response['hw']
        if hardware is None:
            raise MalformedResponseException('Malformed response from device, no [hw] element present.')

        results = {}
        entries = hardware['entry']
        if isinstance(entries, dict):
            entries = [entries]
        for nic in entries:
            results[nic['name']] = nic['state']
        return results

    def get_licenses(self) -> dict:
        """Get device licenses.

        The actual API command is ``request license info``.

        :return: Licenses available on a device.

            Sample output:
            
            ::
                
                {
                    'AutoFocus Device License': {
                        'authcode': 'Snnnnnnn',
                        'base-license-name': 'PA-VM',
                        'description': 'AutoFocus Device License',
                        'expired': 'yes',
                        'expires': 'September 25, 2010',
                        'feature': 'AutoFocus Device License',
                        'issued': 'January 12, 2010',
                        'serial': 'xxxxxxxxxxxxxxxx'
                    },
                    'PA-VM': {
                        'authcode': None,
                        'description': 'Standard VM-300',
                        'expired': 'yes',
                        'expires': 'September 25, 2010',
                        'feature': 'PA-VM',
                        'issued': 'January 12, 2010',
                        'serial': 'xxxxxxxxxxxxxxxx'
                    },
                    ...
                }

        :rtype: dict
        """

        response = self.op_parser(cmd="request license info")

        result = {}
        licenses = response['licenses']['entry']
        for lic in licenses if isinstance(licenses, list) else [licenses]:
            result[lic['feature']] = dict(lic)
        return result

    def get_routes(self) -> dict:
        """Get route table entries, either retrieved from DHCP or configured manually.

        The actual API command is ``show routing route``.

        :return: Routes information.

            The key in this dictionary is made of three route properties delimited with an underscore (``_``) in the following order:
            
                * virtual router name,
                * destination CIDR,
                * network interface name if one is available, empty string otherwise.
            
            The key does not provide any meaningful information, it's there only to introduce uniqueness for each entry. All properties that make a key are also available in the value of a dictionary element.

            Sample output:

            ::

                {'
                    private_0.0.0.0/0_private/i3': {
                        'age': None,
                        'destination': '0.0.0.0/0',
                        'flags': 'A S',
                        'interface': 'private/i3',
                        'metric': '10',
                        'nexthop': 'vr public',
                        'route-table': 'unicast',
                        'virtual-router': 'private'
                    },
                    'public_10.0.0.0/8_public/i3': {
                        'age': None,
                        'destination': '10.0.0.0/8',
                        'flags': 'A S',
                        'interface': 'public/i3',
                        'metric': '10',
                        'nexthop': 'vr private',
                        'route-table': 'unicast',
                        'virtual-router': 'public'
                    }
                }

        :rtype: dict
        """

        response = self.op_parser(cmd="show routing route")

        result = {}
        if 'entry' in response:
            routes = response['entry']
            for route in routes if isinstance(routes, list) else [routes]:
                result[
                    f"{route['virtual-router']}_{route['destination']}_{route['interface'] if route['interface'] else ''}"] = dict(
                    route)

        return result

    def get_arp_table(self) -> dict:
        """Get the currently available ARP table entries.

        The actual API command is ``<show><arp><entry name = 'all'/></arp></show>``.

        :return: ARP table entries.

            The key in this dictionary is made of two properties delimited with an underscore (``_``) in the following order:
            
                * interface name,
                * IP address.
            
            The key does not provide any meaningful information, it's there only to introduce uniqueness for each entry. All properties that make a key are also available in the value of a dictionary element.

            Sample output:

            ::

                {
                    'ethernet1/1_10.0.2.1': {
                        'interface': 'ethernet1/1',
                        'ip': '10.0.2.1',
                        'mac': '12:34:56:78:9a:bc',
                        'port': 'ethernet1/1',
                        'status': 'c',
                        'ttl': '1094'
                    },
                    'ethernet1/2_10.0.1.1': {
                        'interface': 'ethernet1/2',
                        'ip': '10.0.1.1',
                        'mac': '12:34:56:78:9a:bc',
                        'port': 'ethernet1/2',
                        'status': 'c',
                        'ttl': '1094'
                    }
                }

        :rtype: dict
        """
        result = {}
        response = self.op_parser(cmd=f"<show><arp><entry name = 'all'/></arp></show>", cmd_in_xml=True)

        if response.get("entries", {}):
            arp_table = response['entries'].get("entry", [])
            for entry in arp_table if isinstance(arp_table, list) else [arp_table]:
                result[f'{entry["interface"]}_{entry["ip"]}'] = dict(entry)
        return result

    def get_sessions(self) -> list:
        """Get information about currently running sessions.

        The actual API command run is ``show session all``.

        :return: Information about the current sessions.

            Sample output:

            ::

                [
                    {
                        'application': 'undecided',
                        'decrypt-mirror': 'False',
                        'dport': '80',
                        'dst': '10.0.2.11',
                        'dstnat': 'False',
                        'egress': 'ethernet1/1',
                        'flags': None,
                        'from': 'public',
                        'idx': '1116',
                        'ingress': 'ethernet1/1',
                        'nat': 'False',
                        'proto': '6',
                        'proxy': 'False',
                        'source': '168.63.129.16',
                        'sport': '56670',
                        'srcnat': 'False',
                        'start-time': 'Thu Jan 26 02:46:30 2023',
                        'state': 'ACTIVE',
                        'to': 'public',
                        'total-byte-count': '296',
                        'type': 'FLOW',
                        'vsys': 'vsys1',
                        'vsys-idx': '1',
                        'xdport': '80',
                        'xdst': '10.0.2.11',
                        'xsource': '168.63.129.16',
                        'xsport': '56670'
                    },
                    ...
                ]

        :rtype: list
        """
        result = []
        raw_response = self.op_parser(cmd='show session all')
        if not raw_response is None:
            sessions = raw_response['entry']
            result = sessions if isinstance(sessions, list) else [sessions]

        return result

    def get_session_stats(self) -> dict:
        """Get basic session statistics.

        The actual API command is ``show session info``.

        **NOTE**
        This is raw output. Names of stats are the same as returned by API. No translation is made on purpose. The output of this command might vary depending on the version of PanOS.

        For meaning and available statistics, refer to the offical PanOS documentation.

        :return: Session stats in a form of a dictionary.

            Sample output:

            ::

                {
                    'age-accel-thresh': '80',
                    'age-accel-tsf': '2',
                    'age-scan-ssf': '8',
                    'age-scan-thresh': '80',
                    'age-scan-tmo': '10',
                    'cps': '0',
                    'dis-def': '60',
                    'dis-sctp': '30',
                    'dis-tcp': '90',
                    'dis-udp': '60',
                    'icmp-unreachable-rate': '200',
                    'kbps': '0',
                    'max-pending-mcast': '0',
                    'num-active': '4',
                    'num-bcast': '0',
                    'num-gtpc': '0',
                    'num-gtpu-active': '0',
                    'num-gtpu-pending': '0',
                    'num-http2-5gc': '0',
                    'num-icmp': '0',
                    'num-imsi': '0',
                    'num-installed': '1193',
                    'num-max': '819200',
                    'num-mcast': '0',
                    'num-pfcpc': '0',
                    'num-predict': '0',
                    'num-sctp-assoc': '0',
                    'num-sctp-sess': '0',
                    'num-tcp': '4',
                    'num-udp': '0',
                    'pps': '0',
                    'tcp-cong-ctrl': '3',
                    'tcp-reject-siw-thresh': '4',
                    'tmo-5gcdelete': '15',
                    'tmo-cp': '30',
                    'tmo-def': '30',
                    'tmo-icmp': '6',
                    'tmo-sctp': '3600',
                    'tmo-sctpcookie': '60',
                    'tmo-sctpinit': '5',
                    'tmo-sctpshutdown': '60',
                    'tmo-tcp': '3600',
                    'tmo-tcp-delayed-ack': '25',
                    'tmo-tcp-unverif-rst': '30',
                    'tmo-tcphalfclosed': '120',
                    'tmo-tcphandshake': '10',
                    'tmo-tcpinit': '5',
                    'tmo-tcptimewait': '15',
                    'tmo-udp': '30',
                    'vardata-rate': '10485760'
                }

        :rtype: dict
        """
        response = self.op_parser(cmd="show session info")
        result = {key: value for key, value in response.items() if value.isnumeric()}
        return result

    def get_tunnels(self) -> dict:
        """Get information about the configured tunnels.

        The actual API command run is ``show running tunnel flow all``.

        :return: Information about the configured tunnels.

            Sample output (with only one IPSec tunnel configured):

            ::

                {
                    'GlobalProtect-Gateway': {},
                    'GlobalProtect-site-to-site': {},
                    'IPSec': {
                        'ipsec_tunnel': {
                            'gwid': '1',
                            'id': '1',
                            'inner-if': 'tunnel.1',
                            'localip': '0.0.0.0',
                            'mon': 'off',
                            'name': 'ipsec_tunnel',
                            'outer-if': 'ethernet1/2',
                            'owner': '1',
                            'peerip': '192.168.1.1',
                            'state': 'init'
                        }
                    },
                    'SSL-VPN': {},
                    'hop': {}
                }

        :rtype: dict
        """
        response = self.op_parser(cmd='show running tunnel flow all')
        result = {}
        for tunnelType, tunnelData in dict(response).items():
            if tunnelData is None:
                result[tunnelType] = dict()
            elif not isinstance(tunnelData, str):
                result[tunnelType] = dict()
                for tunnel in tunnelData['entry'] if isinstance(tunnelData['entry'], list) else [tunnelData['entry']]:
                    result[tunnelType][tunnel['name']] = dict(tunnel)
        return result

    def get_latest_available_content_version(self) -> str:
        """Get the latest, downloadable content version.

        The actual API command run is ``request content upgrade check``.

        Values returned by API are not ordered. This method tries to reorder them and find the highest available Content DB version. 
        The following assumptions are made:

            * versions are always increasing,
            * both components of the version string are numbers.

        :raises ContentDBVersionsFormatException: An exception is thrown when the Content DB version does not match the expected format.

        :return: The latest available content version.

            Sample output:

            ::

                '8670-7824'

        :rtype: str
        """
        response = self.op_parser(cmd="request content upgrade check", return_xml=False)
        try:
            content_versions = [ entry['version'] for entry in response['content-updates']['entry'] ]
            majors = [ int(ver.split('-')[0]) for ver in content_versions ]
            majors.sort()
            major_minors = [ int(ver.split('-')[1]) for ver in content_versions if ver.startswith(f"{majors[-1]}-") ]
            major_minors.sort()
            latest = f"{majors[-1]}-{major_minors[-1]}"
        except Exception as exc:
            raise ContentDBVersionsFormatException('Cannot parse list of available updates for Content DB.') from exc

        return latest

    def get_content_db_version(self) -> str:
        """Get the currently installed Content DB version.

        The actual API command is ``show system info``.

        :return: Current Content DB version.

            Sample output:

            ::

                '8670-7824'

        :rtype: str
        """
        response = self.op_parser(cmd="show system info", return_xml=True)
        return response.findtext('./system/app-version')

    def get_ntp_servers(self) -> dict:
        """Get the NTP synchronization configuration.

        The actual API command is ``show ntp``.

        :return: The NTP synchronization configuration.

            Sample output - no NTP servers configured:

            ::

                {
                    'synched': 'LOCAL'
                }

            Sample output - NTP servers configured:

            ::

                {
                    'ntp-server-1': {
                        'authentication-type': 'none',
                        'name': '0.pool.ntp.org',
                        'reachable': 'yes',
                        'status': 'available'
                    },
                    'ntp-server-2': {
                        'authentication-type': 'none',
                        'name': '1.pool.ntp.org',
                        'reachable': 'yes',
                        'status': 'synched'
                    },
                    'synched': '1.pool.ntp.org'
                }

        :rtype: dict
        """
        return dict(self.op_parser(cmd="show ntp"))

    def get_disk_utilization(self) -> dict:
        """Get the disk utilization (in MB) and parse it to a machine readable format.

        The actual API command is ``show system disk-space``.

        :return: Disk free space in MBytes.

            Sample output:

            ::

                {
                    '/': 2867
                    '/dev': 7065
                    '/opt/pancfg': 14336
                    '/opt/panrepo': 3276
                    '/dev/shm': 1433
                    '/cgroup': 7065
                    '/opt/panlogs': 20480
                    '/opt/pancfg/mgmt/ssl/private': 12
                }

        :rtype: dict
        """
        result = dict()

        disk_space = self.op_parser(cmd="show system disk-space")
        disk_space_list = disk_space.split('\n')

        # we start with index 1 to skip header
        for i in range(1,len(disk_space_list)):
            row = disk_space_list[i]
            row_items = row.split(' ')
            row_items_trimmed = [item for item in row_items if item != '']
                
            mount_point = row_items_trimmed[-1]
            free_size_short = row_items_trimmed[3]
            free_size_name = free_size_short[-1]
            free_size_number = float(free_size_short[0:-1])

            if isinstance(free_size_name, str):
                if free_size_name == 'G':
                    free_size = free_size_number*1024
                elif free_size_name == 'M':
                    free_size = free_size_number
                elif free_size_name == 'K':
                    free_size = free_size_number/1024

            elif isinstance(free_size_name, int):
                free_size = free_size_short/1024/1024

            else:
                raise WrongDiskSizeFormatException("Free disk size has wrong format.")

            result[mount_point] = floor(free_size)

        return result

    def get_available_image_data(self) -> dict:
        """Get information on the available to download PanOS image versions.

        The actual API command is ``request system software check``.

        :return: Detailed information on available images.

            Sample output:

            ::

                {
                    '11.0.1': {
                        'version': '11.0.1'
                        'filename': 'PanOS_vm-11.0.1'
                        'size': '492'
                        'size-kb': '504796'
                        'released-on': '2023/03/29 15:05:25'
                        'release-notes': 'https://www.paloaltonetworks.com/documentation/11-0/pan-os/pan-os-release-notes'
                        'downloaded': 'no'
                        'current': 'no'
                        'latest': 'yes'
                        'uploaded': 'no'
                    }
                    '11.0.0': {
                        'version': '11.0.0'
                        'filename': 'PanOS_vm-11.0.0'
                        'size': '1037'
                        'size-kb': '1062271'
                        'released-on': '2022/11/17 08:45:28'
                        'release-notes': 'https://www.paloaltonetworks.com/documentation/11-0/pan-os/pan-os-release-notes'
                        'downloaded': 'no'
                        'current': 'no'
                        'latest': 'no'
                        'uploaded': 'no'
                    }
                    ...
                }

        :rtype: dict
        """
        result = dict()

        image_data = self.op_parser(cmd="request system software check")
        images = dict(image_data['sw-updates']['versions'])['entry']
        for image in images if isinstance(images, list) else [images]:
            result[image['version']] = dict(image)

        return result

    def get_mp_clock(self) -> dict:
        """Get the clock information from management plane.

        The actual API command is ``show clock``.
        :return: The clock information represented as a dictionary.

            Sample output:

            ::

                {
                    'time': '00:41:36',
                    'tz': 'PDT',
                    'day': '19',
                    'month': 'Apr',
                    'year': '2023',
                    'day_of_week': 'Wed'
                }

        :rtype: dict
        """
        time_string = self.op_parser(cmd="show clock")
        time_dict = time_string.split(' ')
        result = {
            'time': time_dict[3],
            'tz':  time_dict[4],
            'day':  time_dict[2],
            'month':  time_dict[1],
            'year':  time_dict[5],
            'day_of_week':  time_dict[0],
        }
        
        return(result)

    def get_dp_clock(self) -> dict:
        """Get the clock information from data plane.

        The actual API command is ``show clock more``.
        :return: The clock information represented as a dictionary.

            Sample output:

            ::

                {
                    'time': '00:41:36',
                    'tz': 'PDT',
                    'day': '19',
                    'month': 'Apr',
                    'year': '2023',
                    'day_of_week': 'Wed'
                }

        :rtype: dict
        """
        response = self.op_parser(cmd="show clock more")
        time_string = dict(response)['member']
        time_dict = time_string.split(' ')
        result = {
            'time': time_dict[5],
            'tz':  time_dict[6],
            'day':  time_dict[4],
            'month':  time_dict[3],
            'year':  time_dict[7],
            'day_of_week':  time_dict[2],
        }
        
        return(result)
from typing import Optional, Union, List, Iterable, Dict
from math import ceil
from datetime import datetime

from panos_upgrade_assurance.utils import CheckResult, ConfigParser, interpret_yes_no, CheckType, SnapType, CheckStatus
from panos_upgrade_assurance.firewall_proxy import FirewallProxy
from panos import PanOSVersion

class ContentDBVersionInFutureException(Exception):
    """Used when the installed Content DB version is newer than the latest available version."""
    pass

class WrongDataTypeException(Exception):
    """Used when passed configuration does not meet the data type requirements."""
    pass

class ImageVersionNotAvailableException(Exception):
    """Used when requested image version is not available for downloading."""
    pass

class CheckFirewall:
    """Class responsible for running readiness checks and creating Firewall state snapshots.

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

    :param _snapshot_method_mapping: Internal variable containing a map of all valid snapshot types mapped to the specific methods.
    
        This mapping is used to verify the requested snapshot types and to map the snapshot with an actual method that will eventually run. Keys in this dictionary are snapshot names as defined in the :class:`.SnapType` class, values are references to methods that will be run.
    :type _snapshot_method_mapping: dict
    :param _check_method_mapping: Internal variable containing the map of all valid check types mapped to the specific methods. This mapping is used to verify requested check types and to map a check with an actual method that will be eventually run. Keys in this dictionary are check names as defined in the :class:`.CheckType` class, values are references to methods that will be run.
    :type _check_method_mapping: dict
    """

    def __init__(self, node: FirewallProxy) -> None:
        """CheckFirewall constructor.

        :param node: Object representing a device against which checks and/or snapshots are run.
        :type node: :class:`.FirewallProxy`
        """
        self._node = node
        self._snapshot_method_mapping = {
            SnapType.NICS: self._node.get_nics,
            SnapType.ROUTES: self._node.get_routes,
            SnapType.LICENSE: self._node.get_licenses,
            SnapType.ARP_TABLE: self._node.get_arp_table,
            SnapType.CONTENT_VERSION: self.get_content_db_version,
            SnapType.SESSION_STATS: self._node.get_session_stats,
            SnapType.IPSEC_TUNNELS: self.get_ip_sec_tunnels
        }

        self._check_method_mapping =  {
            CheckType.PANORAMA: self.check_panorama_connectivity,
            CheckType.HA: self.check_ha_status,
            CheckType.NTP_SYNC: self.check_ntp_synchronization,
            CheckType.CANDIDATE_CONFIG: self.check_pending_changes,
            CheckType.EXPIRED_LICENSES: self.check_expired_licenses,
            CheckType.CONTENT_VERSION: self.check_content_version,
            CheckType.SESSION_EXIST: self.check_critical_session,
            CheckType.ARP_ENTRY_EXIST: self.check_arp_entry,
            CheckType.IPSEC_TUNNEL_STATUS: self.check_ipsec_tunnel_status,
            CheckType.FREE_DISK_SPACE: self.check_free_disk_space,
            CheckType.MP_DP_CLOCK_SYNC: self.check_mp_dp_sync
        }

    def check_pending_changes(self) -> CheckResult:
        """Check if there are pending changes on device.

        It checks two states:

        1. if there is full commit required on the device,
        2. if not, if there is a candidate config pending on a device.

        :return: Object representing the result of the content version check:

            * :attr:`.CheckStatus.SUCCESS` if there is no pending configuration,
            * :attr:`.CheckStatus.FAIL` otherwise.

        :rtype: :class:`.CheckResult`

        """
        if self._node.is_full_commit_required():
            return CheckResult(reason="Full commit required on device.")
        else:
            if self._node.is_pending_changes():
                return CheckResult(reason="Pending changes found on device.")
            else:
                return CheckResult(status=CheckStatus.SUCCESS)

    def check_panorama_connectivity(self) -> CheckResult:
        """Check connectivity with the Panorama service.

        :return: State of Panorama connection:

            * :attr:`.CheckStatus.SUCCESS` when device is connected to Panorama,
            * :attr:`.CheckStatus.FAIL` otherwise,
            * :attr:`.CheckStatus.ERROR` is returned when no Panorama configuration is found.

        :rtype: :class:`.CheckResult`
        """

        if self._node.is_panorama_configured():
            if self._node.is_panorama_connected():
                return CheckResult(status=CheckStatus.SUCCESS)
            else:
                return CheckResult(reason="Device not connected to Panorama.")
        else:
            return CheckResult(status=CheckStatus.ERROR, reason="Device not configured with Panorama.")

    def check_ha_status(self, skip_config_sync: Optional[bool] = False) -> CheckResult:
        """Checks HA pair status from the perspective of the current device.

        Currently, only Active-Passive configuration is supported.

        :param skip_config_sync: (defaults to ``False``) Use with caution, when set to ``True`` will skip checking if configuration is synchronized between nodes. Helpful when verifying a state of a partially upgraded HA pair.
        :type skip_config_sync: bool, optional
        :return: Result of HA pair status inspection:

            * :attr:`.CheckStatus.SUCCESS` when pair is configured correctly,
            * :attr:`.CheckStatus.FAIL` otherwise,
            * :attr:`.CheckStatus.ERROR` is returned when device is not a member of an HA pair or the pair is not in Active-Passive configuration.

        :rtype: :class:`.CheckResult`
        """
        states = ("active", "passive")

        ha_config = self._node.get_ha_configuration()
        result = CheckResult()

        if interpret_yes_no(ha_config['enabled']):
            ha_pair = ha_config['group']

            if ha_pair['mode'] != 'Active-Passive':
                result.status = CheckStatus.ERROR
                result.reason = "HA pair is not in Active-Passive mode."

            elif ha_pair['local-info']['state'] not in states:
                result.reason = "Local device is not in active or passive state."

            elif ha_pair['peer-info']['state'] not in states:
                result.reason = "Peer device is not in active or passive state."

            elif ha_pair['local-info']['state'] == ha_pair['peer-info']['state']:
                result.status = CheckStatus.ERROR
                result.reason = f"Both devices have the same state: {ha_pair['local-info']['state']}."

            elif not skip_config_sync and interpret_yes_no(ha_pair['running-sync-enabled']) and ha_pair['running-sync'] != 'synchronized':
                result.status = CheckStatus.ERROR
                result.reason = 'Device configuration is not synchronized between the nodes.'

            else:
                result.status = CheckStatus.SUCCESS
        else:
            result.reason = "Device is not a member of an HA pair."
            result.status = CheckStatus.ERROR

        return result

    def check_is_ha_active(self, skip_config_sync: Optional[bool] = False) -> CheckResult:
        """Checks whether this is an active node of an HA pair.

        Before checking the state of the current device, the :meth:`check_ha_status` method is run. If this method does not end with :attr:`.CheckStatus.SUCCESS`, its return value is passed as the result of :meth:`check_is_ha_active`.

        :param skip_config_sync: (defaults to ``False``) Use with caution, when set to ``True`` will skip checking if configuration is synchronized between nodes. Helpful when working with a partially upgraded HA pair.
        :type skip_config_sync: bool, optional
        :return: The return value depends on the results of running :meth:`check_ha_status` method. If the method returns:

            * :attr:`.CheckStatus.SUCCESS` the actual state of the device in an HA pair is checked, if the state is:
                * active :attr:`,.CheckStatus.SUCCESS` is returned,
                * passive :attr:`,.CheckStatus.FAIL` is returned,
            * anything else than :attr:`.CheckStatus.SUCCESS`, the :meth:`check_ha_status` return value is passed as a return value of this method.

        :rtype: :class:`.CheckResult`
        """
        ha_status = self.check_ha_status(skip_config_sync=skip_config_sync)
        if ha_status:
            ha_config = self._node.get_ha_configuration()
            result = CheckResult()
            if ha_config['group']['local-info']['state'] == 'active':
                result.status = CheckStatus.SUCCESS
            else:
                result.reason = f"Node state is: {ha_config['group']['local-info']['state']}."
            return result
        else:
            return ha_status

    def check_expired_licenses(self) -> CheckResult:
        """Check if any license is expired.

        :return:

            * :attr:`.CheckStatus.SUCCESS` if no license is expired,
            * :attr:`.CheckStatus.FAIL` otherwise.

        :rtype: :class:`.CheckResult`
        """

        licenses = self._node.get_licenses()

        expired_licenses = ""
        result = CheckResult()
        for lic, value in licenses.items():
            if interpret_yes_no(value["expired"]):
                expired_licenses += f"{lic}, "

        if expired_licenses:
            result.reason = f"Found expired licenses:  {expired_licenses[:-2]}."
        else:
            result.status = CheckStatus.SUCCESS

        return result

    def check_critical_session(
        self,
        source: Optional[str] = None,
        destination: Optional[str] = None,
        dest_port: Optional[Union[str, int]] = None) -> CheckResult:
        """Check if a critical session is present in the sessions table.

        :param source: (defaults to ``None``) Source IPv4 address for the examined session.
        :type source: str, optional
        :param destination: (defaults to ``None``) Destination IPv4 address for the examined session.
        :type destination: str, optional
        :param dest_port: (defaults to ``None``) Destination port value. This should be an integer value, but string representations such as ``"8080"`` are also accepted.
        :type dest_port: int, str, optional
        :return:

            * :attr:`.CheckStatus.SUCCESS` if a session is found in the sessions table,
            * :attr:`.CheckStatus.FAIL` otherwise,
            * :attr:`.CheckStatus.SKIPPED` when no config is passed,
            * :attr:`.CheckStatus.ERROR` if the session table is empty.

        :rtype: :class:`.CheckResult`
        """

        result = CheckResult()

        if None in [source, destination, dest_port]:
            result.reason = 'Missing critical session description. Failing check.'
            result.status = CheckStatus.SKIPPED
            return result

        sessions = self._node.get_sessions()
        if not sessions:
            result.reason = "Device's session table is empty."
            result.status = CheckStatus.ERROR
            return result

        for session in sessions:
            source_check = session['source'] == source
            destination_check = session['xdst'] == destination
            port_check = session['dport'] == str(dest_port)
            if all((source_check, destination_check, port_check)):
                result.status = CheckStatus.SUCCESS
                return result

        result.reason = "Session not found in session table."
        return result

    def check_content_version(self, version: Optional[str] = None) -> CheckResult:
        """Verify installed version of the Content Database.

        This method runs in two modes:

            * w/o any configuration - checks if the latest version of the Content DB is installed.
            * with specific version passed - verifies if the installed Content DB is at least equal.

        :param version: (defaults to ``None``) Target version of the content DB.
        :type version: str, optional
        :raises ContentDBVersionInFutureException: If the data returned from a device is newer than the latest version available.
        :return: The return value meaning depends on the ``version`` parameter. If it was:

            * defined:
                * :py:attr:`.CheckStatus.SUCCESS` when the installed Content DB is at least the same as the version passed as a parameter.
                * :py:attr:`.CheckStatus.FAIL` when the installed Content DB version is lower than the version passed as a parameter.
            * not defined:
                * :py:attr:`.CheckStatus.SUCCESS` when the installed Content DB is the latest one.
                * :py:attr:`.CheckStatus.FAIL` when the installed Content DB is not the latest one.

        :rtype: :py:class:`.CheckResult` Object
        """
        result = CheckResult()

        required_version = version if version else self._node.get_latest_available_content_version()
        installed_version = self._node.get_content_db_version()

        if required_version == installed_version:
            result.status = CheckStatus.SUCCESS
        else:
            exception_text = f'Wrong data returned from device, installed version ({installed_version}) is higher than the required_version available ({required_version}).'
            conditional_success_text = f'Installed content DB version ({installed_version}) is higher than the requested one ({required_version}).'

            # we already know that the versions are different, so as a default result we assume FAILED
            # now let's handle corner cases
            if int(required_version.split('-')[0]) < int(installed_version.split('-')[0]):
                # if the passed required version is higher that the installed then we assume the test passed
                # this is a type of a test where we look for the minimum version
                if version:
                    result.status = CheckStatus.SUCCESS
                    result.reason = conditional_success_text
                else:
                    # in case where no version was passed we treat this situation as an exception
                    # latest version cannot by lower than the installed one. 
                    raise ContentDBVersionInFutureException(exception_text)
            elif int(required_version.split('-')[0]) == int(installed_version.split('-')[0]):
                # majors the same, compare minors assuming the same logic we used for majors
                if int(required_version.split('-')[1]) < int(installed_version.split('-')[1]):
                    if version:
                        result.status = CheckStatus.SUCCESS
                        result.reason = conditional_success_text
                    else:
                        raise ContentDBVersionInFutureException(exception_text)

            if not result:
                reason_suffix = f'older then the request one ({required_version}).' if version else f'not the latest one ({required_version}).'
                result.reason = f"Installed content DB version ({installed_version}) is {reason_suffix}"

        return result

    def check_ntp_synchronization(self) -> CheckResult:
        """Check synchronization with NTP server.

        :return:

            * :attr:`.CheckStatus.SUCCESS` when a device is synchronized with the NTP server.
            * :attr:`.CheckStatus.FAIL` when a device is not synchronized with the NTP server.
            * :attr:`.CheckStatus.ERROR` when a device is not configured for NTP synchronization.

        :rtype: :class:`.CheckResult`
        """

        result = CheckResult()
        
        response = self._node.get_ntp_servers()
        if response['synched'] == 'LOCAL':
            if len(response) == 1:
                result.reason = 'No NTP server configured.'
                result.status = CheckStatus.ERROR
            else:
                del response['synched']
                srvs_state = ""
                for v in response.values():
                    srvs_state += f"{v['name']} - {v['status']}, "
                result.reason = f"No NTP synchronization in active, servers in following state: {srvs_state[:-2]}."
        else:
            synched = response['synched']
            del response['synched']

            if synched in [v['name'] for v in response.values()]:
                result.status = CheckStatus.SUCCESS
            else:
                result.reason = f'NTP synchronization in unknown state: {synched}.'

        return result

    def check_arp_entry(self, ip: Optional[str] = None, interface: Optional[str] = None) -> CheckResult:
        """Check if a given ARP entry is available in the ARP table.

        :param interface: (defaults to ``None``) A name of an interface we examine for the ARP entries. When skipped, all interfaces are examined.
        :type interface: str, optional
        :param ip: (defaults to ``None``) IP address of the ARP entry we look for.
        :type ip: str, optional
        :return:
        
            * :attr:`.CheckStatus.SUCCESS` when the ARP entry is found.
            * :attr:`.CheckStatus.FAIL` when the ARP entry is not found.
            * :attr:`.CheckStatus.SKIPPED` when ``ip`` is not provided.
            * :attr:`.CheckStatus.ERROR` when the ARP table is empty.

        :rtype: :class:`.CheckResult`
        """

        result = CheckResult()

        if ip is None:
            result.reason = "Missing ARP table entry description."
            result.status = CheckStatus.SKIPPED
            return result

        arp_table = self._node.get_arp_table()

        if not arp_table:
            result.reason = "ARP table empty."
            result.status = CheckStatus.ERROR
            return result

        for arp_entry in arp_table.values():
            if interface is not None:
                found = ip == arp_entry.get('ip') and interface == arp_entry.get('interface')
            else:
                found = ip == arp_entry.get('ip')

            if found:
                result.status = CheckStatus.SUCCESS
                return result

        result.reason = "Entry not found in ARP table."
        return result

    def check_ipsec_tunnel_status(self, tunnel_name: Optional[str] = None) -> CheckResult:
        """Check if a given IPSec tunnel is in active state.

        :param tunnel_name: (defaults to ``None``) Name of the searched IPSec tunnel.
        :type ip: str, optional
        :return: 
            * :attr:`.CheckStatus.SUCCESS` when a tunnel is found and is in active state.
            * :attr:`.CheckStatus.FAIL` when a tunnel is either not active or missing in the current configuration.
            * :attr:`.CheckStatus.SKIPPED` when ``tunnel_name`` is not provided.
            * :attr:`.CheckStatus.ERROR` when no IPSec tunnels are configured on the device.

        :rtype: :class:`.CheckResult`
        """

        result = CheckResult()

        if tunnel_name is None:
            result.status = CheckStatus.SKIPPED
            result.reason = 'Missing tunnel specification.'
            return result
            
        tunnels = self._node.get_tunnels()

        if not tunnels.get("IPSec"):
            result.reason = 'No IPSec Tunnel is configured on the device.'
            result.status = CheckStatus.ERROR
            return result

        for name in tunnels['IPSec']:
            data = tunnels['IPSec'][name]
            if name == tunnel_name:
                if data["state"] == 'active':
                    result.status = CheckStatus.SUCCESS
                else:
                    result.reason = f"Tunnel {tunnel_name} in state: {data['state']}."
                return result

        result.reason = f"Tunnel {tunnel_name} not found."

        return result

    def check_free_disk_space(self, image_version: Optional[str] = None) -> CheckResult:
        """Check if a there is enough space on the ``/opt/panrepo`` volume for downloading an PanOS image.

        This is a check intended to be run before the actual upgrade process starts.

        The method operates in two modes:
        
            * default - to be used as last resort, it will verify that the ``/opt/panrepo`` volume has at least 3GB free space available. This amount of free space is somewhat arbitrary and it's based maximum image sizes (path level + base image) available at the time the method was written (+ some additional error margin).
            * specific target image - suggested mode, it will take one argument ``image_version`` which is the target PanOS version. For that version the actual image size (path + base image) will be calculated. Next, the available free space is verified against that image size + 10% (as an error margin).

        :param image_version: (defaults to ``None``) Version of the target PanOS image. 
        :type ip: str, optional
        :return: 
            * :attr:`.CheckStatus.SUCCESS` when there is enough free space to download an image.
            * :attr:`.CheckStatus.FAIL` when there is NOT enough free space, additionally the actual free space available is provided as the fail reason.
        :rtype: :class:`.CheckResult`
        """
        result = CheckResult()
        minimum_free_space = ceil(3.0 * 1024)
        if image_version:
            image_sem_version = PanOSVersion(image_version)
            available_versions = self._node.get_available_image_data()
            
            if str(image_sem_version) in available_versions:
                requested_base_image_size = 0
                requested_image_size = int(available_versions[str(image_sem_version)]['size'])

                if image_sem_version.patch != 0:
                    base_image_version = f'{image_sem_version.major}.{image_sem_version.minor}.0'
                    if base_image_version in available_versions:
                        if not interpret_yes_no(available_versions[base_image_version]['downloaded']):
                            requested_base_image_size = int(available_versions[base_image_version]['size'])
                    else:
                        raise ImageVersionNotAvailableException(f'Base image {base_image_version} does not exist.')

                minimum_free_space = ceil(1.1*(requested_base_image_size + requested_image_size))

            else:
                raise ImageVersionNotAvailableException(f'Image {str(image_sem_version)} does not exist.')

        free_space = self._node.get_disk_utilization()
        free_space_panrepo = free_space['/opt/panrepo']

        if free_space_panrepo > minimum_free_space:
            result.status = CheckStatus.SUCCESS
        else:
            result.reason = f"There is not enough free space, only {str(round(free_space_panrepo/1024,1)) + 'G' if free_space_panrepo >= 1024 else str(free_space_panrepo) + 'M'}B is available."
        return result

    def check_mp_dp_sync(self, diff_threshold: int = 0) -> CheckResult:
        """Check if the Data and Management clocks are in sync.

        :param diff_threshold: (defaults to ``0``) Maximum allowable difference in seconds between both clocks. 
        :type ip: int, optional
        :return: 
            * :attr:`.CheckStatus.SUCCESS` when both clocks are the same or within threshold.
            * :attr:`.CheckStatus.FAIL` when both clocks differ.
        :rtype: :class:`.CheckResult`
        """
        if not isinstance(diff_threshold, int):
            raise WrongDataTypeException(f"[diff_threshold] should be of type [int] but is of type [{type(diff_threshold)}].")

        result = CheckResult()

        mp_clock = self._node.get_mp_clock()
        dp_clock = self._node.get_dp_clock()

        mp_dt = datetime.strptime(
            f"{mp_clock['year']}-{mp_clock['month']}-{mp_clock['day']} {mp_clock['time']}",
            "%Y-%b-%d %H:%M:%S"
        )
        dp_dt = datetime.strptime(
            f"{dp_clock['year']}-{dp_clock['month']}-{dp_clock['day']} {dp_clock['time']}",
            "%Y-%b-%d %H:%M:%S"
        )

        time_fluctuation = abs((mp_dt - dp_dt).total_seconds())
        if time_fluctuation > diff_threshold:
            result.reason = f"The data plane clock and management clock are different by {time_fluctuation} seconds."
        else:
            result.status = CheckStatus.SUCCESS

        return result

    def get_content_db_version(self) -> Dict[str,str]:
        """Get Content DB version.
        
        :return: To keep the standard of all ``get`` methods returning a dictionary. This value is also returned as a dictionary in the following format:

            ::
            
                {
                    'version': 'xxxx-yyyy'
                }

        :rtype: dict
        """
        return {'version': self._node.get_content_db_version()}

    def get_ip_sec_tunnels(self) -> Dict[str,Union[str,int]]:
        """Extract information about IPSEC tunnels from all tunnel data retrieved from a device.

        :return: Currently configured IPSEC tunnels.
            The returned value is similar to the example below. It can differ though depending on the version of PanOS:

            ::

                {
                    "tunnel_name": {
                        "peerip": "10.26.129.5",
                        "name": "tunnel_name",
                        "outer-if": "ethernet1/2",
                        "gwid": "1",
                        "localip": "0.0.0.0",
                        "state": "init",
                        "inner-if": "tunnel.1",
                        "mon": "off",
                        "owner": "1",
                        "id": "1"
                    }
                }

        :rtype: dict
        """
        return self._node.get_tunnels()['IPSec']


    def run_readiness_checks(
        self,
        checks_configuration: Optional[List[Union[str, dict]]] = None,
        report_style: bool = False
    ) -> Union[Dict[str, dict], Dict[str,str]]:
        """Run readiness checks.

        This method provides a convenient way of running readiness check methods.

        :param checks_configuration: (defaults to ``None``) A list of readiness checks to run with an optional configuration.
            This list is defined using the :class:`.ConfigParser` class `dialect`_. For details, refer to the documentation for this class. 

            Elements of this list can be either of the ``str`` or ``dict`` type:

                * ``str`` - the element simply specifies the name of a check to run.
                * ``dict`` - the element contains the check name and a configuration (if a particular check requires one); the dictionary format is as follows:

                    ::

                        {
                            'check_name': {
                                'config_name': 'config_value'
                                'config2_name': 'config2_value'
                            }
                        }

                    Refer to the :ref:`readiness_docs` documentation for details on each check configuration.

            Following :class:`.ConfigParser` `dialect`_, when no configuration is provided, the **all** checks are triggered. *Notice* that in this situation checks that require configuration to run will return :attr:`.CheckStatus.SKIPPED`.

            Example of the ``checks_configuration`` parameter:

            ::

                [
                    'all',
                    '!ha',
                    {'content_version': {'version': '8634-7678'}}
                ]

            This is interpreted as: run all checks, except for the HA status verification and override the Content DB version check to check for the minimum version of 8634-7678.

        :rtype: list(str,dict), optional
        :param report_style: (defaults to ``False``) Changes the output to more descriptive. Can be used directly when generating a report.
        :type report_style: bool
        :raises WrongDataTypeException: An exception is raised when the configuration is in a data type different then ``str`` or ``dict``.
        :return: The format differs depending on the value of the ``report_style`` parameter. If the value is:
            
            * ``False`` (default): results of executed checks are formatted as ``dict``, where keys are check names as passed in ``checks_configuration`` and values are dictionaries containing two keys:

                * ``state``: a ``bool`` representation of the :class:`.CheckResult` class for a particular check.
                * ``reason``:  a ``str`` representation of the :class:`.CheckResult` class for a particular check.

                Assuming that we run the checks with the following configuration:

                ::

                    [
                        'ha',
                        'panorama',
                    ]

                The return ``dict`` should look as follows:

                ::

                    {
                        'ha': {
                            'state': False
                            'reason': '[FAIL] Device configuration is not synchronized between the nodes.'
                        }
                        'candidate_config': {
                            'state': True
                            'reason': '[SUCCESS]'
                        }
                    }

            * ``True``: results are also formatted as ``dict`` with the keys corresponding to checks names, but values are a string representations of the :class:`.CheckResult` class.
            
                For the above example of checks, the result would be similar to:

                ::

                    {
                        'ha': '[FAIL] Device configuration is not synchronized between the nodes.'
                        'candidate_config': '[SUCCESS].'
                    }

        :rtype: dict
        """
        result = {}
        checks_list = ConfigParser(valid_elements=set(self._check_method_mapping.keys()),
                                   requested_config=checks_configuration).prepare_config()

        for check in checks_list:
            if isinstance(check, dict):
                check_type, check_config = next(iter(check.items()))
                # check_result = self._check_method_mapping[check_type](check_config)
            elif isinstance(check, str):
                check_type, check_config = check, {}
                # check_result = self._check_method_mapping[check_type]()
            else:
                raise WrongDataTypeException(f'Wrong configuration format for check: {check}.')

            check_result = self._check_method_mapping[check_type](**check_config)  # (**) would pass dict config values as seperate parameters to method.
            result[check_type] = str(check_result) if report_style else {'state': bool(check_result), 'reason': str(check_result)}

        return result

    def run_snapshots(self, snapshots_config: Optional[List[Union[str, dict]]] = None) -> Dict[str, dict]:
        """Run snapshots of different firewall areas' states.

        This method provides a convenient way of running snapshots of a device state.

        :param snapshots_config: (defaults to ``None``) Defines snapshots of which areas will be taken.
        
            This list is specified in :class:`.ConfigParser` class`dialect`_. For details, refer to the documentation for this class.
            Following that`dialect`_, when no list is passed, **all** state snapshots are made.

            On the contrary to ``run_readiness_checks``, it is not possible to configure a snapshot. One can only specify which type of data should be captured.
            That's why, below there is a list of strings only. Refer to the :ref:`snapshot_docs` documentation for details on the currently available snapshot areas.

        :type snapshot_config: list(str), optional
        :raises WrongDataTypeException: An exception is raised when the configuration in a data type is different than in a string.
        :return: The results of the executed snapshots are formatted as a dictionary where:
        
            * keys are state areas as passed in ``snapshot_config`` parameter,
            * values are dictionaries with the actual data.

                Each dictionary can have a different structure. The structure depends on the nature of data we want to capture.
                See the :ref:`snapshot_docs` documentation to refer to the methods used to take snapshots of a particular area. The documentation for these methods inludes details on the actual structure of results.
            
            The sample output containing a snapshot for route tables, licenses, and IPSec tunnels is shown below (one element per each area):

            .. code-block:: python

                {
                    "ip_sec_tunnels": {
                        "ipsec_tun": {
                            "peerip": "10.26.129.5",
                            "name": "ipsec_tun",
                            "outer-if": "ethernet1/2",
                            "gwid": "1",
                            "localip": "0.0.0.0",
                            "state": "init",
                            "inner-if": "tunnel.1",
                            "mon": "off",
                            "owner": "1",
                            "id": "1"
                        },
                    }.
                    "routes": {
                        "default_0.0.0.0/0_ethernet1/3": {
                            "virtual-router": "default",
                            "destination": "0.0.0.0/0",
                            "nexthop": "10.26.129.129",
                            "metric": "10",
                            "flags": "A S",
                            "age": null,
                            "interface": "ethernet1/3",
                            "route-table": "unicast"
                        },
                    },
                    "license": {
                        "DNS Security": {
                            "feature": "DNS Security",
                            "description": "Palo Alto Networks DNS Security License",
                            "serial": "007257000334668",
                            "issued": "November 08, 2022",
                            "expires": "November 01, 2023",
                            "expired": "no",
                            "base-license-name": "PA-VM",
                            "authcode": null
                        },
                    }
                }

        :rtype: dict
        """
        result = {}
        snaps_list = ConfigParser(valid_elements=set(self._snapshot_method_mapping.keys()),
                                  requested_config=snapshots_config).prepare_config()

        for snap_type in snaps_list:
            if not isinstance(snap_type, str):
                raise WrongDataTypeException(f'Wrong configuration format for snapshot: {snap_type}.')

            result[snap_type] = self._snapshot_method_mapping[snap_type]()

        return result

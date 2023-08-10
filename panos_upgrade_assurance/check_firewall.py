from typing import Optional, Union, List, Dict
from math import ceil, floor
from datetime import datetime, timedelta
import locale
import time

from panos_upgrade_assurance.utils import (
    CheckResult,
    ConfigParser,
    interpret_yes_no,
    CheckType,
    SnapType,
    CheckStatus,
    SupportedHashes,
)
from panos_upgrade_assurance.firewall_proxy import FirewallProxy
from panos_upgrade_assurance import exceptions
from panos import PanOSVersion
from OpenSSL import crypto as oSSL


class CheckFirewall:
    """Class responsible for running readiness checks and creating Firewall state snapshots.

    This class is designed to:

    * run one or more [`FirewallProxy`](/panos/docs/panos-upgrade-assurance/api/firewall_proxy#class-firewallproxy) class methods,
    * gather and interpret results,
    * present results.

    It is split into two parts responsible for:

    1. running readiness checks, all methods related to this functionality are prefixed with `check_`,
    2. running state snapshots, all methods related to this functionality are prefixed with `get_`, although usually the
        [`FirewallProxy`](/panos/docs/panos-upgrade-assurance/api/firewall_proxy#class-firewallproxy) methods are run directly.

    Although it is possible to run the methods directly, the preferred way is to run them through one of the following `run`
        methods:

    * [`run_readiness_checks()`](#checkfirewallrun_readiness_checks) is responsible for running specified readiness checks,
    * [`run_snapshots()`](#checkfirewallrun_snapshots) is responsible for getting a snapshot of specified device areas.

    # Attributes

    _snapshot_method_mapping (dict): Internal variable containing a map of all valid snapshot types mapped to the specific
        methods.

        This mapping is used to verify the requested snapshot types and to map the snapshot with an actual method that
        will eventually run. Keys in this dictionary are snapshot names as defined in the
        [`SnapType`](/panos/docs/panos-upgrade-assurance/api/utils#class-snaptype) class, values are references to methods that
        will be run.

    _check_method_mapping (dict): Internal variable containing the map of all valid check types mapped to the specific methods.

        This mapping is used to verify requested check types and to map a check with an actual method that will be eventually run.
        Keys in this dictionary are check names as defined in the
        [`CheckType`](/panos/docs/panos-upgrade-assurance/api/utils#class-checktype) class, values are references to methods that
        will be run.

    """

    def __init__(self, node: FirewallProxy, skip_force_locale: Optional[bool] = False) -> None:
        """CheckFirewall constructor.

        # Parameters

        node (FirewallProxy): Object representing a device against which checks and/or snapshots are run. See
            [`FirewallProxy`](/panos/docs/panos-upgrade-assurance/api/firewall_proxy#class-firewallproxy) class' documentation.
        skip_force_locale (bool, optional): (defaults to `False`) Use with caution, when set to `True` will skip setting locale to
            en_US.UTF-8 for the module which will parse the datetime strings in checks with current locale setting.

        """
        self._node = node
        self._snapshot_method_mapping = {
            SnapType.NICS: self._node.get_nics,
            SnapType.ROUTES: self._node.get_routes,
            SnapType.LICENSE: self._node.get_licenses,
            SnapType.ARP_TABLE: self._node.get_arp_table,
            SnapType.CONTENT_VERSION: self.get_content_db_version,
            SnapType.SESSION_STATS: self._node.get_session_stats,
            SnapType.IPSEC_TUNNELS: self.get_ip_sec_tunnels,
        }

        self._check_method_mapping = {
            CheckType.PANORAMA: self.check_panorama_connectivity,
            CheckType.HA: self.check_ha_status,
            CheckType.NTP_SYNC: self.check_ntp_synchronization,
            CheckType.CANDIDATE_CONFIG: self.check_pending_changes,
            CheckType.EXPIRED_LICENSES: self.check_expired_licenses,
            CheckType.ACTIVE_SUPPORT: self.check_active_support_license,
            CheckType.CONTENT_VERSION: self.check_content_version,
            CheckType.SESSION_EXIST: self.check_critical_session,
            CheckType.ARP_ENTRY_EXIST: self.check_arp_entry,
            CheckType.IPSEC_TUNNEL_STATUS: self.check_ipsec_tunnel_status,
            CheckType.FREE_DISK_SPACE: self.check_free_disk_space,
            CheckType.MP_DP_CLOCK_SYNC: self.check_mp_dp_sync,
            CheckType.CERTS: self.check_ssl_cert_requirements,
            CheckType.UPDATES: self.check_scheduled_updates,
        }
        if not skip_force_locale:
            locale.setlocale(
                locale.LC_ALL, "en_US.UTF-8"
            )  # force locale for datetime string parsing when non-English locale is set on host

    def check_pending_changes(self) -> CheckResult:
        """Check if there are pending changes on device.

        It checks two states:

        1. if there is full commit required on the device,
        2. if not, if there is a candidate config pending on a device.

        # Returns

        CheckResult: Object of [`CheckResult`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkresult) class \
            representing the result of the content version check:

        * [`CheckStatus.SUCCESS`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) if there is no pending
            configuration,
        * [`CheckStatus.FAIL`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) otherwise.

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

        # Returns

        CheckResult: Object of [`CheckResult`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkresult) class \
            representing a state of Panorama connection:

        * [`CheckStatus.SUCCESS`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) when device is connected to
            Panorama,
        * [`CheckStatus.FAIL`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) otherwise,
        * [`CheckStatus.ERROR`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) is returned when no Panorama
            configuration is found.

        """

        if self._node.is_panorama_configured():
            if self._node.is_panorama_connected():
                return CheckResult(status=CheckStatus.SUCCESS)
            else:
                return CheckResult(reason="Device not connected to Panorama.")
        else:
            return CheckResult(status=CheckStatus.ERROR, reason="Device not configured with Panorama.")

    def check_ha_status(
        self,
        skip_config_sync: Optional[bool] = False,
        ignore_non_functional: Optional[bool] = False,
    ) -> CheckResult:
        """Checks HA pair status from the perspective of the current device.

        Currently, only Active-Passive configuration is supported.

        # Parameters

        skip_config_sync (bool, optional): (defaults to `False`) Use with caution, when set to `True` will skip checking if
            configuration is synchronized between nodes. Helpful when verifying a state of a partially upgraded HA pair.
        ignore_non_functional (bool, optional): (defaults to `False`) Use with caution, when set to `True` will ignore if device
            state is `non-functional` on one of the nodes. Helpful when verifying a state of a partially upgraded HA pair with
            vmseries plugin version mismatch.

        # Returns

        CheckResult: Object of [`CheckResult`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkresult) class \
            representing results of HA pair status inspection:

        * [`CheckStatus.SUCCESS`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) when pair is configured
            correctly,
        * [`CheckStatus.FAIL`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) otherwise,
        * [`CheckStatus.ERROR`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) is returned when device is not a
            member of an HA pair or the pair is not in Active-Passive configuration.

        """
        states = ("active", "passive") if not ignore_non_functional else ("active", "passive", "non-functional")

        ha_config = self._node.get_ha_configuration()
        result = CheckResult()

        if interpret_yes_no(ha_config["enabled"]):
            ha_pair = ha_config["group"]

            if ha_pair["mode"] != "Active-Passive":
                result.status = CheckStatus.ERROR
                result.reason = "HA pair is not in Active-Passive mode."

            elif ha_pair["local-info"]["state"] not in states:
                result.reason = "Local device is not in active or passive state."

            elif ha_pair["peer-info"]["state"] not in states:
                result.reason = "Peer device is not in active or passive state."

            elif ha_pair["local-info"]["state"] == ha_pair["peer-info"]["state"]:
                result.status = CheckStatus.ERROR
                result.reason = f"Both devices have the same state: {ha_pair['local-info']['state']}."

            elif (
                not skip_config_sync
                and interpret_yes_no(ha_pair["running-sync-enabled"])
                and ha_pair["running-sync"] != "synchronized"
            ):
                result.status = CheckStatus.ERROR
                result.reason = "Device configuration is not synchronized between the nodes."

            else:
                result.status = CheckStatus.SUCCESS
        else:
            result.reason = "Device is not a member of an HA pair."
            result.status = CheckStatus.ERROR

        return result

    def check_is_ha_active(
        self,
        skip_config_sync: Optional[bool] = False,
        ignore_non_functional: Optional[bool] = False,
    ) -> CheckResult:
        """Checks whether this is an active node of an HA pair.

        Before checking the state of the current device, the [`check_ha_status()`](#checkfirewallcheck_ha_status) method is run.
        If this method does not end with
        [`CheckStatus.SUCCESS`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus), its return value is passed as
        the result of [`check_is_ha_active()`](#checkfirewallcheck_is_ha_active).

        Detailed results matrix looks like this

        - [`CheckStatus.SUCCESS`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) the actual state of the device
            in an HA pair is checked, if the state is

            - active - [`CheckStatus.SUCCESS`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) is returned,
            - passive - [`CheckStatus.FAIL`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) is returned,


        - anything else than [`CheckStatus.SUCCESS`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus), the
        [`check_ha_status()`](#checkfirewallcheck_ha_status) return value is passed as a return value of this method.


        # Parameters

        skip_config_sync (bool, optional): (defaults to `False`) Use with caution, when set to `True` will skip checking if
            configuration is synchronized between nodes. Helpful when working with a partially upgraded HA pair.
        ignore_non_functional (bool, optional): (defaults to `False`) Use with caution, when set to `True` will ignore if device
            state is `non-functional` on one of the nodes. Helpful when verifying a state of a partially upgraded HA pair with
            vmseries plugin version mismatch.

        # Returns

        CheckResult: Boolean information reflecting the state of the device.

        """
        ha_status = self.check_ha_status(
            skip_config_sync=skip_config_sync,
            ignore_non_functional=ignore_non_functional,
        )
        if ha_status:
            ha_config = self._node.get_ha_configuration()
            result = CheckResult()
            if ha_config["group"]["local-info"]["state"] == "active":
                result.status = CheckStatus.SUCCESS
            else:
                result.reason = f"Node state is: {ha_config['group']['local-info']['state']}."
            return result
        else:
            return ha_status

    def check_expired_licenses(self, skip_licenses: Optional[list] = []) -> CheckResult:
        """Check if any license is expired.

        # Parameters

        skip_licenses (list, optional): (defaults to `[]`) List of license names that should be skipped during the check.

        # Raises

        WrongDataTypeException: Raised when `skip_licenses` is not type of `list`.

        # Returns

        CheckResult: Object of [`CheckResult`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkresult) class taking \
            value of:

        * [`CheckStatus.SUCCESS`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) if no license is expired,
        * [`CheckStatus.FAIL`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) otherwise
        * [`CheckStatus.ERROR`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) when there is not license
        information available in the API response.

        """
        if not isinstance(skip_licenses, list):
            raise exceptions.WrongDataTypeException(f"The skip_licenses variable is a {type(skip_licenses)} but should be a list")

        result = CheckResult()
        try:
            licenses = self._node.get_licenses()
        except exceptions.DeviceNotLicensedException as exp:
            result.status = CheckStatus.ERROR
            result.reason = str(exp)
            return result

        expired_licenses = ""
        for lic, value in licenses.items():
            if lic not in skip_licenses:
                if interpret_yes_no(value["expired"]):
                    expired_licenses += f"{lic}, "

        if expired_licenses:
            result.reason = f"Found expired licenses:  {expired_licenses[:-2]}."
        else:
            result.status = CheckStatus.SUCCESS

        return result

    def check_active_support_license(self) -> CheckResult:
        """Check active support license with update server.

        # Returns

        dict: Object of [`CheckResult`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkresult) class taking value of:

        - [`CheckStatus.SUCCESS`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) if the support license is not
            expired,
        - [`CheckStatus.FAIL`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) otherwise,
        - [`CheckStatus.ERROR`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) when no information cannot be
        retrieved or found in the API response.

        """

        result = CheckResult()

        try:
            self._node.get_licenses()
        except exceptions.DeviceNotLicensedException as exp:
            result.status = CheckStatus.ERROR
            result.reason = str(exp)
            return result

        try:
            support_license = self._node.get_support_license()
        except exceptions.UpdateServerConnectivityException:  # raised when connectivity timeouts
            result.reason = "Can not reach update servers to check active support license."
            result.status = CheckStatus.ERROR
            return result

        if not support_license.get("support_expiry_date"):  # if None or empty string
            result.reason = "No ExpiryDate found for support license."
            result.status = CheckStatus.ERROR
            return result

        dt_expiry = datetime.strptime(support_license["support_expiry_date"], "%B %d, %Y")
        dt_today = datetime.now()

        if dt_expiry < dt_today:
            result.reason = "Support License expired."
        else:
            result.status = CheckStatus.SUCCESS

        return result

    def check_critical_session(
        self,
        source: Optional[str] = None,
        destination: Optional[str] = None,
        dest_port: Optional[Union[str, int]] = None,
    ) -> CheckResult:
        """Check if a critical session is present in the sessions table.

        # Parameters

        source (str, optional): (defaults to `None`) Source IPv4 address for the examined session.
        destination (str, optional): (defaults to `None`) Destination IPv4 address for the examined session.
        dest_port (int, str, optional): (defaults to `None`) Destination port value. This should be an integer value, but string
        representations such as `"8080"` are also accepted.

        # Returns

        CheckResult: Object of [`CheckResult`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkresult) class taking \
            value of:

        * [`CheckStatus.SUCCESS`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) if a session is found in the
        sessions table,
        * [`CheckStatus.FAIL`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) otherwise,
        * [`CheckStatus.SKIPPED`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) when no config is passed,
        * [`CheckStatus.ERROR`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) if the session table is empty.

        """

        result = CheckResult()

        if None in [source, destination, dest_port]:
            result.reason = "Missing critical session description. Failing check."
            result.status = CheckStatus.SKIPPED
            return result

        sessions = self._node.get_sessions()
        if not sessions:
            result.reason = "Device's session table is empty."
            result.status = CheckStatus.ERROR
            return result

        for session in sessions:
            source_check = session["source"] == source
            destination_check = session["xdst"] == destination
            port_check = session["dport"] == str(dest_port)
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

        # Parameters

        version (str, optional): (defaults to `None`) Target version of the content DB.

        # Returns
        CheckResult: Object of [`CheckResult`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkresult) class taking \
            value off:

        * [`CheckStatus.SUCCESS`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) when the installed Content DB
            met the requirements.
        * [`CheckStatus.FAIL`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) when it did not.

        """
        result = CheckResult()

        try:
            required_version = version if version else self._node.get_latest_available_content_version()
        except exceptions.ContentDBVersionsFormatException as exp:
            result.reason = str(exp)
            result.status = CheckStatus.ERROR
            return result

        installed_version = self._node.get_content_db_version()

        if required_version == installed_version:
            result.status = CheckStatus.SUCCESS
        else:
            exception_text = f"Wrong data returned from device, installed version ({installed_version}) is higher than the required_version available ({required_version})."
            conditional_success_text = (
                f"Installed content DB version ({installed_version}) is higher than the requested one ({required_version})."
            )

            # we already know that the versions are different, so as a default result we assume FAILED
            # now let's handle corner cases
            if int(required_version.split("-")[0]) < int(installed_version.split("-")[0]):
                # if the passed required version is higher that the installed then we assume the test passed
                # this is a type of a test where we look for the minimum version
                if version:
                    result.status = CheckStatus.SUCCESS
                    result.reason = conditional_success_text
                else:
                    # in case where no version was passed we treat this situation as an exception
                    # latest version cannot by lower than the installed one.
                    result.status = CheckStatus.ERROR
                    result.reason = exception_text

            elif int(required_version.split("-")[0]) == int(installed_version.split("-")[0]):
                # majors the same, compare minors assuming the same logic we used for majors
                if int(required_version.split("-")[1]) < int(installed_version.split("-")[1]):
                    if version:
                        result.status = CheckStatus.SUCCESS
                        result.reason = conditional_success_text
                    else:
                        result.status = CheckStatus.ERROR
                        result.reason = exception_text

            if result.status is CheckStatus.FAIL:  # NOTE skip for SUCCESS and ERROR
                reason_suffix = (
                    f"older then the request one ({required_version})."
                    if version
                    else f"not the latest one ({required_version})."
                )
                result.reason = f"Installed content DB version ({installed_version}) is {reason_suffix}"

        return result

    def check_ntp_synchronization(self) -> CheckResult:
        """Check synchronization with NTP server.

        # Returns

        CheckResult: Object of [`CheckResult`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkresult) class taking \
            value of:

        * [`CheckStatus.SUCCESS`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) when a device is synchronized
            with the NTP server.
        * [`CheckStatus.FAIL`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) when a device is not synchronized
            with the NTP server.
        * [`CheckStatus.ERROR`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) when a device is not configured
            for NTP synchronization.

        """

        result = CheckResult()

        response = self._node.get_ntp_servers()
        if response["synched"] == "LOCAL":
            if len(response) == 1:
                result.reason = "No NTP server configured."
                result.status = CheckStatus.ERROR
            else:
                del response["synched"]
                srvs_state = ""
                for v in response.values():
                    srvs_state += f"{v['name']} - {v['status']}, "
                result.reason = f"No NTP synchronization in active, servers in following state: {srvs_state[:-2]}."
        else:
            synched = response["synched"]
            del response["synched"]

            if synched in [v["name"] for v in response.values()]:
                result.status = CheckStatus.SUCCESS
            else:
                result.reason = f"NTP synchronization in unknown state: {synched}."

        return result

    def check_arp_entry(self, ip: Optional[str] = None, interface: Optional[str] = None) -> CheckResult:
        """Check if a given ARP entry is available in the ARP table.

        # Parameters

        interface (str, optional): (defaults to `None`) A name of an interface we examine for the ARP entries. When skipped, all
            interfaces are examined.
        ip (str, optional): (defaults to `None`) IP address of the ARP entry we look for.

        # Returns

        CheckResult: Object of [`CheckResult`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkresult) class taking \
            value of:

        * [`CheckStatus.SUCCESS`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) when the ARP entry is found.
        * [`CheckStatus.FAIL`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) when the ARP entry is not found.
        * [`CheckStatus.SKIPPED`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) when `ip` is not provided.
        * [`CheckStatus.ERROR`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) when the ARP table is empty.

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
                found = ip == arp_entry.get("ip") and interface == arp_entry.get("interface")
            else:
                found = ip == arp_entry.get("ip")

            if found:
                result.status = CheckStatus.SUCCESS
                return result

        result.reason = "Entry not found in ARP table."
        return result

    def check_ipsec_tunnel_status(self, tunnel_name: Optional[str] = None) -> CheckResult:
        """Check if a given IPSec tunnel is in active state.

        # Parameters

        tunnel_name (str, optional): (defaults to `None`) Name of the searched IPSec tunnel.

        # Returns

        CheckResult: Object of [`CheckResult`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkresult) class taking \
            value of:

        * [`CheckStatus.SUCCESS`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) when a tunnel is found and is
            in active state.
        * [`CheckStatus.FAIL`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) when a tunnel is either not
            active or missing in the current configuration.
        * [`CheckStatus.SKIPPED`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) when `tunnel_name` is not
            provided.
        * [`CheckStatus.ERROR`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) when no IPSec tunnels are
            configured on the device.

        """

        result = CheckResult()

        if tunnel_name is None:
            result.status = CheckStatus.SKIPPED
            result.reason = "Missing tunnel specification."
            return result

        tunnels = self._node.get_tunnels()

        if not tunnels.get("IPSec"):
            result.reason = "No IPSec Tunnel is configured on the device."
            result.status = CheckStatus.ERROR
            return result

        for name in tunnels["IPSec"]:
            data = tunnels["IPSec"][name]
            if name == tunnel_name:
                if data["state"] == "active":
                    result.status = CheckStatus.SUCCESS
                else:
                    result.reason = f"Tunnel {tunnel_name} in state: {data['state']}."
                return result

        result.reason = f"Tunnel {tunnel_name} not found."

        return result

    def check_free_disk_space(self, image_version: Optional[str] = None) -> CheckResult:
        """Check if a there is enough space on the `/opt/panrepo` volume for downloading an PanOS image.

        This is a check intended to be run before the actual upgrade process starts.

        The method operates in two modes:

        * default - to be used as last resort, it will verify that the `/opt/panrepo` volume has at least 3GB free space
            available. This amount of free space is somewhat arbitrary and it's based maximum image sizes
            (path level + base image) available at the time the method was written (+ some additional error margin).
        * specific target image - suggested mode, it will take one argument `image_version` which is the target PanOS version.
            For that version the actual image size (path + base image) will be calculated. Next, the available free space
            is verified against that image size + 10% (as an error margin).

        # Parameters

        image_version (str, optional): (defaults to `None`) Version of the target PanOS image.

        # Returns

        CheckResult: Object of [`CheckResult`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkresult) class taking \
            value of:

        * [`CheckStatus.SUCCESS`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) when there is enough free
            space to download an image.
        * [`CheckStatus.FAIL`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) when there is NOT enough free
            space, additionally the actual free space available is provided as the fail reason.

        """
        result = CheckResult()
        minimum_free_space = ceil(3.0 * 1024)
        if image_version:
            image_sem_version = PanOSVersion(image_version)
            try:
                available_versions = self._node.get_available_image_data()
            except exceptions.UpdateServerConnectivityException:
                result.reason = "Unable to retrieve target image size most probably due to network issues or because the device is not licensed."
                result.status = CheckStatus.ERROR
                return result

            if str(image_sem_version) in available_versions:
                requested_base_image_size = 0
                requested_image_size = int(available_versions[str(image_sem_version)]["size"])

                if image_sem_version.patch != 0:
                    base_image_version = f"{image_sem_version.major}.{image_sem_version.minor}.0"
                    if base_image_version in available_versions:
                        if not interpret_yes_no(available_versions[base_image_version]["downloaded"]):
                            requested_base_image_size = int(available_versions[base_image_version]["size"])
                    else:
                        result.reason = f"Base image {base_image_version} does not exist."
                        result.status = CheckStatus.ERROR

                minimum_free_space = ceil(1.1 * (requested_base_image_size + requested_image_size))

            else:
                result.reason = f"Image {str(image_sem_version)} does not exist."
                result.status = CheckStatus.ERROR

        try:
            free_space = self._node.get_disk_utilization()
        except exceptions.WrongDiskSizeFormatException as exp:
            result.reason = str(exp)
            result.status = CheckStatus.ERROR
            return result

        free_space_panrepo = free_space["/opt/panrepo"]

        if free_space_panrepo > minimum_free_space:
            result.status = CheckStatus.SUCCESS
        else:
            result.reason = f"There is not enough free space, only {str(round(free_space_panrepo/1024,1)) + 'G' if free_space_panrepo >= 1024 else str(free_space_panrepo) + 'M'}B is available."
        return result

    def check_mp_dp_sync(self, diff_threshold: int = 0) -> CheckResult:
        """Check if the Data and Management clocks are in sync.

        # Raises

        WrongDataTypeException: Raised when the `diff_threshold` is not type of `int`.

        # Parameters

        diff_threshold (int, optional): (defaults to `0`) Maximum allowable difference in seconds between both clocks.

        # Returns

        CheckResult: Object of [`CheckResult`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkresult) class taking \
            value of:

        * [`CheckStatus.SUCCESS`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) when both clocks are the same
            or within threshold.
        * [`CheckStatus.FAIL`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) when both clocks differ.

        """
        if not isinstance(diff_threshold, int):
            raise exceptions.WrongDataTypeException(
                f"[diff_threshold] should be of type [int] but is of type [{type(diff_threshold)}]."
            )

        result = CheckResult()

        mp_clock = self._node.get_mp_clock()
        dp_clock = self._node.get_dp_clock()

        time_fluctuation = abs((mp_clock - dp_clock).total_seconds())
        if time_fluctuation > diff_threshold:
            result.reason = f"The data plane clock and management clock are different by {time_fluctuation} seconds."
        else:
            result.status = CheckStatus.SUCCESS

        return result

    def check_ssl_cert_requirements(self, rsa: dict = {}, ecdsa: dict = {}) -> CheckResult:
        """Check if the certificates' keys meet minimum size requirements.

        This method loops over all certificates installed on a device and compares certificate's properties with the ones
        provided in input parameters. There are two parameters available, one describing `RSA` certificate requirements, the
        other for `ECDSA` certificates. Both parameters are dictionaries accepting the following keys:

        - `hash_method` - a minimum (from security perspective) required hashing method,
        - `key_size` - a minimum size of a key.

        # Parameters

        rsa (dict, optional): A dictionary describing minimum security requirements of a `RSA` certificate. Default values \
            for the certificate requirements are as follows:

            - `hash_method` - `SHA256`,
            - `key_size` - `2048`.

        ecdsa (dict, optional): A dictionary describing minimum security requirements of a `ECDSA` certificate. Default values \
        for the certificate requirements are as follows:

            - `hash_method` - `SHA256`,
            - `key_size` - `256`.

        # Returns

        CheckResult: Object of [`CheckResult`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkresult) class taking \
            value of:

        * [`CheckStatus.SUCCESS`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) when all certs meet the size
            requirements.
        * [`CheckStatus.FAIL`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) if a least one cert
            does not meet the requirements - certificate names with their current sizes are provided in `CheckResult.reason`
            property.
        * [`CheckStatus.SKIPPED`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) when device does not have
            certificates installed.
        * [`CheckStatus.ERROR`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) when the certificate's
            properties (installed or required) are not supported.

        """
        result = CheckResult()

        allowed_keys = ["hash_method", "key_size"]

        if not all(key in allowed_keys for key in rsa.keys()):
            raise exceptions.UnknownParameterException(
                f"Unknown configuration parameter(s) found in the `rsa` dictionary: {', '.join(rsa.keys())}."
            )
        if not all(key in allowed_keys for key in ecdsa.keys()):
            raise exceptions.UnknownParameterException(
                f"Unknown configuration parameter(s) found in the `ecdsa` dictionary: {', '.join(ecdsa.keys())}."
            )

        certificates = self._node.get_certificates()
        if not certificates:
            result.status = CheckStatus.SKIPPED
            result.reason = "No certificates installed on device."
            return result

        rsa_min_hash_method = rsa.get("hash_method", "sha256").upper()
        if rsa_min_hash_method in [member.name for member in SupportedHashes]:
            rsa_min_hash = SupportedHashes[rsa_min_hash_method]
        else:
            result.status = CheckStatus.ERROR
            result.reason = f"The provided minimum RSA hashing method ({rsa_min_hash_method}) is not supported."
            return result

        ecdsa_min_hash_method = ecdsa.get("hash_method", "sha256").upper()
        if ecdsa_min_hash_method in [member.name for member in SupportedHashes]:
            ecdsa_min_hash = SupportedHashes[ecdsa_min_hash_method]
        else:
            result.status = CheckStatus.ERROR
            result.reason = f"The provided minimum ECDSA hashing method ({ecdsa_min_hash_method}) is not supported."
            return result

        rsa_min_key_size = rsa.get("key_size", 2048)
        if not (isinstance(rsa_min_key_size, int) and rsa_min_key_size > 0):
            result.status = CheckStatus.ERROR
            result.reason = "The provided minimum RSA key size should be an integer greater than 0."
            return result

        ecdsa_min_key_size = ecdsa.get("key_size", 256)
        if not (isinstance(ecdsa_min_key_size, int) and ecdsa_min_key_size > 0):
            result.status = CheckStatus.ERROR
            result.reason = "The provided minimum ECDSA key size should be an integer greater than 0."
            return result

        failed_certs = []
        for cert_name, certificate in certificates.items():
            cert = oSSL.load_certificate(oSSL.FILETYPE_PEM, certificate["public-key"])

            cert_key_size = cert.get_pubkey().bits()

            cert_algorithm = certificate["algorithm"]
            if cert_algorithm not in ["RSA", "EC"]:
                result.status = CheckStatus.ERROR
                result.reason = f"Failed for certificate: {cert_name}: unknown algorithm {cert_algorithm}."
                return result

            cert_hash_method = cert.to_cryptography().signature_hash_algorithm.name.upper()
            if cert_hash_method in [member.name for member in SupportedHashes]:
                cert_hash = SupportedHashes[cert_hash_method]
            else:
                result.status = CheckStatus.ERROR
                result.reason = (
                    f"The certificate's hashing method ({cert_hash_method}) is not supported? Please check the device."
                )
                return result

            if (cert_key_size < (rsa_min_key_size if cert_algorithm == "RSA" else ecdsa_min_key_size)) or (
                cert_hash.value < (rsa_min_hash.value if cert_algorithm == "RSA" else ecdsa_min_hash.value)
            ):
                failed_certs.append(f"{cert_name} (size: {cert_key_size}, hash: {cert_hash_method})")

        if failed_certs:
            result.reason = f"Following certificates do not meet required criteria: {', '.join(failed_certs)}."
            return result

        result.status = CheckStatus.SUCCESS
        return result

    def _calculate_time_distance(self, now_dt: datetime, schedule_type: str, schedule: dict) -> (int, str):
        """A method that calculates the time distance between two `datetime` objects.

        :::note
        This method is used only by [`CheckFirewall.check_scheduled_updates()`](/panos/docs/panos-upgrade-assurance/api/check_firewall#checkfirewallcheck_scheduled_updates) method and it expects some information
        to be already available.
        :::

        # Parameters

        now_dt (datetime): A `datetime` object representing the current moment in time.
        schedule_type (str): A schedule type returned by PanOS, can be one of: `every-*`, `hourly`, `daily`, `weekly`,
            `real-time`.
        schedule (dict): Value of the `recurring` key in the API response, see [`FirewallProxy.get_update_schedules()`](/panos/docs/panos-upgrade-assurance/api/firewall_proxy#firewallproxyget_update_schedules)
            documentation for details.

        # Raises

        MalformedResponseException: Thrown then the `schedule_type` is not recognizable.

        # Returns

        tuple(int, str): A tuple containing the calculated time difference (in minutes) and human-readable description.

        """
        time_distance = 0
        details = "unsupported schedule type"

        if schedule_type == "daily":
            occurrence = schedule["at"]
            next_occurrence = datetime.strptime(f"{str(now_dt.date())} {occurrence}", "%Y-%m-%d %H:%M")

            if now_dt > next_occurrence:
                next_occurrence = next_occurrence + timedelta(days=1)
            diff = next_occurrence - now_dt
            time_distance = floor(diff.total_seconds() / 60)
            details = f"at {next_occurrence.time()}"

        elif schedule_type == "hourly":
            time_distance = 60
            details = "every hour"
        elif schedule_type == "weekly":
            occurrence_time = schedule["at"]
            occurrence_day = schedule["day-of-week"]
            occurrence_wday = time.strptime(occurrence_day, "%A").tm_wday
            now_wday = now_dt.weekday()

            diff_days = (0 if occurrence_wday >= now_wday else 7) + occurrence_wday - now_wday
            next_occurrence_date = (now_dt + timedelta(days=diff_days)).date()
            next_occurrence = datetime.strptime(f"{str(next_occurrence_date)} {occurrence_time}", "%Y-%m-%d %H:%M")

            if now_dt > next_occurrence:
                next_occurrence = next_occurrence + timedelta(days=7)
            diff = next_occurrence - now_dt
            time_distance = floor(diff.total_seconds() / 60)
            details = f"in {str(diff).split('.')[0]}"

        elif schedule_type.split("-")[0] == "every":
            if schedule_type.split("-")[1] == "min":
                time_distance = 1
                details = "every minute"
            elif schedule_type.split("-")[1] == "hour":
                time_distance = 60
                details = "hourly"
            elif schedule_type.split("-")[1].isnumeric():
                time_distance = int(schedule_type.split("-")[1])
                details = f"every {time_distance} minutes"
            else:
                raise exceptions.MalformedResponseException(f"Unknown schedule type: {schedule_type}.")
        elif schedule_type == "real-time":
            details = "unpredictable (real-time)"
        else:
            raise exceptions.MalformedResponseException(f"Unknown schedule type: {schedule_type}.")

        return time_distance, details

    def check_scheduled_updates(self, test_window: int = 60) -> CheckResult:
        """Check if any Dynamic Update job is scheduled to run within the specified time window.

        # Parameters

        test_window (int, optional): (defaults to 60 minutes). A time window in minutes to look for an update job occurrence.
            Has to be a value between `60` and `10080` (1 week equivalent). The time window is calculated based on the device's
            local time (taken from the management plane).

        # Raises

        MalformedResponseException: Thrown in case API response does not meet expectations.

        # Returns

        CheckResult: Object of [`CheckResult`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkresult) class taking \
            value of:

        * [`CheckStatus.SUCCESS`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) when there is no update job
            planned within the test time window.
        * [`CheckStatus.FAIL`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) otherwise, `CheckResult.reason`
            field contains information about the planned jobs with next occurrence time provided if possible.
        * [`CheckStatus.ERROR`](/panos/docs/panos-upgrade-assurance/api/utils#class-checkstatus) when the `test_window` parameter
            does not meet criteria.

        """
        if not isinstance(test_window, int):
            raise exceptions.WrongDataTypeException(
                f"The test_windows parameter should be of type <class int>, got {type(test_window)} instead."
            )

        result = CheckResult()

        mp_now = self._node.get_mp_clock()

        schedules = self._node.get_update_schedules()
        if not schedules:
            result.status = CheckStatus.SKIPPED
            result.reason = "No scheduled job present on the device."
            return result

        if test_window < 60:
            result.status = CheckStatus.ERROR
            result.reason = "Schedules test window is below the supported, safe minimum of 60 minutes."
            return result
        if test_window > 10080:
            result.status = CheckStatus.ERROR
            result.reason = "Schedules test window is set to over 1 week. This test will always fail."
            return result

        for name, schedule in schedules.items():
            if "recurring" not in schedule.keys():
                raise exceptions.MalformedResponseException(f"Schedule {name} has malformed configuration, missing a schedule..")
            if len(schedule) != 1:
                raise exceptions.MalformedResponseException(f"Schedule {name} has malformed configuration: {schedule}")

        schedules_in_window = []
        for name, schedule in schedules.items():
            schedule_details = schedule["recurring"]

            if "sync-to-peer" in schedule_details:
                schedule_details.pop("sync-to-peer")

            if "none" not in schedule_details:
                time_distance, details = self._calculate_time_distance(
                    now_dt=mp_now,
                    schedule_type=next(iter(schedule_details.keys())),
                    schedule=next(iter(schedule_details.values())),
                )
                if time_distance <= test_window:
                    schedules_in_window.append(f"{name} ({details})")

        if schedules_in_window:
            result.reason = f"Following schedules fall into test window: {', '.join(schedules_in_window)}."
            return result

        result.status = CheckStatus.SUCCESS

        return result

    def get_content_db_version(self) -> Dict[str, str]:
        """Get Content DB version.

        # Returns

        dict(str): To keep the standard of all `get` methods returning a dictionary this value is also returned as a dictionary \
            in the following format:

        ```python showLineNumbers
        {
            'version': 'xxxx-yyyy'
        }
        ```

        """
        return {"version": self._node.get_content_db_version()}

    def get_ip_sec_tunnels(self) -> Dict[str, dict]:
        """Extract information about IPSEC tunnels from all tunnel data retrieved from a device.

        # Returns

        dict: Currently configured IPSEC tunnels. The returned value is similar to the example below. It can differ though \
            depending on the version of PanOS:

        ```python showLineNumbers title="Example"
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
        ```

        """
        return self._node.get_tunnels().get("IPSec", {})

    def run_readiness_checks(
        self,
        checks_configuration: Optional[List[Union[str, dict]]] = None,
        report_style: bool = False,
    ) -> Union[Dict[str, dict], Dict[str, str]]:
        """Run readiness checks.

        This method provides a convenient way of running readiness checks methods. For details on configuration see
        [readiness checks](/panos/docs/panos-upgrade-assurance/configuration-details#readiness-checks) documentation.

        # Parameters

        checks_configuration (list(str,dict), optional): (defaults to `None`) List of readiness checks to run.
        report_style (bool): (defaults to `False`) Changes the output to more descriptive. Can be used when generating a report
            from the checks.

        # Raises

        WrongDataTypeException: An exception is raised when the configuration is in a data type different then `str` or `dict`.

        # Returns

        dict: Results of all configured checks.

        """
        result = {}
        checks_list = ConfigParser(
            valid_elements=set(self._check_method_mapping.keys()),
            requested_config=checks_configuration,
        ).prepare_config()

        for check in checks_list:
            if isinstance(check, dict):
                check_type, check_config = next(iter(check.items()))
                # check_result = self._check_method_mapping[check_type](check_config)
            elif isinstance(check, str):
                check_type, check_config = check, {}
                # check_result = self._check_method_mapping[check_type]()
            else:
                raise exceptions.WrongDataTypeException(
                    f"Wrong configuration format for check: {check}."
                )  # NOTE checks are already validated in ConfigParser._extrac_element_name - this is never executed.

            check_result = self._check_method_mapping[check_type](
                **check_config
            )  # (**) would pass dict config values as separate parameters to method.
            result[check_type] = str(check_result) if report_style else {"state": bool(check_result), "reason": str(check_result)}

        return result

    def run_snapshots(self, snapshots_config: Optional[List[Union[str, dict]]] = None) -> Dict[str, dict]:
        """Run snapshots of different firewall areas states.

        This method provides a convenient way of running snapshots of a device state. For details on configuration see
        [state snapshots](/panos/docs/panos-upgrade-assurance/configuration-details#state-snapshots) documentation.

        # Parameters

        snapshots_config (list(str), optional): (defaults to `None`) Defines snapshots of which areas will be taken.

        # Raises

        WrongDataTypeException: An exception is raised when the configuration in a data type is different than in a string.

        # Returns

        dict: The results of the executed snapshots.

        """
        result = {}
        snaps_list = ConfigParser(
            valid_elements=set(self._snapshot_method_mapping.keys()),
            requested_config=snapshots_config,
        ).prepare_config()

        for snap_type in snaps_list:
            if not isinstance(snap_type, str):
                raise exceptions.WrongDataTypeException(f"Wrong configuration format for snapshot: {snap_type}.")

            result[snap_type] = self._snapshot_method_mapping[snap_type]()

        return result

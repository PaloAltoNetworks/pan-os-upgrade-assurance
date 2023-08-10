import pytest
from unittest.mock import MagicMock
from panos_upgrade_assurance.check_firewall import CheckFirewall
from panos_upgrade_assurance.firewall_proxy import FirewallProxy
from panos_upgrade_assurance.utils import CheckResult
from panos_upgrade_assurance.utils import CheckStatus
from panos_upgrade_assurance.exceptions import (
    WrongDataTypeException,
    UpdateServerConnectivityException,
    DeviceNotLicensedException,
    ContentDBVersionsFormatException,
    WrongDiskSizeFormatException,
    UnknownParameterException,
    MalformedResponseException,
)
from datetime import datetime


@pytest.fixture
def check_firewall_mock():
    tested_class = CheckFirewall(MagicMock(set_spec=FirewallProxy))
    yield tested_class


class TestCheckFirewall:
    def test_check_pending_changes_full_commit_true(self, check_firewall_mock):
        check_firewall_mock._node.is_full_commit_required.return_value = True
        assert check_firewall_mock.check_pending_changes() == CheckResult(reason="Full commit required on device.")

    def test_check_pending_changes_full_commit_false_pending_true(self, check_firewall_mock):
        check_firewall_mock._node.is_full_commit_required.return_value = False
        check_firewall_mock._node.is_pending_changes.return_value = True
        assert check_firewall_mock.check_pending_changes() == CheckResult(reason="Pending changes found on device.")

    def test_check_pending_changes_full_commit_false_pending_false(self, check_firewall_mock):
        check_firewall_mock._node.is_full_commit_required.return_value = False
        check_firewall_mock._node.is_pending_changes.return_value = False
        assert check_firewall_mock.check_pending_changes() == CheckResult(status=CheckStatus.SUCCESS)

    def test_check_panorama_connectivity_panorama_configured_true_connected_true(self, check_firewall_mock):
        check_firewall_mock._node.is_panorama_configured.return_value = True
        check_firewall_mock._node.is_panorama_connected.return_value = True
        assert check_firewall_mock.check_panorama_connectivity() == CheckResult(status=CheckStatus.SUCCESS)

    def test_check_panorama_connectivity_panorama_configured_true_connected_false(self, check_firewall_mock):
        check_firewall_mock._node.is_panorama_configured.return_value = True
        check_firewall_mock._node.is_panorama_connected.return_value = False
        assert check_firewall_mock.check_panorama_connectivity() == CheckResult(reason="Device not connected to Panorama.")

    def test_check_panorama_connectivity_panorama_configured_false(self, check_firewall_mock):
        check_firewall_mock._node.is_panorama_configured.return_value = False
        assert check_firewall_mock.check_panorama_connectivity() == CheckResult(
            status=CheckStatus.ERROR, reason="Device not configured with Panorama."
        )

    def test_check_ha_status_success(self, check_firewall_mock):
        check_firewall_mock._node.get_ha_configuration.return_value = {
            "enabled": "yes",
            "group": {
                "mode": "Active-Passive",
                "local-info": {"state": "active"},
                "peer-info": {"state": "passive"},
                "running-sync-enabled": "yes",
                "running-sync": "synchronized",
            },
        }
        assert check_firewall_mock.check_ha_status() == CheckResult(status=CheckStatus.SUCCESS)

    def test_check_ha_status_enabled(self, check_firewall_mock):
        check_firewall_mock._node.get_ha_configuration.return_value = {
            "enabled": "no",
            "group": {
                "mode": "Active-Passive",
                "local-info": {"state": "active"},
                "peer-info": {"state": "passive"},
                "running-sync-enabled": "yes",
                "running-sync": "synchronized",
            },
        }
        assert check_firewall_mock.check_ha_status() == CheckResult(
            status=CheckStatus.ERROR, reason="Device is not a member of an HA pair."
        )

    def test_check_ha_status_no_sync(self, check_firewall_mock):
        check_firewall_mock._node.get_ha_configuration.return_value = {
            "enabled": "yes",
            "group": {
                "mode": "Active-Passive",
                "local-info": {"state": "active"},
                "peer-info": {"state": "passive"},
                "running-sync-enabled": "yes",
                "running-sync": "not-synchronized",
            },
        }
        assert check_firewall_mock.check_ha_status() == CheckResult(
            status=CheckStatus.ERROR, reason="Device configuration is not synchronized between the nodes."
        )

    def test_check_ha_status_skip_sync(self, check_firewall_mock):
        check_firewall_mock._node.get_ha_configuration.return_value = {
            "enabled": "yes",
            "group": {
                "mode": "Active-Passive",
                "local-info": {"state": "active"},
                "peer-info": {"state": "passive"},
                "running-sync-enabled": "yes",
                "running-sync": "not-synchronized",
            },
        }
        assert check_firewall_mock.check_ha_status(skip_config_sync=True) == CheckResult(status=CheckStatus.SUCCESS)

    def test_check_ha_status_mode(self, check_firewall_mock):
        check_firewall_mock._node.get_ha_configuration.return_value = {
            "enabled": "yes",
            "group": {
                "mode": "Active-Active",
                "local-info": {"state": "active"},
                "peer-info": {"state": "passive"},
                "running-sync-enabled": "yes",
                "running-sync": "synchronized",
            },
        }
        assert check_firewall_mock.check_ha_status() == CheckResult(
            status=CheckStatus.ERROR, reason="HA pair is not in Active-Passive mode."
        )

    def test_check_ha_status_local_info(self, check_firewall_mock):
        check_firewall_mock._node.get_ha_configuration.return_value = {
            "enabled": "yes",
            "group": {
                "mode": "Active-Passive",
                "local-info": {"state": "someotherstate"},
                "peer-info": {"state": "passive"},
                "running-sync-enabled": "yes",
                "running-sync": "synchronized",
            },
        }
        assert check_firewall_mock.check_ha_status() == CheckResult(reason="Local device is not in active or passive state.")

    def test_check_ha_status_peer_info(self, check_firewall_mock):
        check_firewall_mock._node.get_ha_configuration.return_value = {
            "enabled": "yes",
            "group": {
                "mode": "Active-Passive",
                "local-info": {"state": "active"},
                "peer-info": {"state": "someotherstate"},
                "running-sync-enabled": "yes",
                "running-sync": "synchronized",
            },
        }
        assert check_firewall_mock.check_ha_status() == CheckResult(reason="Peer device is not in active or passive state.")

    def test_check_ha_status_peer_info_ignore_non_functional(self, check_firewall_mock):
        check_firewall_mock._node.get_ha_configuration.return_value = {
            "enabled": "yes",
            "group": {
                "mode": "Active-Passive",
                "local-info": {"state": "active"},
                "peer-info": {"state": "non-functional"},
                "running-sync-enabled": "yes",
                "running-sync": "synchronized",
            },
        }
        assert check_firewall_mock.check_ha_status(ignore_non_functional=True) == CheckResult(status=CheckStatus.SUCCESS)

    def test_check_ha_status_peer_info_local_info(self, check_firewall_mock):
        check_firewall_mock._node.get_ha_configuration.return_value = {
            "enabled": "yes",
            "group": {
                "mode": "Active-Passive",
                "local-info": {"state": "active"},
                "peer-info": {"state": "active"},
                "running-sync-enabled": "yes",
                "running-sync": "synchronized",
            },
        }
        assert check_firewall_mock.check_ha_status() == CheckResult(
            status=CheckStatus.ERROR, reason="Both devices have the same state: active."
        )

    def test_check_is_ha_active_success(self, check_firewall_mock):
        check_firewall_mock.check_ha_status = MagicMock()
        check_firewall_mock._node.get_ha_configuration.return_value = {
            "enabled": "yes",
            "group": {
                "mode": "Active-Passive",
                "local-info": {"state": "active"},
                "peer-info": {"state": "passive"},
                "running-sync-enabled": "yes",
                "running-sync": "synchronized",
            },
        }
        assert check_firewall_mock.check_is_ha_active() == CheckResult(status=CheckStatus.SUCCESS)

    def test_check_is_ha_active_fail(self, check_firewall_mock):
        check_firewall_mock.check_ha_status = MagicMock()
        check_firewall_mock._node.get_ha_configuration.return_value = {
            "enabled": "yes",
            "group": {
                "mode": "Active-Passive",
                "local-info": {"state": "someothervalue"},
                "peer-info": {"state": "passive"},
                "running-sync-enabled": "yes",
                "running-sync": "synchronized",
            },
        }
        assert check_firewall_mock.check_is_ha_active() == CheckResult(
            status=CheckStatus.FAIL, reason="Node state is: someothervalue."
        )

    def test_check_is_ha_active_no_ha_status(self, check_firewall_mock):
        check_ha_status_mock = MagicMock(return_value=False)
        check_firewall_mock.check_ha_status = check_ha_status_mock
        result = check_firewall_mock.check_is_ha_active()
        assert result is False

    def test_check_expired_licenses_true(self, check_firewall_mock):
        check_firewall_mock._node.get_licenses.return_value = {
            "AutoFocus Device License": {
                "authcode": "Snnnnnnn",
                "base-license-name": "PA-VM",
                "description": "AutoFocus Device License",
                "expired": "yes",
                "expires": "September 25, 2010",
                "feature": "AutoFocus Device License",
                "issued": "January 12, 2010",
                "serial": "xxxxxxxxxxxxxxxx",
            },
            "PA-VM": {
                "authcode": None,
                "description": "Standard VM-300",
                "expired": "yes",
                "expires": "September 25, 2010",
                "feature": "PA-VM",
                "issued": "January 12, 2010",
                "serial": "xxxxxxxxxxxxxxxx",
            },
        }
        assert check_firewall_mock.check_expired_licenses() == CheckResult(
            reason="Found expired licenses:  AutoFocus Device License, PA-VM."
        )

    def test_check_expired_licenses_false(self, check_firewall_mock):
        check_firewall_mock._node.get_licenses.return_value = {
            "AutoFocus Device License": {
                "authcode": "Snnnnnnn",
                "base-license-name": "PA-VM",
                "description": "AutoFocus Device License",
                "expired": "no",
                "expires": "September 25, 2099",
                "feature": "AutoFocus Device License",
                "issued": "January 12, 2010",
                "serial": "xxxxxxxxxxxxxxxx",
            },
            "PA-VM": {
                "authcode": None,
                "description": "Standard VM-300",
                "expired": "no",
                "expires": "September 25, 2099",
                "feature": "PA-VM",
                "issued": "January 12, 2010",
                "serial": "xxxxxxxxxxxxxxxx",
            },
        }
        assert check_firewall_mock.check_expired_licenses() == CheckResult(status=CheckStatus.SUCCESS)

    def test_check_expired_licenses_skip_licenses(self, check_firewall_mock):
        check_firewall_mock._node.get_licenses.return_value = {
            "AutoFocus Device License": {
                "authcode": "Snnnnnnn",
                "base-license-name": "PA-VM",
                "description": "AutoFocus Device License",
                "expired": "yes",
                "expires": "September 25, 2010",
                "feature": "AutoFocus Device License",
                "issued": "January 12, 2010",
                "serial": "xxxxxxxxxxxxxxxx",
            },
            "PA-VM": {
                "authcode": None,
                "description": "Standard VM-300",
                "expired": "no",
                "expires": "September 25, 2099",
                "feature": "PA-VM",
                "issued": "January 12, 2010",
                "serial": "xxxxxxxxxxxxxxxx",
            },
        }
        assert check_firewall_mock.check_expired_licenses(skip_licenses=["AutoFocus Device License"]) == CheckResult(
            status=CheckStatus.SUCCESS
        )

    def test_check_expired_licenses_param_exception(self, check_firewall_mock):
        with pytest.raises(WrongDataTypeException) as exception_msg:
            check_firewall_mock.check_expired_licenses(skip_licenses="not_a_list")

        assert str(exception_msg.value) == "The skip_licenses variable is a <class 'str'> but should be a list"

    def test_check_expired_licenses_not_licensed(self, check_firewall_mock):
        check_firewall_mock._node.get_licenses.side_effect = DeviceNotLicensedException
        assert check_firewall_mock.check_expired_licenses() == CheckResult(status=CheckStatus.ERROR)

    def test_check_critical_session_none(self, check_firewall_mock):
        assert check_firewall_mock.check_critical_session(source=None, destination="5.5.5.5", dest_port="443") == CheckResult(
            status=CheckStatus.SKIPPED, reason="Missing critical session description. Failing check."
        )

    def test_check_critical_session_empty_sessions(self, check_firewall_mock):
        check_firewall_mock._node.get_sessions.return_value = []
        assert check_firewall_mock.check_critical_session(
            source="10.10.10.10", destination="5.5.5.5", dest_port="443"
        ) == CheckResult(status=CheckStatus.ERROR, reason="Device's session table is empty.")

    def test_check_critical_session_sessions_in_list(self, check_firewall_mock):
        check_firewall_mock._node.get_sessions.return_value = [{"source": "10.10.10.10", "xdst": "5.5.5.5", "dport": "443"}]
        assert check_firewall_mock.check_critical_session(
            source="10.10.10.10", destination="5.5.5.5", dest_port="443"
        ) == CheckResult(status=CheckStatus.SUCCESS)

    def test_check_critical_session_not_found(self, check_firewall_mock):
        check_firewall_mock._node.get_sessions.return_value = [{"source": "10.10.10.10", "xdst": "5.5.5.5", "dport": "443"}]
        assert check_firewall_mock.check_critical_session(
            source="10.10.10.11", destination="5.5.5.6", dest_port="80"
        ) == CheckResult(status=CheckStatus.FAIL, reason="Session not found in session table.")

    def test_check_content_version_latest_installed(self, check_firewall_mock):
        check_firewall_mock._node.get_latest_available_content_version.return_value = "1111-0000"
        check_firewall_mock._node.get_content_db_version.return_value = "1111-0000"
        assert check_firewall_mock.check_content_version() == CheckResult(status=CheckStatus.SUCCESS)

    @pytest.mark.parametrize(
        "latest, installed",
        [
            ("1111-0123", "1111-0000"),  # compare minors with leading zero
            ("1111-1234", "1111-0000"),  # compare minors
            ("0123-0000", "0111-0000"),  # compare majors with leading zero
            ("1234-0000", "1111-0000"),  # compare majors
        ],
    )
    def test_check_content_version_latest_not_installed(self, latest, installed, check_firewall_mock):
        check_firewall_mock._node.get_latest_available_content_version.return_value = latest
        check_firewall_mock._node.get_content_db_version.return_value = installed
        assert check_firewall_mock.check_content_version() == CheckResult(
            status=CheckStatus.FAIL, reason=f"Installed content DB version ({installed}) is not the latest one ({latest})."
        )

    def test_check_content_version_installed_same_as_requested(self, check_firewall_mock):
        check_firewall_mock._node.get_content_db_version.return_value = "1111-0000"
        result = check_firewall_mock.check_content_version(version="1111-0000")
        assert result.status == CheckStatus.SUCCESS

    @pytest.mark.parametrize(
        "latest, installed",
        [
            ("1111-0000", "1234-0000"),  # compare majors
            ("0234-0000", "1234-0000"),  # compare majors with leading zero
            ("1111-0000", "1111-1234"),  # compare minors
            ("1111-0000", "1111-0123"),  # compare minors with leading zero
        ],
    )
    def test_check_content_version_installed_higher_than_latest_error(self, latest, installed, check_firewall_mock):
        check_firewall_mock._node.get_latest_available_content_version.return_value = latest
        check_firewall_mock._node.get_content_db_version.return_value = installed

        assert check_firewall_mock.check_content_version() == CheckResult(
            CheckStatus.ERROR,
            reason=f"Wrong data returned from device, installed version ({installed}) is higher than the required_version available ({latest}).",
        )

    @pytest.mark.parametrize(
        "installed, requested",
        [
            ("1111-0000", "1234-0000"),  # compare majors
            ("0234-0000", "1234-0000"),  # compare majors with leading zero
            ("1111-0000", "1111-1234"),  # compare minors
            ("1111-0000", "1111-0123"),  # compare minors with leading zero
        ],
    )
    def test_check_content_version_installed_lower_than_requested(self, installed, requested, check_firewall_mock):
        check_firewall_mock._node.get_content_db_version.return_value = installed
        assert check_firewall_mock.check_content_version(version=requested) == CheckResult(
            CheckStatus.FAIL, reason=f"Installed content DB version ({installed}) is older then the request one ({requested})."
        )

    @pytest.mark.parametrize(
        "installed, requested",
        [
            ("1111-0123", "1111-0000"),  # compare minors with leading zero
            ("1111-1234", "1111-0000"),  # compare minors
            ("0123-0000", "0111-0000"),  # compare majors with leading zero
            ("1234-0000", "1111-0000"),  # compare majors
        ],
    )
    def test_check_content_version_installed_higher_than_requested(self, installed, requested, check_firewall_mock):
        check_firewall_mock._node.get_content_db_version.return_value = installed
        assert check_firewall_mock.check_content_version(version=requested) == CheckResult(
            CheckStatus.SUCCESS,
            reason=f"Installed content DB version ({installed}) is higher than the requested one ({requested}).",
        )

    def test_check_content_version_format_error(self, check_firewall_mock):
        check_firewall_mock._node.get_latest_available_content_version.side_effect = ContentDBVersionsFormatException
        assert check_firewall_mock.check_content_version() == CheckResult(status=CheckStatus.ERROR)

    def test_check_ntp_synchronization_local_no_ntp(self, check_firewall_mock):
        check_firewall_mock._node.get_ntp_servers.return_value = {"synched": "LOCAL"}
        assert check_firewall_mock.check_ntp_synchronization() == CheckResult(
            status=CheckStatus.ERROR, reason="No NTP server configured."
        )

    def test_check_ntp_synchronization_local_no_ntp_sync(self, check_firewall_mock):
        check_firewall_mock._node.get_ntp_servers.return_value = {
            "ntp-server-1": {"authentication-type": "none", "name": "0.pool.ntp.org", "reachable": "yes", "status": "available"},
            "ntp-server-2": {"authentication-type": "none", "name": "1.pool.ntp.org", "reachable": "yes", "status": "synched"},
            "synched": "LOCAL",
        }
        assert check_firewall_mock.check_ntp_synchronization() == CheckResult(
            reason="No NTP synchronization in active, servers in following state: 0.pool.ntp.org - available, 1.pool.ntp.org - synched."
        )

    def test_check_ntp_synchronization_synched_ok(self, check_firewall_mock):
        check_firewall_mock._node.get_ntp_servers.return_value = {
            "ntp-server-1": {"authentication-type": "none", "name": "1.pool.ntp.org", "reachable": "yes", "status": "synched"},
            "synched": "1.pool.ntp.org",
        }
        assert check_firewall_mock.check_ntp_synchronization() == CheckResult(status=CheckStatus.SUCCESS)

    def test_check_ntp_synchronization_synched_unknown(self, check_firewall_mock):
        check_firewall_mock._node.get_ntp_servers.return_value = {"synched": "unknown"}
        assert check_firewall_mock.check_ntp_synchronization() == CheckResult(
            reason="NTP synchronization in unknown state: unknown."
        )

    def test_check_arp_entry_none(self, check_firewall_mock):
        assert check_firewall_mock.check_arp_entry(ip=None) == CheckResult(
            CheckStatus.SKIPPED, reason="Missing ARP table entry description."
        )

    def test_check_arp_entry_empty(self, check_firewall_mock):
        check_firewall_mock._node.get_arp_table.return_value = None

        assert check_firewall_mock.check_arp_entry(ip="5.5.5.5") == CheckResult(
            status=CheckStatus.ERROR, reason="ARP table empty."
        )

    def test_check_arp_entry_found(self, check_firewall_mock):
        check_firewall_mock._node.get_arp_table.return_value = {
            "ethernet1/1_10.0.2.1": {
                "interface": "ethernet1/1",
                "ip": "10.0.2.1",
                "mac": "12:34:56:78:9a:bc",
                "port": "ethernet1/1",
                "status": "c",
                "ttl": "1094",
            }
        }
        assert check_firewall_mock.check_arp_entry(ip="10.0.2.1", interface="ethernet1/1") == CheckResult(CheckStatus.SUCCESS)

    def test_check_arp_entry_found_without_interface(self, check_firewall_mock):
        check_firewall_mock._node.get_arp_table.return_value = {
            "ethernet1/1_10.0.2.1": {
                "interface": "ethernet1/1",
                "ip": "10.0.2.1",
                "mac": "12:34:56:78:9a:bc",
                "port": "ethernet1/1",
                "status": "c",
                "ttl": "1094",
            }
        }
        assert check_firewall_mock.check_arp_entry(ip="10.0.2.1") == CheckResult(CheckStatus.SUCCESS)

    def test_check_arp_entry_not_found(self, check_firewall_mock):
        check_firewall_mock._node.get_arp_table.return_value = {
            "ethernet1/1_10.0.2.1": {
                "interface": "ethernet1/1",
                "ip": "10.0.2.1",
                "mac": "12:34:56:78:9a:bc",
                "port": "ethernet1/1",
                "status": "c",
                "ttl": "1094",
            }
        }
        assert check_firewall_mock.check_arp_entry(ip="10.0.3.1", interface="ethernet1/2") == CheckResult(
            reason="Entry not found in ARP table."
        )

    def test_ipsec_tunnel_status_none(self, check_firewall_mock):
        assert check_firewall_mock.check_ipsec_tunnel_status(tunnel_name=None) == CheckResult(
            CheckStatus.SKIPPED, reason="Missing tunnel specification."
        )

    def test_ipsec_tunnel_status_no_ipsec_tunnels(self, check_firewall_mock):
        check_firewall_mock._node.get_tunnels.return_value = {"key": "value"}

        assert check_firewall_mock.check_ipsec_tunnel_status(tunnel_name="MyTunnel") == CheckResult(
            CheckStatus.ERROR, reason="No IPSec Tunnel is configured on the device."
        )

    def test_ipsec_tunnel_status_active(self, check_firewall_mock):
        check_firewall_mock._node.get_tunnels.return_value = {"IPSec": {"MyTunnel": {"state": "active"}}}
        assert check_firewall_mock.check_ipsec_tunnel_status(tunnel_name="MyTunnel") == CheckResult(CheckStatus.SUCCESS)

    def test_ipsec_tunnel_status_not_active(self, check_firewall_mock):
        check_firewall_mock._node.get_tunnels.return_value = {"IPSec": {"MyTunnel": {"state": "down"}}}
        assert check_firewall_mock.check_ipsec_tunnel_status(tunnel_name="MyTunnel") == CheckResult(
            CheckStatus.FAIL, reason="Tunnel MyTunnel in state: down."
        )

    def test_ipsec_tunnel_status_not_found(self, check_firewall_mock):
        check_firewall_mock._node.get_tunnels.return_value = {"IPSec": {"MyTunnel": {"state": "active"}}}
        assert check_firewall_mock.check_ipsec_tunnel_status(tunnel_name="NotMyTunnel") == CheckResult(
            reason="Tunnel NotMyTunnel not found."
        )

    def test_check_free_disk_space_ok(self, check_firewall_mock):
        check_firewall_mock._node.get_disk_utilization.return_value = {"/opt/panrepo": 50000}

        assert check_firewall_mock.check_free_disk_space() == CheckResult(CheckStatus.SUCCESS)

    def test_check_free_disk_space_nok(self, check_firewall_mock):
        check_firewall_mock._node.get_disk_utilization.return_value = {"/opt/panrepo": 50}

        assert check_firewall_mock.check_free_disk_space() == CheckResult(
            CheckStatus.FAIL, reason="There is not enough free space, only 50MB is available."
        )

    def test_check_free_disk_space_with_available_version(self, check_firewall_mock):
        check_firewall_mock._node.get_available_image_data.return_value = {"9.0.0": {"size": "2000"}}
        check_firewall_mock._node.get_disk_utilization.return_value = {"/opt/panrepo": 3000}

        assert check_firewall_mock.check_free_disk_space("9.0.0").status == CheckStatus.SUCCESS

    def test_check_free_disk_space_with_base_image(self, check_firewall_mock):
        check_firewall_mock._node.get_available_image_data.return_value = {
            "9.0.0": {"size": "2000", "downloaded": "no"},
            "9.0.1": {"size": "500", "downloaded": "no"},
        }
        check_firewall_mock._node.get_disk_utilization.return_value = {"/opt/panrepo": 3000}

        assert check_firewall_mock.check_free_disk_space("9.0.1").status == CheckStatus.SUCCESS

    def test_check_free_disk_space_with_unavailable_base_image(self, check_firewall_mock):
        check_firewall_mock._node.get_available_image_data.return_value = {"9.2.2": {"size": "2000"}}
        check_firewall_mock._node.get_disk_utilization.return_value = {"/opt/panrepo": 5000}

        assert check_firewall_mock.check_free_disk_space("9.2.2") == CheckResult(
            CheckStatus.SUCCESS, reason="Base image 9.2.0 does not exist."
        )

    def test_check_free_disk_space_image_does_not_exist(self, check_firewall_mock):
        check_firewall_mock._node.get_available_image_data.return_value = {"9.2.2": {"size": "2000"}}
        check_firewall_mock._node.get_disk_utilization.return_value = {"/opt/panrepo": 5000}

        assert check_firewall_mock.check_free_disk_space("9.1.1") == CheckResult(
            CheckStatus.SUCCESS, reason="Image 9.1.1 does not exist."
        )

    def test_check_free_disk_space_connectivity_error(self, check_firewall_mock):
        check_firewall_mock._node.get_available_image_data.side_effect = UpdateServerConnectivityException(
            "Unable to retrieve target image size most probably due to network issues or because the device is not licensed."
        )

        assert check_firewall_mock.check_free_disk_space("9.0.0") == CheckResult(
            CheckStatus.ERROR,
            reason="Unable to retrieve target image size most probably due to network issues or because the device is not licensed.",
        )

    def test_check_free_disk_space_format_error(self, check_firewall_mock):
        check_firewall_mock._node.get_disk_utilization.side_effect = WrongDiskSizeFormatException

        assert check_firewall_mock.check_free_disk_space() == CheckResult(CheckStatus.ERROR)

    def test_get_content_db_version(self, check_firewall_mock):
        check_firewall_mock._node.get_content_db_version.return_value = "5555-6666"

        assert check_firewall_mock.get_content_db_version() == {"version": "5555-6666"}

    def test_get_ip_sec_tunnels(self, check_firewall_mock):
        check_firewall_mock._node.get_tunnels.return_value = {"IPSec": {"MyTunnel": {"name": "tunnel_name"}}}

        check_firewall_mock.get_ip_sec_tunnels() == {"MyTunnel": {"name": "tunnel_name"}}

    def test_check_active_support_license_not_licensed(self, check_firewall_mock):
        check_firewall_mock._node.get_licenses.side_effect = DeviceNotLicensedException

        assert check_firewall_mock.check_active_support_license() == CheckResult(status=CheckStatus.ERROR)

    def test_check_active_support_license_connectivity_error(self, check_firewall_mock):
        check_firewall_mock._node.get_support_license.side_effect = UpdateServerConnectivityException(
            "Can not reach update servers to check active support license."
        )

        assert check_firewall_mock.check_active_support_license() == CheckResult(
            CheckStatus.ERROR, reason="Can not reach update servers to check active support license."
        )

    def test_check_active_support_license_no_expiry_date(self, check_firewall_mock):
        check_firewall_mock._node.get_support_license.return_value = {"support_expiry_date": ""}

        assert check_firewall_mock.check_active_support_license() == CheckResult(
            status=CheckStatus.ERROR, reason="No ExpiryDate found for support license."
        )

    def test_check_active_support_license_expired(self, check_firewall_mock):
        check_firewall_mock._node.get_support_license.return_value = {"support_expiry_date": "June 06, 2023"}

        assert check_firewall_mock.check_active_support_license() == CheckResult(
            status=CheckStatus.FAIL, reason="Support License expired."
        )

    def test_check_active_support_license_success(self, check_firewall_mock):
        check_firewall_mock._node.get_support_license.return_value = {"support_expiry_date": "June 06, 9999"}

        assert check_firewall_mock.check_active_support_license() == CheckResult(status=CheckStatus.SUCCESS)

    def test_check_mp_dp_sync_wrong_input_data(self, check_firewall_mock):
        with pytest.raises(WrongDataTypeException) as exception_msg:
            check_firewall_mock.check_mp_dp_sync("1.0")

        assert str(exception_msg.value) == "[diff_threshold] should be of type [int] but is of type [<class 'str'>]."

    def test_check_mp_dp_sync_time_diff(self, check_firewall_mock):
        check_firewall_mock._node.get_mp_clock.return_value = datetime.strptime(
            "Wed May 31 11:50:21 2023", "%a %b %d %H:%M:%S %Y"
        )
        check_firewall_mock._node.get_dp_clock.return_value = datetime.strptime(
            "Wed May 31 11:52:34 2023", "%a %b %d %H:%M:%S %Y"
        )

        assert check_firewall_mock.check_mp_dp_sync(1) == CheckResult(
            status=CheckStatus.FAIL, reason="The data plane clock and management clock are different by 133.0 seconds."
        )

    def test_check_mp_dp_sync_time_diff_with_threshold(self, check_firewall_mock):
        check_firewall_mock._node.get_mp_clock.return_value = datetime.strptime(
            "Wed May 31 11:50:21 2023", "%a %b %d %H:%M:%S %Y"
        )
        check_firewall_mock._node.get_dp_clock.return_value = datetime.strptime(
            "Wed May 31 11:50:34 2023", "%a %b %d %H:%M:%S %Y"
        )

        assert check_firewall_mock.check_mp_dp_sync(30) == CheckResult(status=CheckStatus.SUCCESS)

    def test_check_mp_dp_sync_time_synced(self, check_firewall_mock):
        check_firewall_mock._node.get_mp_clock.return_value = datetime.strptime(
            "Wed May 31 11:50:21 2023", "%a %b %d %H:%M:%S %Y"
        )
        check_firewall_mock._node.get_dp_clock.return_value = datetime.strptime(
            "Wed May 31 11:50:21 2023", "%a %b %d %H:%M:%S %Y"
        )

        assert check_firewall_mock.check_mp_dp_sync(1) == CheckResult(status=CheckStatus.SUCCESS)

    @pytest.mark.parametrize(
        "param_rsa, param_ecdsa, exc_msg",
        [
            (
                {"hash_method": "SHA256", "size": 4096},
                {},
                "Unknown configuration parameter(s) found in the `rsa` dictionary: hash_method, size.",
            ),
            (
                {},
                {"hash": "SHA256", "key_size": 384},
                "Unknown configuration parameter(s) found in the `ecdsa` dictionary: hash, key_size.",
            ),
        ],
    )
    def test_check_ssl_cert_requirements_param_exception(self, param_rsa, param_ecdsa, exc_msg, check_firewall_mock):
        with pytest.raises(UnknownParameterException) as exception_msg:
            check_firewall_mock.check_ssl_cert_requirements(rsa=param_rsa, ecdsa=param_ecdsa)

        assert str(exception_msg.value) == exc_msg

    def test_check_ssl_cert_requirements_no_certificates(self, check_firewall_mock):
        check_firewall_mock._node.get_certificates.return_value = {}

        assert check_firewall_mock.check_ssl_cert_requirements() == CheckResult(
            status=CheckStatus.SKIPPED, reason="No certificates installed on device."
        )

    def test_check_ssl_cert_requirements_rsa_not_supported_hash(self, check_firewall_mock):
        rsa = {"hash_method": "SHA3", "key_size": 2048}

        assert check_firewall_mock.check_ssl_cert_requirements(rsa=rsa) == CheckResult(
            status=CheckStatus.ERROR, reason="The provided minimum RSA hashing method (SHA3) is not supported."
        )

    def test_check_ssl_cert_requirements_ecdsa_not_supported_hash(self, check_firewall_mock):
        ecdsa = {"hash_method": "SHA3", "key_size": 256}

        assert check_firewall_mock.check_ssl_cert_requirements(ecdsa=ecdsa) == CheckResult(
            status=CheckStatus.ERROR, reason="The provided minimum ECDSA hashing method (SHA3) is not supported."
        )

    @pytest.mark.parametrize("key_size", ["-100", "abc"])
    def test_check_ssl_cert_requirements_rsa_invalid_key_size(self, key_size, check_firewall_mock):
        rsa = {"hash_method": "SHA256", "key_size": key_size}

        assert check_firewall_mock.check_ssl_cert_requirements(rsa=rsa) == CheckResult(
            status=CheckStatus.ERROR, reason="The provided minimum RSA key size should be an integer greater than 0."
        )

    @pytest.mark.parametrize("key_size", ["-100", "abc"])
    def test_check_ssl_cert_requirements_ecdsa_invalid_key_size(self, key_size, check_firewall_mock):
        ecdsa = {"hash_method": "SHA256", "key_size": key_size}

        assert check_firewall_mock.check_ssl_cert_requirements(ecdsa=ecdsa) == CheckResult(
            status=CheckStatus.ERROR, reason="The provided minimum ECDSA key size should be an integer greater than 0."
        )

    def test_check_ssl_cert_requirements_cert_algorithm_not_supported(self, check_firewall_mock, monkeypatch):
        certificates = {"cert1": {"public-key": "public_key_data", "algorithm": "DSA"}}
        check_firewall_mock._node.get_certificates = lambda: certificates

        class MockCert:
            def get_pubkey(self):
                return MockBits()

            def to_cryptography(self):
                return MockCryptography()

        class MockBits:
            def bits(self):
                return 2048

        class MockCryptography:
            @property
            def signature_hash_algorithm(self):
                return MockHashAlgorithm()

        class MockHashAlgorithm:
            @property
            def name(self):
                return "SHA256"

        def ossl_load_certificate_mock(*args, **kwargs):
            return MockCert()

        monkeypatch.setattr("OpenSSL.crypto.load_certificate", ossl_load_certificate_mock)

        assert check_firewall_mock.check_ssl_cert_requirements() == CheckResult(
            status=CheckStatus.ERROR, reason="Failed for certificate: cert1: unknown algorithm DSA."
        )

    def test_check_ssl_cert_requirements_cert_hash_not_supported(self, check_firewall_mock, monkeypatch):
        certificates = {"cert1": {"public-key": "public_key_data", "algorithm": "RSA"}}
        check_firewall_mock._node.get_certificates = lambda: certificates

        class MockCert:
            def get_pubkey(self):
                return MockBits()

            def to_cryptography(self):
                return MockCryptography()

        class MockBits:
            def bits(self):
                return 2048

        class MockCryptography:
            @property
            def signature_hash_algorithm(self):
                return MockHashAlgorithm()

        class MockHashAlgorithm:
            @property
            def name(self):
                return "UNKNOWN_HASH"

        def ossl_load_certificate_mock(*args, **kwargs):
            return MockCert()

        monkeypatch.setattr("OpenSSL.crypto.load_certificate", ossl_load_certificate_mock)

        result = check_firewall_mock.check_ssl_cert_requirements()
        assert result.status == CheckStatus.ERROR
        assert result.reason == "The certificate's hashing method (UNKNOWN_HASH) is not supported? Please check the device."

    def test_check_ssl_cert_requirements_failed_certs_rsa(self, check_firewall_mock, monkeypatch):
        rsa = {"hash_method": "SHA256", "key_size": 4096}  # required key size

        certificates = {
            "cert1": {
                "public-key": "public_key_data",
                "algorithm": "RSA",
            },
        }
        check_firewall_mock._node.get_certificates = lambda: certificates

        class MockCert:
            def get_pubkey(self):
                return MockBits()

            def to_cryptography(self):
                return MockCryptography()

        class MockBits:
            def bits(self):
                return 2048  # key size returned from ossl

        class MockCryptography:
            @property
            def signature_hash_algorithm(self):
                return MockHashAlgorithm()

        class MockHashAlgorithm:
            @property
            def name(self):
                return "SHA256"

        def ossl_load_certificate_mock(*args, **kwargs):
            return MockCert()

        monkeypatch.setattr("OpenSSL.crypto.load_certificate", ossl_load_certificate_mock)

        result = check_firewall_mock.check_ssl_cert_requirements(rsa=rsa)
        assert result.status == CheckStatus.FAIL
        assert result.reason == "Following certificates do not meet required criteria: cert1 (size: 2048, hash: SHA256)."

    def test_check_ssl_cert_requirements_failed_certs_ecdsa(self, check_firewall_mock, monkeypatch):
        ecdsa = {"hash_method": "SHA256", "key_size": 384}  # required key size

        certificates = {
            "cert2": {
                "public-key": "public_key_data",
                "algorithm": "EC",
            }
        }
        check_firewall_mock._node.get_certificates = lambda: certificates

        class MockCert:
            def get_pubkey(self):
                return MockBits()

            def to_cryptography(self):
                return MockCryptography()

        class MockBits:
            def bits(self):
                return 256  # key size returned from ossl

        class MockCryptography:
            @property
            def signature_hash_algorithm(self):
                return MockHashAlgorithm()

        class MockHashAlgorithm:
            @property
            def name(self):
                return "SHA256"

        def ossl_load_certificate_mock(*args, **kwargs):
            return MockCert()

        monkeypatch.setattr("OpenSSL.crypto.load_certificate", ossl_load_certificate_mock)

        result = check_firewall_mock.check_ssl_cert_requirements(ecdsa=ecdsa)
        assert result.status == CheckStatus.FAIL
        assert result.reason == "Following certificates do not meet required criteria: cert2 (size: 256, hash: SHA256)."

    def test_check_ssl_cert_requirements_success(self, check_firewall_mock):
        rsa = {"hash_method": "SHA256", "key_size": 2048}
        ecdsa = {"hash_method": "SHA256", "key_size": 256}

        certificates = {
            "cert1": {  # rsa key size 2048
                "public-key": """-----BEGIN CERTIFICATE-----
MIICiDCCAfGgAwIBAgIEWo92UzANBgkqhkiG9w0BAQsFADAPMQ0wCwYDVQQDDARy
b290MB4XDTIzMDYxOTA4MzYxMloXDTI0MDYxODA4MzYxMlowDzENMAsGA1UEAwwE
Y2VydDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAO7CKS7qrdSblk8E
56Abkd9ikJVFDiDM7kC6l9ezKF4TK5q3tYbKywBiiNHw3DrRvuzwg3GsXDMSaUZZ
ItsyOOxE4G6Ai48X0gSzAY5aQU2WY+1MErEWR0sMSxSVzNGkPVEDAQmI2KFPrzvX
U4JGoOXwEsq4tH39nkj7Mo7VfKM/bsZ0obA8llt9VyjBCF1uN9+J1G+nY9mUzyEC
yFemEexgMqWqmSY9DiL1xwFLfTog73zCvu9SfzvFzUEg+q/16RJF766AVb8TT27d
KBowEpPdOqmWOXLbiZh9CzP4/GZZQuIWjS+DmSzI3nyDGF591iridlmmuTjPOyEy
FnEfwsUCAwEAAaNtMGswCQYDVR0TBAIwADALBgNVHQ8EBAMCA7gwJwYDVR0lBCAw
HgYIKwYBBQUHAwEGCCsGAQUFBwMCBggrBgEFBQcDBTAJBgNVHSMEAjAAMB0GA1Ud
DgQWBBRmVL1rXamoHiqE1+MWuKhFx4y3lzANBgkqhkiG9w0BAQsFAAOBgQA2d4v4
ABP1sOk603DTgwF3BmKGJLmdsbzD/GGYH1vs9INOxs/ftcbyld5uNJ8XCVZIX16l
DbCDmPxxUkiQsjjGxKNKUh33xiqPWM8oqzGxbaLy9SK3YBl5leBPbI4rNozderlm
BHR62OTIlfRtS0hwLUYkwdis/Tt0v0sc2hJxVw==
-----END CERTIFICATE-----""",
                "algorithm": "RSA",
            },
            "cert2": {  # ecdsa key size 256
                "public-key": """-----BEGIN CERTIFICATE-----
MIIBaTCCAQ+gAwIBAgIBBDAKBggqhkjOPQQDAjAYMRYwFAYDVQQDDA1BU2VjdXJp
dHlzaXRlMB4XDTE1MTIzMTIzNTk1OVoXDTI1MTIzMTIzNTk1OVowFTETMBEGA1UE
AwwKV2ViIHNlcnZlcjBZMBMGByqGSM49AgEGCCqGSM49AwEHA0IABCSmjAROGnxw
0PgGFkiakV/v/gKKJwRSv3qMEvQ6B1zWbhzCYHTNu7oVW3vmfvQD6nv0VqTIQRc5
o8f1Fv0ZBn6jTTBLMAkGA1UdEwQCMAAwDgYDVR0PAQH/BAQDAgeAMC4GA1UdHwQn
MCUwI6AhoB+GHWh0dHA6Ly9ib2IuYXNlY3VyaXR5c2l0ZS5jb20vMAoGCCqGSM49
BAMCA0gAMEUCIQCFSCjlrfMKHI+QD/kcs3iZSkA2q3BlhR2zH8+fkSUdXgIgD70Z
UT1F7XqZcTWaThXLFMpQyUvUpuhilcmzucrvVI0=
-----END CERTIFICATE-----""",
                "algorithm": "EC",
            },
        }
        check_firewall_mock._node.get_certificates = lambda: certificates

        assert check_firewall_mock.check_ssl_cert_requirements(rsa=rsa, ecdsa=ecdsa) == CheckResult(status=CheckStatus.SUCCESS)

    @pytest.mark.parametrize(
        "param_now_dts, param_schedule_type, param_schedule, param_time_d, param_details",
        [
            (
                "2023-08-07 00:00:00",  # this is Monday
                "daily",
                {"action": "download-and-install", "at": "07:45"},
                465,
                "at 07:45:00",
            ),
            ("2023-08-07 00:00:00", "hourly", {"action": "download-and-install", "at": "0"}, 60, "every hour"),  # this is Monday
            (
                "2023-08-07 00:00:00",  # this is Monday
                "every-5-mins",
                {"action": "download-and-install", "at": "1"},
                5,
                "every 5 minutes",
            ),
            ("2023-08-07 00:00:00", "real-time", None, 0, "unpredictable (real-time)"),  # this is Monday
        ],
    )
    def test__calculate_schedule_time_diff(
        self, param_now_dts, param_schedule_type, param_schedule, param_time_d, param_details, check_firewall_mock
    ):
        mock_now_dt = datetime.strptime(param_now_dts, "%Y-%m-%d %H:%M:%S")

        time_delta, delta_reason = check_firewall_mock._calculate_schedule_time_diff(
            mock_now_dt, param_schedule_type, param_schedule
        )

        assert time_delta == param_time_d
        assert delta_reason == param_details

    @pytest.mark.parametrize("param_schedule_type", ["every-something", "something"])
    def test__calculate_schedule_time_diff_exception(self, param_schedule_type, check_firewall_mock):
        with pytest.raises(MalformedResponseException) as exception_msg:
            check_firewall_mock._calculate_schedule_time_diff(datetime.now(), param_schedule_type, None)

        assert str(exception_msg.value) == f"Unknown schedule type: {param_schedule_type}."

    @pytest.mark.parametrize(
        "param_now_dts, param_test_window, param_schedules_block, check_result",
        [
            (
                "2023-08-07 00:00:00",  # this is Monday
                120,
                {"anti-virus": {"recurring": {"daily": {"action": "download-and-install", "at": "07:45"}}}},
                CheckResult(CheckStatus.SUCCESS, ""),
            ),
            (
                "2023-08-07 00:00:00",  # this is Monday
                120,
                {"anti-virus": {"recurring": {"real-time": None}}},
                CheckResult(
                    CheckStatus.FAIL, "Following schedules fall into test window: anti-virus (unpredictable (real-time))."
                ),
            ),
            (
                "2023-08-07 07:00:00",  # this is Monday
                60,
                {"anti-virus": {"recurring": {"daily": {"action": "download-and-install", "at": "07:45"}}}},
                CheckResult(CheckStatus.FAIL, "Following schedules fall into test window: anti-virus (at 07:45:00)."),
            ),
            (
                "2023-08-07 00:00:00",  # this is Monday
                180,
                {
                    "global-protect-datafile": {
                        "recurring": {"weekly": {"action": "download-and-install", "at": "02:45", "day-of-week": "monday"}}
                    },
                    "threats": {"recurring": {"daily": {"action": "download-and-install", "at": "15:30"}}},
                },
                CheckResult(CheckStatus.FAIL, "Following schedules fall into test window: global-protect-datafile (in 2:45:00)."),
            ),
            (
                "2023-08-07 07:00:00",  # this is Monday
                20,
                {},
                CheckResult(CheckStatus.SKIPPED, "No scheduled job present on the device."),
            ),
            (
                "2023-08-07 07:00:00",  # this is Monday
                20,
                {"anti-virus": {"recurring": {"real-time": None}}},
                CheckResult(CheckStatus.ERROR, "Schedules test window is below the supported, safe minimum of 60 minutes."),
            ),
            (
                "2023-08-07 07:00:00",  # this is Monday
                10081,
                {"anti-virus": {"recurring": {"real-time": None}}},
                CheckResult(CheckStatus.ERROR, "Schedules test window is set to over 1 week. This test will always fail."),
            ),
        ],
    )
    def test_check_scheduled_updates(
        self, param_now_dts, param_test_window, param_schedules_block, check_result, check_firewall_mock
    ):
        now_dt = datetime.strptime(param_now_dts, "%Y-%m-%d %H:%M:%S")
        check_firewall_mock._node.get_mp_clock = lambda: now_dt

        check_firewall_mock._node.get_update_schedules = lambda: param_schedules_block

        assert check_firewall_mock.check_scheduled_updates(param_test_window) == check_result

    def test_check_jobs_success(self, check_firewall_mock):
        jobs = {
            "4": {
                "tenq": "2023/08/07 04:00:40",
                "tdeq": "04:00:40",
                "user": "Auto update agent",
                "type": "WildFire",
                "status": "FIN",
                "queued": "NO",
                "stoppable": "no",
                "result": "OK",
                "tfin": "2023/08/07 04:00:45",
                "description": None,
                "positionInQ": "0",
                "progress": "2023/08/07 04:00:45",
                "details": {"line": ["Configuration committed successfully", "Successfully committed last configuration"]},
                "warnings": None,
            },
            "1": {
                "tenq": "2023/08/07 03:59:57",
                "tdeq": "03:59:57",
                "user": None,
                "type": "AutoCom",
                "status": "FIN",
                "queued": "NO",
                "stoppable": "no",
                "result": "OK",
                "tfin": "2023/08/07 04:00:28",
                "description": None,
                "positionInQ": "0",
                "progress": "100",
                "details": {"line": ["Configuration committed successfully", "Successfully committed last configuration"]},
                "warnings": None,
            },
        }

        check_firewall_mock._node.get_jobs = lambda: jobs

        assert check_firewall_mock.check_non_finished_jobs() == CheckResult(status=CheckStatus.SUCCESS)

    def test_check_jobs_failure(self, check_firewall_mock):
        jobs = {
            "4": {
                "tenq": "2023/08/07 04:00:40",
                "tdeq": "04:00:40",
                "user": "Auto update agent",
                "type": "WildFire",
                "status": "ACC",
                "queued": "NO",
                "stoppable": "no",
                "result": "OK",
                "tfin": "2023/08/07 04:00:45",
                "description": None,
                "positionInQ": "0",
                "progress": "2023/08/07 04:00:45",
                "details": {"line": ["Configuration committed successfully", "Successfully committed last configuration"]},
                "warnings": None,
            },
            "1": {
                "tenq": "2023/08/07 03:59:57",
                "tdeq": "03:59:57",
                "user": None,
                "type": "AutoCom",
                "status": "FIN",
                "queued": "NO",
                "stoppable": "no",
                "result": "OK",
                "tfin": "2023/08/07 04:00:28",
                "description": None,
                "positionInQ": "0",
                "progress": "100",
                "details": {"line": ["Configuration committed successfully", "Successfully committed last configuration"]},
                "warnings": None,
            },
        }
        check_firewall_mock._node.get_jobs = lambda: jobs
        result = CheckResult(status=CheckStatus.FAIL, reason="At least one job (ID=4) is not in finished state (state=ACC).")
        assert check_firewall_mock.check_non_finished_jobs() == result

    def test_check_jobs_no_jobs(self, check_firewall_mock):
        check_firewall_mock._node.get_jobs = lambda: {}
        result = CheckResult(status=CheckStatus.SKIPPED, reason="No jobs found on device. This is unusual, please investigate.")
        assert check_firewall_mock.check_non_finished_jobs() == result

    def test_run_readiness_checks(self, check_firewall_mock):
        check_firewall_mock._check_method_mapping = {
            "check1": MagicMock(return_value=True),
            "check2": MagicMock(return_value=False),
        }

        checks_configuration = ["check1", {"check2": {"param1": 123}}]
        report_style = False

        result = check_firewall_mock.run_readiness_checks(checks_configuration, report_style)

        expected_result = {
            "check1": {"state": True, "reason": "True"},
            "check2": {"state": False, "reason": "False"},
        }
        assert result == expected_result

        check_firewall_mock._check_method_mapping["check1"].assert_called_once_with()
        check_firewall_mock._check_method_mapping["check2"].assert_called_once_with(param1=123)

    def test_run_readiness_checks_empty_dict(self, check_firewall_mock):
        check_firewall_mock._check_method_mapping = {
            "check1": MagicMock(return_value=True),
        }

        checks_configuration = [{"check1": None}]
        report_style = False

        result = check_firewall_mock.run_readiness_checks(checks_configuration, report_style)

        expected_result = {
            "check1": {"state": True, "reason": "True"},
        }
        assert result == expected_result

        check_firewall_mock._check_method_mapping["check1"].assert_called_once_with()

    def test_run_readiness_checks_wrong_data_type_exception(self, check_firewall_mock):
        # Set up the input parameters for the method
        checks_configuration = ["check1", [123]]
        report_style = False

        with pytest.raises(WrongDataTypeException):
            check_firewall_mock.run_readiness_checks(checks_configuration, report_style)

        # raise exceptions.WrongDataTypeException(f"Wrong configuration format for check: {check}.")
        # NOTE configs are already validated in ConfigParser._extrac_element_name - above exception is never executed.
        # which is listed as missing in pytest coverage
        # assert str(exception_msg.value) == f"Wrong configuration format for check: check1."

    def test_run_snapshots(self, check_firewall_mock):
        check_firewall_mock._snapshot_method_mapping = {
            "snapshot1": MagicMock(return_value={"status": "success"}),
            "snapshot2": MagicMock(return_value={"status": "failed"}),
        }

        snapshots_config = ["snapshot1", "snapshot2"]

        result = check_firewall_mock.run_snapshots(snapshots_config)

        expected_result = {
            "snapshot1": {"status": "success"},
            "snapshot2": {"status": "failed"},
        }
        assert result == expected_result

        check_firewall_mock._snapshot_method_mapping["snapshot1"].assert_called_once_with()
        check_firewall_mock._snapshot_method_mapping["snapshot2"].assert_called_once_with()

    def test_run_snapshots_wrong_data_type_exception(self, check_firewall_mock):
        snapshots_config = ["snapshot1", 123]

        with pytest.raises(WrongDataTypeException):
            check_firewall_mock.run_snapshots(snapshots_config)

        # raise exceptions.WrongDataTypeException(f"Wrong configuration format for snapshot: {snap_type}.")
        # NOTE configs are already validated in ConfigParser._extrac_element_name - above exception is never executed.
        # which is listed as missing in pytest coverage
        # assert str(exception_msg.value) == f"Wrong configuration format for snapshot: snap_type."

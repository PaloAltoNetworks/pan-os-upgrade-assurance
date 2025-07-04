import panos.errors
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

    def test_ipsec_tunnel_status_proxyids_not_found(self, check_firewall_mock):
        """tunnel with proxyids - proxyids given but not found"""
        check_firewall_mock._node.get_tunnels.return_value = {
            "IPSec": {
                "east1-vpn:ProxyID1": {"state": "active"},
                "east1-vpn:ProxyID2": {"state": "active"},
                "central1-vpn:ProxyID1": {"state": "init"},
            }
        }
        assert check_firewall_mock.check_ipsec_tunnel_status(
            tunnel_name="east1-vpn", proxy_ids=["ProxyID1", "ProxyID3"]
        ) == CheckResult(reason="Tunnel east1-vpn has missing ProxyIDs in ['ProxyID1', 'ProxyID3'].")

    @pytest.mark.parametrize(
        "require_all_active, expected_status",
        [
            (True, CheckStatus.SUCCESS),
            (False, CheckStatus.SUCCESS),
        ],
    )
    def test_ipsec_tunnel_status_proxyids_all_active(self, require_all_active, expected_status, check_firewall_mock):
        """tunnel with proxyids - proxyids given and all active
        Should return success whether require_all_active is True or False.
        """
        check_firewall_mock._node.get_tunnels.return_value = {
            "IPSec": {
                "east1-vpn:ProxyID1": {"state": "active"},
                "east1-vpn:ProxyID2": {"state": "active"},
                "east1-vpn:ProxyID3": {"state": "active"},
                "central1-vpn:ProxyID1": {"state": "init"},
            }
        }
        assert check_firewall_mock.check_ipsec_tunnel_status(
            tunnel_name="east1-vpn", proxy_ids=["ProxyID1", "ProxyID2", "ProxyID3"], require_all_active=require_all_active
        ) == CheckResult(expected_status)

    @pytest.mark.parametrize(
        "require_all_active, expected_status, reason",
        [
            (True, CheckStatus.FAIL, "Tunnel:ProxyID east1-vpn:ProxyID3 in state: init."),
            (False, CheckStatus.SUCCESS, ""),
        ],
    )
    def test_ipsec_tunnel_status_proxyids_some_active(self, require_all_active, expected_status, reason, check_firewall_mock):
        """tunnel with proxyids - proxyids given and some active
        Should return fail by default. Success if require_all_active is False.
        """
        check_firewall_mock._node.get_tunnels.return_value = {
            "IPSec": {
                "east1-vpn:ProxyID1": {"state": "active"},
                "east1-vpn:ProxyID2": {"state": "active"},
                "east1-vpn:ProxyID3": {"state": "init"},
                "central1-vpn:ProxyID1": {"state": "init"},
            }
        }
        assert check_firewall_mock.check_ipsec_tunnel_status(
            tunnel_name="east1-vpn", proxy_ids=["ProxyID1", "ProxyID2", "ProxyID3"], require_all_active=require_all_active
        ) == CheckResult(expected_status, reason=reason)

    @pytest.mark.parametrize(
        "require_all_active, expected_status, reason",
        [
            (True, CheckStatus.FAIL, "Tunnel:ProxyID east1-vpn:ProxyID1 in state: init."),
            (False, CheckStatus.FAIL, "No active state for tunnel east1-vpn in ProxyIDs ['ProxyID1', 'ProxyID2', 'ProxyID3']."),
        ],
    )
    def test_ipsec_tunnel_status_proxyids_none_active(self, require_all_active, expected_status, reason, check_firewall_mock):
        """tunnel with proxyids - proxyids given and all not active
        Should return fail whether require_all_active is True or False.
        """
        check_firewall_mock._node.get_tunnels.return_value = {
            "IPSec": {
                "east1-vpn:ProxyID1": {"state": "init"},
                "east1-vpn:ProxyID2": {"state": "init"},
                "east1-vpn:ProxyID3": {"state": "init"},
                "central1-vpn:ProxyID1": {"state": "active"},
            }
        }
        assert check_firewall_mock.check_ipsec_tunnel_status(
            tunnel_name="east1-vpn", proxy_ids=["ProxyID1", "ProxyID2", "ProxyID3"], require_all_active=require_all_active
        ) == CheckResult(expected_status, reason=reason)

    @pytest.mark.parametrize(
        "require_all_active, expected_status",
        [
            (True, CheckStatus.SUCCESS),
            (False, CheckStatus.SUCCESS),
        ],
    )
    def test_ipsec_tunnel_status_none_proxyids_all_active(self, require_all_active, expected_status, check_firewall_mock):
        """tunnel with proxyids - proxyids not given and all active"""
        check_firewall_mock._node.get_tunnels.return_value = {
            "IPSec": {
                "east1-vpn:ProxyID1": {"state": "active"},
                "east1-vpn:ProxyID2": {"state": "active"},
                "east1-vpn:ProxyID3": {"state": "active"},
                "central1-vpn:ProxyID1": {"state": "init"},
            }
        }
        assert check_firewall_mock.check_ipsec_tunnel_status(
            tunnel_name="east1-vpn", require_all_active=require_all_active
        ) == CheckResult(expected_status)

        assert check_firewall_mock.check_ipsec_tunnel_status(
            tunnel_name="east1-vpn", proxy_ids=[], require_all_active=require_all_active
        ) == CheckResult(expected_status)

    @pytest.mark.parametrize(
        "require_all_active, expected_status, reason",
        [
            (True, CheckStatus.FAIL, "Tunnel:ProxyID east1-vpn:ProxyID2 in state: init."),
            (False, CheckStatus.SUCCESS, ""),
        ],
    )
    def test_ipsec_tunnel_status_none_proxyids_some_active(
        self, require_all_active, expected_status, reason, check_firewall_mock
    ):
        """tunnel with proxyids - proxyids not given and some active
        Should return fail by default. Success if require_all_active is False.
        """
        check_firewall_mock._node.get_tunnels.return_value = {
            "IPSec": {
                "east1-vpn:ProxyID1": {"state": "active"},
                "east1-vpn:ProxyID2": {"state": "init"},
                "east1-vpn:ProxyID3": {"state": "active"},
                "central1-vpn:ProxyID1": {"state": "init"},
            }
        }
        assert check_firewall_mock.check_ipsec_tunnel_status(
            tunnel_name="east1-vpn", require_all_active=require_all_active
        ) == CheckResult(expected_status, reason=reason)

        assert check_firewall_mock.check_ipsec_tunnel_status(
            tunnel_name="east1-vpn", proxy_ids=[], require_all_active=require_all_active
        ) == CheckResult(expected_status, reason=reason)

    @pytest.mark.parametrize(
        "require_all_active, expected_status, reason",
        [
            (True, CheckStatus.FAIL, "Tunnel:ProxyID east1-vpn:ProxyID1 in state: init."),
            (False, CheckStatus.FAIL, "No active state for tunnel east1-vpn in ProxyIDs ['ProxyID1', 'ProxyID2', 'ProxyID3']."),
        ],
    )
    def test_ipsec_tunnel_status_none_proxyids_none_active(
        self, require_all_active, expected_status, reason, check_firewall_mock
    ):
        """tunnel with proxyids - proxyids not given and not active
        Should return fail whether require_all_active is True or False.
        """
        check_firewall_mock._node.get_tunnels.return_value = {
            "IPSec": {
                "east1-vpn:ProxyID1": {"state": "init"},
                "east1-vpn:ProxyID2": {"state": "init"},
                "east1-vpn:ProxyID3": {"state": "init"},
                "central1-vpn:ProxyID1": {"state": "active"},
            }
        }
        assert check_firewall_mock.check_ipsec_tunnel_status(
            tunnel_name="east1-vpn", require_all_active=require_all_active
        ) == CheckResult(expected_status, reason=reason)

        assert check_firewall_mock.check_ipsec_tunnel_status(
            tunnel_name="east1-vpn", proxy_ids=[], require_all_active=require_all_active
        ) == CheckResult(expected_status, reason=reason)

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

    @pytest.mark.parametrize("global_jumbo_frame", [True, False])
    def test_get_global_jumbo_frame(self, global_jumbo_frame, check_firewall_mock):
        check_firewall_mock._node.is_global_jumbo_frame_set.return_value = global_jumbo_frame
        result = check_firewall_mock.get_global_jumbo_frame()

        assert result == {"mode": global_jumbo_frame}

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
                {
                    "anti-virus": {
                        "@ptpl": "lab",  # a template provided config
                        "@src": "tpl",
                        "recurring": {
                            "@ptpl": "lab",
                            "@src": "tpl",
                            "daily": {
                                "@ptpl": "lab",
                                "@src": "tpl",
                                "action": {"#text": "download-and-install", "@ptpl": "lab", "@src": "tpl"},
                                "at": {"#text": "03:30", "@ptpl": "lab", "@src": "tpl"},
                            },
                            "sync-to-peer": {"#text": "yes", "@ptpl": "lab", "@src": "tpl"},
                            "threshold": {"#text": "15", "@ptpl": "lab", "@src": "tpl"},
                        },
                    }
                },
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

    @pytest.mark.parametrize(
        "current_mode, desired_mode, expected_status, expected_reason",
        [
            (True, True, CheckStatus.SUCCESS, ""),
            (False, False, CheckStatus.SUCCESS, ""),
            (True, False, CheckStatus.FAIL, "Global jumbo frame is enabled, but desired mode is disabled."),
            (False, True, CheckStatus.FAIL, "Global jumbo frame is disabled, but desired mode is enabled."),
            (True, None, CheckStatus.SKIPPED, "Missing desired mode for global jumbo frame."),
            (False, None, CheckStatus.SKIPPED, "Missing desired mode for global jumbo frame."),
        ],
    )
    def test_check_global_jumbo_frame(self, current_mode, desired_mode, expected_status, expected_reason, check_firewall_mock):
        check_firewall_mock._node.is_global_jumbo_frame_set.return_value = current_mode
        result = check_firewall_mock.check_global_jumbo_frame(mode=desired_mode)
        assert CheckResult(status=expected_status, reason=expected_reason) == result

    def test_check_system_environmentals_success(self, check_firewall_mock):
        check_firewall_mock._node.get_system_environmentals.return_value = {
            "thermal": {"Slot0": {"entry": {"alarm": "False"}}},
            "fantray": {"Slot1": {"entry": {"alarm": "False"}}},
            "fan": {"Slot1": {"entry": {"alarm": "False"}}},
            "power": {"Slot1": {"entry": {"alarm": "False"}}},
            "power-supply": {"Slot1": {"entry": {"alarm": "False"}}},
        }

        result = check_firewall_mock.check_system_environmentals()
        assert result.status == CheckStatus.SUCCESS

    def test_check_system_environmentals_with_alarm(self, check_firewall_mock):
        check_firewall_mock._node.get_system_environmentals.return_value = {
            "thermal": {"Slot0": {"entry": {"alarm": "False"}}},
            "fantray": {"Slot1": {"entry": {"alarm": "False"}}},
            "fan": {"Slot1": {"entry": {"alarm": "False"}}},
            "power": {"Slot1": {"entry": {"alarm": "True"}}},
            "power-supply": {"Slot1": {"entry": {"alarm": "False"}}},
        }

        result = check_firewall_mock.check_system_environmentals()
        assert result.status == CheckStatus.FAIL
        assert "power" in result.reason

    def test_check_system_environmentals_specific_components(self, check_firewall_mock):
        check_firewall_mock._node.get_system_environmentals.return_value = {
            "thermal": {"Slot0": {"entry": {"alarm": "False"}}},
            "fantray": {"Slot1": {"entry": {"alarm": "False"}}},
            "fan": {"Slot1": {"entry": {"alarm": "True"}}},
            "power": {"Slot1": {"entry": {"alarm": "False"}}},
            "power-supply": {"Slot1": {"entry": {"alarm": "True"}}},
        }

        result = check_firewall_mock.check_system_environmentals(components=["thermal", "power"])
        assert result.status == CheckStatus.SUCCESS

        result = check_firewall_mock.check_system_environmentals(components=["fan", "power-supply"])
        assert result.status == CheckStatus.FAIL
        assert "fan" in result.reason and "power-supply" in result.reason

    def test_check_system_environmentals_invalid_component(self, check_firewall_mock):
        result = check_firewall_mock.check_system_environmentals(components=["invalid-component"])
        assert result.status == CheckStatus.ERROR
        assert "Invalid components provided" in result.reason

    def test_check_system_environmentals_no_data(self, check_firewall_mock):
        check_firewall_mock._node.get_system_environmentals.return_value = {}
        result = check_firewall_mock.check_system_environmentals()
        assert result.status == CheckStatus.ERROR
        assert "Device did not return environmentals" in result.reason

    @pytest.mark.parametrize("threshold", [-10, 120])
    def test_check_dp_cpu_utilization_invalid_threshold(self, threshold, check_firewall_mock):
        with pytest.raises(WrongDataTypeException) as exception_msg:
            check_firewall_mock.check_dp_cpu_utilization(threshold=threshold)

        assert "Threshold parameter should be between 0 and 100" in str(exception_msg.value)

    @pytest.mark.parametrize("minutes", [-5, 0, 61])
    def test_check_dp_cpu_utilization_invalid_minutes(self, minutes, check_firewall_mock):
        with pytest.raises(WrongDataTypeException) as exception_msg:
            check_firewall_mock.check_dp_cpu_utilization(minutes=minutes)

        assert "Minutes parameter should be between 1 and 60" in str(exception_msg.value)

    @pytest.mark.parametrize("param_value", ["12", 12.5])
    def test_check_dp_cpu_utilization_invalid_param_types(self, param_value, check_firewall_mock):
        # both threshold and minutes accept integer only
        with pytest.raises(WrongDataTypeException):
            check_firewall_mock.check_dp_cpu_utilization(threshold=param_value)

        with pytest.raises(WrongDataTypeException):
            check_firewall_mock.check_dp_cpu_utilization(minutes=param_value)

    def test_check_dp_cpu_utilization_success(self, check_firewall_mock):
        # Mock data for low CPU utilization
        check_firewall_mock._node.get_dp_cpu_utilization.return_value = {
            "dp0": {"cpu-load-average": {"0": [10, 10, 10, 10, 10], "1": [15, 15, 15, 15, 15]}}
        }

        assert check_firewall_mock.check_dp_cpu_utilization(threshold=50) == CheckResult(status=CheckStatus.SUCCESS)

    def test_check_dp_cpu_utilization_high(self, check_firewall_mock):
        # Mock data for high CPU utilization
        check_firewall_mock._node.get_dp_cpu_utilization.return_value = {
            "dp0": {"cpu-load-average": {"0": [85, 85, 85, 85, 85], "1": [90, 90, 90, 90, 90]}}
        }

        result = check_firewall_mock.check_dp_cpu_utilization(threshold=50)

        assert result.status == CheckStatus.FAIL
        assert "Average data plane CPU utilization" in result.reason
        assert "is above or equal to the threshold (50%)" in result.reason

    def test_check_dp_cpu_utilization_api_error(self, check_firewall_mock):
        # Simulate API error
        check_firewall_mock._node.get_dp_cpu_utilization.side_effect = Exception("API error")

        result = check_firewall_mock.check_dp_cpu_utilization()

        assert result.status == CheckStatus.ERROR
        assert "Failed to retrieve data plane CPU utilization" in result.reason

    def test_check_dp_cpu_utilization_no_data(self, check_firewall_mock):
        # Mock empty data
        check_firewall_mock._node.get_dp_cpu_utilization.return_value = {"dp0": {"cpu-load-average": {"0": [], "1": []}}}

        result = check_firewall_mock.check_dp_cpu_utilization()

        assert result.status == CheckStatus.ERROR
        assert "No CPU utilization data available" in result.reason

    def test_check_dp_cpu_utilization_average_calculation(self, check_firewall_mock):
        check_firewall_mock._node.get_dp_cpu_utilization.return_value = {
            "dp0": {"cpu-load-average": {"0": [10, 20, 30, 40, 50], "1": [50, 60, 70, 80, 90]}}  # avg = 30  # avg = 70
        }

        # Average should be (30+70)/2 = 50
        # With threshold 49, it should fail
        result_fail = check_firewall_mock.check_dp_cpu_utilization(threshold=49)
        assert result_fail.status == CheckStatus.FAIL

        # With threshold 50, it should fail (equal to threshold)
        result_equal = check_firewall_mock.check_dp_cpu_utilization(threshold=50)
        assert result_equal.status == CheckStatus.FAIL

        # With threshold 51, it should pass
        result_pass = check_firewall_mock.check_dp_cpu_utilization(threshold=51)
        assert result_pass.status == CheckStatus.SUCCESS

    @pytest.mark.parametrize("threshold", [-10, 120])
    def test_check_mp_cpu_utilization_invalid_threshold(self, threshold, check_firewall_mock):
        with pytest.raises(WrongDataTypeException) as exception_msg:
            check_firewall_mock.check_mp_cpu_utilization(threshold=threshold)

        assert "Threshold parameter should be between 0 and 100" in str(exception_msg.value)

    @pytest.mark.parametrize("param_value", ["12", 12.5])
    def test_check_mp_cpu_utilization_invalid_param_types(self, param_value, check_firewall_mock):
        with pytest.raises(WrongDataTypeException):
            check_firewall_mock.check_mp_cpu_utilization(threshold=param_value)

    def test_check_mp_cpu_utilization_success(self, check_firewall_mock):
        # Mock data for low CPU utilization
        check_firewall_mock._node.get_mp_cpu_utilization.return_value = 20

        assert check_firewall_mock.check_mp_cpu_utilization(threshold=50) == CheckResult(status=CheckStatus.SUCCESS)

    def test_check_mp_cpu_utilization_high(self, check_firewall_mock):
        # Mock data for high CPU utilization
        check_firewall_mock._node.get_mp_cpu_utilization.return_value = 85

        result = check_firewall_mock.check_mp_cpu_utilization(threshold=50)

        assert result.status == CheckStatus.FAIL
        assert "Management plane CPU utilization" in result.reason
        assert "threshold (50%)" in result.reason

    def test_check_mp_cpu_utilization_error(self, check_firewall_mock):
        check_firewall_mock._node.get_mp_cpu_utilization.side_effect = Exception("some error")

        result = check_firewall_mock.check_mp_cpu_utilization()

        assert result.status == CheckStatus.ERROR
        assert "Failed to retrieve management plane CPU utilization" in result.reason

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

        snapshots_config = ["snapshot1", {"snapshot2": {"param1": 123}}]

        result = check_firewall_mock.run_snapshots(snapshots_config)

        expected_result = {
            "snapshot1": {"status": "success"},
            "snapshot2": {"status": "failed"},
        }
        assert result == expected_result

        check_firewall_mock._snapshot_method_mapping["snapshot1"].assert_called_once_with()
        check_firewall_mock._snapshot_method_mapping["snapshot2"].assert_called_once_with(param1=123)

    def test_run_snapshots_empty_dict(self, check_firewall_mock):
        check_firewall_mock._snapshot_method_mapping = {
            "snapshot1": MagicMock(return_value={"status": "success"}),
        }

        snapshots_config = [{"snapshot1": None}]

        result = check_firewall_mock.run_snapshots(snapshots_config)

        expected_result = {
            "snapshot1": {"status": "success"},
        }
        assert result == expected_result

        check_firewall_mock._snapshot_method_mapping["snapshot1"].assert_called_once_with()

    def test_run_snapshots_wrong_data_type_exception(self, check_firewall_mock):
        snapshots_config = ["snapshot1", 123]

        with pytest.raises(WrongDataTypeException):
            check_firewall_mock.run_snapshots(snapshots_config)

        # raise exceptions.WrongDataTypeException(f"Wrong configuration format for snapshot: {snapshot}.")
        # NOTE configs are already validated in ConfigParser._extrac_element_name - above exception is never executed.
        # which is listed as missing in pytest coverage
        # assert "Wrong configuration format for snapshot:" in str(exception_msg.value)

    @pytest.mark.parametrize(
        "running_software, expected_status",
        [
            ("8.1.21.2", CheckStatus.SUCCESS),  # Device running fixed software, exact match
            ("8.1.26", CheckStatus.SUCCESS),  # Device running fixed software, greater than match
            ("11.0.3", CheckStatus.SUCCESS),  # Device running fixed software, greater than match
            ("8.1.0", CheckStatus.FAIL),  # Device running broken version
        ],
    )
    def test_check_device_root_certificate_issue_by_software(self, check_firewall_mock, running_software, expected_status):
        """This test validates the behavior when the test is only checking the software version is affected by
        the issue."""

        from packaging import version

        check_firewall_mock._node.get_device_software_version = MagicMock(return_value=version.parse(running_software))
        assert check_firewall_mock.check_device_root_certificate_issue().status == expected_status

    @pytest.mark.parametrize(
        "redistribution_status, expected_status",
        [
            ({"clients": ([("host", "1.1.1.1")]), "agents": []}, CheckStatus.FAIL),  # Device running redistribution
            ({"clients": [], "agents": []}, CheckStatus.SUCCESS),  # Device not running redistribution
        ],
    )
    def test_check_device_root_certificate_issue_fixed_content_running_redistribution(
        self, check_firewall_mock, redistribution_status, expected_status
    ):
        """This test validates the check fails in the scenarios where the user is running out of date software,
        but up-to-date Content"""

        from packaging import version

        check_firewall_mock._node.get_device_software_version = MagicMock(
            return_value=version.parse("10.1.0")  # Affected Version
        )
        check_firewall_mock._node.get_redistribution_status = MagicMock(return_value=redistribution_status)

        check_firewall_mock._node.get_content_db_version = MagicMock(return_value="8776-8391")  # Fixed Content Version

        assert (
            check_firewall_mock.check_device_root_certificate_issue(fail_when_affected_version_only=False).status
            == expected_status
        )

    @pytest.mark.parametrize(
        "running_content_version, expected_status",
        [
            ("8776-8391", CheckStatus.SUCCESS),  # Device running fixed content version
            ("8000-8391", CheckStatus.FAIL),  # Device running older content version
            ("9000-0111", CheckStatus.SUCCESS),  # Device running newer version
        ],
    )
    def test_check_device_root_certificate_issue_content_version(
        self, check_firewall_mock, running_content_version, expected_status
    ):
        from packaging import version

        check_firewall_mock._node.get_device_software_version = MagicMock(
            return_value=version.parse("10.1.0")  # Affected Version
        )
        check_firewall_mock._node.get_redistribution_status = MagicMock(
            return_value={"clients": [], "agents": []}  # Device not running redistribution
        )

        check_firewall_mock._node.get_content_db_version = MagicMock(return_value=running_content_version)

        assert (
            check_firewall_mock.check_device_root_certificate_issue(fail_when_affected_version_only=False).status
            == expected_status
        )

    @pytest.mark.parametrize(
        "user_id_status, expected_status",
        [
            ({"status": "up"}, CheckStatus.FAIL),  # Device running user-id service
            ({"status": "down"}, CheckStatus.SUCCESS),  # Device NOT running user-id service
            ({"status": "unknown"}, CheckStatus.SUCCESS),  # Status str not found in command output
        ],
    )
    def test_check_device_root_certificate_issue_fixed_content_running_user_id(
        self, check_firewall_mock, user_id_status, expected_status
    ):
        """This test validates the check fails in the scenarios where the user is running out of date software,
        but up-to-date Content"""

        from packaging import version

        check_firewall_mock._node.get_device_software_version = MagicMock(
            return_value=version.parse("10.1.0")  # Affected Version
        )
        check_firewall_mock._node.get_redistribution_status = MagicMock(side_effect=panos.errors.PanDeviceXapiError)
        check_firewall_mock._node.get_user_id_service_status = MagicMock(return_value=user_id_status)

        check_firewall_mock._node.get_content_db_version = MagicMock(return_value="8776-8391")  # Fixed Content Version

        assert (
            check_firewall_mock.check_device_root_certificate_issue(fail_when_affected_version_only=False).status
            == expected_status
        )

    def test_run_health_checks(self, check_firewall_mock):
        check_firewall_mock._health_check_method_mapping = {
            "check1": MagicMock(return_value=True),
            "check2": MagicMock(return_value=False),
        }

        checks_configuration = ["check1", {"check2": {"param1": 123}}]
        report_style = False

        result = check_firewall_mock.run_health_checks(checks_configuration, report_style)

        expected_result = {
            "check1": {"state": True, "reason": "True"},
            "check2": {"state": False, "reason": "False"},
        }
        assert result == expected_result

        check_firewall_mock._health_check_method_mapping["check1"].assert_called_once_with()
        check_firewall_mock._health_check_method_mapping["check2"].assert_called_once_with(param1=123)

    @pytest.mark.parametrize(
        "running_software, expected_status",
        [
            ("10.1.2", CheckStatus.FAIL),  # Device running broken version
            ("10.1.13", CheckStatus.SUCCESS),  # Device running fixed version
        ],
    )
    def test_check_cdss_and_panorama_certificate_issue(self, running_software, expected_status, check_firewall_mock):
        """This test validates the behavior when the test is only checking the software version is affected by
        the issue."""

        from packaging import version

        check_firewall_mock._node.get_device_software_version = MagicMock(return_value=version.parse(running_software))
        assert check_firewall_mock.check_cdss_and_panorama_certificate_issue().status == expected_status

    @pytest.mark.parametrize(
        "running_content_version, last_reboot, expected_status",
        [
            ("8000-8391", datetime(2022, 1, 1, 0, 0, 0), CheckStatus.FAIL),  # Device running older content version and no reboot
            ("8795-8489", datetime(2022, 1, 1, 0, 0, 0), CheckStatus.FAIL),  # Device running fixed version without reboot
            ("8795-8489", datetime(2024, 1, 10, 0, 0, 0), CheckStatus.SUCCESS),  # Device running fixed version and rebooted
        ],
    )
    def test_check_cdss_and_panorama_certificate_issue_by_content_version(
        self, running_content_version, last_reboot, expected_status, check_firewall_mock
    ):
        """Tests that we check the content version and use a best effort approach for seeing if the device has been
        rebooted in the time since it was released/installed"""
        from packaging import version

        check_firewall_mock._node.get_device_software_version = MagicMock(
            return_value=version.parse("10.1.0")  # Affected Version
        )

        check_firewall_mock._node.get_content_db_version = MagicMock(return_value=running_content_version)

        # Device hasn't been rebooted
        check_firewall_mock._node.get_system_time_rebooted = MagicMock(return_value=last_reboot)

        assert check_firewall_mock.check_cdss_and_panorama_certificate_issue().status == expected_status

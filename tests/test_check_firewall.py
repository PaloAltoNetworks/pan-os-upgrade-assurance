import pytest
from unittest.mock import MagicMock, patch
from panos_upgrade_assurance.check_firewall import CheckFirewall
from panos_upgrade_assurance.firewall_proxy import FirewallProxy
from panos_upgrade_assurance.utils import CheckResult
from panos_upgrade_assurance.utils import CheckStatus
from panos_upgrade_assurance.utils import interpret_yes_no
from panos.errors import PanDeviceXapiError
from panos_upgrade_assurance.exceptions import (
    WrongDataTypeException,
    UpdateServerConnectivityException,
)
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
        assert check_firewall_mock.check_panorama_connectivity() == CheckResult(status=CheckStatus.ERROR, reason="Device not configured with Panorama.")

    def test_check_ha_status_success(self, check_firewall_mock):
        check_firewall_mock._node.get_ha_configuration.return_value = {
            'enabled': 'yes',
            'group': {
                'mode': 'Active-Passive',
                'local-info': {'state': 'active'},
                'peer-info': {'state': 'passive'},
                'running-sync-enabled': 'yes',
                'running-sync': 'synchronized'
            }
        }
        assert check_firewall_mock.check_ha_status() == CheckResult(status=CheckStatus.SUCCESS)

    def test_check_ha_status_enabled(self, check_firewall_mock):
        check_firewall_mock._node.get_ha_configuration.return_value = {
            'enabled': 'no',
            'group': {
                'mode': 'Active-Passive',
                'local-info': {'state': 'active'},
                'peer-info': {'state': 'passive'},
                'running-sync-enabled': 'yes',
                'running-sync': 'synchronized'
            }
        }
        assert check_firewall_mock.check_ha_status() == CheckResult(status=CheckStatus.ERROR, reason="Device is not a member of an HA pair.")

    def test_check_ha_status_no_sync(self, check_firewall_mock):
        check_firewall_mock._node.get_ha_configuration.return_value = {
            'enabled': 'yes',
            'group': {
                'mode': 'Active-Passive',
                'local-info': {'state': 'active'},
                'peer-info': {'state': 'passive'},
                'running-sync-enabled': 'yes',
                'running-sync': 'not-synchronized'
            }
        }
        assert check_firewall_mock.check_ha_status() == CheckResult(status=CheckStatus.ERROR, reason="Device configuration is not synchronized between the nodes.")

    def test_check_ha_status_mode(self, check_firewall_mock):
        check_firewall_mock._node.get_ha_configuration.return_value = {
            'enabled': 'yes',
            'group': {
                'mode': 'Active-Active',
                'local-info': {'state': 'active'},
                'peer-info': {'state': 'passive'},
                'running-sync-enabled': 'yes',
                'running-sync': 'synchronized'
            }
        }
        assert check_firewall_mock.check_ha_status() == CheckResult(status=CheckStatus.ERROR, reason = "HA pair is not in Active-Passive mode.")

    def test_check_ha_status_local_info(self, check_firewall_mock):
        check_firewall_mock._node.get_ha_configuration.return_value = {
            'enabled': 'yes',
            'group': {
                'mode': 'Active-Passive',
                'local-info': {'state': 'someotherstate'},
                'peer-info': {'state': 'passive'},
                'running-sync-enabled': 'yes',
                'running-sync': 'synchronized'
            }
        }
        assert check_firewall_mock.check_ha_status() == CheckResult(reason = "Local device is not in active or passive state.")

    def test_check_ha_status_peer_info(self, check_firewall_mock):
        check_firewall_mock._node.get_ha_configuration.return_value = {
            'enabled': 'yes',
            'group': {
                'mode': 'Active-Passive',
                'local-info': {'state': 'active'},
                'peer-info': {'state': 'someotherstate'},
                'running-sync-enabled': 'yes',
                'running-sync': 'synchronized'
            }
        }
        assert check_firewall_mock.check_ha_status() == CheckResult(reason = "Peer device is not in active or passive state.")

    def test_check_ha_status_peer_info_local_info(self, check_firewall_mock):
        check_firewall_mock._node.get_ha_configuration.return_value = {
            'enabled': 'yes',
            'group': {
                'mode': 'Active-Passive',
                'local-info': {'state': 'active'},
                'peer-info': {'state': 'active'},
                'running-sync-enabled': 'yes',
                'running-sync': 'synchronized'
            }
        }
        assert check_firewall_mock.check_ha_status() == CheckResult(status=CheckStatus.ERROR, reason = "Both devices have the same state: active.")

    def test_check_is_ha_active_success(self, check_firewall_mock):
        check_firewall_mock.check_ha_status = MagicMock()
        check_firewall_mock._node.get_ha_configuration.return_value = {
            'enabled': 'yes',
            'group': {
                'mode': 'Active-Passive',
                'local-info': {'state': 'active'},
                'peer-info': {'state': 'passive'},
                'running-sync-enabled': 'yes',
                'running-sync': 'synchronized'
            }
        }
        assert check_firewall_mock.check_is_ha_active() == CheckResult(status=CheckStatus.SUCCESS)

    def test_check_is_ha_active_fail(self, check_firewall_mock):
        check_firewall_mock.check_ha_status = MagicMock()
        check_firewall_mock._node.get_ha_configuration.return_value = {
            'enabled': 'yes',
            'group': {
                'mode': 'Active-Passive',
                'local-info': {'state': 'someothervalue'},
                'peer-info': {'state': 'passive'},
                'running-sync-enabled': 'yes',
                'running-sync': 'synchronized'
            }
        }
        assert check_firewall_mock.check_is_ha_active() == CheckResult(status=CheckStatus.FAIL,reason="Node state is: someothervalue.")

    def test_check_is_ha_active_no_ha_status(self, check_firewall_mock):
        check_ha_status_mock = MagicMock(return_value=False)
        check_firewall_mock.check_ha_status = check_ha_status_mock
        result = check_firewall_mock.check_is_ha_active()
        assert result is False

    def test_check_expired_licenses_true(self, check_firewall_mock):
        check_firewall_mock._node.get_licenses.return_value = {
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
                    }
                
        }
        assert check_firewall_mock.check_expired_licenses() == CheckResult(reason=f"Found expired licenses:  AutoFocus Device License, PA-VM.")

    def test_check_expired_licenses_false(self, check_firewall_mock):
        check_firewall_mock._node.get_licenses.return_value = {
                    'AutoFocus Device License': {
                        'authcode': 'Snnnnnnn',
                        'base-license-name': 'PA-VM',
                        'description': 'AutoFocus Device License',
                        'expired': 'no',
                        'expires': 'September 25, 2010',
                        'feature': 'AutoFocus Device License',
                        'issued': 'January 12, 2010',
                        'serial': 'xxxxxxxxxxxxxxxx'
                    },
                    'PA-VM': {
                        'authcode': None,
                        'description': 'Standard VM-300',
                        'expired': 'no',
                        'expires': 'September 25, 2010',
                        'feature': 'PA-VM',
                        'issued': 'January 12, 2010',
                        'serial': 'xxxxxxxxxxxxxxxx'
                    }
                
        }
        assert check_firewall_mock.check_expired_licenses() == CheckResult(status=CheckStatus.SUCCESS)

    def test_check_expired_licenses_param_error(self, check_firewall_mock):

        with pytest.raises(WrongDataTypeException) as execption_msg:
            check_firewall_mock.check_expired_licenses(skip_licenses = "not_a_list")
    
        assert str(execption_msg.value) == "The skip_licenses variable is a <class 'str'> but should be a list"

    def test_check_critical_session_none(self, check_firewall_mock):
        assert check_firewall_mock.check_critical_session(source=None, destination="5.5.5.5", dest_port="443") == CheckResult(status=CheckStatus.SKIPPED, reason="Missing critical session description. Failing check.")

    def test_check_critical_session_empty_sessions(self, check_firewall_mock):
        check_firewall_mock._node.get_sessions.return_value = []
        assert check_firewall_mock.check_critical_session(source="10.10.10.10", destination="5.5.5.5", dest_port="443") == CheckResult(status=CheckStatus.ERROR, reason="Device's session table is empty.")

    def test_check_critical_session_sessions_in_list(self, check_firewall_mock):
        check_firewall_mock._node.get_sessions.return_value = [
            {
            'source': '10.10.10.10',
            'xdst': '5.5.5.5',
            'dport': '443'
            }
        ]
        assert check_firewall_mock.check_critical_session(source='10.10.10.10', destination='5.5.5.5', dest_port='443') == CheckResult(status=CheckStatus.SUCCESS)

    def test_check_critical_session_not_found(self, check_firewall_mock):
        check_firewall_mock._node.get_sessions.return_value = [
            {
            'source': '10.10.10.10',
            'xdst': '5.5.5.5',
            'dport': '443'
            }
        ]
        assert check_firewall_mock.check_critical_session(source='10.10.10.11', destination='5.5.5.6', dest_port='80') == CheckResult(status=CheckStatus.FAIL, reason="Session not found in session table.")

    def test_check_content_version_latest_installed(self, check_firewall_mock):
        check_firewall_mock._node.get_latest_available_content_version.return_value = "1-10"
        check_firewall_mock._node.get_content_db_version.return_value = "1-10"
        assert check_firewall_mock.check_content_version() == CheckResult(status=CheckStatus.SUCCESS)

    def test_check_content_version_latest_not_installed(self, check_firewall_mock):
        check_firewall_mock._node.get_latest_available_content_version.return_value = "2-10"
        check_firewall_mock._node.get_content_db_version.return_value = "1-10"
        assert check_firewall_mock.check_content_version() == CheckResult(status=CheckStatus.FAIL, reason=f"Installed content DB version (1-10) is not the latest one (2-10).")

    # def test_check_content_version_latest_not_installed_version_not_passed(self, check_firewall_mock):
    #     check_firewall_mock._node.get_latest_available_content_version.return_value = "2-10"
    #     check_firewall_mock._node.get_content_db_version.return_value = "2-20"
    #     with pytest.raises(ContentDBVersionInFutureException) as execption_msg:
    #         check_firewall_mock.check_content_version()
    #     assert str(execption_msg.value) == "Wrong data returned from device, installed version (2-20) is higher than the required_version available (2-10)."

    def test_check_content_version_latest_not_installed_version_passed(self, check_firewall_mock):
        check_firewall_mock._node.get_latest_available_content_version.return_value = "2-10"
        check_firewall_mock._node.get_content_db_version.return_value = "2-20"
        assert check_firewall_mock.check_content_version(version="2-10") == CheckResult(status=CheckStatus.SUCCESS, reason=f'Installed content DB version (2-20) is higher than the requested one (2-10).')

    def test_check_content_version_latest_not_installed_version_passed_higher_major(self, check_firewall_mock):
        check_firewall_mock._node.get_latest_available_content_version.return_value = "2-10"
        check_firewall_mock._node.get_content_db_version.return_value = "3-10"
        assert check_firewall_mock.check_content_version(version="2-10") == CheckResult(status=CheckStatus.SUCCESS, reason=f'Installed content DB version (3-10) is higher than the requested one (2-10).')

    # def test_check_content_version_latest_not_installed(self, check_firewall_mock):
    #     check_firewall_mock._node.get_latest_available_content_version.return_value = "2-10"
    #     check_firewall_mock._node.get_content_db_version.return_value = "3-20"
    #     with pytest.raises(ContentDBVersionInFutureException) as execption_msg:
    #         check_firewall_mock.check_content_version()
    #     assert str(execption_msg.value) == "Wrong data returned from device, installed version (3-20) is higher than the required_version available (2-10)."

    def test_check_content_version_installed_older_than_requested(self, check_firewall_mock):
        check_firewall_mock._node.get_latest_available_content_version.return_value = "4-0"
        check_firewall_mock._node.get_content_db_version.return_value = "3-20"
        assert check_firewall_mock.check_content_version("4-0") == CheckResult(CheckStatus.FAIL, reason = "Installed content DB version (3-20) is older then the request one (4-0).")

    def test_check_content_version_installed_newer_than_requested(self, check_firewall_mock):
        check_firewall_mock._node.get_latest_available_content_version.return_value = "3-20"
        check_firewall_mock._node.get_content_db_version.return_value = "4-0"
        assert check_firewall_mock.check_content_version("3-20") == CheckResult(CheckStatus.SUCCESS, reason = "Installed content DB version (4-0) is higher than the requested one (3-20).")
    
    def test_check_content_version_installed_older_than_latest(self, check_firewall_mock):
        check_firewall_mock._node.get_latest_available_content_version.return_value = "4-0"
        check_firewall_mock._node.get_content_db_version.return_value = "3-20"
        result = check_firewall_mock.check_content_version()
        assert result.status == CheckStatus.FAIL
        assert result.reason == "Installed content DB version (3-20) is not the latest one (4-0)."
    
    def test_check_content_version_installed_same_as_latest(self, check_firewall_mock):
        check_firewall_mock._node.get_latest_available_content_version.return_value = "3-20"
        check_firewall_mock._node.get_content_db_version.return_value = "3-20"
        result = check_firewall_mock.check_content_version()
        assert result.status == CheckStatus.SUCCESS

    def test_check_ntp_synchronization_local_no_ntp(self, check_firewall_mock):
        check_firewall_mock._node.get_ntp_servers.return_value = {
            'synched' : 'LOCAL'
        }
        assert check_firewall_mock.check_ntp_synchronization() == CheckResult(status=CheckStatus.ERROR, reason="No NTP server configured.")

    def test_check_ntp_synchronization_local_no_ntp_sync(self, check_firewall_mock):
        check_firewall_mock._node.get_ntp_servers.return_value = {
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
            'synched': 'LOCAL'
        }
        assert check_firewall_mock.check_ntp_synchronization() == CheckResult(reason=f"No NTP synchronization in active, servers in following state: 0.pool.ntp.org - available, 1.pool.ntp.org - synched.")

    def test_check_ntp_synchronization_synched_ok(self, check_firewall_mock):
        check_firewall_mock._node.get_ntp_servers.return_value = {
            'ntp-server-1': {
                'authentication-type': 'none',
                'name': '1.pool.ntp.org',
                'reachable': 'yes',
                'status': 'synched'
            },
            'synched': '1.pool.ntp.org'
        }
        assert check_firewall_mock.check_ntp_synchronization() == CheckResult(status=CheckStatus.SUCCESS)

    def test_check_ntp_synchronization_synched_unknown(self, check_firewall_mock):
        check_firewall_mock._node.get_ntp_servers.return_value = {
            'synched': 'unknown'
        }
        assert check_firewall_mock.check_ntp_synchronization() == CheckResult(reason=f"NTP synchronization in unknown state: unknown.")

    def test_check_arp_entry_none(self, check_firewall_mock):

        assert check_firewall_mock.check_arp_entry(ip=None) == CheckResult(CheckStatus.SKIPPED, reason="Missing ARP table entry description.")
    
    def test_check_arp_entry_empty(self, check_firewall_mock):
        check_firewall_mock._node.get_arp_table.return_value = None

        assert check_firewall_mock.check_arp_entry(ip="5.5.5.5") == CheckResult(status=CheckStatus.ERROR, reason="ARP table empty.")

    def test_check_arp_entry_not_found(self, check_firewall_mock):
        check_firewall_mock._node.get_arp_table.return_value = {
            'ethernet1/1_10.0.2.1': {
                'interface': 'ethernet1/1',
                'ip': '10.0.2.1',
                'mac': '12:34:56:78:9a:bc',
                'port': 'ethernet1/1',
                'status': 'c',
                'ttl': '1094'
            }
        }
        assert check_firewall_mock.check_arp_entry(ip="10.0.2.1", interface="ethernet1/1") == CheckResult(CheckStatus.SUCCESS)

    def test_check_arp_entry_found_without_interface(self, check_firewall_mock):
        check_firewall_mock._node.get_arp_table.return_value = {
            'ethernet1/1_10.0.2.1': {
                'interface': 'ethernet1/1',
                'ip': '10.0.2.1',
                'mac': '12:34:56:78:9a:bc',
                'port': 'ethernet1/1',
                'status': 'c',
                'ttl': '1094'
            }
        }
        assert check_firewall_mock.check_arp_entry(ip="10.0.2.1") == CheckResult(CheckStatus.SUCCESS)


    def test_check_arp_entry_not_found(self, check_firewall_mock):
        check_firewall_mock._node.get_arp_table.return_value = {
            'ethernet1/1_10.0.2.1': {
                'interface': 'ethernet1/1',
                'ip': '10.0.2.1',
                'mac': '12:34:56:78:9a:bc',
                'port': 'ethernet1/1',
                'status': 'c',
                'ttl': '1094'
            }
        }
        assert check_firewall_mock.check_arp_entry(ip="10.0.3.1", interface="ethernet1/2") == CheckResult(reason="Entry not found in ARP table.")

    def test_check_arp_entry_found(self, check_firewall_mock):
        check_firewall_mock._node.get_arp_table.return_value = {
            'ethernet1/2_10.0.3.1': {
                'interface': 'ethernet1/2',
                'ip': '10.0.3.1',
                'mac': '12:34:56:78:9a:bc',
                'port': '443',
                'status': 'c',
                'ttl': '1094'
            }
        }
        assert check_firewall_mock.check_arp_entry(ip="10.0.3.1", interface="ethernet1/2") == CheckResult(CheckStatus.SUCCESS)

    def test_ipsec_tunnel_status_none(self, check_firewall_mock):

        assert check_firewall_mock.check_ipsec_tunnel_status(tunnel_name=None) == CheckResult(CheckStatus.SKIPPED, reason="Missing tunnel specification.")
    
    def test_ipsec_tunnel_status_no_ipsec_tunnels(self, check_firewall_mock):
        check_firewall_mock._node.get_tunnels.return_value = {"key" : "value"}

        assert check_firewall_mock.check_ipsec_tunnel_status(tunnel_name="MyTunnel") == CheckResult(CheckStatus.ERROR, reason="No IPSec Tunnel is configured on the device.")
    
    def test_ipsec_tunnel_status_active(self, check_firewall_mock):
        check_firewall_mock._node.get_tunnels.return_value = {
            "IPSec" : {
                "MyTunnel" : {
                    "state" : "active"
                }
            }
        }
        assert check_firewall_mock.check_ipsec_tunnel_status(tunnel_name="MyTunnel") == CheckResult(CheckStatus.SUCCESS)
    
    def test_ipsec_tunnel_status_not_active(self, check_firewall_mock):
        check_firewall_mock._node.get_tunnels.return_value = {
            "IPSec" : {
                "MyTunnel" : {
                    "state" : "down"
                }
            }
        }
        assert check_firewall_mock.check_ipsec_tunnel_status(tunnel_name="MyTunnel") == CheckResult(CheckStatus.FAIL, reason="Tunnel MyTunnel in state: down.")

    def test_ipsec_tunnel_status_not_found(self, check_firewall_mock):
        check_firewall_mock._node.get_tunnels.return_value = {
            "IPSec" : {
                "MyTunnel" : {
                    "state" : "active"
                }
            }
        }
        assert check_firewall_mock.check_ipsec_tunnel_status(tunnel_name="NotMyTunnel") == CheckResult(reason="Tunnel NotMyTunnel not found.")

    def test_check_free_disk_space_ok(self, check_firewall_mock):
        check_firewall_mock._node.get_disk_utilization.return_value = {
            "/opt/panrepo" : 50000
        }

        assert check_firewall_mock.check_free_disk_space() == CheckResult(CheckStatus.SUCCESS)

    def test_check_free_disk_space_nok(self, check_firewall_mock):
        check_firewall_mock._node.get_disk_utilization.return_value = {
            "/opt/panrepo" : 50
        }

        assert check_firewall_mock.check_free_disk_space() == CheckResult(CheckStatus.FAIL, reason="There is not enough free space, only 50MB is available.")

    def test_check_free_disk_space_with_available_version(self, check_firewall_mock):
        check_firewall_mock._node.get_available_image_data.return_value = {
            "9.0.0": {
                "size": "2000"
            }
        }
        check_firewall_mock._node.get_disk_utilization.return_value = {
            "/opt/panrepo": 3000
        }

        assert check_firewall_mock.check_free_disk_space("9.0.0").status == CheckStatus.SUCCESS

    def test_check_free_disk_space_with_unavailable_base_image(self, check_firewall_mock):

        check_firewall_mock._node.get_available_image_data.return_value = {
            "9.2.2": {
                "size": "2000"
            }
        }
        check_firewall_mock._node.get_disk_utilization.return_value = {
            "/opt/panrepo": 5000
        }

        assert check_firewall_mock.check_free_disk_space("9.2.2") == CheckResult(CheckStatus.SUCCESS, reason="Base image 9.2.0 does not exist.")

    def test_check_free_disk_space_image_does_not_exist(self, check_firewall_mock):

        check_firewall_mock._node.get_available_image_data.return_value = {
            "9.2.2": {
                "size": "2000"
            }
        }
        check_firewall_mock._node.get_disk_utilization.return_value = {
            "/opt/panrepo": 5000
        }

        assert check_firewall_mock.check_free_disk_space("9.1.1") == CheckResult(CheckStatus.SUCCESS, reason="Image 9.1.1 does not exist.")

    # def test_check_free_disk_space_image_does_not_exist(self, check_firewall_mock):
    #     check_firewall_mock._node.get_available_image_data.return_value = {
    #         "9.2.0": {
    #             "size": "2000",
    #             "downloaded": "no"
    #         }
    #     }
    #     check_firewall_mock._node.get_disk_utilization.return_value = {
    #         "/opt/panrepo": 5000
    #     }

    #     with patch("panos_upgrade_assurance.check_firewall.interpret_yes_no", return_value=False):
    #         result = check_firewall_mock.check_free_disk_space("9.2.0")

    #     assert result.status == CheckStatus.SUCCESS


    def test_get_content_db_version(self, check_firewall_mock):
        check_firewall_mock._node.get_content_db_version.return_value = "5555-6666"

        assert check_firewall_mock.get_content_db_version() == {'version':'5555-6666'}

    def test_get_ip_sec_tunnels(self, check_firewall_mock):
        check_firewall_mock._node.get_tunnels.return_value = {
            "IPSec" : {
                "MyTunnel" : {
                    "name" : "tunnel_name"
                }
            }
        }

        check_firewall_mock.get_ip_sec_tunnels() == {
                "MyTunnel" : {
                    "name" : "tunnel_name"
                }
            }

    def test_check_active_support_license_connectivity_error(self, check_firewall_mock):
        check_firewall_mock._node.get_support_license.side_effect = UpdateServerConnectivityException(
            "Can not reach update servers to check active support license."
        )

        result = check_firewall_mock.check_active_support_license()

        assert check_firewall_mock.check_active_support_license() == CheckResult(CheckStatus.ERROR, reason="Can not reach update servers to check active support license.")

    def test_check_active_support_license_no_expiry_date(self, check_firewall_mock):
        check_firewall_mock._node.get_support_license.return_value = {
                "support_expiry_date" : ""
            }

        assert check_firewall_mock.check_active_support_license() == CheckResult(status=CheckStatus.ERROR, reason="No ExpiryDate found for support license.")

    def test_check_active_support_license_expired(self, check_firewall_mock):
        check_firewall_mock._node.get_support_license.return_value = {
                "support_expiry_date" : "June 06, 2023"
            }

        assert check_firewall_mock.check_active_support_license() == CheckResult(status=CheckStatus.FAIL, reason="Support License expired.")

    def test_check_active_support_license_success(self, check_firewall_mock):
        check_firewall_mock._node.get_support_license.return_value = {
                "support_expiry_date" : "June 06, 9999"
            }

        assert check_firewall_mock.check_active_support_license() == CheckResult(status=CheckStatus.SUCCESS)

    def test_check_mp_dp_sync_wrong_input_data(self, check_firewall_mock):

        with pytest.raises(WrongDataTypeException) as exception_msg:
            check_firewall_mock.check_mp_dp_sync("1.0")

        assert str(exception_msg.value) == f"[diff_threshold] should be of type [int] but is of type [<class 'str'>]."

    def test_check_mp_dp_sync_time_diff(self, check_firewall_mock):

        check_firewall_mock._node.get_mp_clock.return_value = {
            'day': '31',
            'day_of_week': 'Wed',
            'month': 'May',
            'time': '11:50:21',
            'tz': 'PDT',
            'year': '2023',
        }
        check_firewall_mock._node.get_dp_clock.return_value = {
            'day': '31',
            'day_of_week': 'Wed',
            'month': 'May',
            'time': '11:52:34',
            'tz': 'PDT',
            'year': '2023',
        }

        assert check_firewall_mock.check_mp_dp_sync(1) == CheckResult(status=CheckStatus.FAIL, reason=f"The data plane clock and management clock are different by 133.0 seconds.")

    def test_check_mp_dp_sync_time_synced(self, check_firewall_mock):

        check_firewall_mock._node.get_mp_clock.return_value = {
            'day': '31',
            'day_of_week': 'Wed',
            'month': 'May',
            'time': '11:50:21',
            'tz': 'PDT',
            'year': '2023',
        }
        check_firewall_mock._node.get_dp_clock.return_value = {
            'day': '31',
            'day_of_week': 'Wed',
            'month': 'May',
            'time': '11:50:21',
            'tz': 'PDT',
            'year': '2023',
        }

        assert check_firewall_mock.check_mp_dp_sync(1) == CheckResult(status=CheckStatus.SUCCESS)

    def test_run_readiness_checks(self, check_firewall_mock):
        check_firewall_mock._check_method_mapping = {
            'check1': MagicMock(return_value=True),
            'check2': MagicMock(return_value=False),
        }

        checks_configuration = ['check1', {'check2': {'param1': 123}}]
        report_style = False

        result = check_firewall_mock.run_readiness_checks(checks_configuration, report_style)

        expected_result = {
            'check1': {'state': True, 'reason': 'True'},
            'check2': {'state': False, 'reason': 'False'},
        }
        assert result == expected_result

        check_firewall_mock._check_method_mapping['check1'].assert_called_once_with()
        check_firewall_mock._check_method_mapping['check2'].assert_called_once_with(param1=123)


    # def test_run_readiness_checks_exception(self, check_firewall_mock):

    #     # Set up the input parameters for the method
    #     checks_configuration = ['check1', [123]]
    #     report_style = False

    #     with pytest.raises(WrongDataTypeException) as exception_msg:
    #         check_firewall_mock.run_readiness_checks(checks_configuration, report_style)

    #     assert str(exception_msg.value) == f"Wrong configuration format for check: check1."

    def test_run_snapshots(self, check_firewall_mock):
        check_firewall_mock._snapshot_method_mapping = {
            'snapshot1': MagicMock(return_value={'status': 'success'}),
            'snapshot2': MagicMock(return_value={'status': 'failed'}),
        }

        snapshots_config = ['snapshot1', 'snapshot2']

        result = check_firewall_mock.run_snapshots(snapshots_config)

        expected_result = {
            'snapshot1': {'status': 'success'},
            'snapshot2': {'status': 'failed'},
        }
        assert result == expected_result

        check_firewall_mock._snapshot_method_mapping['snapshot1'].assert_called_once_with()
        check_firewall_mock._snapshot_method_mapping['snapshot2'].assert_called_once_with()

    # def test_run_snapshots_wrong_data_type(self, check_firewall_mock):

    #     snapshots_config = ['snapshot1', 123]

    #     with pytest.raises(WrongDataTypeException) as exception_msg:
    #         check_firewall_mock.run_snapshots(snapshots_config)
        
    #     assert str(exception_msg.value) == f"Wrong configuration format for snapshot: snap_type."
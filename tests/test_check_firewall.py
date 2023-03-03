import pytest
from unittest.mock import MagicMock
from panos_upgrade_assurance.check_firewall import CheckFirewall
from panos_upgrade_assurance.firewall_proxy import FirewallProxy
from panos_upgrade_assurance.utils import CheckResult
from panos_upgrade_assurance.utils import CheckStatus
\
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

    # TO DO
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
        assert check_firewall_mock.check_ha_status() == CheckResult(reason = "HA pair is not in Active-Passive mode.")
    
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





    # @pytest.mark.parametrize("version",[None, "3421-3234"])
    # def test_check_content_version(self, check_firewall_mock, version):
    #     check_firewall_mock._node.get_latest_available_content_version = MagicMock()
    #     if version is None:
    #         check_firewall_mock._node.get_latest_available_content_version.called_once()
    #     else:
    #         check_firewall_mock._node.get_latest_available_content_version.assert_not_called()

    # def test_get_content_db_version(self, check_firewall_mock):
    #     check_firewall_mock._node.get_content_db_version.return_value = "1234-2345"
    #     result = check_firewall_mock._node.get_content_db_version()

    #     assert check_firewall_mock.get_content_db_version() == {"version": result}

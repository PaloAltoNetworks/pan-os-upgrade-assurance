import pytest
from unittest.mock import MagicMock
from panos_upgrade_assurance.firewall_proxy import FirewallProxy, CommandRunFailedException,MalformedResponseException
from panos_upgrade_assurance.utils import interpret_yes_no
from xmltodict import parse as xml_parse
import xml.etree.ElementTree as ET

@pytest.fixture(scope="function")
def fw_node():
    tested_class = FirewallProxy()
    tested_class.op = MagicMock()
    yield tested_class

class TestFirewallProxy:
    def test_op_parser_correct_response_default_params(self, fw_node):

        xml_text = "<response status='success'><result example='1'></result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response
        cmd = "Example cmd"

        assert fw_node.op_parser(cmd) == xml_parse(
            ET.tostring(raw_response.find('result'), encoding='utf8', method='xml'))['result']

        fw_node.op.assert_called_with(cmd, xml=False, cmd_xml=True, vsys=fw_node.vsys)

    def test_op_parser_correct_response_custom_params(self, fw_node):

        xml_text = "<response status='success'><result example='1'></result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response
        cmd = "Example cmd"

        assert fw_node.op_parser(cmd, True, True) == raw_response.find("result")

        fw_node.op.assert_called_with(cmd, xml=False, cmd_xml=False, vsys=fw_node.vsys)

    def test_op_parser_incorrect(self, fw_node):

        xml_text = "<response status='fail'><result example='1'></result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response
        cmd = "Example cmd"

        with pytest.raises(CommandRunFailedException) as exc_info:
            fw_node.op_parser(cmd)

        expected = f'Failed to run command: {cmd}.'
        assert expected in str(exc_info.value)

        fw_node.op.assert_called_with(cmd, xml=False, cmd_xml=True, vsys=fw_node.vsys)

    def test_op_parser_none(self, fw_node):

        xml_text = "<response status='success'><noresult example='1'></noresult></response>"
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response
        cmd = "Example cmd"

        with pytest.raises(MalformedResponseException) as exc_info:
            fw_node.op_parser(cmd)

        expected = f'No result field returned for: {cmd}'
        assert expected in str(exc_info.value)

        fw_node.op.assert_called_with(cmd, xml=False, cmd_xml=True, vsys=fw_node.vsys)

    def test_is_pending_changes_true(self, fw_node):

        xml_text = "<response status='success'><result>yes</result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response

        assert fw_node.is_pending_changes() == True

    def test_is_pending_changes_false(self, fw_node):

        xml_text = "<response status='success'><result>no</result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response

        assert fw_node.is_pending_changes() == False

    def test_is_full_commit_required_true(self, fw_node):

        xml_text = "<response status='success'><result>yes</result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response

        assert fw_node.is_full_commit_required() == True

    def test_is_full_commit_required_false(self, fw_node):

        xml_text = "<response status='success'><result>no</result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response

        assert fw_node.is_full_commit_required() == False

    def test_is_panorama_configured_true(self, fw_node):

        xml_text = "<response status='success'><result>SomePanoramaConfig</result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response

        assert fw_node.is_panorama_configured() == True

    def test_is_panorama_configured_false(self, fw_node):

        xml_text = "<response status='success'><result></result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response

        assert fw_node.is_panorama_configured() == False

# TO DO - IS PANORAMA CONNECTED
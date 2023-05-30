import pytest
from unittest.mock import MagicMock
from panos_upgrade_assurance.firewall_proxy import FirewallProxy, CommandRunFailedException
from xmltodict import parse as xml_parse
import xml.etree.ElementTree as ET

@pytest.fixture(scope="function")
def fw_node():
    tested_class = FirewallProxy()
    tested_class.op = MagicMock()
    yield tested_class

class TestFirewallProxy:
    def test_op_parser_correct_response_default_params(self, fw_node):
        """Test op parser with correct response and default parameters. Check if response is OrderedDict"""

        xml_text = "<response status='success'><result example='1'></result></response>"
        raw_response = ET.fromstring(xml_text)
        fw_node.op.return_value = raw_response
        cmd = "Example cmd"

        assert fw_node.op_parser(cmd) == xml_parse(
            ET.tostring(raw_response.find('result'), encoding='utf8', method='xml'))['result']

        fw_node.op.assert_called_with(cmd, xml=False, cmd_xml=True, vsys=fw_node.vsys)
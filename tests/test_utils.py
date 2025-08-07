import pytest
from panos_upgrade_assurance.check_firewall import CheckFirewall
from panos_upgrade_assurance.utils import ConfigParser, CheckType, SnapType, interpret_yes_no
from deepdiff import DeepDiff
from panos_upgrade_assurance.exceptions import WrongDataTypeException, UnknownParameterException


valid_check_types = [v for k, v in vars(CheckType).items() if not k.startswith("__")]
valid_snap_types = [v for k, v in vars(SnapType).items() if not k.startswith("__")]


class TestConfigParser:
    @pytest.mark.parametrize(
        "valid_config_elements, requested_config",
        [
            (valid_check_types, ["not_valid_check"]),
            (
                valid_check_types,
                [
                    "panorama",
                    "ntp_sync",
                    "not_valid_check",
                    "candidate_config",
                ],
            ),
            (
                valid_check_types,
                [
                    "panorama",
                    "ntp_sync",
                    {"content_version": {"version": "8634-7678"}},
                    {"not_valid_check": {"image_version": "10.1.6-h6"}},
                    "candidate_config",
                ],
            ),
        ],
    )
    def test_init_exception_unknown_parameter(self, valid_config_elements, requested_config):
        """Check if exception is raised when ConfigParser is called with unknown param in requested config."""
        with pytest.raises(
            UnknownParameterException,
            match=r"Unknown configuration parameter passed: .*$",
        ):
            ConfigParser(valid_config_elements, requested_config)

    @pytest.mark.parametrize(
        "valid_config_elements, requested_config",
        [
            (valid_check_types, None),
            (valid_check_types, []),
        ],
    )
    def test_init_no_requested_config(self, valid_config_elements, requested_config):
        """Check if ConfigParser sets _requested_config_element_names when requested_config is not provided."""
        parser = ConfigParser(valid_config_elements, requested_config)
        assert parser._requested_config_element_names == set(valid_config_elements)
        assert sorted(parser.requested_config) == sorted(valid_config_elements)

    @pytest.mark.parametrize(
        "requested_config, expected_requested_config_element_names",
        [
            (
                [
                    {
                        "routes": {
                            "properties": ["!flags"],
                            "count_change_threshold": 10,
                        }
                    },
                    "!content_version",
                    {
                        "session_stats": {
                            "thresholds": [
                                {"num-max": 10},
                                {"num-tcp": 10},
                            ]
                        }
                    },
                ],
                ["routes", "!content_version", "session_stats"],
            ),
        ],
    )
    def test_init_requested_config_element_names(self, requested_config, expected_requested_config_element_names, monkeypatch):
        """Check if ConfigParser sets _requested_config_element_names properly according to requested_config."""

        def _is_valid_element_name_mock(*args, **kwargs):
            return True

        # Overwrite _is_valid_element_name
        monkeypatch.setattr(ConfigParser, "_is_valid_element_name", _is_valid_element_name_mock)

        parser = ConfigParser([], requested_config)  # testing requested config - valid_elements is not important here
        assert parser._requested_config_element_names == set(
            expected_requested_config_element_names
        )  # _requested_config_element_names is a set

    @pytest.mark.parametrize(
        "requested_config, expected_requested_all_not_elements",
        [
            (["!routes"], True),
            (
                [
                    {
                        "!routes": {
                            "properties": ["!flags"],
                            "count_change_threshold": 10,
                        }
                    },
                ],
                True,
            ),
            (["!routes", "!content_version", "!session_stats"], True),
            (
                [
                    {
                        "!routes": {
                            "properties": ["!flags"],
                            "count_change_threshold": 10,
                        }
                    },
                    "!content_version",
                    {
                        "!session_stats": {
                            "thresholds": [
                                {"num-max": 10},
                                {"num-tcp": 10},
                            ]
                        }
                    },
                ],
                True,
            ),
            (["all"], False),
            (["!routes", "all"], False),
            (["!routes", "!content_version", "session_stats"], False),
            (["routes", "content_version", "session_stats"], False),
            ([], False),
            (None, False),
        ],
    )
    def test_init_requested_all_not_elements(self, requested_config, expected_requested_all_not_elements, monkeypatch):
        """Check if _requested_all_not_elements is set correctly according to the requested config."""

        def _is_valid_element_name_mock(*args, **kwargs):
            return True

        # Overwrite _is_valid_element_name
        monkeypatch.setattr(ConfigParser, "_is_valid_element_name", _is_valid_element_name_mock)

        parser = ConfigParser([], requested_config)  # testing requested config - valid_elements is not important here
        assert parser._requested_all_not_elements == expected_requested_all_not_elements

    def test_init_requested_config_element_names_with_explicit_elements(self):
        """Test ConfigParser with explicit_elements parameter.

        _requested_config_element_names is set by subsctracting explicit_elements from valid_elements, only when requested_config
            is NOT provided.

        """
        valid_elements = ["check1", "check2", "check3", "check4"]
        explicit_elements = {"check3", "check4"}

        # Test with no requested config - explicit elements should be excluded
        parser = ConfigParser(valid_elements, explicit_elements=explicit_elements)
        assert parser._requested_config_element_names == set(["check1", "check2"])

        # Test with explicit request of an explicit element as string
        parser = ConfigParser(valid_elements, requested_config=["check3"], explicit_elements=explicit_elements)
        assert parser._requested_config_element_names == {"check3"}

        # Test with explicit request of an explicit element as dict with config
        parser = ConfigParser(
            valid_elements, requested_config=[{"check3": {"param": "value"}}], explicit_elements=explicit_elements
        )
        assert parser._requested_config_element_names == {"check3"}

        # Test with 'all' including explicit elements as dict
        parser = ConfigParser(
            valid_elements, requested_config=["all", {"check3": {"param": "value"}}], explicit_elements=explicit_elements
        )
        assert parser._requested_config_element_names == {"all", "check3"}

    @pytest.mark.parametrize(
        "requested_config, element_name",
        [
            (valid_check_types, "content_version"),
            (valid_check_types, "ntp_sync"),
            (["!routes", "!content_version", "session_stats"], "session_stats"),
            (["!routes", "!content_version", "session_stats", "all"], "ntp_sync"),
            (["!routes", "!content_version", "!session_stats"], "ntp_sync"),
            (
                [
                    {
                        "!routes": {
                            "properties": ["!flags"],
                            "count_change_threshold": 10,
                        }
                    },
                    "!content_version",
                    {
                        "session_stats": {
                            "thresholds": [
                                {"num-max": 10},
                                {"num-tcp": 10},
                            ]
                        }
                    },
                ],
                "session_stats",
            ),
            (
                [
                    {
                        "!routes": {
                            "properties": ["!flags"],
                            "count_change_threshold": 10,
                        }
                    },
                    "!content_version",
                    {
                        "session_stats": {
                            "thresholds": [
                                {"num-max": 10},
                                {"num-tcp": 10},
                            ]
                        }
                    },
                    "all",
                ],
                "ntp_sync",
            ),
            (["all"], "ntp_sync"),
            ([], "ntp_sync"),
            (None, "ntp_sync"),
        ],
    )
    def test__is_element_included_true(self, requested_config, element_name):
        """Check if method returns True for given element name that should be included."""
        assert ConfigParser.is_element_included(element_name, requested_config)  # assert True

    @pytest.mark.parametrize(
        "requested_config, element_name",
        [
            (valid_check_types, "none_existing_element"),
            (["!routes", "!content_version", "session_stats"], "routes"),
            (["!routes", "!content_version", "session_stats"], "ntp_sync"),
            (["!routes", "!content_version", "session_stats", "all"], "content_version"),
            (["!routes", "!content_version", "!session_stats"], "session_stats"),
            (
                [
                    {
                        "!routes": {
                            "properties": ["!flags"],
                            "count_change_threshold": 10,
                        }
                    },
                    "!content_version",
                    {
                        "session_stats": {
                            "thresholds": [
                                {"num-max": 10},
                                {"num-tcp": 10},
                            ]
                        }
                    },
                ],
                "routes",
            ),
            (
                [
                    {
                        "!routes": {
                            "properties": ["!flags"],
                            "count_change_threshold": 10,
                        }
                    },
                    "!content_version",
                    {
                        "session_stats": {
                            "thresholds": [
                                {"num-max": 10},
                                {"num-tcp": 10},
                            ]
                        }
                    },
                    "all",
                ],
                "content_version",
            ),
        ],
    )
    def test__is_element_included_false(self, requested_config, element_name):
        """Check if method returns False for given element name that should NOT be included."""
        assert not ConfigParser.is_element_included(element_name, requested_config)  # assert False

    @pytest.mark.parametrize(
        "requested_config, element_name",
        [
            (["!routes", "!content_version", "session_stats"], "routes"),
            (["!routes", "!content_version", "session_stats", "all"], "content_version"),
            (
                [
                    {
                        "!routes": {
                            "properties": ["!flags"],
                            "count_change_threshold": 10,
                        }
                    },
                    "!content_version",
                    {
                        "session_stats": {
                            "thresholds": [
                                {"num-max": 10},
                                {"num-tcp": 10},
                            ]
                        }
                    },
                ],
                "routes",
            ),
            (
                [
                    {
                        "!routes": {
                            "properties": ["!flags"],
                            "count_change_threshold": 10,
                        }
                    },
                    "!content_version",
                    {
                        "session_stats": {
                            "thresholds": [
                                {"num-max": 10},
                                {"num-tcp": 10},
                            ]
                        }
                    },
                    "all",
                ],
                "content_version",
            ),
        ],
    )
    def test__is_element_explicit_excluded_true(self, requested_config, element_name):
        """Check if method returns True for given element name that should be excluded."""
        assert ConfigParser.is_element_explicit_excluded(element_name, requested_config)  # assert True

    @pytest.mark.parametrize(
        "requested_config, element_name",
        [
            (valid_check_types, "content_version"),
            (["!routes", "!content_version", "session_stats"], "session_stats"),
            (["!routes", "!content_version", "session_stats", "all"], "ntp_sync"),
            (["!routes", "!content_version", "!session_stats"], "ntp_sync"),
            (
                [
                    {
                        "!routes": {
                            "properties": ["!flags"],
                            "count_change_threshold": 10,
                        }
                    },
                    "!content_version",
                    {
                        "session_stats": {
                            "thresholds": [
                                {"num-max": 10},
                                {"num-tcp": 10},
                            ]
                        }
                    },
                ],
                "session_stats",
            ),
            (
                [
                    {
                        "!routes": {
                            "properties": ["!flags"],
                            "count_change_threshold": 10,
                        }
                    },
                    "!content_version",
                    {
                        "session_stats": {
                            "thresholds": [
                                {"num-max": 10},
                                {"num-tcp": 10},
                            ]
                        }
                    },
                    "all",
                ],
                "ntp_sync",
            ),
            (["all"], "ntp_sync"),
            ([], "ntp_sync"),
            (None, "ntp_sync"),
        ],
    )
    def test__is_element_explicit_excluded_false(self, requested_config, element_name):
        """Check if method returns False for given element name that is not excluded explicitly."""
        assert not ConfigParser.is_element_explicit_excluded(element_name, requested_config)  # assert True

    @pytest.mark.parametrize(
        "element_name, expected",
        [
            ("content_version", "content_version"),
            ("!ntp_sync", "ntp_sync"),
        ],
    )
    def test__strip_element_name(self, element_name, expected, monkeypatch):
        """Check method removes leading exclamation mark from element name."""
        monkeypatch.setattr(ConfigParser, "__init__", lambda _: None)
        parser = ConfigParser()
        assert parser._strip_element_name(element_name) == expected

    @pytest.mark.parametrize(
        "valid_config_elements, element_name",
        [
            (valid_check_types, "content_version"),
            (valid_check_types, "!ntp_sync"),
        ],
    )
    def test__is_valid_element_name_true(self, valid_config_elements, element_name, monkeypatch):
        """Check if method returns True for given config element in valid elements."""
        monkeypatch.setattr(ConfigParser, "__init__", lambda _: None)
        parser = ConfigParser()
        parser.valid_elements = valid_config_elements

        assert parser._is_valid_element_name(element_name)  # assert True

    @pytest.mark.parametrize(
        "valid_config_elements, element_name",
        [
            (valid_check_types, "not_valid_check"),
            (valid_check_types, "!not_valid_check"),
        ],
    )
    def test__is_valid_element_name_false(self, valid_config_elements, element_name, monkeypatch):
        """Check if method returns False if given config element is not in valid elements."""
        monkeypatch.setattr(ConfigParser, "__init__", lambda _: None)
        parser = ConfigParser()
        parser.valid_elements = valid_config_elements

        assert not parser._is_valid_element_name(element_name)  # assert False

    @pytest.mark.parametrize(
        "valid_config_elements, element_name",
        [
            (valid_check_types, "all"),
            (valid_snap_types, "all"),
        ],
    )
    def test__is_valid_element_name_all(self, valid_config_elements, element_name, monkeypatch):
        """Check if method returns True for all keyword with different valid elements."""
        monkeypatch.setattr(ConfigParser, "__init__", lambda _: None)
        parser = ConfigParser()
        parser.valid_elements = valid_config_elements
        parser.requested_config = ["all"]

        assert parser._is_valid_element_name(element_name)  # assert True

    @pytest.mark.parametrize(
        "config_element, expected",
        [
            ("panorama", "panorama"),
            ("!ha", "!ha"),
            ({"content_version": {"version": "1234-5678"}}, "content_version"),
            (
                {
                    "session_exist": {  # dict with dict multiple keys
                        "source": "134.238.135.137",
                        "destination": "10.1.0.4",
                        "dest_port": "80",
                    }
                },
                "session_exist",
            ),
            (
                {
                    "thresholds": [  # dict with list value
                        {"num-max": 10},
                        {"num-tcp": 10},
                    ]
                },
                "thresholds",
            ),
        ],
    )
    def test__extract_element_name(self, config_element, expected):
        """Check if method properly extracts config element name from given parameter."""
        assert ConfigParser._extract_element_name(config_element) == expected

    @pytest.mark.parametrize("config_element", [12, None, ("a", "b"), ["a", "b"]])
    def test__extract_element_name_exception_incorrect_type(self, config_element):
        """Check if exception is raised when method is called with incorrect parameter type."""
        with pytest.raises(WrongDataTypeException) as exc_info:
            ConfigParser._extract_element_name(config_element)

        expected = "Config definition is neither string or dict"
        assert expected == str(exc_info.value)

    @pytest.mark.parametrize(
        "config_element",
        [
            {
                "ha": {"skip_config_sync": True},
                "content_version": {"version": "1234-5678"},
            },  # dict config element should have single key
        ],
    )
    def test__extract_element_name_exception_incorrect_dict(self, config_element):
        """Check if exception is raised when dict provided as param has incorrect format - should have a single key-value."""
        with pytest.raises(WrongDataTypeException) as exc_info:
            ConfigParser._extract_element_name(config_element)

        expected = "Dict provided as config definition has incorrect format, it is supposed to have only one key {key:[]}"
        assert expected == str(exc_info.value)

    @pytest.mark.parametrize(
        "requested_config, expected",
        [
            (["!routes", "!content_version", "session_stats"], ["!routes", "!content_version", "session_stats"]),
            (["!routes", "!content_version", "session_stats", "all"], ["!routes", "!content_version", "session_stats", "all"]),
            (
                [
                    {
                        "!routes": {
                            "properties": ["!flags"],
                            "count_change_threshold": 10,
                        }
                    },
                    "!content_version",
                    {
                        "session_stats": {
                            "thresholds": [
                                {"num-max": 10},
                                {"num-tcp": 10},
                            ]
                        }
                    },
                ],
                ["!routes", "!content_version", "session_stats"],
            ),
            (
                [
                    {
                        "!routes": {
                            "properties": ["!flags"],
                            "count_change_threshold": 10,
                        }
                    },
                    "!content_version",
                    {
                        "session_stats": {
                            "thresholds": [
                                {"num-max": 10},
                                {"num-tcp": 10},
                            ]
                        }
                    },
                    "all",
                ],
                ["!routes", "!content_version", "session_stats", "all"],
            ),
            ([], []),
        ],
    )
    def test__iter_config_element_names(self, requested_config, expected):
        """Check method iterates correctly on the requested_config extracting config element names."""
        assert list(ConfigParser._iter_config_element_names(requested_config)) == expected

    @pytest.mark.parametrize(
        "requested_config, element_name, expected",
        [
            (["!routes", "!content_version", "session_stats"], "session_stats", "session_stats"),
            (
                [
                    {
                        "!routes": {
                            "properties": ["!flags"],
                            "count_change_threshold": 10,
                        }
                    },
                    "!content_version",
                    {
                        "session_stats": {
                            "thresholds": [
                                {"num-max": 10},
                                {"num-tcp": 10},
                            ]
                        }
                    },
                    "all",
                ],
                "session_stats",
                {
                    "session_stats": {
                        "thresholds": [
                            {"num-max": 10},
                            {"num-tcp": 10},
                        ]
                    }
                },
            ),
            (["!routes", "!content_version", "session_stats"], "none_existing_element", None),
            ([], "routes", None),
        ],
    )
    def test_get_config_element_by_name(self, requested_config, element_name, expected, monkeypatch):
        """Check if method returns config element as str or dict for requested element name.

        This method does not support returning `not-element` of a given config element so it's not
        included in the tests.
        """

        def _is_valid_element_name_mock(*args, **kwargs):
            return True

        # Overwrite _is_valid_element_name
        monkeypatch.setattr(ConfigParser, "_is_valid_element_name", _is_valid_element_name_mock)

        parser = ConfigParser([], requested_config)  # valid_elements is not important here
        assert parser.get_config_element_by_name(element_name) == expected

    @pytest.mark.parametrize(
        "valid_config_elements, requested_config, expected",
        [
            (valid_check_types, [], list(set(valid_check_types) - CheckFirewall.EXPLICIT_CHECKS)),
            (valid_check_types, ["all"], list(set(valid_check_types) - CheckFirewall.EXPLICIT_CHECKS)),
            (
                valid_check_types,
                [{"ha": None}, "content_version", {"free_disk_space": {"image_version": "10.1.1"}}],
                [{"ha": None}, "content_version", {"free_disk_space": {"image_version": "10.1.1"}}],
            ),
            (
                valid_check_types,
                ["!ha", "!ntp_sync"],
                list(set(valid_check_types) - {"ha", "ntp_sync"} - CheckFirewall.EXPLICIT_CHECKS),
            ),
            (valid_check_types, ["all"] + list(CheckFirewall.EXPLICIT_CHECKS), valid_check_types),
            (
                valid_check_types,
                [
                    "panorama",
                    {"arp_entry_exist": {"ip": "10.10.10.10"}},
                    {"content_version": {"version": "123"}},
                ],
                [
                    "panorama",
                    {"arp_entry_exist": {"ip": "10.10.10.10"}},
                    {"content_version": {"version": "123"}},
                ],
            ),
            (
                valid_snap_types,
                [
                    {
                        "routes": {
                            "properties": ["!flags"],
                            "count_change_threshold": 10,
                        }
                    },
                    "!content_version",
                    {
                        "session_stats": {
                            "thresholds": [
                                {"num-max": 10},
                                {"num-tcp": 10},
                            ]
                        }
                    },
                ],
                [
                    {
                        "routes": {
                            "properties": ["!flags"],
                            "count_change_threshold": 10,
                        }
                    },
                    {
                        "session_stats": {
                            "thresholds": [
                                {"num-max": 10},
                                {"num-tcp": 10},
                            ]
                        }
                    },
                ],
            ),
            (
                valid_snap_types,
                [
                    "all",
                    {
                        "routes": {
                            "properties": ["!flags"],
                            "count_change_threshold": 10,
                        }
                    },
                    "!content_version",
                    {
                        "session_stats": {
                            "thresholds": [
                                {"num-max": 10},
                                {"num-tcp": 10},
                            ]
                        }
                    },
                ],
                # subtract specified and excluded tests from all and then re-add the specified tests with properties
                # to find the final config
                list(set(valid_snap_types) - {"routes", "content_version", "session_stats"})
                + [
                    {
                        "routes": {
                            "properties": ["!flags"],
                            "count_change_threshold": 10,
                        }
                    },
                    {
                        "session_stats": {
                            "thresholds": [
                                {"num-max": 10},
                                {"num-tcp": 10},
                            ]
                        }
                    },
                ],
            ),
        ],
    )
    def test_prepare_config(self, valid_config_elements, requested_config, expected):
        """Check if config is prepared in expected way."""
        parser = ConfigParser(valid_config_elements, requested_config, CheckFirewall.EXPLICIT_CHECKS)
        final_config = parser.prepare_config()
        assert not DeepDiff(
            final_config, expected, ignore_order=True
        )  # assert list == doesnt work for nested objects and unordered lists


@pytest.mark.parametrize("boolstr", ["yes", "no"])
def test_interpret_yes_no(boolstr):
    interpret_yes_no(boolstr)


@pytest.mark.parametrize("boolstr", [1, "true", True])
def test_interpret_yes_no_exception(boolstr):
    with pytest.raises(WrongDataTypeException, match="Cannot interpret following string as boolean:.*$"):
        interpret_yes_no(boolstr)

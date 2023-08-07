import pytest
from unittest.mock import MagicMock
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
        """Check if ConfigParser sets _requested_config_names when requested_config is not provided."""
        parser = ConfigParser(valid_config_elements, requested_config)
        assert parser._requested_config_names == set(valid_config_elements)
        assert parser.requested_config == valid_config_elements

    @pytest.mark.parametrize(
        "requested_config, expected_requested_config_names",
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
    def test_init_requested_config_names(self, requested_config, expected_requested_config_names, monkeypatch):
        """Check if ConfigParser sets _requested_config_names properly according to requested_config."""

        def _is_element_included_mock(*args, **kwargs):
            return True

        # Overwrite _is_element_included
        monkeypatch.setattr(ConfigParser, "_is_element_included", _is_element_included_mock)

        parser = ConfigParser([], requested_config)  # testing requested config - valid_elements is not important here
        assert parser._requested_config_names == set(expected_requested_config_names)  # _requested_config_names is a set

    @pytest.mark.parametrize(
        "valid_config_elements, config_element",
        [
            (valid_check_types, "content_version"),
            (valid_check_types, "!ntp_sync"),
        ],
    )
    def test__is_element_included_true(self, valid_config_elements, config_element, monkeypatch):
        """Check if method returns True for given config element in valid elements."""
        monkeypatch.setattr(ConfigParser, "__init__", lambda _: None)
        parser = ConfigParser()
        parser.valid_elements = valid_config_elements

        assert parser._is_element_included(config_element)  # assert True

    @pytest.mark.parametrize(
        "valid_config_elements, config_element",
        [
            (valid_check_types, "not_valid_check"),
            (valid_check_types, "!not_valid_check"),
        ],
    )
    def test__is_element_included_false(self, valid_config_elements, config_element, monkeypatch):
        """Check if method returns False if given config element is not in valid elements."""
        monkeypatch.setattr(ConfigParser, "__init__", lambda _: None)
        parser = ConfigParser()
        parser.valid_elements = valid_config_elements

        assert not parser._is_element_included(config_element)  # assert False

    @pytest.mark.parametrize(
        "valid_config_elements, config_element",
        [
            (valid_check_types, "all"),
            (valid_snap_types, "all"),
        ],
    )
    def test__is_element_included_all(self, valid_config_elements, config_element, monkeypatch):
        """Check if method returns True for all keyword with different valid elements."""
        monkeypatch.setattr(ConfigParser, "__init__", lambda _: None)
        parser = ConfigParser()
        parser.valid_elements = valid_config_elements
        parser.requested_config = ["all"]

        assert parser._is_element_included(config_element)  # assert True

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
        "requested_config, requested_config_all_inserted",
        [
            (["!ha", "!panorama"], ["all", "!ha", "!panorama"]),
        ],
    )
    def test_prepare_config_insert_all(self, requested_config, requested_config_all_inserted, monkeypatch):
        """Check if method add "all" keyword when all provided tests are skipped in configuration."""

        def _expand_all_mock(*args, **kwargs):
            pass

        def _is_element_included_mock(*args, **kwargs):
            return True

        # Overwrite _is_element_included and _expand_all
        monkeypatch.setattr(ConfigParser, "_expand_all", _expand_all_mock)
        monkeypatch.setattr(ConfigParser, "_is_element_included", _is_element_included_mock)

        parser = ConfigParser([], requested_config)  # testing requested config - valid_elements is not important here
        parser.prepare_config()

        assert parser.requested_config == requested_config_all_inserted

    @pytest.mark.parametrize(
        "requested_config",
        [
            ["all"],
            [
                "all",
                "!ntp_sync",
                {"content_version": {"version": "8634-7678"}},
            ],
            ["!ha", "!panorama"],
        ],
    )
    def test_prepare_config_call_expand_all(self, requested_config, monkeypatch):
        """Check if _expand_all is called when there is "all" keyword in requested config or all elements are exclusions."""

        def _is_element_included_mock(*args, **kwargs):
            return True

        # Overwrite _is_element_included
        monkeypatch.setattr(ConfigParser, "_is_element_included", _is_element_included_mock)

        parser = ConfigParser([], requested_config)  # testing requested config - valid_elements is not important here
        parser._expand_all = MagicMock()

        parser.prepare_config()
        parser._expand_all.assert_called()

    @pytest.mark.parametrize(
        "requested_config",
        [
            ["panorama", "!ha"],
            [
                {"routes": {"properties": ["!flags"], "count_change_threshold": 10}},
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
        ],
    )
    def test_prepare_config_dont_call_expand_all(self, requested_config, monkeypatch):
        """Check if _expand_all is not called without "all" keyword in requested_config
        or all elements are not exclusions.
        """

        def _is_element_included_mock(*args, **kwargs):
            return True

        # Overwrite _is_element_included
        monkeypatch.setattr(ConfigParser, "_is_element_included", _is_element_included_mock)

        parser = ConfigParser([], requested_config)  # testing requested config - valid_elements is not important here
        parser._expand_all = MagicMock()

        parser.prepare_config()
        parser._expand_all.assert_not_called()

    @pytest.mark.parametrize(
        "valid_config_elements, requested_config, expected",
        [
            (valid_check_types, [], valid_check_types),
            (valid_check_types, ["all"], valid_check_types),
            (
                valid_check_types,
                [
                    {"ha": None},
                    "content_version",
                    {"free_disk_space": { "image_version": "10.1.1" }}
                ],
                [
                    {"ha": None},
                    "content_version",
                    {"free_disk_space": { "image_version": "10.1.1" }}
                ],
            ),
            (
                valid_check_types,
                ["!ha", "!ntp_sync"],
                list(set(valid_check_types) - {"ha", "ntp_sync"}),
            ),
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
        parser = ConfigParser(valid_config_elements, requested_config)
        final_config = parser.prepare_config()
        # print(final_config)
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

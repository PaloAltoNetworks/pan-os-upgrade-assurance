import pytest
from unittest.mock import MagicMock
from deepdiff import DeepDiff
from panos_upgrade_assurance.snapshot_compare import SnapshotCompare
from panos_upgrade_assurance.exceptions import (
    WrongDataTypeException,
    MissingKeyException,
    SnapshotSchemeMismatchException,
    SnapshotNoneComparisonException,
)
from snapshots import snap1, snap2


class TestSnapshotCompare:
    def test_validate_keys_exist_single_key_present(self):
        key = "nics"
        SnapshotCompare.validate_keys_exist(snap1, snap2, key)

    def test_validate_keys_exist_multiple_keys_present(self):
        key = ["nics", "arp_table"]
        SnapshotCompare.validate_keys_exist(snap1, snap2, key)

    @pytest.mark.parametrize(
        "left_snapshot, right_snapshot, key, missing",
        [
            ({"key1": "value1"}, {"key1": "value1"}, "key2", "both snapshots"),
            ({"key1": "value1"}, {"key1": "value1", "key2": "value2"}, "key2", "left snapshot"),
            ({"key1": "value1", "key2": "value2"}, {"key1": "value1"}, "key2", "right snapshot"),
            ({"key1": "value1"}, {"key1": "value1"}, ["key2", "key3"], "both snapshots"),
            ({"key1": "value1"}, {"key1": "value1", "key2": "value2", "key3": "value3"}, ["key2", "key3"], "left snapshot"),
            ({"key1": "value1"}, {"key1": "value1", "key2": "value2", "key3": "value3"}, ["key2"], "left snapshot"),
            ({"key1": "value1", "key2": "value2", "key3": "value3"}, {"key1": "value1"}, ["key2", "key3"], "right snapshot"),
            ({"key1": "value1", "key2": "value2", "key3": "value3"}, {"key1": "value1"}, ["key2"], "right snapshot"),
        ],
    )
    def test_validate_keys_exist_keys_missing(self, left_snapshot, right_snapshot, key, missing):
        with pytest.raises(MissingKeyException) as exception_msg:
            SnapshotCompare.validate_keys_exist(left_snapshot, right_snapshot, key)

        assert str(exception_msg.value) == f"{key} (some elements if set/list) is missing in {missing}"

    @pytest.mark.parametrize("key", [123, 12.3, {"key": "value"}])
    def test_validate_keys_exist_wrong_data_type_exception(self, key):
        with pytest.raises(WrongDataTypeException) as exception_msg:
            SnapshotCompare.validate_keys_exist(snap1, snap2, key)

        assert str(exception_msg.value) == f"The key variable is a {type(key)} but should be either: str, set or list"

    def test_calculate_diff_on_dicts_same_dicts(self):
        left_snapshot = {"key1": "value1", "key2": "value2"}
        right_snapshot = {"key1": "value1", "key2": "value2"}

        result = SnapshotCompare.calculate_diff_on_dicts(left_snapshot, right_snapshot)

        assert result == {
            "added": {"added_keys": [], "passed": True},
            "changed": {"changed_raw": {}, "passed": True},
            "missing": {"missing_keys": [], "passed": True},
        }

    def test_calculate_diff_on_dicts_different_values(self):
        left_snapshot = {"key1": "value1", "key2": "value2"}
        right_snapshot = {"key1": "new_value1", "key2": "value2"}

        result = SnapshotCompare.calculate_diff_on_dicts(left_snapshot, right_snapshot)

        assert result == {
            "added": {"added_keys": [], "passed": True},
            "changed": {"changed_raw": {"key1": {"left_snap": "value1", "right_snap": "new_value1"}}, "passed": False},
            "missing": {"missing_keys": [], "passed": True},
        }

    def test_calculate_diff_on_dicts_additional_key(self):
        left_snapshot = {"key1": "value1", "key2": "value2"}
        right_snapshot = {"key1": "value1", "key2": "value2", "key3": "value3"}

        result = SnapshotCompare.calculate_diff_on_dicts(left_snapshot, right_snapshot)

        assert result == {
            "added": {"added_keys": ["key3"], "passed": False},
            "changed": {"changed_raw": {}, "passed": True},
            "missing": {"missing_keys": [], "passed": True},
        }

    def test_calculate_diff_on_dicts_missing_key(self):
        left_snapshot = {"key1": "value1", "key2": "value2"}
        right_snapshot = {"key1": "value1"}

        result = SnapshotCompare.calculate_diff_on_dicts(left_snapshot, right_snapshot)

        assert result == {
            "added": {"added_keys": [], "passed": True},
            "changed": {"changed_raw": {}, "passed": True},
            "missing": {"missing_keys": ["key2"], "passed": False},
        }

    def test_calculate_diff_on_dicts_nested_dicts(self):
        left_snapshot = {"key1": {"nested_key1": "value1"}, "key2": "value2"}
        right_snapshot = {"key1": {"nested_key1": "new_value1"}, "key2": "value2"}

        result = SnapshotCompare.calculate_diff_on_dicts(left_snapshot, right_snapshot)

        assert result == {
            "added": {"added_keys": [], "passed": True},
            "changed": {
                "changed_raw": {
                    "key1": {
                        "added": {"added_keys": [], "passed": True},
                        "changed": {
                            "changed_raw": {"nested_key1": {"left_snap": "value1", "right_snap": "new_value1"}},
                            "passed": False,
                        },
                        "missing": {"missing_keys": [], "passed": True},
                        "passed": False,
                    }
                },
                "passed": False,
            },
            "missing": {"missing_keys": [], "passed": True},
        }

    def test_calculate_diff_on_dicts_empty_dicts(self):
        left_snapshot = {}
        right_snapshot = {}

        result = SnapshotCompare.calculate_diff_on_dicts(left_snapshot, right_snapshot)

        assert result == {
            "missing": {"passed": True, "missing_keys": []},
            "added": {"passed": True, "added_keys": []},
            "changed": {"passed": True, "changed_raw": {}},
        }

    def test_calculate_diff_on_dicts_parents(self):
        """Check if specific parent dict is compared only on a report type."""
        report_type = "ip_sec_tunnels"
        properties = ["ipsec_tun"]  # compare specific ipsec tunnel only
        result = SnapshotCompare.calculate_diff_on_dicts(
            snap1[report_type]["snapshot"], snap2[report_type]["snapshot"], properties
        )
        assert result == {
            "added": {"added_keys": [], "passed": True},
            "changed": {
                "changed_raw": {
                    "ipsec_tun": {
                        "added": {"added_keys": [], "passed": True},
                        "changed": {"changed_raw": {"mon": {"left_snap": "on", "right_snap": "off"}}, "passed": False},
                        "missing": {"missing_keys": ["gwid"], "passed": False},
                        "passed": False,
                    }
                },
                "passed": False,
            },
            "missing": {"missing_keys": [], "passed": True},
        }

    def test_calculate_diff_on_dicts_skip_parents(self):
        """Check if rest is compared when specific parent dict is skipped on a report type."""
        report_type = "ip_sec_tunnels"
        properties = ["!ipsec_tun"]  # skip specific ipsec tunnel and compare the rest
        result = SnapshotCompare.calculate_diff_on_dicts(
            snap1[report_type]["snapshot"], snap2[report_type]["snapshot"], properties
        )
        assert result == {
            "added": {"added_keys": [], "passed": True},
            "changed": {
                "changed_raw": {
                    "priv_tun": {
                        "added": {"added_keys": [], "passed": True},
                        "changed": {"changed_raw": {"state": {"left_snap": "active", "right_snap": "init"}}, "passed": False},
                        "missing": {"missing_keys": [], "passed": True},
                        "passed": False,
                    }
                },
                "passed": False,
            },
            "missing": {"missing_keys": ["sres"], "passed": False},
        }

    def test_calculate_diff_on_dicts_with_subdicts(self):
        """Check if sub-dicts are also compared on a report type."""
        report_type = "license"
        properties = ["Logging Service"]  # Logging Service has "custom" sub-dict
        result = SnapshotCompare.calculate_diff_on_dicts(
            snap1[report_type]["snapshot"], snap2[report_type]["snapshot"], properties
        )
        assert result == {
            "added": {"added_keys": [], "passed": True},
            "changed": {
                "changed_raw": {
                    "Logging Service": {
                        "added": {"added_keys": [], "passed": True},
                        "changed": {
                            "changed_raw": {
                                "custom": {
                                    "added": {"added_keys": [], "passed": True},
                                    "changed": {
                                        "changed_raw": {"_Log_Storage_TB": {"left_snap": "7", "right_snap": "9"}},
                                        "passed": False,
                                    },
                                    "missing": {"missing_keys": [], "passed": True},
                                    "passed": False,
                                },
                                "serial": {"left_snap": "007257000334668", "right_snap": "007257000334667"},
                            },
                            "passed": False,
                        },
                        "missing": {"missing_keys": [], "passed": True},
                        "passed": False,
                    }
                },
                "passed": False,
            },
            "missing": {"missing_keys": [], "passed": True},
        }

    def test_calculate_diff_on_dicts_exclude_subdict(self):
        """Check if excluding sub-dicts works on a report type."""
        report_type = "license"
        properties = [  # "Logging Service" has "custom" sub-dict which will be skipped
            "!custom",
            "!DNS Security",  # other license types are skipped to reduce clutter
            "!AutoFocus Device License",
            "!Premium",
            "!GlobalProtect Gateway",
            "!Threat Prevention",
            "!WildFire License",
            "!PA-VM",
            "!PAN-DB URL Filtering",
        ]
        result = SnapshotCompare.calculate_diff_on_dicts(
            snap1[report_type]["snapshot"], snap2[report_type]["snapshot"], properties
        )
        assert result == {
            "added": {"added_keys": [], "passed": True},
            "changed": {
                "changed_raw": {
                    "Logging Service": {
                        "added": {"added_keys": [], "passed": True},
                        "changed": {
                            "changed_raw": {"serial": {"left_snap": "007257000334668", "right_snap": "007257000334667"}},
                            "passed": False,
                        },
                        "missing": {"missing_keys": [], "passed": True},
                        "passed": False,
                    }
                },
                "passed": False,
            },
            "missing": {"missing_keys": [], "passed": True},
        }

    def test_calculate_diff_on_dicts_compare_subdict(self):
        """Check if only provided sub-dicts(keys) are compared on a report type."""
        report_type = "license"
        properties = ["custom"]  # Logging Service has "custom" sub-dict
        result = SnapshotCompare.calculate_diff_on_dicts(
            snap1[report_type]["snapshot"], snap2[report_type]["snapshot"], properties
        )
        assert result == {
            "added": {"added_keys": [], "passed": True},
            "changed": {
                "changed_raw": {
                    "Logging Service": {
                        "added": {"added_keys": [], "passed": True},
                        "changed": {
                            "changed_raw": {
                                "custom": {
                                    "added": {"added_keys": [], "passed": True},
                                    "changed": {
                                        "changed_raw": {"_Log_Storage_TB": {"left_snap": "7", "right_snap": "9"}},
                                        "passed": False,
                                    },
                                    "missing": {"missing_keys": [], "passed": True},
                                    "passed": False,
                                },
                            },
                            "passed": False,
                        },
                        "missing": {"missing_keys": [], "passed": True},
                        "passed": False,
                    }
                },
                "passed": False,
            },
            "missing": {"missing_keys": [], "passed": True},
        }

    def test_calculate_diff_on_dicts_no_nested_and(self):
        """Check if sub-dicts are fully compared if properties have parent-child relantionship and child property is ignored."""
        report_type = "license"
        # Logging Service has "custom" sub-dict but since properities have parent-child relantionship,
        # no "and" operation will be applied and all keys for "Logging Service" will be compared
        properties = ["custom", "Logging Service"]
        result = SnapshotCompare.calculate_diff_on_dicts(
            snap1[report_type]["snapshot"], snap2[report_type]["snapshot"], properties
        )
        assert result == {
            "added": {"added_keys": [], "passed": True},
            "changed": {
                "changed_raw": {
                    "Logging Service": {
                        "added": {"added_keys": [], "passed": True},
                        "changed": {
                            "changed_raw": {
                                "custom": {
                                    "added": {"added_keys": [], "passed": True},
                                    "changed": {
                                        "changed_raw": {"_Log_Storage_TB": {"left_snap": "7", "right_snap": "9"}},
                                        "passed": False,
                                    },
                                    "missing": {"missing_keys": [], "passed": True},
                                    "passed": False,
                                },
                                "serial": {"left_snap": "007257000334668", "right_snap": "007257000334667"},
                            },
                            "passed": False,
                        },
                        "missing": {"missing_keys": [], "passed": True},
                        "passed": False,
                    }
                },
                "passed": False,
            },
            "missing": {"missing_keys": [], "passed": True},
        }

    def test_calculate_diff_on_dicts_multi_exclusions(self):
        """Check if multiple exlusions works on a report type."""
        report_type = "license"
        properties = ["!custom", "!serial"]
        result = SnapshotCompare.calculate_diff_on_dicts(
            snap1[report_type]["snapshot"], snap2[report_type]["snapshot"], properties
        )
        assert result == {
            "added": {"added_keys": [], "passed": True},
            "changed": {"changed_raw": {}, "passed": True},
            "missing": {"missing_keys": ["AutoFocus Device License"], "passed": False},
        }

    # NOTE: Non-dictionary input is not handled in the code and not tested
    # if non supported input is passed it raises AttributeError since it doesnt have keys() method
    def test_calculate_diff_on_dicts_invalid_input(self):
        left_snapshot = {"key1": 1.23, "key2": "value2"}
        right_snapshot = {"key1": {"nested_key1": "value1"}, "key2": "value2"}

        with pytest.raises(WrongDataTypeException) as exception_msg:
            SnapshotCompare.calculate_diff_on_dicts(left_snapshot, right_snapshot)

        assert str(exception_msg.value) == "Unknown value format for key key1."

    def test_calculate_diff_on_dicts_identical_returns_structure_not_none(self):
        """Test that calculate_diff_on_dicts always returns a structured dict, even for identical inputs.

        This documents that the method always returns {'missing': {...}, 'added': {...}, 'changed': {...}}
        which means `if result:` will always be True, making line 911 in compare_type_are_routes
        and similar code paths unreachable.
        """
        # Test with identical dictionaries
        left = {"key1": "value1", "key2": "value2"}
        right = {"key1": "value1", "key2": "value2"}

        result = SnapshotCompare.calculate_diff_on_dicts(left, right)

        # Result should always be a dict with structure, never None or empty {}
        assert result is not None
        assert isinstance(result, dict)
        assert result != {}  # Not an empty dict

        # Should have the standard structure
        assert "missing" in result
        assert "added" in result
        assert "changed" in result

        # All should be passing with empty lists/dicts
        assert result["missing"]["passed"] is True
        assert result["missing"]["missing_keys"] == []
        assert result["added"]["passed"] is True
        assert result["added"]["added_keys"] == []
        assert result["changed"]["passed"] is True
        assert result["changed"]["changed_raw"] == {}

        # The dict will always evaluate to True (not empty)
        assert bool(result) is True

    @pytest.mark.parametrize(
        "param_result, pass_returned",
        [
            (
                {  # all passed
                    "added": {"added_keys": [], "passed": True},
                    "changed": {"changed_raw": {}, "passed": True},
                    "missing": {"missing_keys": [], "passed": True},
                },
                True,
            ),
            (
                {  # mixed failed
                    "added": {"added_keys": [], "passed": True},
                    "changed": {"changed_raw": {}, "passed": True},
                    "missing": {"missing_keys": ["key2"], "passed": False},
                },
                False,
            ),
            (
                {  # all failed
                    "added": {"added_keys": ["key3"], "passed": False},
                    "changed": {"changed_raw": {"key1": {"left_snap": "value1", "right_snap": "new_value1"}}, "passed": False},
                    "missing": {"missing_keys": ["key2"], "passed": False},
                },
                False,
            ),
        ],
    )
    def test_calculate_passed(self, param_result, pass_returned):
        SnapshotCompare.calculate_passed(result=param_result)

        assert param_result["passed"] is pass_returned

    def test_calculate_metric_change_percentage_within_threshold(self):
        # first_value = 100       # NOTE: this results in 16.67 change instead of 20..
        # second_value = 120
        # threshold = 20
        first_value = 10
        second_value = 15
        threshold = 40

        snapshot_compare = SnapshotCompare({}, {})
        result = snapshot_compare._calculate_metric_change_percentage(first_value, second_value, threshold)

        assert result["passed"] is True
        assert result["change_percentage"] == 33.33
        assert result["change_threshold"] == threshold

    def test_calculate_metric_change_percentage_exceeds_threshold(self):
        first_value = 10
        second_value = 15
        threshold = 20

        snapshot_compare = SnapshotCompare({}, {})
        result = snapshot_compare._calculate_metric_change_percentage(first_value, second_value, threshold)

        assert result["passed"] is False
        assert result["change_percentage"] == 33.33
        assert result["change_threshold"] == threshold

    def test_calculate_metric_change_percentage_invalid_threshold(self):
        first_value = 100
        second_value = 110
        threshold = 110

        snapshot_compare = SnapshotCompare({}, {})
        with pytest.raises(WrongDataTypeException) as exception_msg:
            snapshot_compare._calculate_metric_change_percentage(first_value, second_value, threshold)

        assert str(exception_msg.value) == "The threshold should be a percentage value between 0 and 100."

    @pytest.mark.parametrize(
        "comparison_result, left_dict, right_dict, threshold, expected",
        [
            # Case 1: Changes exceed 100% but within threshold
            (
                {
                    "added": {"added_keys": ["key1", "key2"]},
                    "missing": {"missing_keys": ["key3"]},
                    "changed": {"changed_raw": {"key4": {}, "key5": {}}},
                },
                {"key3": "value", "key4": "old", "key5": "old", "key6": "unchanged"},
                {"key1": "value", "key2": "value", "key4": "new", "key5": "new", "key6": "unchanged"},
                100.0,
                {"change_percentage": 125.0, "change_threshold": 100.0, "passed": False},
            ),
            # Case 2: Changes exceed threshold
            (
                {
                    "added": {"added_keys": ["key1", "key2"]},
                    "missing": {"missing_keys": ["key3"]},
                    "changed": {"changed_raw": {"key4": {}, "key5": {}}},
                },
                {"key3": "value", "key4": "old", "key5": "old", "key6": "unchanged"},
                {"key1": "value", "key2": "value", "key4": "new", "key5": "new", "key6": "unchanged"},
                50.0,
                {"change_percentage": 125.0, "change_threshold": 50.0, "passed": False},
            ),
            # Case 3: Empty left snapshot
            (
                {"added": {"added_keys": ["key1"]}, "missing": {"missing_keys": []}, "changed": {"changed_raw": {}}},
                {},
                {"key1": "value"},
                10.0,
                {"change_percentage": 100.0, "change_threshold": 10.0, "passed": False},
            ),
            # Case 4: Both snapshots empty
            (
                {"added": {"added_keys": []}, "missing": {"missing_keys": []}, "changed": {"changed_raw": {}}},
                {},
                {},
                10.0,
                {"change_percentage": 0.0, "change_threshold": 10.0, "passed": True},
            ),
            # Case 5: Changes within threshold - should pass
            (
                {
                    "added": {"added_keys": ["key11"]},
                    "missing": {"missing_keys": ["key1"]},
                    "changed": {"changed_raw": {"key2": {}}},
                },
                {
                    "key1": "v1",
                    "key2": "old",
                    "key3": "v3",
                    "key4": "v4",
                    "key5": "v5",
                    "key6": "v6",
                    "key7": "v7",
                    "key8": "v8",
                    "key9": "v9",
                    "key10": "v10",
                },  # 10 items
                {
                    "key2": "new",
                    "key3": "v3",
                    "key4": "v4",
                    "key5": "v5",
                    "key6": "v6",
                    "key7": "v7",
                    "key8": "v8",
                    "key9": "v9",
                    "key10": "v10",
                    "key11": "v11",
                },  # 1 missing, 1 added, 1 changed
                50.0,
                {"change_percentage": 30.0, "change_threshold": 50.0, "passed": True},
            ),
        ],
    )
    def test_calculate_count_change_percentage(self, comparison_result, left_dict, right_dict, threshold, expected):
        """Test various scenarios for count change percentage calculation."""
        sc = SnapshotCompare({}, {})

        result = sc._calculate_count_change_percentage(
            comparison_result=comparison_result,
            left_snapshot_type_dict=left_dict,
            right_snapshot_type_dict=right_dict,
            count_change_threshold=threshold,
        )

        assert result["change_percentage"] == expected["change_percentage"]
        assert result["change_threshold"] == expected["change_threshold"]
        assert result["passed"] == expected["passed"]

    def test_compare_type_generic_call_calculate_passed(self):
        snapshot_compare = SnapshotCompare(snap1, snap2)
        # NOTE do NOT use MagicMock on Class.method directly, it messes up other tests, mock self method
        snapshot_compare.calculate_passed = MagicMock()
        snapshot_compare.compare_type_generic(report_type="nics")

        snapshot_compare.calculate_passed.assert_called()

    def test_compare_type_generic_calls_calculate_diff_on_dicts(self):
        """Test that compare_type_generic calls calculate_diff_on_dicts."""
        snapshot_compare = SnapshotCompare(snap1, snap2)
        snapshot_compare.calculate_diff_on_dicts = MagicMock(
            return_value={
                "missing": {"passed": True, "missing_keys": []},
                "added": {"passed": True, "added_keys": []},
                "changed": {"passed": True, "changed_raw": {}},
            }
        )

        snapshot_compare.compare_type_generic(report_type="nics")

        snapshot_compare.calculate_diff_on_dicts.assert_called_once()

    def test_compare_type_generic_calls_calculate_count_change_percentage(self):
        """Test that compare_type_generic calls _calculate_count_change_percentage when threshold is provided."""
        snapshot_compare = SnapshotCompare(snap1, snap2)

        # Mock the helper method
        snapshot_compare._calculate_count_change_percentage = MagicMock(
            return_value={"passed": True, "change_percentage": 10.0, "change_threshold": 50.0}
        )

        # Call with count_change_threshold
        snapshot_compare.compare_type_generic(report_type="nics", count_change_threshold=50)

        # Verify _calculate_count_change_percentage was called
        snapshot_compare._calculate_count_change_percentage.assert_called_once()

        # Verify it was called with correct parameters
        call_args = snapshot_compare._calculate_count_change_percentage.call_args
        assert call_args.kwargs["count_change_threshold"] == 50

    def test_compare_type_generic_count_change_false(self):
        left_snapshot = {
            "nics": {
                "state": True,
                "status": "SUCCESS",
                "reason": "",
                "snapshot": {"ethernet1/2": "up", "ethernet1/3": "up", "tunnel": "up"},
            }
        }
        right_snapshot = {
            "nics": {
                "state": True,
                "status": "SUCCESS",
                "reason": "",
                "snapshot": {"ethernet1/2": "up", "ethernet1/3": "down", "tunnel": "up"},
            }
        }
        change_threshold = 10
        snapshot_compare = SnapshotCompare(left_snapshot, right_snapshot)
        result = snapshot_compare.compare_type_generic(report_type="nics", count_change_threshold=change_threshold)

        assert result["count_change_percentage"] == {
            "passed": False,
            "change_percentage": 33.33,
            "change_threshold": float(change_threshold),
        }

    def test_compare_type_generic_count_change_true(self):
        left_snapshot = {
            "nics": {
                "state": True,
                "status": "SUCCESS",
                "reason": "",
                "snapshot": {"ethernet1/2": "up", "ethernet1/3": "up", "tunnel": "up"},
            }
        }
        right_snapshot = {
            "nics": {
                "state": True,
                "status": "SUCCESS",
                "reason": "",
                "snapshot": {"ethernet1/2": "up", "ethernet1/3": "down", "tunnel": "up"},
            }
        }
        change_threshold = 40

        snapshot_compare = SnapshotCompare(left_snapshot, right_snapshot)
        result = snapshot_compare.compare_type_generic(report_type="nics", count_change_threshold=change_threshold)

        assert result["count_change_percentage"] == {
            "passed": True,
            "change_percentage": 33.33,
            "change_threshold": float(change_threshold),
        }

    @pytest.mark.parametrize("count_change_threshold", [-10, 120])
    def test_compare_type_generic_invalid_count_change_threshold(self, count_change_threshold):
        snapshot_compare = SnapshotCompare(snap1, snap2)
        snapshot_compare.calculate_diff_on_dicts.return_value = {
            "added": {"added_keys": [], "passed": True},
            "changed": {"changed_raw": {}, "passed": True},
            "missing": {"missing_keys": [], "passed": True},
        }

        with pytest.raises(WrongDataTypeException, match="The threshold should be a percentage value between 0 and 100."):
            snapshot_compare.compare_type_generic(report_type="nics", count_change_threshold=count_change_threshold)

    @pytest.mark.parametrize(
        "left_snapshot, right_snapshot, expected_change_pct",
        [
            (
                {"nics": {"state": True, "status": "SUCCESS", "reason": "", "snapshot": {}}},
                {"nics": {"state": True, "status": "SUCCESS", "reason": "", "snapshot": {}}},
                0,
            ),
            (
                {"nics": {"state": True, "status": "SUCCESS", "reason": "", "snapshot": {}}},
                {
                    "nics": {
                        "state": True,
                        "status": "SUCCESS",
                        "reason": "",
                        "snapshot": {"ethernet1/2": "up", "ethernet1/3": "down", "tunnel": "up"},
                    }
                },
                100,
            ),
            (
                {
                    "nics": {
                        "state": True,
                        "status": "SUCCESS",
                        "reason": "",
                        "snapshot": {"ethernet1/2": "up", "ethernet1/3": "up", "tunnel": "up"},
                    }
                },
                {"nics": {"state": True, "status": "SUCCESS", "reason": "", "snapshot": {}}},
                100,
            ),
        ],
    )
    def test_compare_type_generic_empty_dicts_count_change(self, left_snapshot, right_snapshot, expected_change_pct):
        change_threshold = 40
        snapshot_compare = SnapshotCompare(left_snapshot, right_snapshot)
        result = snapshot_compare.compare_type_generic(report_type="nics", count_change_threshold=change_threshold)

        assert result["count_change_percentage"]["change_percentage"] == expected_change_pct

    def test_compare_type_generic_none_snapshot(self):
        """Test compare_type_generic when snapshot is None."""
        # Create test snapshots with None values
        left_snapshot = {"nics": {"state": True, "status": "SUCCESS", "reason": "", "snapshot": {"ethernet1/1": "up"}}}
        right_snapshot = {"nics": {"state": True, "status": "SUCCESS", "reason": "", "snapshot": None}}

        snapshot_compare = SnapshotCompare(left_snapshot, right_snapshot)

        with pytest.raises(SnapshotNoneComparisonException) as excinfo:
            snapshot_compare.compare_type_generic(report_type="nics")

        assert "Cannot compare snapshot when either side is None" in str(excinfo.value)

    def test_compare_type_generic_both_none_snapshot(self):
        """Test compare_type_generic when both snapshots are None."""
        # Create test snapshots with None values
        left_snapshot = {"nics": {"state": True, "status": "SUCCESS", "reason": "", "snapshot": None}}
        right_snapshot = {"nics": {"state": True, "status": "SUCCESS", "reason": "", "snapshot": None}}

        snapshot_compare = SnapshotCompare(left_snapshot, right_snapshot)

        with pytest.raises(SnapshotNoneComparisonException) as excinfo:
            snapshot_compare.compare_type_generic(report_type="nics")

        assert "Cannot compare snapshot when either side is None" in str(excinfo.value)

    def test_compare_type_metric_values_no_thresholds(self):
        snapshot_compare = SnapshotCompare(snap1, snap2)
        assert snapshot_compare.compare_type_metric_values(report_type="session_stats") is None

    def test_compare_type_metric_values_validate_keys_exist_called_with(self):
        """Test threshold elements are extracted properly and validate_keys_exist is called"""
        report_type = "session_stats"
        thresholds = [
            {"num-tcp": 1.5},
            {"num-udp": 15},
        ]

        threshold_elements = {"num-tcp", "num-udp"}

        snapshot_compare = SnapshotCompare(snap1, snap2)

        snapshot_compare.validate_keys_exist = MagicMock()
        snapshot_compare.compare_type_metric_values(report_type=report_type, thresholds=thresholds)

        snapshot_compare.validate_keys_exist.assert_called_with(
            snap1[report_type]["snapshot"], snap2[report_type]["snapshot"], threshold_elements
        )

    def test_compare_type_metric_values_scheme_mismatch_exception(self):
        report_type = "session_stats"
        thresholds = [
            {"num-tcp": 1.5},
            {"NON-EXISTING": 15},
        ]

        snapshot_compare = SnapshotCompare(snap1, snap2)
        with pytest.raises(SnapshotSchemeMismatchException, match="Snapshots have missing keys in .*."):
            snapshot_compare.compare_type_metric_values(report_type=report_type, thresholds=thresholds)

    @pytest.mark.parametrize(
        "thresholds, expected_result",
        [
            (
                [{"num-tcp": 30}, {"num-udp": 10}],
                {
                    "num-tcp": {"change_percentage": 28.57, "change_threshold": 30.0, "passed": True},
                    "num-udp": {"change_percentage": 0.0, "change_threshold": 10.0, "passed": True},
                    "passed": True,
                },
            ),
            (
                [{"num-tcp": 20}, {"num-udp": 10}],
                {
                    "num-tcp": {"change_percentage": 28.57, "change_threshold": 20.0, "passed": False},
                    "num-udp": {"change_percentage": 0.0, "change_threshold": 10.0, "passed": True},
                    "passed": False,
                },
            ),
        ],
    )
    def test_compare_type_metric_values(self, thresholds, expected_result):
        report_type = "session_stats"

        snapshot_compare = SnapshotCompare(snap1, snap2)
        result = snapshot_compare.compare_type_metric_values(report_type=report_type, thresholds=thresholds)

        assert result == expected_result

    def test_compare_type_metric_values_none_snapshot(self):
        """Test compare_type_metric_values when snapshot is None."""
        # Create test snapshots with None values
        left_snapshot = {"session_stats": {"state": True, "status": "SUCCESS", "reason": "", "snapshot": None}}
        right_snapshot = {"session_stats": {"state": True, "status": "SUCCESS", "reason": "", "snapshot": {"num-tcp": "50"}}}

        snapshot_compare = SnapshotCompare(left_snapshot, right_snapshot)

        thresholds = [{"num-tcp": 10}]

        with pytest.raises(SnapshotNoneComparisonException) as excinfo:
            snapshot_compare.compare_type_metric_values(report_type="session_stats", thresholds=thresholds)

        assert "Cannot compare snapshot when either side is None" in str(excinfo.value)

    def test_normalize_are_routes(self):
        """Test the _normalize_are_routes method for processing ARE routes."""
        snapshot_compare = SnapshotCompare(snap1, snap2)

        # Sample ARE routes data
        are_routes = {
            "public-lr": {
                "0.0.0.0/0": [
                    {
                        "prefix": "0.0.0.0/0",
                        "protocol": "static",
                        "installed": True,
                        "nexthops": [
                            {"interfaceName": "ethernet1/1", "ip": "10.0.0.1", "active": True},
                            {"interfaceName": "ethernet1/2", "ip": "10.0.0.2", "active": True},
                        ],
                    }
                ]
            }
        }

        normalized = snapshot_compare._normalize_are_routes(are_routes)

        # Verify the structure is properly normalized
        assert "public-lr" in normalized
        assert "0.0.0.0/0" in normalized["public-lr"]
        assert "nexthops" in normalized["public-lr"]["0.0.0.0/0"]
        assert "ethernet1/1_10.0.0.1" in normalized["public-lr"]["0.0.0.0/0"]["nexthops"]
        assert "ethernet1/2_10.0.0.2" in normalized["public-lr"]["0.0.0.0/0"]["nexthops"]

        # Verify the original data (except nexthops) is preserved
        assert normalized["public-lr"]["0.0.0.0/0"]["protocol"] == "static"
        assert normalized["public-lr"]["0.0.0.0/0"]["prefix"] == "0.0.0.0/0"

    def test_normalize_are_routes_with_uninstalled_routes(self):
        """Test the _normalize_are_routes method with routes that aren't installed."""
        snapshot_compare = SnapshotCompare(snap1, snap2)

        # Sample with mixed installed/uninstalled routes
        are_routes = {
            "public-lr": {
                "0.0.0.0/0": [
                    {"prefix": "0.0.0.0/0", "protocol": "static", "installed": False, "nexthops": []},  # Not installed
                    {
                        "prefix": "0.0.0.0/0",
                        "protocol": "bgp",
                        "installed": True,  # Installed
                        "nexthops": [{"interfaceName": "ethernet1/3", "ip": "10.0.0.3", "active": True}],
                    },
                ]
            }
        }

        normalized = snapshot_compare._normalize_are_routes(are_routes)

        # Verify only installed route is included
        assert normalized["public-lr"]["0.0.0.0/0"]["protocol"] == "bgp"
        assert "ethernet1/3_10.0.0.3" in normalized["public-lr"]["0.0.0.0/0"]["nexthops"]

    @pytest.mark.parametrize(
        "left_routes, right_routes, expected_diff",
        [
            # Test case 1: Identical routes
            (
                {
                    "public-lr": {
                        "0.0.0.0/0": [
                            {
                                "prefix": "0.0.0.0/0",
                                "protocol": "static",
                                "installed": True,
                                "nexthops": [{"interfaceName": "ethernet1/1", "ip": "10.0.0.1"}],
                            }
                        ]
                    }
                },
                {
                    "public-lr": {
                        "0.0.0.0/0": [
                            {
                                "prefix": "0.0.0.0/0",
                                "protocol": "static",
                                "installed": True,
                                "nexthops": [{"interfaceName": "ethernet1/1", "ip": "10.0.0.1"}],
                            }
                        ]
                    }
                },
                True,  # Expecting passed=True (no differences)
            ),
            # Test case 2: Different nexthops
            (
                {
                    "public-lr": {
                        "0.0.0.0/0": [
                            {
                                "prefix": "0.0.0.0/0",
                                "protocol": "static",
                                "installed": True,
                                "nexthops": [{"interfaceName": "ethernet1/1", "ip": "10.0.0.1"}],
                            }
                        ]
                    }
                },
                {
                    "public-lr": {
                        "0.0.0.0/0": [
                            {
                                "prefix": "0.0.0.0/0",
                                "protocol": "static",
                                "installed": True,
                                "nexthops": [{"interfaceName": "ethernet1/2", "ip": "10.0.0.2"}],
                            }
                        ]
                    }
                },
                False,  # Expecting passed=False (differences found)
            ),
            # Test case 3: Added route
            (
                {"public-lr": {}},
                {
                    "public-lr": {
                        "0.0.0.0/0": [
                            {
                                "prefix": "0.0.0.0/0",
                                "protocol": "static",
                                "installed": True,
                                "nexthops": [{"interfaceName": "ethernet1/1", "ip": "10.0.0.1"}],
                            }
                        ]
                    }
                },
                False,  # Expecting passed=False (differences found)
            ),
        ],
    )
    def test_compare_type_are_routes(self, left_routes, right_routes, expected_diff):
        """Test the compare_type_are_routes method."""
        # Create mock snapshots
        left_snapshot = {"are_routes": {"state": True, "status": "SUCCESS", "reason": "", "snapshot": left_routes}}
        right_snapshot = {"are_routes": {"state": True, "status": "SUCCESS", "reason": "", "snapshot": right_routes}}

        # Initialize SnapshotCompare
        snapshot_compare = SnapshotCompare(left_snapshot, right_snapshot)

        # Call the method
        result = snapshot_compare.compare_type_are_routes(report_type="are_routes")

        # Check the result
        assert result["passed"] == expected_diff

    def test_compare_type_are_routes_actual_snapshots(self):
        """Test compare_type_are_routes with the actual snapshots from the test data."""
        snapshot_compare = SnapshotCompare(snap1, snap2)
        result = snapshot_compare.compare_type_are_routes(report_type="are_routes")

        # The snapshots have differences in nexthops and uptime
        assert result["passed"] is False

        # Check if the differences are identified correctly
        assert "public-lr" in result["changed"]["changed_raw"]
        assert "0.0.0.0/0" in result["changed"]["changed_raw"]["public-lr"]["changed"]["changed_raw"]

        # Verify uptime is different
        nexthops_diff = result["changed"]["changed_raw"]["public-lr"]["changed"]["changed_raw"]["0.0.0.0/0"]["changed"][
            "changed_raw"
        ]
        assert "uptime" in nexthops_diff
        assert nexthops_diff["uptime"]["left_snap"] == "00:00:26"
        assert nexthops_diff["uptime"]["right_snap"] == "01:30:26"

    def test_compare_type_are_routes_calls_calculate_diff_on_dicts(self):
        """Test that compare_type_are_routes calls calculate_diff_on_dicts."""
        # Create test snapshots with ARE routes
        left_routes = {
            "public-lr": {
                "0.0.0.0/0": [
                    {
                        "prefix": "0.0.0.0/0",
                        "protocol": "static",
                        "installed": True,
                        "nexthops": [{"interfaceName": "ethernet1/1", "ip": "10.0.0.1"}],
                    }
                ]
            }
        }
        right_routes = {
            "public-lr": {
                "0.0.0.0/0": [
                    {
                        "prefix": "0.0.0.0/0",
                        "protocol": "static",
                        "installed": True,
                        "nexthops": [{"interfaceName": "ethernet1/2", "ip": "10.0.0.2"}],
                    }
                ]
            }
        }
        left_snapshot = {"are_routes": {"state": True, "status": "SUCCESS", "reason": "", "snapshot": left_routes}}
        right_snapshot = {"are_routes": {"state": True, "status": "SUCCESS", "reason": "", "snapshot": right_routes}}

        snapshot_compare = SnapshotCompare(left_snapshot, right_snapshot)

        # Mock calculate_diff_on_dicts
        snapshot_compare.calculate_diff_on_dicts = MagicMock(
            return_value={
                "missing": {"passed": True, "missing_keys": []},
                "added": {"passed": True, "added_keys": []},
                "changed": {"passed": True, "changed_raw": {}},
            }
        )

        # Call the method
        snapshot_compare.compare_type_are_routes(report_type="are_routes")

        # Verify calculate_diff_on_dicts was called
        snapshot_compare.calculate_diff_on_dicts.assert_called_once()

    def test_compare_type_are_routes_calls_calculate_count_change_percentage(self):
        """Test that compare_type_are_routes calls _calculate_count_change_percentage when threshold is provided."""
        # Create test snapshots with ARE routes
        left_routes = {
            "public-lr": {
                "0.0.0.0/0": [
                    {
                        "prefix": "0.0.0.0/0",
                        "protocol": "static",
                        "installed": True,
                        "nexthops": [{"interfaceName": "ethernet1/1", "ip": "10.0.0.1"}],
                    }
                ]
            }
        }
        right_routes = {
            "public-lr": {
                "0.0.0.0/0": [
                    {
                        "prefix": "0.0.0.0/0",
                        "protocol": "static",
                        "installed": True,
                        "nexthops": [{"interfaceName": "ethernet1/2", "ip": "10.0.0.2"}],
                    }
                ]
            }
        }
        left_snapshot = {"are_routes": {"state": True, "status": "SUCCESS", "reason": "", "snapshot": left_routes}}
        right_snapshot = {"are_routes": {"state": True, "status": "SUCCESS", "reason": "", "snapshot": right_routes}}

        snapshot_compare = SnapshotCompare(left_snapshot, right_snapshot)

        # Mock the helper method
        snapshot_compare._calculate_count_change_percentage = MagicMock(
            return_value={"passed": True, "change_percentage": 5.0, "change_threshold": 25.0}
        )

        # Call with count_change_threshold
        snapshot_compare.compare_type_are_routes(report_type="are_routes", count_change_threshold=25)

        # Verify _calculate_count_change_percentage was called
        snapshot_compare._calculate_count_change_percentage.assert_called_once()

        # Verify it was called with correct parameters
        call_args = snapshot_compare._calculate_count_change_percentage.call_args
        assert call_args.kwargs["count_change_threshold"] == 25

    def test_compare_type_are_routes_identical_snapshots_returns_result_not_none(self):
        """Test that compare_type_are_routes returns a result dict (not None) even when snapshots are identical.

        This test documents the actual behavior and will alert if the logic changes.
        """
        # Create identical ARE routes snapshots
        identical_routes = {
            "public-lr": {
                "0.0.0.0/0": [
                    {
                        "prefix": "0.0.0.0/0",
                        "protocol": "static",
                        "installed": True,
                        "nexthops": [{"interfaceName": "ethernet1/1", "ip": "10.0.0.1"}],
                    }
                ]
            }
        }
        left_snapshot = {"are_routes": {"state": True, "status": "SUCCESS", "reason": "", "snapshot": identical_routes}}
        right_snapshot = {"are_routes": {"state": True, "status": "SUCCESS", "reason": "", "snapshot": identical_routes}}

        snapshot_compare = SnapshotCompare(left_snapshot, right_snapshot)

        # Call the method
        result = snapshot_compare.compare_type_are_routes(report_type="are_routes")

        # Result should NOT be None - it should be a dict with the standard structure
        assert result is not None
        assert isinstance(result, dict)
        assert "missing" in result
        assert "added" in result
        assert "changed" in result
        assert "passed" in result
        # All should pass with no differences
        assert result["passed"] is True
        assert result["missing"]["passed"] is True
        assert result["added"]["passed"] is True
        assert result["changed"]["passed"] is True

    def test_compare_type_are_routes_none_snapshot(self):
        """Test compare_type_are_routes when snapshot is None."""
        # Create test snapshots with None values
        left_snapshot = {"are_routes": {"state": True, "status": "SUCCESS", "reason": "", "snapshot": {"public-lr": {}}}}
        right_snapshot = {"are_routes": {"state": True, "status": "SUCCESS", "reason": "", "snapshot": None}}

        snapshot_compare = SnapshotCompare(left_snapshot, right_snapshot)

        with pytest.raises(SnapshotNoneComparisonException) as excinfo:
            snapshot_compare.compare_type_are_routes(report_type="are_routes")

        assert "Cannot compare snapshot when either side is None" in str(excinfo.value)

    @pytest.mark.parametrize(
        "reports, expected_result",
        [
            (
                ["nics"],
                {
                    "nics": {
                        "added": {"added_keys": [], "passed": True},
                        "changed": {"changed_raw": {"ethernet1/1": {"left_snap": "up", "right_snap": "down"}}, "passed": False},
                        "missing": {"missing_keys": ["tunnel"], "passed": False},
                        "passed": False,
                    }
                },
            ),
            (
                ["nics", "ip_sec_tunnels"],
                {
                    "nics": {
                        "added": {"added_keys": [], "passed": True},
                        "changed": {"changed_raw": {"ethernet1/1": {"left_snap": "up", "right_snap": "down"}}, "passed": False},
                        "missing": {"missing_keys": ["tunnel"], "passed": False},
                        "passed": False,
                    },
                    "ip_sec_tunnels": {
                        "added": {"added_keys": [], "passed": True},
                        "changed": {
                            "changed_raw": {
                                "ipsec_tun": {
                                    "added": {"added_keys": [], "passed": True},
                                    "changed": {
                                        "changed_raw": {"mon": {"left_snap": "on", "right_snap": "off"}},
                                        "passed": False,
                                    },
                                    "missing": {"missing_keys": ["gwid"], "passed": False},
                                    "passed": False,
                                },
                                "priv_tun": {
                                    "added": {"added_keys": [], "passed": True},
                                    "changed": {
                                        "changed_raw": {"state": {"left_snap": "active", "right_snap": "init"}},
                                        "passed": False,
                                    },
                                    "missing": {"missing_keys": [], "passed": True},
                                    "passed": False,
                                },
                            },
                            "passed": False,
                        },
                        "missing": {"missing_keys": ["sres"], "passed": False},
                        "passed": False,
                    },
                },
            ),
            (
                [{"routes": None}],
                {
                    "routes": {
                        "added": {"added_keys": [], "passed": True},
                        "changed": {
                            "changed_raw": {
                                "default_10.26.130.0/25_ethernet1/2_10.26.129.1": {
                                    "added": {"added_keys": [], "passed": True},
                                    "changed": {
                                        "changed_raw": {"flags": {"left_snap": "A S", "right_snap": "A"}},
                                        "passed": False,
                                    },
                                    "missing": {"missing_keys": [], "passed": True},
                                    "passed": False,
                                }
                            },
                            "passed": False,
                        },
                        "missing": {"missing_keys": [], "passed": True},
                        "passed": False,
                    }
                },
            ),
            (
                [{"routes": {"properties": ["!flags"]}}],
                {
                    "routes": {
                        "added": {"added_keys": [], "passed": True},
                        "changed": {"changed_raw": {}, "passed": True},
                        "missing": {"missing_keys": [], "passed": True},
                        "passed": True,
                    }
                },
            ),
            (
                [{"bgp_peers": {"properties": ["status"]}}],
                {
                    "bgp_peers": {
                        "added": {"added_keys": [], "passed": True},
                        "changed": {
                            "changed_raw": {
                                "default_Peer-Group1_Peer1": {
                                    "added": {"added_keys": [], "passed": True},
                                    "changed": {
                                        "changed_raw": {"status": {"left_snap": "Established", "right_snap": "Idle"}},
                                        "passed": False,
                                    },
                                    "missing": {"missing_keys": [], "passed": True},
                                    "passed": False,
                                }
                            },
                            "passed": False,
                        },
                        "missing": {"missing_keys": [], "passed": True},
                        "passed": False,
                    }
                },
            ),
            (
                ["arp_table"],
                {
                    "arp_table": {
                        "added": {"added_keys": ["ethernet1/1_10.0.2.11"], "passed": False},
                        "changed": {"changed_raw": {}, "passed": True},
                        "missing": {"missing_keys": ["ethernet1/2_10.0.1.1", "ethernet1/1_10.0.2.1"], "passed": False},
                        "passed": False,
                    }
                },
            ),
            (
                [
                    {
                        "session_stats": {
                            "thresholds": [
                                {"num-max": 10},
                                {"num-tcp": 10},
                            ]
                        }
                    }
                ],
                {
                    "session_stats": {
                        "num-max": {"change_percentage": 0.0, "change_threshold": 10.0, "passed": True},
                        "num-tcp": {"change_percentage": 28.57, "change_threshold": 10.0, "passed": False},
                        "passed": False,
                    }
                },
            ),
            (
                [{"are_routes": {"properties": ["!uptime", "!internalNextHopNum", "!internalNextHopActiveNum"]}}],
                {
                    "are_routes": {
                        "added": {"added_keys": [], "passed": True},
                        "changed": {
                            "changed_raw": {
                                "public-lr": {
                                    "added": {"added_keys": [], "passed": True},
                                    "changed": {
                                        "changed_raw": {
                                            "0.0.0.0/0": {
                                                "added": {"added_keys": [], "passed": True},
                                                "changed": {
                                                    "changed_raw": {
                                                        "nexthops": {
                                                            "added": {"added_keys": [], "passed": True},
                                                            "changed": {"changed_raw": {}, "passed": True},
                                                            "missing": {"missing_keys": ["ethernet1/1_direct"], "passed": False},
                                                            "passed": False,
                                                        }
                                                    },
                                                    "passed": False,
                                                },
                                                "missing": {"missing_keys": [], "passed": True},
                                                "passed": False,
                                            }
                                        },
                                        "passed": False,
                                    },
                                    "missing": {"missing_keys": [], "passed": True},
                                    "passed": False,
                                }
                            },
                            "passed": False,
                        },
                        "missing": {"missing_keys": [], "passed": True},
                        "passed": False,
                    }
                },
            ),
            (
                ["are_fib_routes"],
                {
                    "are_fib_routes": {
                        "added": {
                            "passed": False,
                            "added_keys": ["10.0.0.0/8_ethernet1/3_0.0.0.0", "0.0.0.0/0_ethernet1/2_10.10.11.1"],
                        },
                        "changed": {"passed": True, "changed_raw": {}},
                        "passed": False,
                        "missing": {
                            "passed": False,
                            "missing_keys": ["0.0.0.0/0_ethernet1/1_10.10.11.1", "1.1.1.1/32_loopback.10_0.0.0.0"],
                        },
                    }
                },
            ),
        ],
    )
    def test_compare_snapshots(self, reports, expected_result):
        snapshot_compare = SnapshotCompare(snap1, snap2)
        result = snapshot_compare.compare_snapshots(reports)

        assert not DeepDiff(
            result, expected_result, ignore_order=True
        )  # assert == doesnt work for nested objects and unordered lists

    # NOTE reports are already validated in ConfigParser called from the compare_snapshots method
    # so below check is never executed
    # @pytest.mark.parametrize(
    #     "reports", [ (-100), ({"a", "b"}), ([1, 2]) ]
    # )
    # def test_compare_snapshots_report_format_exception(self, reports):
    #     snapshot_compare = SnapshotCompare(snap1, snap2)
    #     with pytest.raises(WrongDataTypeException,
    #                        match="Wrong configuration format for report: .*"):
    #         snapshot_compare.compare_snapshots(reports)

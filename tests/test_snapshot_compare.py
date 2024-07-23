import pytest
from unittest.mock import MagicMock
from deepdiff import DeepDiff
from panos_upgrade_assurance.snapshot_compare import SnapshotCompare
from panos_upgrade_assurance.exceptions import WrongDataTypeException, MissingKeyException, SnapshotSchemeMismatchException
from snapshots import snap1, snap2


class TestSnapshotCompare:
    def test_key_checker_single_key_present(self):
        key = "nics"
        SnapshotCompare.key_checker(snap1, snap2, key)

    def test_key_checker_multiple_keys_present(self):
        key = ["nics", "arp_table"]
        SnapshotCompare.key_checker(snap1, snap2, key)

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
    def test_key_checker_keys_missing(self, left_snapshot, right_snapshot, key, missing):
        with pytest.raises(MissingKeyException) as exception_msg:
            SnapshotCompare.key_checker(left_snapshot, right_snapshot, key)

        assert str(exception_msg.value) == f"{key} (some elements if set/list) is missing in {missing}"

    @pytest.mark.parametrize("key", [123, 12.3, {"key": "value"}])
    def test_key_checker_wrong_data_type_exception(self, key):
        with pytest.raises(WrongDataTypeException) as exception_msg:
            SnapshotCompare.key_checker(snap1, snap2, key)

        assert str(exception_msg.value) == f"The key variable is a {type(key)} but should be either: str, set or list"

    def test_calculate_change_percentage_within_threshold(self):
        # first_value = 100       # NOTE: this results in 16.67 change instead of 20..
        # second_value = 120
        # threshold = 20
        first_value = 10
        second_value = 15
        threshold = 40

        result = SnapshotCompare.calculate_change_percentage(first_value, second_value, threshold)

        assert result["passed"] is True
        assert result["change_percentage"] == 33.33
        assert result["change_threshold"] == threshold

    def test_calculate_change_percentage_exceeds_threshold(self):
        first_value = 10
        second_value = 15
        threshold = 20

        result = SnapshotCompare.calculate_change_percentage(first_value, second_value, threshold)

        assert result["passed"] is False
        assert result["change_percentage"] == 33.33
        assert result["change_threshold"] == threshold

    def test_calculate_change_percentage_invalid_threshold(self):
        first_value = 100
        second_value = 110
        threshold = 110

        with pytest.raises(WrongDataTypeException) as exception_msg:
            SnapshotCompare.calculate_change_percentage(first_value, second_value, threshold)

        assert str(exception_msg.value) == "The threshold should be a percentage value between 0 and 100."

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

    # TODO test_calculate_diff_on_dicts properties flag

    # NOTE: Non-dictionary input is not handled in the code and not tested
    # if non supported input is passed it raises AttributeError since it doesnt have keys() method
    def test_calculate_diff_on_dicts_invalid_input(self):
        left_snapshot = {"key1": 1.23, "key2": "value2"}
        right_snapshot = {"key1": {"nested_key1": "value1"}, "key2": "value2"}

        with pytest.raises(WrongDataTypeException) as exception_msg:
            SnapshotCompare.calculate_diff_on_dicts(left_snapshot, right_snapshot)

        assert str(exception_msg.value) == "Unknown value format for key key1."

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

    def test_get_diff_and_threshold_call_calculate_passed(self):
        snapshot_compare = SnapshotCompare(snap1, snap2)
        # NOTE do NOT use MagicMock on Class.method directly, it messes up other tests, mock self method
        snapshot_compare.calculate_passed = MagicMock()
        snapshot_compare.get_diff_and_threshold(report_type="nics")

        snapshot_compare.calculate_passed.assert_called()

    def test_get_diff_and_threshold_call_calculate_diff(self):
        snapshot_compare = SnapshotCompare(snap1, snap2)
        snapshot_compare.calculate_diff_on_dicts = MagicMock()
        snapshot_compare.get_diff_and_threshold(report_type="nics")

        snapshot_compare.calculate_diff_on_dicts.assert_called()

    def test_get_diff_and_threshold_count_change_false(self):
        left_snapshot = {"nics": {"ethernet1/2": "up", "ethernet1/3": "up", "tunnel": "up"}}
        right_snapshot = {"nics": {"ethernet1/2": "up", "ethernet1/3": "down", "tunnel": "up"}}
        change_threshold = 10
        snapshot_compare = SnapshotCompare(left_snapshot, right_snapshot)
        result = snapshot_compare.get_diff_and_threshold(report_type="nics", count_change_threshold=change_threshold)

        assert result["count_change_percentage"] == {
            "passed": False,
            "change_percentage": 33.33,
            "change_threshold": float(change_threshold),
        }

    def test_get_diff_and_threshold_count_change_true(self):
        left_snapshot = {"nics": {"ethernet1/2": "up", "ethernet1/3": "up", "tunnel": "up"}}
        right_snapshot = {"nics": {"ethernet1/2": "up", "ethernet1/3": "down", "tunnel": "up"}}
        change_threshold = 40

        snapshot_compare = SnapshotCompare(left_snapshot, right_snapshot)
        result = snapshot_compare.get_diff_and_threshold(report_type="nics", count_change_threshold=change_threshold)

        assert result["count_change_percentage"] == {
            "passed": True,
            "change_percentage": 33.33,
            "change_threshold": float(change_threshold),
        }

    @pytest.mark.parametrize("count_change_threshold", [-10, 120])
    def test_get_diff_and_threshold_invalid_count_change_threshold(self, count_change_threshold):
        snapshot_compare = SnapshotCompare(snap1, snap2)
        snapshot_compare.calculate_diff_on_dicts.return_value = {
            "added": {"added_keys": [], "passed": True},
            "changed": {"changed_raw": {}, "passed": True},
            "missing": {"missing_keys": [], "passed": True},
        }

        with pytest.raises(WrongDataTypeException, match="The threshold should be a percentage value between 0 and 100."):
            snapshot_compare.get_diff_and_threshold(report_type="nics", count_change_threshold=count_change_threshold)

    @pytest.mark.parametrize(
        "left_snapshot, right_snapshot, expected_change_pct",
        [
            ({"nics": {}}, {"nics": {}}, 0),
            ({"nics": {}}, {"nics": {"ethernet1/2": "up", "ethernet1/3": "down", "tunnel": "up"}}, 100),
            ({"nics": {"ethernet1/2": "up", "ethernet1/3": "up", "tunnel": "up"}}, {"nics": {}}, 100),
        ],
    )
    def test_get_diff_and_threshold_empty_dicts_count_change(self, left_snapshot, right_snapshot, expected_change_pct):
        change_threshold = 40
        snapshot_compare = SnapshotCompare(left_snapshot, right_snapshot)
        result = snapshot_compare.get_diff_and_threshold(report_type="nics", count_change_threshold=change_threshold)

        assert result["count_change_percentage"]["change_percentage"] == expected_change_pct

    def test_get_count_change_percentage_no_thresholds(self):
        snapshot_compare = SnapshotCompare(snap1, snap2)
        assert snapshot_compare.get_count_change_percentage(report_type="session_stats") is None

    def test_get_count_change_percentage_key_checker_called_with(self):
        """Test threshold elements are extracted properly and key_checker is called"""
        report_type = "session_stats"
        thresholds = [
            {"num-tcp": 1.5},
            {"num-udp": 15},
        ]

        threshold_elements = {"num-tcp", "num-udp"}

        snapshot_compare = SnapshotCompare(snap1, snap2)

        snapshot_compare.key_checker = MagicMock()
        snapshot_compare.get_count_change_percentage(report_type=report_type, thresholds=thresholds)

        snapshot_compare.key_checker.assert_called_with(snap1[report_type], snap2[report_type], threshold_elements)

    def test_get_count_change_percentage_scheme_mismatch_exception(self):
        report_type = "session_stats"
        thresholds = [
            {"num-tcp": 1.5},
            {"NON-EXISTING": 15},
        ]

        snapshot_compare = SnapshotCompare(snap1, snap2)
        with pytest.raises(SnapshotSchemeMismatchException, match="Snapshots have missing keys in .*."):
            snapshot_compare.get_count_change_percentage(report_type=report_type, thresholds=thresholds)

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
    def test_get_count_change_percentage(self, thresholds, expected_result):
        report_type = "session_stats"

        snapshot_compare = SnapshotCompare(snap1, snap2)
        result = snapshot_compare.get_count_change_percentage(report_type=report_type, thresholds=thresholds)

        assert result == expected_result

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
                                    "changed": {"changed_raw": {}, "passed": True},
                                    "missing": {"missing_keys": ["gwid"], "passed": False},
                                    "passed": False,
                                }
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

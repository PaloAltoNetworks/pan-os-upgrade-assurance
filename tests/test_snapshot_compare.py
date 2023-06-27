import pytest
from panos_upgrade_assurance.snapshot_compare import SnapshotCompare, MissingKeyException, WrongDataTypeException

class TestSnapshotCompare:
    def setup_method(self):
        # Set up the snapshots for testing
        self.left_snap = {
            'root_key': {
                'key': 'value'
            }
        }
        self.right_snap = {
            'root_key': {
                'key': 'other_value'
            }
        }

    def test_key_checker(self):
        snapshot_compare = SnapshotCompare(self.left_snap, self.right_snap)

        assert snapshot_compare.key_checker(self.left_snap, self.right_snap, 'root_key') is None

        assert snapshot_compare.key_checker(self.left_snap, self.right_snap, {'root_key'}) is None

        assert snapshot_compare.key_checker(self.left_snap, self.right_snap, ['root_key']) is None

        with pytest.raises(MissingKeyException):
            snapshot_compare.key_checker(self.left_snap, self.right_snap, 'missing_key')

    def test_calculate_change_percentage(self):
        assert (
            SnapshotCompare.calculate_change_percentage(10, 15, 20)
            == {'passed': False, 'change_percentage': 33.33, 'change_threshold': 20.0}
        )

        assert (
            SnapshotCompare.calculate_change_percentage(10, 15, '20')
            == {'passed': False, 'change_percentage': 33.33, 'change_threshold': 20.0}
        )

        with pytest.raises(WrongDataTypeException):
            SnapshotCompare.calculate_change_percentage(10, 15, 120)

    def test_calculate_diff_on_dicts(self):
        snapshot_compare = SnapshotCompare(self.left_snap, self.right_snap)

        assert (
            snapshot_compare.calculate_diff_on_dicts(self.left_snap, self.right_snap)
            == {
                    "added": {"added_keys": [], "passed": True},
                    "changed": {
                        "changed_raw": {
                            "root_key": {
                                "added": {"added_keys": [], "passed": True},
                                "changed": {
                                    "changed_raw": {
                                        "key": {"left_snap": "value", "right_snap": "other_value"}
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
        )

    # def test_compare_snapshots(self):
    #     # Test the compare_snapshots method
    #     snapshot_compare = SnapshotCompare(self.left_snap, self.right_snap)

    #     # Test with a single report
    #     result = snapshot_compare.compare_snapshots(['nics'])
    #     assert 'nics' in result

    #     # Test with multiple reports
    #     result = snapshot_compare.compare_snapshots(['nics', 'routes'])
    #     assert 'nics' in result
    #     assert 'routes' in result

    #     # Test with an invalid report
    #     with pytest.raises(WrongDataTypeException):
    #         snapshot_compare.compare_snapshots(['invalid_report'])

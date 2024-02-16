from dataclasses import dataclass
from copy import deepcopy
from typing import Optional, Union, List, Iterable
from enum import Enum
from panos_upgrade_assurance import exceptions


class CheckType:
    """Class mapping check configuration strings for commonly used variables.

    Readiness checks configuration passed to the
    [`CheckFirewall`](/panos/docs/panos-upgrade-assurance/api/check_firewall#class-checkfirewall) class is in a form of a list of
    strings. These strings are compared in several places to parse the configuration and set the proper checks. This class is
    used to avoid hardcoding these strings. It maps the actual configuration string to a variable that can be referenced in the
    code.
    """

    PANORAMA = "panorama"
    HA = "ha"
    NTP_SYNC = "ntp_sync"
    CANDIDATE_CONFIG = "candidate_config"
    EXPIRED_LICENSES = "expired_licenses"
    ACTIVE_SUPPORT = "active_support"
    CONTENT_VERSION = "content_version"
    SESSION_EXIST = "session_exist"
    ARP_ENTRY_EXIST = "arp_entry_exist"
    IPSEC_TUNNEL_STATUS = "ip_sec_tunnel_status"
    FREE_DISK_SPACE = "free_disk_space"
    MP_DP_CLOCK_SYNC = "planes_clock_sync"
    CERTS = "certificates_requirements"
    UPDATES = "dynamic_updates"
    JOBS = "jobs"


class SnapType:
    """Class mapping the snapshot configuration strings to the commonly used variables.

    Snapshot configuration passed to the
    [`CheckFirewall`](/panos/docs/panos-upgrade-assurance/api/check_firewall#class-checkfirewall) class is in a form of a list of
    strings. These strings are compared in several places to parse the configuration and set proper snapshots.
    This class is used to avoid hardcoding these strings. It maps the actual configuration string to a variable that can be
    referenced in the code.
    """

    NICS = "nics"
    ROUTES = "routes"
    LICENSE = "license"
    ARP_TABLE = "arp_table"
    CONTENT_VERSION = "content_version"
    SESSION_STATS = "session_stats"
    IPSEC_TUNNELS = "ip_sec_tunnels"
    FIB_ROUTES = "fib_routes"


class HealthType:
    """Class mapping the health check configuration strings to commonly used variables.

    [`CheckFirewall`](/panos/docs/panos-upgrade-assurance/api/check_firewall#class-checkfirewall) class is in a form of a list of
    strings. These strings are compared in several places to parse the configuration.

    This class is used to avoid hardcoding these strings. It maps the actual configuration string to a variable that can be
    referenced in the code.
    """

    DEVICE_ROOT_CERTIFICATE_ISSUE = "device_root_certificate_issue"
    DEVICE_CDSS_AND_PANORAMA_CERTIFICATE_ISSUE = "cdss_and_panorama_certificate_issue"


class CheckStatus(Enum):
    """Class containing possible statuses for the check results.

    Its main purpose is to extend the simple `True`/`False` logic in a way that would provide more details/explanation in case a
    check fails. It provides the following statuses:

    * `SUCCESS`
    * `FAIL`
    * `ERROR`
    * `SKIPPED`

    """

    SUCCESS = 0
    FAIL = 1
    ERROR = 2
    SKIPPED = 3


class SupportedHashes(Enum):
    """Class listing supported hashing methods.

    Algorithms listed here are order from less to most secure (this order follows many criteria, some of them are mentioned
    [here](https://en.wikipedia.org/wiki/Hash_function_security_summary)).

    By extending the `Enum` class we can easily use this class to compare two hashing methods in terms of their security,
    for example:

    ```python showLineNumbers title="Example"
    bool(SupportedHashes.MD5.value < SupportedHashes.SHA256.value)
    ```

    would produce `True`.
    """

    MD5 = 1
    SHA1 = 2
    SHA256 = 3
    SHA384 = 4
    SHA512 = 5


@dataclass
class CheckResult:
    """Class representing the readiness check results.

    It provides two types of information:

    * `status` which represents information about the check outcome,
    * `reason` a reason behind the particular outcome, this comes in handy when a check fails.

    Most of the [`CheckFirewall`](/panos/docs/panos-upgrade-assurance/api/check_firewall#class-checkfirewall) methods use this
    class to store the return values, but mostly internally. The
    [`CheckFirewall.run_readiness_checks()`](/panos/docs/panos-upgrade-assurance/api/check_firewall#checkfirewallrun_readiness_checks)
    method translates this class into the python primitives: `str` and `bool`.

    # Attributes

    status (CheckStatus): Holds the status of a check. See [`CheckStatus`](#class-checkstatus) class for details.
    reason (str): Holds a reason explaining why a check fails. Provides no value if the check is successful.

    """

    status: CheckStatus = CheckStatus.FAIL
    reason: str = ""

    def __str__(self):
        """This class' string representation.

        # Returns

        str: a string combined from the `self.status` and `self.reason` variables. Provides a human readable representation of
        the class. Perfect to provide a reason for a particular check outcome.

        """
        return f"[{self.status.name}] {self.reason}"

    def __bool__(self):
        """Class' boolean representation.

        # Returns

        bool: a boolean value interpreting the value of the current `state`:

        * `True` when `status` [`CheckStatus.SUCCESS`](#class-checkstatus)
        * `False` otherwise.

        """
        return True if self.status == CheckStatus.SUCCESS else False


class ConfigParser:
    """Class responsible for parsing the provided configuration.

    This class is universal, meaning it parses configuration provided as the list of strings or dictionaries and verifies it
    against the list of valid configuration items.
    There are no hardcoded items against which the configuration is checked. This class is used in many places in this package
    and it uses a specific [`dialect`](/panos/docs/panos-upgrade-assurance/dialect).

    # Attributes

    _requested_config_names (set): Contains only element names of the requested configuration. When no requested configuration is
        passed (implicit `'all'`), this is equal to `self.valid_elements`.

    """

    def __init__(
        self,
        valid_elements: Iterable,
        requested_config: Optional[List[Union[str, dict]]] = None,
    ):
        """ConfigParser constructor.

        Introduces some initial verification logic:

        * `valid_elements` is converted to `set` - this way we get rid of all duplicates,
        * if `requested_config` is `None` we immediately treat it as if `all`  was passed implicitly
            (see [`dialect`](/panos/docs/panos-upgrade-assurance/dialect)) - it's expanded to `valid_elements`
        * `_requested_config_names` is introduced as `requested_config` stripped of any element configurations. Additionally, we
            do verification if elements of this variable match `valid_elements`. An exception is thrown if not.

        # Parameters

        valid_elements (iterable): Valid elements against which we check the requested config.
        requested_config (list, optional): (defaults to `None`) A list of requested configuration items with an optional
            configuration.

        # Raises

        UnknownParameterException: An exception is raised when a requested configuration element is not one of the valid elements.

        """
        self.valid_elements = set(valid_elements)

        if requested_config:  # if not None or not empty list
            self.requested_config = deepcopy(requested_config)
            self._requested_config_names = set(
                [ConfigParser._extract_element_name(config_keyword) for config_keyword in self.requested_config]
            )
            for config_name in self._requested_config_names:
                if not self._is_element_included(element=config_name):
                    raise exceptions.UnknownParameterException(f"Unknown configuration parameter passed: {config_name}.")
        else:
            self._requested_config_names = set(valid_elements)
            self.requested_config = list(valid_elements)  # Meaning 'all' valid tests

    def _is_element_included(self, element: str) -> bool:
        """Method verifying if a config element is a correct (supported) value.

        This method can also handle `not-elements` (see [`dialect`](/panos/docs/panos-upgrade-assurance/dialect)).

        # Parameters

        element (str): The config element to verify. This can be a `not-element`. This parameter is verified against
            `self.valid_elements` `set`. Key word `'all'` is also accepted.

        # Returns
        bool: `True` if the value is correct, `False` otherwise.

        """
        if element in self.valid_elements or (element.startswith("!") and element[1:] in self.valid_elements):
            return True
        elif element == "all" and "all" in self.requested_config:
            return True
        else:
            return False

    @staticmethod
    def _extract_element_name(config: Union[str, dict]) -> str:
        """Method that extracts the name from a config element.

        If a config element is a string, the actual config element is returned. For elements of a dictionary type, the
        1<sup>st</sup> key is returned.

        # Parameters

        config (str, dict): A config element to provide a name for.

        # Raises

        WrongDataTypeException: Thrown when config does not meet requirements.

        # Returns

        str: The config element name.

        """
        if isinstance(config, str):
            return config
        elif isinstance(config, dict):
            if len(config) == 1:
                return list(config.keys())[0]
            else:
                raise exceptions.WrongDataTypeException(
                    "Dict provided as config definition has incorrect format, it is supposed to have only one key {key:[]}"
                )
        else:
            raise exceptions.WrongDataTypeException("Config definition is neither string or dict")

    def _expand_all(self) -> None:
        """Expand key word `'all'` to  `self.valid_elements`.

        During expansion, elements from `self.valid_elements` which are already available in `self.requested_config` are skipped.
        This way we do not introduce duplicates for elements that were provided explicitly.

        This method directly operates on `self.requested_config`.
        """
        pure_names = set([(name[1:] if name.startswith("!") else name) for name in self._requested_config_names if name != "all"])
        self.requested_config.extend(list(self.valid_elements - pure_names))
        self.requested_config.remove("all")

    def prepare_config(self) -> List[Union[str, dict]]:
        """Parse the input config and return a machine-usable configuration.

        The parsed configuration retains element types. This means that an element of a dictionary type will remain a dictionary
        in the parsed config.

        This method handles most of the [`dialect`](/panos/docs/panos-upgrade-assurance/dialect)'s logic.

        # Returns
        list: The parsed configuration.

        """
        if all((config_name.startswith("!") for config_name in self._requested_config_names)):
            self.requested_config.insert(0, "all")

        if "all" in self.requested_config:
            self._expand_all()

        final_configs = []

        for config_element in self.requested_config:
            if not ConfigParser._extract_element_name(config_element).startswith("!"):
                final_configs.append(config_element)

        return final_configs


def interpret_yes_no(boolstr: str) -> bool:
    """Interpret `yes`/`no` as booleans.

    # Parameters

    boolstr (str): `yes` or `no`, a typical device response for simple boolean-like queries.

    # Raises

    WrongDataTypeException: An exception is raised when `boolstr` is neither `yes` or `no`.

    # Returns

    bool: `True` for *yes*, `False` for *no*.

    """
    if boolstr not in ["yes", "no"]:
        raise exceptions.WrongDataTypeException(f"Cannot interpret following string as boolean: {boolstr}.")

    return True if boolstr == "yes" else False


def printer(report: dict, indent_level: int = 0) -> None:  # pragma: no cover - exclude from pytest coverage
    """Print reports in human friendly format.

    # Parameters

    report (dict): Dict with reports from tests.
    indent_level (int): Indentation level.

    """
    delim = "   |"
    if "passed" in report:
        print(f'{delim*indent_level} passed: {report["passed"]}')
        if report["passed"]:
            return
    for k, v in report.items():
        if k != "passed":
            if isinstance(v, list):
                print(f"{delim*indent_level} {k}:")
                for element in v:
                    print(f"{delim*(indent_level +1)}- {element}")
            elif isinstance(v, dict):
                print(f"{delim * indent_level} {k}:")
                printer(v, indent_level + 1)
            else:
                print(f"{delim * indent_level} {k}: {v}")

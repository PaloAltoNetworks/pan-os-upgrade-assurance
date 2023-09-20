class WrongDataTypeException(Exception):
    """Used when passed configuration does not meet the data type requirements. Used in all modules."""

    pass


class FirewallProxyException(Exception):
    """Parent class for all exceptions coming from [FirewallProxy](/panos/docs/panos-upgrade-assurance/api/firewall_proxy)
    module."""

    pass


class CheckFirewallException(Exception):
    """Parent class for all exceptions coming from [CheckFirewall](/panos/docs/panos-upgrade-assurance/api/check_firewall)
    module."""

    pass


class SnapshotCompareException(Exception):
    """Parent class for all exceptions coming from [SnapshotCompare](/panos/docs/panos-upgrade-assurance/api/snapshot_compare)
    module."""

    pass


class UtilsException(Exception):
    """Parent class for all exceptions coming from [Utils](/panos/docs/panos-upgrade-assurance/api/utils) module."""

    pass


class WrongNumberOfArgumentsException(FirewallProxyException):
    """Thrown when [FirewallProxy](/panos/docs/panos-upgrade-assurance/api/firewall_proxy) constructor is given wrong number or
    set of arguments.
    """

    pass


class CommandRunFailedException(FirewallProxyException):
    """Used when a command run on a device does not return the `success` status."""

    pass


class GetXpathConfigFailedException(FirewallProxyException):
    """Used when XAPI does not return a `success` state when running a `get` operation."""

    pass


class MalformedResponseException(FirewallProxyException):
    """A generic exception class used when a response does not meet the expected standards."""

    pass


class DeviceNotLicensedException(FirewallProxyException):
    """Used when no license is retrieved from a device."""

    pass


class ContentDBVersionsFormatException(FirewallProxyException):
    """Used when parsing Content DB versions fail due to an unknown version format (assuming `XXXX-YYYY`)."""

    pass


class PanoramaConfigurationMissingException(FirewallProxyException):
    """Used when checking Panorama connectivity on a device that was not configured with Panorama."""

    pass


class WrongDiskSizeFormatException(FirewallProxyException):
    """Used when parsing free disk size information."""

    pass


class UpdateServerConnectivityException(FirewallProxyException):
    """Used when connection to the Update Server cannot be established."""

    pass


class MissingKeyException(SnapshotCompareException):
    """Used when an exception about the missing keys in a dictionary is thrown."""

    pass


class SnapshotSchemeMismatchException(SnapshotCompareException):
    """Used when a snapshot element contains different properties in both snapshots."""

    pass


class UnknownParameterException(CheckFirewallException, UtilsException):
    """Used when one of the requested configuration parameters is not a valid."""

    pass

class WrongDataTypeException(Exception):
    """Used when passed configuration does not meet the data type requirements. Used in all modules."""

    pass


class FirewallProxyExceptions(Exception):
    """Parent class for all exceptions comming from [FirewallProxy](/panos/docs/panos-upgrade-assurance/api/firewall_proxy) module."""

    pass


class SnapshotCompareExceptions(Exception):
    """Parent class for all exceptions comming from [SnapshotCompare](/panos/docs/panos-upgrade-assurance/api/snapshot_compare) module."""

    pass


class UtilsExceptions(Exception):
    """Parent class for all exceptions comming from [Utils](/panos/docs/panos-upgrade-assurance/api/utils) module."""

    pass


class CommandRunFailedException(FirewallProxyExceptions):
    """Used when a command run on a device does not return the `success` status."""

    pass


class MalformedResponseException(FirewallProxyExceptions):
    """A generic exception class used when a response does not meet the expected standards."""

    pass


class DeviceNotLicensedException(FirewallProxyExceptions):
    """Used when no license is retrieved from a device."""

    pass


class ContentDBVersionsFormatException(FirewallProxyExceptions):
    """Used when parsing Content DB versions fail due to an unknown version format (assuming `XXXX-YYYY`)."""

    pass


class PanoramaConfigurationMissingException(FirewallProxyExceptions):
    """Used when checking Panorama connectivity on a device that was not configured with Panorama."""

    pass


class WrongDiskSizeFormatException(FirewallProxyExceptions):
    """Used when parsing free disk size information."""

    pass


class UpdateServerConnectivityException(FirewallProxyExceptions):
    """Used when connection to the Update Server cannot be established."""

    pass


class MissingKeyException(SnapshotCompareExceptions):
    """Used when an exception about the missing keys in a dictionary is thrown."""

    pass


class SnapshotSchemeMismatchException(SnapshotCompareExceptions):
    """Used when a snapshot element contains different properties in both snapshots."""

    pass


class UnknownParameterException(UtilsExceptions):
    """Used when one of the requested configuration parameters processed by [`ConfigParser`](#class-configparser) is not a valid parameter."""

    pass

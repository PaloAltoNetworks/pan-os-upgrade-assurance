---
id: errors
sidebar_label: errors module
title: errors
hide_title: true
custom_edit_url: null
---
## class `CommandRunFailedException`

Used when a command run on a device does not return the `success` status.

## class `MalformedResponseException`

A generic exception class used when a response does not meet the expected standards.

## class `DeviceNotLicensedException`

Used when no license is retrieved from a device.

## class `ContentDBVersionsFormatException`

Used when parsing Content DB versions fail due to an unknown version format (assuming `XXXX-YYYY`).

## class `PanoramaConfigurationMissingException`

Used when checking Panorama connectivity on a device that was not configured with Panorama.

## class `WrongDiskSizeFormatException`

Used when parsing free disk size information.

## class `UpdateServerConnectivityException`

Used when connection to the Update Server cannot be established.

## class `ContentDBVersionInFutureException`

Used when the installed Content DB version is newer than the latest available version.

## class `WrongDataTypeException`

Used when passed configuration does not meet the data type requirements.

## class `MissingKeyException`

Used when an exception about the missing keys in a dictionary is thrown.

## class `SnapshotSchemeMismatchException`

Used when a snapshot element contains different properties in both snapshots.

## class `UnknownParameterException`

Used when one of the requested configuration parameters processed by [`ConfigParser`](#class-configparser) is not a valid parameter.


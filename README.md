# PAN-OS Upgrade Assurance

## Overview

The `panos-upgrade-assurance` package includes the set of classes written in `Python` to ease the process of writing checks and state snapshots during PanOS upgrade on the Next Generation Firewall.

Both checks and snapshots can be used to verify the state of a device during an upgrade process. What more, it is possible to generate a report for these checks.

The libraries were written to support Ansible and XSOAR integrations. They depend on [pan-os-python](https://pan.dev/panos/docs/panospython/) libraries and therefore are quite easy to fit into the [PanOS Ansible modules collection](https://galaxy.ansible.com/paloaltonetworks/panos).

For more detailed documentation please refer to [PAN.DEV](https://pan.dev/panos/docs/panos-upgrade-assurance/) portal.

## Installation

To install the package you can use `pip`:

``` console
python -m pip install panos-upgrade-assurance
```

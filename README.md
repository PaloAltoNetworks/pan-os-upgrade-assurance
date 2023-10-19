![GitHub release (latest by date)](https://img.shields.io/github/v/release/PaloAltoNetworks/pan-os-upgrade-assurance?style=flat-square)
![GitHub](https://img.shields.io/github/license/PaloAltoNetworks/terraform-modules-vmseries-ci-workflows?style=flat-square)
![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/PaloAltoNetworks/pan-os-upgrade-assurance/release.yml?style=flat-square)
![GitHub issues](https://img.shields.io/github/issues/PaloAltoNetworks/pan-os-upgrade-assurance?style=flat-square)
![GitHub pull requests](https://img.shields.io/github/issues-pr/PaloAltoNetworks/pan-os-upgrade-assurance?style=flat-square)
![PyPI - Downloads](https://img.shields.io/pypi/dm/panos-upgrade-assurance?style=flat-square)


# PAN-OS Upgrade Assurance

The `panos-upgrade-assurance` package includes the set of classes written in `Python` to ease the process of writing checks and state snapshots during PanOS upgrade on the Next Generation Firewall.

Both checks and snapshots can be used to verify the state of a device during an upgrade process. What more, it is possible to generate a report for these checks.

The libraries were written to support Ansible and XSOAR integrations. They depend on [pan-os-python](https://pan.dev/panos/docs/panospython/) libraries and therefore are quite easy to fit into the [PanOS Ansible modules collection](https://galaxy.ansible.com/paloaltonetworks/panos).

For more detailed documentation please refer to [PAN.DEV](https://pan.dev/panos/docs/panos-upgrade-assurance/) portal.

The libraries are available in three form factors:

- a python package hosted on [PyPI](https://pypi.org/project/panos-upgrade-assurance/) repository
- a docker image hosted on [GHCR](https://github.com/PaloAltoNetworks/pan-os-upgrade-assurance/pkgs/container/panos_upgrade_assurance), with the main purpose of being used in XSOAR
- an Ansible Execution Environment image hosted on [GHCR](https://github.com/PaloAltoNetworks/pan-os-upgrade-assurance/pkgs/container/panos_upgrade_assurance_ee), ready to be used directly in any Ansible Tower/AWX instance.

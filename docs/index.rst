.. Upgrade Assurance documentation master file, created by
   sphinx-quickstart on Tue Jan 24 15:24:53 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

===========================================
Welcome to Upgrade Assurance documentation!
===========================================

Upgrade Assurance documentation includes the set of libraries written in ``Python`` to ease the process of writing checks and state snapshots during PanOS upgrade on the Next Generation Firewall.
Both checks and snapshots can be used to verify the state of a device during an upgrade process. What'more, it is possible to generate a report for these checks.

The libraries were written to support Ansible. They depend on `Pan-OS-Python`_ libraries and therefore, are quite easy to fit into the `PanOS Ansible modules collection`_.

.. _Pan-OS-Python: https://github.com/PaloAltoNetworks/pan-os-python
.. _PanOS Ansible modules collection: https://galaxy.ansible.com/paloaltonetworks/panos

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   overview
   installation
   usage
   configuration_details
   api
   building_docs

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

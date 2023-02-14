Building documentation
======================

To build documentation for the project, install Sphinx using the following command:

.. code-block:: console

   $ poetry install --only=dev

Once all dependencies are installed, you can build HTML documentation by calling the following commands:

.. code-block:: console

   $ cd <path-to-repository>/docs
   $ make html

If there are some major changes including TOC, you should initially run the **make clean** command:

.. code-block:: console

   $ make clean html
   $ make html


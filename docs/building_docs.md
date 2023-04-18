# Building documentation

To build documentation for the project, install Sphinx using the
following command:

``` console
$ poetry install --only=dev
```

Once all dependencies are installed, you can build HTML documentation
by:

-   entering the poetry virtual environment:

    > ``` console
    > $ poetry shell
    > ```

-   calling the following commands:

    > ``` console
    > $ cd <path-to-repository>/docs
    > $ make html
    > ```

If there are some major changes including TOC, you should initially run
the **make clean** command:

``` console
$ make clean html
$ make html
```

# README

## running examples

Install poetry if you don't have it:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Install dependencies:

```bash
poetry install
```

This will create a virtualenv and install the dependencies. Afterwards you may active the virtualenv with:

```bash
poetry shell
```

Go into the examples directory to run them:

```bash
cd examples

./demo_upgrade.py
```

## Building

```bash
poetry build
```

This will create the wheel and tarball packages in the `dist` directory.

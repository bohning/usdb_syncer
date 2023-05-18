# USDB Syncer

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat)](https://pycqa.github.io/isort/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Release](https://github.com/bohning/usdb_syncer/actions/workflows/release.yaml/badge.svg)](https://github.com/bohning/usdb_syncer/actions/workflows/release.yaml)
[![tox](https://github.com/bohning/usdb_syncer/actions/workflows/tox.yaml/badge.svg)](https://github.com/bohning/usdb_syncer/actions/workflows/tox.yaml)

## Development

**USDB Syncer** is written in Python.
The following explains how to set up a development environment.
A Python 3.11 installation is assumed.

### Python Setup

[tox](https://github.com/tox-dev/tox) makes it easy to run the full CI pipeline on your local machine, i.e., if the pipeline passes on your machine there is a good chance it will also pass on the build server.
The minimal setup to develop your package is to create a virtual environment and install the package and its runtime requirements:

```bash
# Your Python installation may instead be available under `py` or `python`.
python3 -m venv venv
# In Windows PowerShell run this instead: `.\venv\Scripts\Activate.ps1`
# In Windows CMD run this instead: `.\venv\scripts\activate.bat`
source venv/bin/activate
pip install --upgrade pip tox setuptools
pip install -e '.[dev]'
```

### Run usdb_syncer

The package has a defined entry point for the GUI. Simply type in `usdb_syncer` in your terminal. Make sure that your venv is activated.

### Run tests

Run `tox` to execute the test pipeline. The tox pipelines are configured in the tox.ini file. Configurations for specific tools in the pipeline are maintained in the `pyproject.toml` file. Tox is configured to create its own virtual environments, install test dependencies and the package you are developing, and run all tests. If you changed the test requirements or want to perform a clean run for some reason, you can run `tox -r` to recreate tox's virtual environment.

The following tools are part of the test pipeline:

- [isort](https://github.com/PyCQA/isort): Automatically sorts your imports.

- [black](https://github.com/psf/black): Automatically and deterministically formats your code.

- [mypy](https://github.com/python/mypy): Statically checks your type hints.

- [pylint](https://github.com/PyCQA/pylint): Statically checks your code for errors and code smells.

- [pytest](https://github.com/pytest-dev/pytest): Provides a framework for unit tests.

If you don’t want to run the whole test pipeline, you can also use single commands from the pipeline, e.g., `pytest`. The tools will automatically pick up the correct configuration from the `pyproject.toml` file.

### Building

**USDB Syncer** uses [pyinstaller](https://github.com/pyinstaller/pyinstaller) for creating
executables. In order to build **USDB Syncer**, run the following command

```bash
# On Linux
pyinstaller --name "USDBSyncer" --onefile src/usdb_syncer/main.py

# On macOS
pyinstaller --name "USDBSyncer" --windowed src/usdb_syncer/main.py

# On Windows
pyinstaller --name "USDBSyncer" --onefile src/usdb_syncer/main.py
```

## Versioning

**USDB Syncer** uses [semantic versioning (semver)](https://semver.org/) as versioning scheme.
However, since **USDB Syncer** is not a library/API but a user-facing application, we use `MAJOR`, `MINOR` and `PATCH`
versions according to the following scheme:

- `MAJOR` version increments mean a breaking change for the end user, be it the need to install additional
  (3rd party) tools or changes that make it necessary to make changes to the already downloaded songs.
- `MINOR` version increments only involve adding backward compatible features.
- `PATCH` version increments bring bugfixes.

We will try to avoid `MAJOR` version increments whenever possible, but since the project is still in the
startup phase, they cannot be completely ruled out.

## Support

<a href="https://www.buymeacoffee.com/usdbsyncer"><img src="https://img.buymeacoffee.com/button-api/?text=Buy us some vegan pizza!&emoji=🍕&slug=usdbsyncer&button_colour=40DCA5&font_colour=ffffff&font_family=Cookie&outline_colour=000000&coffee_colour=FFDD00" /></a>

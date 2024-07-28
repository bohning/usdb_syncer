# USDB Syncer

[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat)](https://pycqa.github.io/isort/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Release](https://github.com/bohning/usdb_syncer/actions/workflows/release.yaml/badge.svg)](https://github.com/bohning/usdb_syncer/actions/workflows/release.yaml)
[![tox](https://github.com/bohning/usdb_syncer/actions/workflows/tox.yaml/badge.svg)](https://github.com/bohning/usdb_syncer/actions/workflows/tox.yaml)

**USDB Syncer** is an app to download and synchronize UltraStar songs hosted on [USDB](https://usdb.animux.de).
The project [extensively uses the `#VIDEO` tag](https://github.com/bohning/usdb_syncer/wiki/Meta-Tags#format) to automaticly retrieve the resources (audio, video, images, etc...) to make the UltraStar song complete.
Once a song is downloaded it can be synchronized (new notes, audio, video, images...) by redownloading the song. If a resource didn't change it's skipped.

````

## Development

**USDB Syncer** is written in Python, and uses Poetry to manage its dependencies.
The following explains how to set up a development environment.

### Prerequisites

- [git](https://www.git-scm.com/downloads)
- [Python 3.12](https://www.python.org/downloads/)
- [Poetry](https://python-poetry.org/docs/#installation)

### Project Setup

Clone the project:

```bash
git clone https://github.com/bohning/usdb_syncer.git
cd usdb_syncer
````

Additionally requires extra packages when developing **on Linux**:

```bash
apt install -y gcc python3-dev libdbus-1-dev
pkg-config --cflags --libs dbus-1
```

Now make sure the Python 3.12 environment you installed Poetry to is activated and run:

```bash
poetry install
# optionally activate the venv
poetry shell
```

### Run usdb_syncer

The package has a defined entry point for the GUI. Simply type in `usdb_syncer` in your
terminal (`poetry run usdb_syncer` if you did not activate the venv).

### Run tests

[tox](https://github.com/tox-dev/tox) makes it easy to run the full CI pipeline on your local machine, i.e., if the pipeline passes on your machine there is a good chance it will also pass on the build server.

Run `tox` (or `poetry run tox`) to execute the test pipeline. The tox pipelines are configured in the tox.ini file.
Configurations for specific tools in the pipeline are maintained in the `pyproject.toml` file.
Tox is configured to create its own virtual environments, install test dependencies and the package you are developing, and run all tests.
If you changed the test requirements or want to perform a clean run for some reason, you can run `tox -r` to recreate tox's virtual environment.

The following tools are part of the test pipeline:

- [isort](https://github.com/PyCQA/isort): Automatically sorts your imports.

- [black](https://github.com/psf/black): Automatically and deterministically formats your code.

- [mypy](https://github.com/python/mypy): Statically checks your type hints.

- [pylint](https://github.com/PyCQA/pylint): Statically checks your code for errors and code smells.

- [pytest](https://github.com/pytest-dev/pytest): Provides a framework for functional unit tests.

- [unittest](https://docs.python.org/3/library/unittest.html): A built-in objective unittest framework
  with extensive support for mocking.

If you don’t want to run the whole test pipeline, you can also use single commands from the pipeline, e.g., `pytest`. The tools will automatically pick up the correct configuration from the `pyproject.toml` file.

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

## Troubleshooting

- may require extra packages on Linux

  ```bash
  apt update
  apt install libdbus-1-3
  ```

- The `keyring` package auto-detects an appropriate installed keyring backend (see [PyPI - keyring](https://pypi.org/project/keyring/)). Thus may require following additional package if no backend can be detected, see #136

  ```bash
  apt install gnome-keyring
  ```

## Linux Distributions

Linux Build are generated on `Ubuntu:latest`, should run on `Ubuntu >=22.04`

known requirements:

- package `glibc >= 2.35`

  Therefore the following table (based on <https://pkgs.org/search/?q=glibc>, 8.7.2023) summarizes different Linux Distributions for having greater or equal version of `glibc`. For (likely) supported distributions the minimum OS Version is given that has a required glibc version. For (likely) unsupported distributions the recent highest Versions (if known) of Linux Distributions with its highest glibc version is given:

  |                    |         OS          |    OS Version    | glibc |
  | :----------------: | :-----------------: | :--------------: | :---: |
  |        :x:         |      AlmaLinux      |        9         | 2.34  |
  |        :x:         |      ALT Linux      |       P10        | 2.32  |
  |        :x:         |    Amazon Linux     |        2         | 2.26  |
  | :white_check_mark: |     Arch Linux      |                  | 2.37  |
  |        :x:         |       CentOS        |        9         | 2.34  |
  |        :x:         |  Enterprise Linux   |        7         | 2.24  |
  | :white_check_mark: |       Debian        |  12 "Bookworm"   | 2.36  |
  | :white_check_mark: |       Fedora        |        38        | 2.37  |
  | :white_check_mark: |        KaOS         |                  | 2.36  |
  | :white_check_mark: |       Mageia        |     Cauldron     | 2.36  |
  | :white_check_mark: |    OpenMandriva     | Rolling & Cooker | 2.37  |
  | :white_check_mark: | openSUSE Tumbleweed |                  | 2.37  |
  |        :x:         |    Oracle Linux     |        9         | 2.34  |
  | :white_check_mark: |      PCLinuxOS      |                  | 2.36  |
  |        :x:         |     Rocky Linux     |        9         | 2.34  |
  | :white_check_mark: |      Slackware      |                  | 2.37  |
  | :white_check_mark: |        Solus        |                  | 2.36  |
  | :white_check_mark: |       Ubuntu        |      23.04       | 2.35  |
  | :white_check_mark: |     Void Linux      |                  | 2.36  |

  :x: pretty sure not working

  :white_check_mark: should work

confirmed support:

- Ubuntu 23.04

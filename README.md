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

## Installation

There are three ways to run USDB Syncer:

1. To run from source, see [Development](#Development).
2. Use your favourite package manager to install the Python package, e.g. [pipx](https://pipx.pypa.io/stable/): `pipx install usdb_syncer`
3. We provide [ready-to-run executables](https://github.com/bohning/usdb_syncer/releases) for all major operating systems.

## Development

**USDB Syncer** is written in Python, and uses Poetry to manage its dependencies.
The following explains how to set up a development environment.

### Prerequisites

- [git](https://www.git-scm.com/downloads)
- [Python 3.12](https://www.python.org/downloads/) (3.11 should work as well)
- [Poetry](https://python-poetry.org/docs/#installation)

### Project Setup

Clone the project:

```bash
git clone https://github.com/bohning/usdb_syncer.git
cd usdb_syncer
```

<details>

<summary>If you're on <b>Linux</b>, make sure required packages for Qt are installed.</summary>

```bash
apt install -y libgstreamer-gl1.0-0 libxcb-glx0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-render0 libxcb-shape0 libxcb-shm0 libxcb-sync1 libxcb-util1 libxcb-xfixes0 libxcb1 libxkbcommon-dev libxkbcommon-x11-0 libxcb-cursor0 libva-dev libva-drm2 libva-x11-2
```

</details>

Now make sure the Python 3.12 environment you installed Poetry to is activated and run:

```bash
poetry install
```

### Run usdb_syncer

The package has a defined entry point for the GUI. Simply type in `poetry run usdb_syncer` in your terminal.

### Run tests

[tox](https://github.com/tox-dev/tox) makes it easy to run the full CI pipeline on your local machine, i.e., if the pipeline passes on your machine there is a good chance it will also pass on the build server.

Run `poetry run tox` to execute the test pipeline. The tox pipelines are configured in the tox.ini file.
Configurations for specific tools in the pipeline are maintained in the `pyproject.toml` file.
Tox is configured to create its own virtual environments, install test dependencies and the package you are developing, and run all tests.
If you changed the test requirements or want to perform a clean run for some reason, you can run `poetry run tox -r` to recreate tox's virtual environment.

The following tools are part of the test pipeline:

- [mypy](https://github.com/python/mypy): Statically checks your type hints.

- [ruff](https://docs.astral.sh/ruff/): A linter and code formatter.

- [pytest](https://github.com/pytest-dev/pytest): Provides a framework for functional unit tests.

- [unittest](https://docs.python.org/3/library/unittest.html): A built-in objective unittest framework
  with extensive support for mocking.

If you don’t want to run the whole test pipeline, you can also use single commands from the pipeline, e.g., `poetry run pytest`. The tools will automatically pick up the correct configuration from the `pyproject.toml` file.

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

- The `keyring` package auto-detects an appropriate installed keyring backend (see [PyPI - keyring](https://pypi.org/project/keyring/)). Thus may require following additional package if no backend can be detected, see #136

  ```bash
  apt install gnome-keyring
  ```

  If using KDE, a Wallet will have to be activated in the system settings.

- One user using KDE Plasma experiencing an [issue with the menu bar](https://github.com/bohning/usdb_syncer/issues/198)
  solved it by forcing XWayland instead of Wayland being used: `env WAYLAND_DISPLAY=`.

## Linux Distributions

Linux bundles are generated on AlmaLinux 9. They should be compatible with any modern distribution. If not, please open an issue.

The only known requirement for the binary is `glibc >= 2.34`. The current `glibc` version can be checked with:

```bash
ldd --version
```

Support for the following distributions has been manually confirmed as of March 2025:

- Ubuntu 22.04 and 24.04
- Debian 12
- Manjaro 24.2
- Fedora 41

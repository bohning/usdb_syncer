# USDB Syncer

[![PyPI](https://img.shields.io/pypi/v/usdb_syncer)](https://pypi.org/project/usdb-syncer/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: GPL](https://img.shields.io/badge/License-GPL-yellow.svg)](https://https://www.gnu.org/licenses/gpl-3.0.en.html)
[![Release](https://github.com/bohning/usdb_syncer/actions/workflows/release.yaml/badge.svg)](https://github.com/bohning/usdb_syncer/actions/workflows/release.yaml)
[![tox](https://github.com/bohning/usdb_syncer/actions/workflows/tox.yaml/badge.svg)](https://github.com/bohning/usdb_syncer/actions/workflows/tox.yaml)

**USDB Syncer** is an app to download and synchronize UltraStar songs hosted on [USDB](https://usdb.animux.de).
The project [extensively uses the `#VIDEO` tag](https://github.com/bohning/usdb_syncer/wiki/Meta-Tags#format) to automatically retrieve the resources (audio, video, images, etc...) to make the UltraStar song complete.
Once a song is downloaded it can be synchronized (new notes, audio, video, images...) by redownloading the song. If a resource didn't change it's skipped.

## Installation

There are three ways to run USDB Syncer:

1. To run from source, see [Development](#development).
2. Use your favourite package manager to install the Python package, e.g. [pipx](https://pipx.pypa.io/stable/): `pipx install usdb_syncer`
3. We provide [ready-to-run executables](https://github.com/bohning/usdb_syncer/releases) for all major operating systems.

> [!IMPORTANT]  
> Linux users should check [Linux Compatibility](#linux-compatibility) as additional configuration is usually required.

## Development

**USDB Syncer** is written in Python, and uses uv to manage its dependencies.
The following explains how to set up a development environment.

### Prerequisites

- [git](https://www.git-scm.com/downloads)
- [Python 3.12](https://www.python.org/downloads/) (3.11 should work as well)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

### Project Setup

Clone the project:
```bash
git clone https://github.com/bohning/usdb_syncer.git
cd usdb_syncer
```

Install dependencies:
```bash
uv sync
```

### Run usdb_syncer

The package has a defined entry point for the GUI. Simply run:
```bash
uv run usdb_syncer
```

### Run tests

[tox](https://github.com/tox-dev/tox) makes it easy to run the full CI pipeline on your local machine, i.e., if the pipeline passes on your machine there is a good chance it will also pass on the build server.

Run `uv run tox` to execute the test pipeline. The tox pipelines are configured in the tox.ini file.
Configurations for specific tools in the pipeline are maintained in the `pyproject.toml` file.
Tox is configured to create its own virtual environments, install test dependencies and the package you are developing, and run all tests.
If you changed the test requirements or want to perform a clean run for some reason, you can run `uv run tox -r` to recreate tox's virtual environment.

The following tools are part of the test pipeline:

- [mypy](https://github.com/python/mypy): Statically checks your type hints.

- [ruff](https://docs.astral.sh/ruff/): A linter and code formatter.

- [pytest](https://github.com/pytest-dev/pytest): Provides a framework for functional unit tests.

- [unittest](https://docs.python.org/3/library/unittest.html): A built-in objective unittest framework
  with extensive support for mocking.

If you don't want to run the whole test pipeline, you can also use single commands from the pipeline, e.g., `uv run pytest`. The tools will automatically pick up the correct configuration from the `pyproject.toml` file.

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

## Addons

**USDB Syncer** supports simple addons. Consult `addons/README.md` for detailed information.

## Support

<a href="https://www.buymeacoffee.com/usdbsyncer"><img src="https://img.buymeacoffee.com/button-api/?text=Buy us some vegan pizza!&emoji=🍕&slug=usdbsyncer&button_colour=40DCA5&font_colour=ffffff&font_family=Cookie&outline_colour=000000&coffee_colour=FFDD00" /></a>

## Troubleshooting

- With Qt issues, set the `QT_DEBUG_PLUGINS` environment variable to 1, then re-run. It will output diagnostics while running.

- The `keyring` package auto-detects an appropriate installed keyring backend (see [PyPI - keyring](https://pypi.org/project/keyring/)). This may require following additional package if no backend can be detected, see #136
  
  With KDE, a Wallet may have to be activated in the system settings.

  With gnome, install gnome-keyring

  ```bash
  apt install gnome-keyring
  ```

  You can also disable the keyring entirely by setting `PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring`. The Syncer will not be able to store your USDB password in that case.

- One user using KDE Plasma experiencing an [issue with the menu bar](https://github.com/bohning/usdb_syncer/issues/198)
  solved it by forcing XWayland instead of Wayland being used: `env WAYLAND_DISPLAY=`.

## Linux Compatibility

### Required packages

The bundle contains most of the required packages. You will need to supply video libraries (which should be included for your desktop already) as well as [pipewire](https://pkgs.org/search/?q=pipewire) and [portaudio](https://pkgs.org/search/?q=portaudio).

If you do encounter a warning or an error, set `export QT_DEBUG_PLUGINS=1` to see the exact library you are missing.

More packages are required when running from source or the official Python package:

<details>
<summary>Ubuntu/Debian</summary>

````bash
apt install libgssapi-krb5-2 libgl1 libegl1 libva2 libva-drm2 libva-x11-2 libpipewire-0.3-0 libportaudio2 libxkbcommon0 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxcb-shape0 libxrandr2 libfontconfig1
````

</details>
<details>
<summary>Fedora</summary>

````bash
dnf install libglvnd-glx libglvnd-egl fontconfig libxkbcommon libXrandr libxkbcommon-x11 xcb-util-cursor xcb-util-wm xcb-util-keysyms libva pipewire portaudio
````

</details>
<details>
<summary>Arch</summary>

````bash
pacman -Sy fontconfig libxkbcommon libxkbcommon-x11 xcb-util-cursor xcb-util-wm xcb-util-keysyms pipewire portaudio
````

</details>

You can also use the corresponding wayland libraries. We will fix issues related to wayland, but we don't test on wayland, which is why problems may be more frequent.

### Compatibility

The wheels are pure Python with no extension modules, and are thus only restricted by the Python version.

Linux bundles are generated on an AlmaLinux 9 host. They should be compatible with any modern distribution. If not, please open an issue.

They are linked against `glibc 2.34`. The current `glibc` version can be checked with:

```bash
ldd --version
```

We confirm support automatically for these distros:

- Ubuntu 22.04 (Deadsnakes PPA), 24.04, 25.10
- Debian 12, 13
- Fedora 42, 43
- Arch

The following distros are officially unsupported:

- Ubuntu 20.04
- Debian 11

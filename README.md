# USDB Syncer

## Development

usdb_syncer is written in Python.
The following explains how to set up a development environment.

### Python Setup

[tox](https://github.com/tox-dev/tox) makes it easy to run the full CI pipeline on your local machine, i.e., if the pipeline passes on your machine there is a good chance it will also pass on the build server.
The minimal setup to develop your package is to create a virtual environment and install the package and its runtime requirements:

```bash
# your Python installation may instead be available under `py` or `python`
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -e '.[dev]'
```

#### Run usdb_syncer

The package has a defined entry point for the GUI. Simply type in `usdb_syncer` in your terminal. Make sure that your venv is activated.

On Windows, this might not work out of the box, because symlinks are disabled by default.
Try following this answer on Stack Overflow: <https://stackoverflow.com/a/59761201/7542749>

#### Run tests

Run `tox` to execute the test pipeline. The tox pipelines are configured in the tox.ini file. Configurations for specific tools in the pipeline are maintained in the `pyproject.toml` file. Tox is configured to create its own virtual environments, install test dependencies and the package you are developing, and run all tests. If you changed the test requirements or want to perform a clean run for some reason, you can run `tox -r` to recreate tox's virtual environment.

The following tools are part of the test pipeline:

- [isort](https://github.com/PyCQA/isort): Automatically sorts your imports.

- [black](https://github.com/psf/black): Automatically and deterministically formats your code.

- [mypy](https://github.com/python/mypy): Statically checks your type hints.

- [pylint](https://github.com/PyCQA/pylint): Statically checks your code for errors and code smells.

- [pytest](https://github.com/pytest-dev/pytest): Provides a framework for unit tests. Also doc-tests your docstrings and collects coverage information via pytest-cov.

- [pydocstyle](https://github.com/PyCQA/pydocstyle): Checks your docstring style. Use Google style docstrings.

If you don’t want to run the whole test pipeline, you can also use single commands from the pipeline, e.g., pytest. The tools will automatically pick up the correct configuration from the `pyproject.toml` file. There is a nice explanatory video here that touches on some of these tools and the overall structure of a Python project.

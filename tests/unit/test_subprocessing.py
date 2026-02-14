import unittest.mock

from usdb_syncer import subprocessing

subprocessing.APPLY_CLEAN_ENV = True


def test_get_env_clean() -> None:
    test_env = {
        "TEST_ENV": "test_value",
        "LD_LIBRARY_PATH": "/some/path",
        "LD_LIBRARY_PATH_ORIG": "/some/original/path",
        "QT_PLUGIN_PATH": "/some/qt/plugins",
    }
    with unittest.mock.patch.dict(subprocessing.os.environ, test_env, clear=True):
        for key, value in test_env.items():
            subprocessing.os.environ[key] = value

        clean_env = subprocessing.get_env_clean()
    assert clean_env["TEST_ENV"] == "test_value"
    assert clean_env["LD_LIBRARY_PATH"] == "/some/original/path"
    assert "QT_PLUGIN_PATH" not in clean_env
    assert "QT_PLUGIN_PATH_ORIG" not in clean_env


def test_unsafe_clean() -> None:
    test_env = {
        "TEST_ENV": "test_value",
        "LD_LIBRARY_PATH": "/some/path",
        "LD_LIBRARY_PATH_ORIG": "/some/original/path",
        "QT_PLUGIN_PATH": "/some/qt/plugins",
    }
    with unittest.mock.patch.dict(subprocessing.os.environ, test_env, clear=True):
        with subprocessing.unsafe_clean():
            assert subprocessing.os.environ["TEST_ENV"] == "test_value"
            assert subprocessing.os.environ["LD_LIBRARY_PATH"] == "/some/original/path"
            assert "QT_PLUGIN_PATH" not in subprocessing.os.environ
            assert "QT_PLUGIN_PATH_ORIG" not in subprocessing.os.environ
        # After the context manager, the original environment should be restored
        assert subprocessing.os.environ["TEST_ENV"] == "test_value"
        assert subprocessing.os.environ["LD_LIBRARY_PATH"] == "/some/path"
        assert subprocessing.os.environ["QT_PLUGIN_PATH"] == "/some/qt/plugins"

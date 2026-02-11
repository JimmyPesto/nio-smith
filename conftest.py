# internal modules
import os
import logging
# external modules
import pytest
# own modules
from core.plugin import Plugin

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True, scope="function")
def mock_plugin_setup_of_static_vars(tmp_path):
    Plugin.state_dir = os.path.join(tmp_path, "state/")
    Plugin.config_dir = os.path.join(tmp_path, "config/")
    yield
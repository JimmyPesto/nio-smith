import logging
import re
import os
import yaml
import sys
from typing import List, Any, Optional
from core.errors import ConfigError

logger = logging.getLogger()


def check_file_exists(file_path: str, content_description: str):
    if not os.path.isfile(file_path):
        raise ConfigError(f"{content_description} file '{file_path}' does not exist")


def check_dir_exists(dir_path: str, content_description: str):
    if not os.path.isdir(dir_path):
        raise ConfigError(f"{content_description} directory '{dir_path}' does not exist")


def create_dir_if_not_exists(dir_path: str):
    # Create the store folder if it doesn't exist
    if not os.path.isdir(dir_path):
        if not os.path.exists(dir_path):
            os.mkdir(dir_path)
        else:
            var_name = [k for k, v in globals().items() if v == dir_path][0]
            raise ConfigError(f"{var_name} '{dir_path}' is not a directory")


class Config(object):
    def __init__(self, filepath):
        """
        Args:
            filepath (str): Path to config file
        """
        check_file_exists(filepath, "Config")

        # Load in the config file at the given filepath
        with open(filepath) as file_stream:
            self.config_dict = yaml.safe_load(file_stream.read())

        # Logging setup
        formatter = logging.Formatter("%(asctime)s | %(name)s [%(levelname)s] %(message)s")

        log_level = self._get_cfg(["logging", "level"], default="INFO")
        logger.setLevel(log_level)

        file_logging_enabled = self._get_cfg(["logging", "file_logging", "enabled"], default=False)
        file_logging_filepath = self._get_cfg(["logging", "file_logging", "filepath"], default="./data/logs/bot.log")
        if file_logging_enabled:
            handler = logging.FileHandler(file_logging_filepath)
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        console_logging_enabled = self._get_cfg(["logging", "console_logging", "enabled"], default=True)
        if console_logging_enabled:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        # directories setup
        self.state_dir: str = self._get_cfg(["storage", "state_dir"], required=True)
        self.plugins_src_dir: str = self._get_cfg(["storage", "plugins_src_dir"], required=True)
        self.plugins_config_dir: str = self._get_cfg(["storage", "plugins_config_dir"], required=True)

        check_dir_exists(self.plugins_src_dir, "Plugins")
        create_dir_if_not_exists(self.state_dir)
        create_dir_if_not_exists(self.plugins_config_dir)

        self.database_filepath = os.path.join(self.state_dir, "bot.db")
        self.store_filepath = os.path.join(self.state_dir, "store")
        create_dir_if_not_exists(self.store_filepath)

        # Matrix bot account setup
        self.user_id = self._get_cfg(["matrix", "user_id"], required=True)
        if not re.match("@.*:.*", self.user_id):
            raise ConfigError("matrix.user_id must be in the form @name:domain")

        self.user_password = self._get_cfg(["matrix", "user_password"], required=True)
        self.device_id = self._get_cfg(["matrix", "device_id"], required=True)
        self.device_name = self._get_cfg(["matrix", "device_name"], default="nio-template")
        self.homeserver_url = self._get_cfg(["matrix", "homeserver_url"], required=True)
        self.enable_encryption = self._get_cfg(["matrix", "enable_encryption"], default=False)
        self.botmasters = self._get_cfg(["matrix", "botmasters"], required=False, default=[])

        self.command_prefix = self._get_cfg(["command_prefix"], default="!c ")

        # plugins
        self.plugins_allowlist = self._get_cfg(["plugins", "allow_list"], required=False, default=[])
        self.plugins_denylist = self._get_cfg(["plugins", "deny_list"], required=False, default=[])

    def _get_cfg(
        self,
        path: List[str],
        default: Optional[Any] = None,
        required: Optional[bool] = True,
    ) -> Any:
        """Get a config option from a path and option name, specifying whether it is
        required.
        Raises:
            ConfigError: If required is True and the object is not found (and there is
                no default value provided), a ConfigError will be raised.
        """
        # Sift through the config until we reach our option
        config = self.config_dict
        for name in path:
            config = config.get(name)

            # If at any point we don't get our expected option...
            if config is None:
                # Raise an error if it was required
                if required and not default:
                    raise ConfigError(f"Config option {'.'.join(path)} is required")

                # or return the default value
                return default

        # We found the option. Return it.
        return config

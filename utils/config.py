"""Provide the Config class."""
import logging
import logging.config
import os
import sys

import anyconfig
import coloredlogs


class Config:
    """A class containing the configuration for the module."""

    def __init__(self, config_file=None):
        """Construct an instance of the Config object."""
        config_list = [os.path.join(sys.path[0], "config_default.yml")]

        if config_file:
            config_list.append(config_file)

        self.config = anyconfig.load(config_list)

    def __getitem__(self, key):
        """Return an item of the config by key."""
        return self.config[key]

    def __contains__(self, key):
        """Return true if an item exists in the config."""
        return key in config[key]

    def setup_logging(self):
        """Setup the `logging` module using the configuration under the
        `logging` key and setup the `coloredlogs` module."""
        logging.config.dictConfig(self.config["logging"])

        coloredlogs.install(
            level=self.config["logging"]["root"]["level"],
            fmt=self.config["coloredlogs"]["fmt"],
        )

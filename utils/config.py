"""@@@@@@Provide the Subreddit class."""
import logging
import logging.config
import os
import sys

import anyconfig
import coloredlogs


class Config:
    """@@@@@@A class providing a set of functions to interact with the target
    Subreddit.
    """

    def __init__(self, config_file=None):
        """@@@@@@Construct an instance of the Subreddit object."""
        config_list = [os.path.join(sys.path[0], "config_default.yml")]

        if config_file:
            config_list.append(config_file)

        self.config = anyconfig.load(config_list)

    def __getitem__(self, key):
        return self.config[key]

    def __contains__(self, key):
        return key in config[key]

    def setup_logging(self):
        logging.config.dictConfig(self.config["logging"])

        coloredlogs.install(
            level=self.config["logging"]["root"]["level"],
            fmt=self.config["coloredlogs"]["fmt"],
        )

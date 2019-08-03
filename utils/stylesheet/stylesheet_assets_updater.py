"""Provide the StylesheetAssetsUpdater class."""
import logging
import os
import re

from ruamel.yaml import YAML

from stylesheet import (LocalStylesheetImage, RemoteStylesheetImage,
                        StoredStylesheetImage, StylesheetData,
                        StylesheetImageList)
from stylesheet_exceptions import (FileReadingException, FileSavingException,
                                   ImageUploadException)

logger = logging.getLogger(__name__)


class StylesheetAssetsUpdater:
    """A class providing a set of functions for updating Reddit Stylesheet
    assets.
    """

    @property
    def new_images(self):
        """Return the list of new images (which are meant to be uploaded)."""
        return self.stylesheet_data.local_images.new

    @property
    def unused_images(self):
        """Return the list of unused images (which are meant to be removed)."""
        return self.stylesheet_data.remote_images.removed

    def __init__(self, config, stylesheet_data: StylesheetData = None):
        """Construct an instance of the StylesheetAssetsUpdater object."""

        self.config = config
        self.stylesheet_data = stylesheet_data
        self.css_content = None

    def load(self):
        """Load the data about Stylesheet Assets and the new CSS content."""
        yaml = YAML(typ="safe")
        yaml.register_class(StylesheetData)
        yaml.register_class(StylesheetImageList)
        yaml.register_class(LocalStylesheetImage)
        yaml.register_class(StoredStylesheetImage)
        yaml.register_class(RemoteStylesheetImage)

        logger.debug("Loading serialized StylesheetData class from: "
                     "'{}'".format(
                         self.config["data_file"],
                     ))
        try:
            with open(self.config["data_file"], "r") as yaml_stream:
                self.stylesheet_data = yaml.load(yaml_stream)
        except OSError as error:
            raise FileReadingException(
                error,
                "the Stylesheet Data file",
            ) from error

        logger.debug("Loading CSS content from: '{}'".format(
            self.stylesheet_data.css_file,
        ))
        try:
            with open(self.stylesheet_data.css_file, "r", encoding="utf-8") \
                    as css_stream:
                self.css_content = css_stream.read()
        except OSError as error:
            raise FileReadingException(
                error,
                "the CSS file",
            ) from error

    def remove_image(self, subreddit, remote_image):
        """Remove image of the specified name from the specified Subreddit."""
        subreddit.remove_image(remote_image.reddit_name)

    def save_data_page(self, subreddit, client_secret):
        """Save the data page the specified Subreddit.

        The content of the Data Page is provided by the instance of the
        StylesheetData class held in the `stylesheet_data` property.
        """
        subreddit.save_data_page(
            data_page_name=self.stylesheet_data.data_page_name,
            content=self.stylesheet_data.create_data_page(client_secret),
            revision_comment=self.stylesheet_data.revision_comment,
        )

    def upload_image(self, subreddit, local_image):
        """Upload image to the specified Subreddit.

        The information about the image is held by the provided instance of the
        LocalStylesheetImage class.
        """
        try:
            image_url = subreddit.upload_image(
                reddit_name=local_image.reddit_name,
                path=local_image.path,
                image_format=local_image.image_format,
            )
        except OSError as error:
            raise FileReadingException(
                error,
                "the local image",
            ) from error

        if not local_image.update_url_and_remote_size(image_url):
            raise ImageUploadException(
                local_image.path,
                "Unable to retrieve the size of the uploaded image."
            )

    def update_stylesheet(self, subreddit):
        """Submit content of the `css_content` property to the Stylesheet of
        the specified Subreddit.

        The existing Stylesheet is stored to `stylesheet_data` before
        performing the update.
        """
        logger.debug("Storing the size of the current CSS (before update).")
        self.stylesheet_data.previous_css_size = len(subreddit.stylesheet)

        logger.debug("Submitting the CSS to the Reddit Stylesheet.")
        self.stylesheet_data.saved_css_size = subreddit.update_stylesheet(
            css_content=self.css_content,
            revision_comment=self.stylesheet_data.revision_comment,
        )

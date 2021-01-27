"""Provide the StylesheetAssetsBuilder class."""
import logging
import os
import re

import csscompressor
import subprocess
from ruamel.yaml import YAML

from stylesheet import (LocalStylesheetImage, RemoteStylesheetImage,
                        StoredStylesheetImage, StylesheetAssets,
                        StylesheetAssetsValidator, StylesheetData,
                        StylesheetImageList, StylesheetImageMapper)
from stylesheet_exceptions import (FileSavingException, SassCompileException,
                                   ValidationException)

logger = logging.getLogger(__name__)


class StylesheetAssetsBuilder:
    """A class providing a set of functions for building Reddit Stylesheet
    assets.
    """

    def __init__(
        self,
        config,
        stylesheet_assets: StylesheetAssets,
        stylesheet_data: StylesheetData,
    ):
        """Construct an instance of the StylesheetAssetsBuilder object."""
        self.config = config
        self.assets = stylesheet_assets
        stylesheet_data.local_images = stylesheet_assets.local_images
        self.stylesheet_data = stylesheet_data

    def _create_validator(self):
        """Provide an instance of `StylesheetAssetsValidator` bound to the
        `StylesheetAssets` of this instance.
        """
        return StylesheetAssetsValidator(self.config, self.assets)

    def _filter_css(self, css_content):
        """Filter the CSS to comply with Reddit requirements:

        - Remove the @charset rule which is not supported by Reddit.
        """
        return re.sub(r"@charset(.+?);", "", css_content)

    def adapt(self):
        """Replace the local image filenames with the Reddit names in the image
        references of the CSS.

        Validate whether the final size of the CSS fits the Reddit limit.

        For example, local reference 'url("images/sprite-sheet-001.jpg")' is
        replaced by 'url(%%a%%)'.
        """
        css_content = self.assets.css_content

        logger.debug("Adapting the CSS content ({} bytes). Replacing local "
                     "image references with Reddit Names.".format(
                         len(css_content),
                     ))
        relative_images_dir = self.assets.relative_images_dir
        for local_image in self.assets.local_images:
            image_path = relative_images_dir + "/" \
                + local_image.filename
            css_content = re.sub(
                r"url\(\"" + re.escape(image_path) + r"\"\)",
                f"url(%%{local_image.reddit_name}%%)",
                css_content
            )
            logger.debug("Replaced \"{}\" with %%{}%%.".format(
                image_path,
                local_image.reddit_name,
            ))

        self.assets.adapted_css_content = css_content

    def build_css(self, sass_file):
        """Compile the Sass code to CSS using the "libsass-python" package
        and compress the CSS using the "csscompressor" package.

        Apply the custom filter on CSS by calling the `_filter_css` method.
        """
        logger.debug("Reading the Sass file.")
        sass_content = sass_file.read()

        logger.debug("Compiling the Sass file.")
        process = subprocess.run(
            ["sass", "--no-charset", "main.scss"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if process.stderr:
            raise SassCompileException(process.stderr, sass_file.name)
        if process.returncode != 0:
            raise SassCompileException(
                f"Sass gave non-zero exit code {process.returncode}",
                sass_file.name,
            )
        css_content = process.stdout
        logger.debug(
            "Compiled the Sass file. CSS content size: {} bytes".format(
                len(css_content),
            ))

        logger.debug("Filtering the CSS content.")
        css_content = self._filter_css(css_content)

        logger.debug("Compressing the CSS content.")
        css_content = csscompressor.compress(css_content)

        self.assets.css_content = css_content

    def load_local_images(self, images_dir):
        """Load all images stored in the 'images_dir' and supply them to the
        instance of the `StylesheetAssets` class.
        """
        self.assets.images_dir = images_dir

        for filename in os.listdir(images_dir):
            extension = os.path.splitext(filename)[1]
            if extension.lower() not in self.config["image_extensions"]:
                logger.debug(
                    f"Skipped a file of as unsupported extension: {filename}")
                continue

            logger.debug(f"Found image: '{filename}'")
            self.assets.add_local_image(filename)

    def load_remote_images(self, subreddit_images):
        """Load data about images hosted on Reddit into the instance of the
        `StylesheetData` class.

        The attributes of images are parsed from the `list` of images provided
        by the Reddit API.
        """
        for subreddit_image in subreddit_images:
            remote_image = RemoteStylesheetImage(
                reddit_name=subreddit_image["name"],
                url=subreddit_image["url"],
            )
            logger.debug(f"Found image: '{remote_image.reddit_name}'")
            self.stylesheet_data.remote_images.append(remote_image)

        for remote_image in self.stylesheet_data.remote_images:
            remote_image.load_remote_image_size()

    def map_images(self):
        """Map the data about locally stored images to the data about
        previously stored images and images currently hosted on Reddit.

        The goal is to identify which of the locally stored images should be
        uploaded to Reddit and which images hosted on Reddit should be removed.
        """
        mapper = StylesheetImageMapper(self.config)

        mapper.match_images(self.stylesheet_data)
        mapper.assign_reddit_names()

    def save(self):
        """Save the data about Stylesheet Assets and the final CSS."""
        yaml = YAML(typ="safe")
        yaml.register_class(StylesheetData)
        yaml.register_class(StylesheetImageList)
        yaml.register_class(LocalStylesheetImage)
        yaml.register_class(StoredStylesheetImage)
        yaml.register_class(RemoteStylesheetImage)

        logger.debug("Saving serialized StylesheetData class to: '{}'".format(
            self.config["data_file"],
        ))
        try:
            with open(self.config["data_file"], "w") as yaml_stream:
                yaml.dump(self.stylesheet_data, yaml_stream)
        except OSError as error:
            raise FileSavingException(
                error,
                "the Stylesheet Data file",
            ) from error

        css_file = self.assets.css_file_path
        logger.debug("Saving the CSS content to: '{}'".format(
            css_file,
        ))
        try:
            with open(css_file, "w", encoding="utf-8") as css_stream:
                css_stream.write(self.assets.adapted_css_content)
        except OSError as error:
            raise FileSavingException(
                error,
                "the CSS file",
            ) from error

    def validate_css(self, skip_css_validation):
        """Validate the CSS:

        1. Validate whether the size of CSS fits the limit.

        2. Validate CSS syntax using the W3C CSS Validator. This validation can
        be skipped by setting the `skip_css_validation` True.
        """
        validator = self._create_validator()

        validator.validate_css_size()

        if not skip_css_validation:
            validator.validate_css_syntax()

        if validator.validation_errors:
            raise ValidationException(validator.validation_errors)

    def validate_images(self):
        """Validate the Images:

        1. Validate whether all images comply with Reddit restrictions.

        2. Validate whether locally stored images are matching with the image
        references in the CSS.

        3. Validate whether CSS contains only supported image references.

        4. Validate whether all images are unique.
        """
        validator = self._create_validator()

        validator.validate_images()
        validator.validate_integrity()
        validator.validate_image_references()
        validator.validate_uniqueness()

        if validator.validation_errors:
            raise ValidationException(validator.validation_errors)

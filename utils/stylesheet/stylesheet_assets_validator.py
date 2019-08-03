"""Provide the StylesheetAssetsValidator class."""
import logging
import re
from collections import Counter

import requests

from stylesheet import StylesheetAssets, StylesheetImage
from stylesheet_exceptions import FileSavingException

logger = logging.getLogger(__name__)


class StylesheetAssetsValidator:
    """A class providing a set of functions for validating Reddit Stylesheet
    assets.
    """

    def __init__(self, config, stylesheet_assets: StylesheetAssets):
        """Construct an instance of the StylesheetAssetsValidator object."""
        self.config = config
        self.stylesheet_assets = stylesheet_assets
        self.validation_errors = []

    def _validate_image(self, stylesheet_image: StylesheetImage):
        """Validate whether the image complies with Reddit restrictions:

        - Image format
        - Filesize
        - Image width
        """
        logger.debug(f"Validating Image '{stylesheet_image.filename}'.")
        if stylesheet_image.image_format \
                not in self.config["allowed_image_formats"]:
            self.validation_errors.append(
                "Image '{}' is not in allowed format. The allowed formats "
                "are: {} (the format of the image is {}).".format(
                    stylesheet_image.path,
                    ", ".join(self.config["allowed_image_formats"]),
                    stylesheet_image.image_format,
                ))
        if stylesheet_image.file_size > self.config["max_image_size"]:
            self.validation_errors.append(
                "Image '{}' exceeds the maximum file size of {} bytes (the "
                "size of the image is {} bytes).".format(
                    stylesheet_image.path,
                    self.config["max_image_size"],
                    stylesheet_image.file_size,
                ))
        if stylesheet_image.width > self.config["max_image_width"]:
            self.validation_errors.append(
                "Image '{}' exceeds the maximum width of {} px (the width of "
                "the image is {} px).".format(
                    stylesheet_image.path,
                    self.config["max_image_width"],
                    stylesheet_image.width,
                ))

    def validate_css_size(self):
        """Validate whether size of the CSS is below the Reddit's limit."""
        logger.debug("Validating the CSS size.")
        if self.stylesheet_assets.adapted_css_size \
                > self.config["max_css_size"]:
            self.validation_errors.append(
                "The maximum size of CSS is {}, but the current CSS has {} "
                "bytes.".format(
                    self.config["max_css_size"],
                    self.stylesheet_assets.adapted_css_size,
                ))

        return self

    def validate_css_syntax(self):
        """Use W3C CSS Validator Web Service to check the final CSS syntax.

        If errors are found the validation output is saved to the file
        specified in the config.
        """
        logger.debug("Validating CSS syntax using the W3C CSS Validator.")
        w3c_validator_url = self.config["w3c_validator_url"]
        try:
            response = requests.post(w3c_validator_url, files={
                'profile': (None, "css3svg"),
                'text': (None, self.stylesheet_assets.adapted_css_content),
            })
        except Exception as error:
            logger.warning("The request to the W3C CSS Validator Web Service "
                           "has failed. The CSS syntax validation has been "
                           "skipped. The service might be overloaded. The "
                           f"following error has occurred: {error}")
            return self

        if response.status_code != requests.codes.ok:
            logger.warning("Warning: The request to the W3C CSS Validator Web "
                           "Service  has resulted in Error {}: {}. The CSS "
                           "syntax validation has been skipped.".format(
                               response.status_code,
                               response.reason,
                           ))
            return self

        validation_errors = response.headers["x-w3c-validator-errors"]

        if validation_errors == "0":
            logger.debug("The CSS successfully passed the validation.")
            return self

        logger.debug(f"Validation found {validation_errors} errors.")
        css_validator_output_file = self.config["css_validator_output_file"]
        if css_validator_output_file:
            logger.debug("Saving the validation results to {}.".format(
                css_validator_output_file,
            ))
            try:
                with open(css_validator_output_file, "wb") \
                        as output_stream:
                    output_stream.write(response.content)
            except OSError as error:
                raise FileSavingException(
                    error,
                    "the CSS validation output file",
                ) from error

            self.validation_errors.append(
                "The W3C CSS Validator has found {} errors in the CSS. The "
                "results have been saved to '{}'".format(
                    validation_errors,
                    css_validator_output_file,
                ))
        else:
            self.validation_errors.append(
                "The W3C CSS Validator has found {} errors in the CSS.".format(
                    validation_errors,
                ))

        return self

    def validate_image_references(self):
        """Validate whether the CSS contains only image references in
        a supported format (which could be parsed).
        """
        logger.debug("Validating CSS image references.")

        all_references = re.findall(
            r"url\(.*?\)",
            self.stylesheet_assets.css_content)

        regex = self.stylesheet_assets.image_reference_regex

        invalid_references = [r for r in all_references if not regex.search(r)]

        for invalid_reference in invalid_references:
            self.validation_errors.append(
                "The CSS contains an invalid image reference: '{}'".format(
                    invalid_reference,
                ))

        return self

    def validate_images(self):
        """Validate whether the image count is below Reddit's limit and whether
        all images comply with Reddit restrictions.
        """
        logger.debug("Validating the count of Stylesheet Images.")
        if len(self.stylesheet_assets.local_images) \
                > self.config["max_image_count"]:
            self.validation_errors.append(
                "The maximum number of images is {}, but {} images are "
                "stored in the Images directory.".format(
                    self.config["max_image_count"],
                    len(self.stylesheet_assets.local_images),
                ))

        for stylesheet_image in self.stylesheet_assets.local_images:
            self._validate_image(stylesheet_image)

        return self

    def validate_integrity(self):
        """Validate whether locally stored images are matching with the image
        references in the CSS. Image files must exactly match with the
        references with no exception.
        """
        css_image_references = \
            self.stylesheet_assets.css_image_references.copy()

        logger.debug("Validating if CSS image references correspond with the "
                     "Local Images.")
        for local_image in self.stylesheet_assets.local_images:
            if local_image.filename in css_image_references:
                css_image_references.pop(local_image.filename)
            else:
                self.validation_errors.append(
                    "Image '{}' is stored in the Images directory, but there "
                    "is no reference to the image in the CSS.".format(
                        local_image.filename,
                    ))

        for extra_image_reference in css_image_references:
            self.validation_errors.append(
                "The CSS contains a reference to '{}', but the image of this "
                "filename is missing in the Images directory.".format(
                    extra_image_reference,
                ))

        return self

    def validate_uniqueness(self):
        """Validate whether all images are unique. The images are compared by
        their `md5` property.
        """
        logger.debug("Validating that all Stylesheet Images are unique.")
        images = self.stylesheet_assets.local_images
        for md5, count in Counter(i.md5 for i in images).items():
            if count == 1:
                continue

            self.validation_errors.append(
                "The following images are duplicate: {}".format(
                    ", ".join(i.filename for i in images if i.md5 == md5),
                ))

        return self

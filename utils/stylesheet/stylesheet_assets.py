"""Provide the StylesheetAssets class."""
import functools
import os
import re
from collections import Counter

from stylesheet import LocalStylesheetImage, StylesheetImageList


class StylesheetAssets:
    """A class representing assets of Reddit Stylesheet."""

    @property
    def adapted_css_size(self):
        """Return the size of the CSS after replacing the local image filenames
        with the Reddit names in the image references.
        """
        return len(self.adapted_css_content.encode("utf-8"))

    @property
    @functools.lru_cache()
    def css_image_references(self):
        """Return a ``Counter`` of images references in the CSS."""
        assert self.css_content is not None, "'css_content' property must " \
            "be set in order to access the 'css_image_references' property."

        all_references = self.image_reference_regex.findall(self.css_content)

        return Counter(all_references)

    @property
    def css_size(self):
        """Return the size of the CSS with the local names used in the image
        references.
        """
        return len(self.css_content.encode("utf-8"))

    @property
    def image_reference_regex(self):
        """Return the regular expression pattern object for parsing image
        references in the CSS. The supported image extensions specified in the
        config are inserted into the pattern.
        """
        extensions = "|".join(self.config["image_extensions"])
        pattern = r"url\(\"" + self.relative_images_dir \
            + r"\/([\w_-]+.(?:" + extensions + r"))\"\)"

        return re.compile(pattern, re.I)

    @property
    def relative_images_dir(self):
        """Return the relative path from CSS the file to the Images directory.
        """
        css_dir = os.path.dirname(self.css_file_path)
        return os.path.relpath(self.images_dir, css_dir)

    def __init__(self, config, css_file_path):
        """Construct an instance of the StylesheetAssets object."""
        self.config = config
        self.css_file_path = css_file_path
        self.css_content = None
        self.adapted_css_content = None
        self.images_dir = None
        self.local_images = StylesheetImageList()

    def add_local_image(self, filename):
        """Add an image to the assets. Get the Usage Count of the image and add
        it as an instance of the `LocalStylesheetImage` class to
        `local_images`.
        """
        usage_count = self.css_image_references.get(filename, 0)

        local_images = LocalStylesheetImage(
            images_dir=self.images_dir,
            filename=filename,
            usage_count=usage_count,
        )

        self.local_images.append(local_images)

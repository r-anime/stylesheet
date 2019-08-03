"""Provide the StylesheetImage class and its subclasses."""
import hashlib
import io
import logging
import os
from pathlib import Path

import requests
from PIL import Image

from stylesheet_exceptions import InvalidImageException

logger = logging.getLogger(__name__)


class StylesheetImage:
    """A class representing a Reddit Stylesheet Image."""

    @property
    def file_size(self):
        """Return the size of the locally stored image file in bytes."""
        return self._file_size

    @property
    def filename(self):
        """Return the filename of the locally stored image file."""
        return self._filename

    @property
    def height(self):
        """Return the height of the image."""
        return self._height

    @property
    def image_format(self):
        """Return the format of the image."""
        return self._image_format

    @property
    def md5(self):
        """Return the MD5 hash of the locally stored image file."""
        return self._md5

    @property
    def path(self):
        """Return the path of the locally stored image file."""
        return self._path

    @property
    def reddit_name(self):
        """Return the name of the image used by Reddit.

        Note: Reddit Names are supposed to be as short as possible to reduce
        the size of CSS. It is recommended to use base-26 alphabet number
        strings (e.g. 'a', 'b', ..., 'aa', 'ab', ...).
        """
        return self._reddit_name

    @property
    def remote_file_size(self):
        """Return the size of the image file hosted on Reddit in bytes."""
        return self._remote_file_size

    @property
    def usage_count(self):
        """Return the count of usage of the image in CSS."""
        return self._usage_count

    @property
    def url(self):
        """Return the URL of the image file hosted on Reddit."""
        return self._url

    @property
    def width(self):
        """Return the width of the image."""
        return self._width

    def __init__(
        self,
        filename=None,
        path=None,
        reddit_name=None,
        url=None,
        md5=None,
        usage_count=None,
        file_size=None,
        remote_file_size=None,
        width=None,
        height=None,
        image_format=None,
    ):
        """Construct an instance of the StylesheetImage object."""
        self._filename = filename
        self._path = path
        self._reddit_name = reddit_name
        self._url = url
        self._md5 = md5
        self._usage_count = usage_count
        self._file_size = file_size
        self._remote_file_size = remote_file_size
        self._width = width
        self._height = height
        self._image_format = image_format

    def _parse(self, image_content):
        """Parse the contents of the image file and update the following
        properties:
        - `file_size`
        - `width`
        - `height`
        - `md5`
        """
        self._file_size = len(image_content)

        try:
            image = Image.open(io.BytesIO(image_content))
        except IOError as error:
            name = self._filename or self._url
            raise InvalidImageException(name) from error

        self._width, self._height = image.size
        self._image_format = image.format

        hash = hashlib.md5()
        hash.update(image_content)
        self._md5 = hash.hexdigest()

    def load_remote_image_size(self):
        """Load the file size of the image hosted on Reddit."""
        logger.debug("Trying to retrive the size of image '{}'.".format(
            self._reddit_name,
        ))
        response = requests.head(self.url)
        if response.status_code != requests.codes.ok:
            return None
        if "image/" not in response.headers.get("content-type"):
            return None

        remote_file_size = int(response.headers.get("content-length"))
        self._remote_file_size = remote_file_size
        logger.debug("Retrieved the size of image '{}': {} bytes".format(
            self._reddit_name,
            self._remote_file_size
        ))

        return remote_file_size


class LocalStylesheetImage(StylesheetImage):
    """A class representing a locally stored Reddit Stylesheet Image file."""

    @property
    def is_new(self):
        """Return 'True' when the image is marked as new."""
        return self._is_new

    @StylesheetImage.reddit_name.setter
    def reddit_name(self, reddit_name):
        """Update the Reddit Name of the image."""
        self._reddit_name = reddit_name

    @StylesheetImage.remote_file_size.setter
    def remote_file_size(self, remote_file_size):
        """Update the Remote File Size of the image."""
        self._remote_file_size = remote_file_size

    @StylesheetImage.url.setter
    def url(self, url):
        """Update the URL of the image."""
        self._url = url

    def __init__(self, images_dir, filename, usage_count):
        """Construct an instance of the LocalStylesheetImage object."""
        super().__init__(
            filename=filename,
            path=os.path.join(images_dir, filename),
            usage_count=usage_count,
        )

        self._is_new = False

        with open(Path(self._path), "rb") as image_file:
            image_content = image_file.read()

        self._parse(image_content)

    def mark_as_new(self):
        """Mark the image as new and set the `url` property as `None`."""
        self._is_new = True
        self._url = None

    def update_url_and_remote_size(self, url):
        """Update the URL and load the size of the hosted image and returns the
        loaded size of the image.
        """
        self._url = url
        self.load_remote_image_size()
        return self.remote_file_size


class RemoteStylesheetImage(StylesheetImage):
    """A class representing a Reddit Stylesheet Image hosted on Reddit."""

    @property
    def is_removed(self):
        """Return 'True' when the image is marked as removed."""
        return not (self._is_used or self._is_replaced)

    @property
    def is_replaced(self):
        """Return 'True' when the image is marked as replaced."""
        return self._is_replaced

    @property
    def is_used(self):
        """Return 'True' when the image is marked as used."""
        return self._is_used

    def __init__(self, reddit_name, url):
        """Construct an instance of the RemoteStylesheetImage object."""
        super().__init__(reddit_name=reddit_name, url=url)

        self._is_replaced = False
        self._is_used = False

    def mark_as_replaced(self):
        """Mark the image as replaced."""
        self._is_replaced = True

    def mark_as_used(self):
        """Mark the image as used."""
        self._is_used = True


class StoredStylesheetImage(StylesheetImage):
    """A class representing a Reddit Stylesheet Image that was previously
    stored on Reddit.

    The attributes of this class are loaded from the Subreddit Data Page.
    """

    def __init__(self, filename, reddit_name, url, md5, remote_file_size):
        """Construct an instance of the StoredStylesheetImage object."""
        super().__init__(
            filename=filename,
            reddit_name=reddit_name,
            url=url,
            md5=md5,
            remote_file_size=remote_file_size
        )

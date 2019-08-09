"""Provide the StylesheetImageMapper class."""
import logging
import string

from stylesheet import LocalStylesheetImage, StylesheetData

logger = logging.getLogger(__name__)

# Alphabet of characters valid in Reddit image names
alphabet = string.digits + string.ascii_letters
alphabet_length = len(alphabet)


class StylesheetImageMapper:
    """A class providing a set of functions for mapping images when updating a
    Reddit Stylesheet.
    """

    def __init__(self, config):
        """Construct an instance of the StylesheetImageMapper object."""
        self.config = config
        self._used_reddit_names = {}
        self._unnamed_images = []

    def _alpha_base(self, number):
        """Convert the provided decimal number into base-26 alphabet number
        string.
        """
        string = ""
        while number > 0:
            number, remainder = divmod(number - 1, alphabet_length)
            string = alphabet[remainder] + string
        return string

    def _match_image(self, local_image: LocalStylesheetImage,
                     stylesheet_data: StylesheetData):
        """Match the locally stored image (Local Image) with the data about
        previously stored images (Stored Images) and freshly loaded data about
        images hosted on Reddit (Remote Images).

        1. If the Stored Image is not found mark the Local Image as new.

        2. If the Remote Image is not found mark the Local Image as new.

        3a. If the MD5 of the Stored Image is not matching with the Local Image
        mark the Local Image as new and the Remote Image as replaced (Local
        Image will be uploaded over the current Remote Image)

        3b. Otherwise the image is considered unchanged and the Remote Image
        is marked as used and the URL of the Local Image is set to the URL of
        the Stored Image (Remote Image).

        Note: Only Remote Images marked as used are kept on Reddit. All the
        other Remote Images are either replaced or removed.
        """
        logger.debug(f"Matching the Local Image '{local_image.filename}'.")
        stored_image = stylesheet_data.stored_images.find(
            filename=local_image.filename)

        if stored_image is None:
            local_image.mark_as_new()
            logger.debug("Image not found in Stored Images. Marked as new.")
            return

        logger.debug("Image found in Stored Images. Reddit Name: '{}'".format(
            stored_image.reddit_name,
        ))

        remote_image = stylesheet_data.remote_images.find(
            reddit_name=stored_image.reddit_name,
            url=stored_image.url,
            remote_file_size=stored_image.remote_file_size,
        )

        if remote_image is None:
            local_image.mark_as_new()
            logger.debug("Image not found in Remote Images.")
            return

        logger.debug("Image found in Remote Images.")

        if local_image.md5 != stored_image.md5:
            local_image.mark_as_new()
            remote_image.mark_as_replaced()
            logger.debug("The hash differs from the hash of the Stored Image. "
                         "The Local Image is marked as new and the Remote "
                         "image is marked as replaced.")
        else:
            local_image.url = stored_image.url
            local_image.remote_file_size = stored_image.remote_file_size
            remote_image.mark_as_used()
            logger.debug("The hash is matching with the hash of the Stored "
                         "Image. The Remote Image is marked as used and the "
                         "attributes are copied to the Local Image.")

        reddit_name = stored_image.reddit_name

        local_image.reddit_name = reddit_name
        self._used_reddit_names[reddit_name] = local_image.usage_count

    def _prepare_available_reddit_names(self):
        """Build a `list` of available Reddit Names as an ascending series of
        base-26 alphabet number strings while leaving out the names that are
        already used.
        """
        available_reddit_names = []
        min_usage_count, update_count = 0, False
        max_image_count = self.config["max_image_count"]
        for name in map(self._alpha_base, range(max_image_count, 0, -1)):
            if name in self._used_reddit_names:
                if update_count:
                    min_usage_count = self._used_reddit_names[name]
                    update_count = False
            else:
                available_reddit_names.append((name, min_usage_count))
                update_count = True

        logger.debug("Prepared available Reddit Names: {}".format(
            ", ".join("'" + n + "'" for n, u in available_reddit_names),
        ))
        return available_reddit_names

    def assign_reddit_names(self):
        """Assign the available Reddit Names to the new Local Images.

        The new Local Images are sorted by usage in descending order to assign
        the shotest names to the images that are used the most (in the CSS).
        """
        logger.debug("Count of Local Images without the Reddit Name assigned:"
                     f" {len(self._unnamed_images)}")

        if not self._unnamed_images:
            return

        available_reddit_names = self._prepare_available_reddit_names()
        extra_names = len(available_reddit_names) - len(self._unnamed_images)
        logger.debug(f"Extra names count: {extra_names}")

        for reddit_name, min_usage_count in reversed(available_reddit_names):
            if not self._unnamed_images:
                break

            if extra_names \
                    and min_usage_count > self._unnamed_images[0].usage_count:
                extra_names -= 1
                continue

            unnamed_image = self._unnamed_images.pop(0)
            unnamed_image.reddit_name = reddit_name

            logger.debug("Reddit Name '{}' assigned to the image '{}'.".format(
                reddit_name,
                unnamed_image.filename,
            ))

    def match_images(self, stylesheet_data: StylesheetData):
        """Match the locally stored images (Local Images) with the data about
        previously stored images (Stored Images) and freshly loaded data about
        images hosted on Reddit (Remote Images).

        Store the list of unnamed images into a property of this object.
        """
        local_images = stylesheet_data.local_images

        logger.debug(f"Matching {len(local_images)} Local Images.")
        for local_image in local_images.by_filename:
            self._match_image(local_image, stylesheet_data)

        self._unnamed_images.extend(local_images.unnamed.by_usage_count.desc)
        logger.debug("Matching of Local Images completed.")

"""Provide the StylesheetData class."""
import hashlib
import hmac
import logging
import os
import re
from datetime import datetime
from string import Template

from stylesheet import StoredStylesheetImage, StylesheetImageList

templates_dir = os.path.join(os.path.dirname(__file__), 'templates')

logger = logging.getLogger(__name__)


class StylesheetData:
    """A class holding a data for updating a Reddit Stylesheet.

    At the beginning of the Reddit Stylesheet update, stored data are loaded
    from the Subreddit Data Page.

    At the end of the Reddit Stylesheet update, updated data are stored to
    the Subreddit Data Page.
    """

    def __init__(self, subreddit_name, css_file, data_page_name,
                 revision_comment):
        """Construct an instance of the StylesheetData object."""
        self.subreddit_name = subreddit_name
        self.css_file = css_file
        self.data_page_name = data_page_name
        self.revision_comment = revision_comment
        self.stored_images: StylesheetImageList = StylesheetImageList()
        self.local_images: StylesheetImageList = StylesheetImageList()
        self.remote_images: StylesheetImageList = StylesheetImageList()
        self.previous_css_size = None
        self.saved_css_size = None

    def _image_table_rows(self):
        """Build the rows of a Markdown table with the data about the locally
        stored images.

        Order the images by Reddit Name.
        """
        logger.debug("Building rows for the Image Table: {} images ".format(
            len(self.local_images.by_reddit_name),
        ))
        return "\n".join(["|".join((
            f"[{image.reddit_name}]({image.url})",
            image.filename,
            str(image.usage_count),
            str(image.file_size),
            str(image.remote_file_size),
            f"{image.width}x{image.height}",
            image.md5,
        )) for image in self.local_images.by_reddit_name])

    def append_hmac(self, content, key):
        """Append the HMAC-SHA-384 to the provided content using the provided
        key.
        """
        logger.debug("Appending HMAC to the content.")
        digest = hmac.new(
            key.encode(),
            content.encode(),
            hashlib.sha384,
        )

        return content + digest.hexdigest()

    def create_data_page(self, key):
        """Build the contents of the Data Page using the locally stored
        Markdown template filled by properties of this object.

        Append the HMAC-SHA-384 to the contents to ensure the integrity of
        the data.
        """
        try:
            template_path = os.path.join(
                templates_dir, "data_page_template.md")
            logger.debug("Loading the Data Page template from '{}'.".format(
                template_path,
            ))
            with open(template_path, "r", encoding="utf-8") as template_file:
                template_content = template_file.read()
            logger.debug("Loaded the Data Page template. Current size: "
                         "{} bytes".format(
                             len(template_content),
                         ))

            self._data_page_template = Template(template_content)
        except IOError as error:
            raise Exception(f"Failed to load the data page template: {error}")

        data_page = self._data_page_template.substitute(
            updated_at=datetime.utcnow().isoformat(' ', 'seconds') + " (UTC)",
            comment=self.revision_comment,
            current_css_size=self.saved_css_size,
            previous_css_size=self.previous_css_size,
            images_unchanged=len(self.local_images.unchanged),
            images_added=len(self.local_images.new),
            images_removed=len(self.remote_images.removed),
            image_table_rows=self._image_table_rows(),
        )
        logger.debug("Filled the Data Page template. Current size: "
                     "{} bytes".format(
                         len(data_page),
                     ))

        data_page = self.append_hmac(data_page, key)
        logger.debug("Appended HMAC to the Data Page content. Current size: "
                     "{} bytes".format(
                         len(data_page),
                     ))

        return data_page

    def parse_data_page(self, page_content, key):
        """Validate the provided content of the Data Page and parse the
        selected data into properties of this object.
        """
        if not self.validate_data_page(page_content, key):
            return False

        table_pattern = r"###Images\s+([^\|]+(?:\|[^\|]+)+\n)+"
        row_pattern = r"\|".join((
            r"\[(?P<reddit_name>\w+)\]\((?P<url>.*?)\)",
            r"(?P<filename>[\w\-_]+\.\w+)",
            r"(?P<usage_count>\d+)",
            r"(?P<file_size>\d+)",
            r"(?P<remote_file_size>\d+)",
            r"(?P<width>\d+)x(?P<height>\d+)",
            r"(?P<md5>\w+)",
        ))

        logger.debug("Parsing the Image Table from the Data Page.")
        table_match = re.search(table_pattern, page_content)

        if not table_match:
            logger.warning("Image Table not found on the Data Page.")
            return True

        logger.debug("Parsing images from the Image Table.")

        for row in re.finditer(row_pattern, table_match.group(1)):
            stored_image = StoredStylesheetImage(
                filename=row.group("filename"),
                reddit_name=row.group("reddit_name"),
                url=row.group("url"),
                md5=row.group("md5"),
                remote_file_size=int(row.group("remote_file_size")),
            )
            logger.debug("Parsed image: '{}' as '{}' ({} bytes)".format(
                stored_image.filename,
                stored_image.reddit_name,
                stored_image.remote_file_size,
            ))
            self.stored_images.append(stored_image)

        return True

    def validate_data_page(self, page_content, key):
        """Validate the HMAC-SHA-384 which is expected to be appended to the
        page content."""
        digest_length = hashlib.sha384().digest_size * 2
        content = page_content[:-digest_length]
        src_digest = page_content[-digest_length:]

        digest = hmac.new(
            key.encode(),
            content.encode(),
            hashlib.sha384,
        )
        hexdigest = digest.hexdigest()

        logger.debug("Validating HMAC:\n- Expected key: '{}'\n- Provided key: "
                     "'{}'".format(
                         hexdigest,
                         src_digest,
                     ))

        return src_digest == hexdigest

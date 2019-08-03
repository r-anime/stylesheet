"""Provide the Subreddit class."""
import logging

import praw
from prawcore.exceptions import NotFound, OAuthException

from stylesheet_exceptions import (AuthException, DataPageAccessException,
                                   DataPageMissingException,
                                   ImageUploadException,
                                   StylesheetUpdateException)

logger = logging.getLogger(__name__)


class Subreddit:
    """A class providing a set of functions to interact with the target
    Subreddit.
    """

    @property
    def images(self):
        """Return a ``list`` of images used by the stylesheet."""
        return self._subreddit.stylesheet().images

    @property
    def stylesheet(self):
        """Return the contents of the stylesheet, as CSS."""
        return self._subreddit.stylesheet().stylesheet

    def __init__(self, subreddit_name, client_id, client_secret, username,
                 password, redirect_uri):
        """Construct an instance of the Subreddit object."""
        self.subreddit_name = subreddit_name
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            redirect_uri=redirect_uri,
            user_agent="Stylesheet update (run by /u/{})".format(username),
        )
        self._subreddit = self.reddit.subreddit(subreddit_name)

        logger.debug(f"Trying if the user /u/{username} can log in to Reddit")
        try:
            self.reddit.user.me()
        except OAuthException as error:
            raise AuthException(username) from error

    def _unify_line_endings(self, content):
        """Replace line endings of provided string by a single Line Feed."""
        return "\n".join(content.splitlines())

    def _upload_image_as_png(self, reddit_name, path):
        """Upload an image to the Subreddit as PNG and return a dictionary
        containing a link to the uploaded image under the key ``img_src``.
        """

        with open(path, "rb") as image:
            data = {
                "name": reddit_name,
                "upload_type": "img",
                "img_type": "png",
            }
            url = praw.endpoints.API_PATH["upload_image"].format(
                subreddit=self.subreddit_name)
            response = self.reddit.post(
                url, data=data, files={"file": image}
            )
            if response["errors"]:
                error_type = response["errors"][0]
                error_value = response.get("errors_values", [""])[0]
                raise praw.exceptions.APIException(
                    error_type, error_value, None)
            return response

    def load_data_page(self, data_page_name):
        """Return the contents of the Reddit Wiki Page designated as the Data
        Page and check whether the current user has permissions to edit the
        page.

        Unify line endings of the returned content.

        Raise Exception if the Wiki Page does not exist or the current user
        does not have sufficient permissions to edit it.
        """
        wiki_page = self._subreddit.wiki[data_page_name]
        try:
            content = wiki_page.content_md
        except NotFound as error:
            raise DataPageMissingException(
                subreddit_name=self.subreddit_name,
                data_page_name=data_page_name,
            ) from error

        if not wiki_page.may_revise:
            raise DataPageAccessException(
                subreddit_name=self.subreddit_name,
                data_page_name=data_page_name,
                username=self.reddit.user.me(),
            ) from error

        return self._unify_line_endings(content)

    def remove_image(self, reddit_name):
        """Remove the named image from the subreddit."""
        self._subreddit.stylesheet.delete_image(reddit_name)

    def save_data_page(self, data_page_name, content, revision_comment):
        """Update the contents of the Reddit Wiki Page designated as the Data
        Page and load the contents to check if the update succeeded. Reddit API
        does not provide any confirmation of successful update.
        """
        self._subreddit.wiki[data_page_name].edit(
            content=content,
            reason=revision_comment,
        )

        logger.debug("The Data Page was updated. Loading the saved page "
                     "to verify whether the update succeeded.")
        saved_content = self.load_data_page(data_page_name)

        if content != saved_content:
            raise StylesheetUpdateException(content, saved_content)

    def update_stylesheet(self, css_content, revision_comment):
        """Update the Stylesheet of the Subreddit and load the contents to
        check if the update succeeded. Reddit API does not provide any
        confirmation of successful update.

        Returns the length of the saved CSS.
        """
        self._subreddit.stylesheet.update(css_content, revision_comment)

        logger.debug("The Stylesheet was updated. Loading the saved CSS "
                     "to verify whether the update succeeded.")
        saved_css_content = self.stylesheet

        if css_content != saved_css_content:
            raise StylesheetUpdateException(css_content, saved_css_content)

        return len(saved_css_content)

    def upload_image(self, reddit_name, path, image_format):
        """Upload an image to the Subreddit and return the url of the uploaded
        image.

        Uploading images to Reddit is a bit tricky. If an image is uploaded
        "as JPEG" it is encoded with a quality set to 85 regardless of the
        source image provided:

        https://github.com/reddit-archive/reddit/blob/753b17407e9a9dca09558526805922de24133d53/r2/r2/lib/media.py#L299

        Thus any JPEG image which is stored in JPEG format on Reddit is
        re-encoded after the upload.

        The only way how to avoid double compression of JPEG image is to store
        it in PNG format on Reddit.

        In some cases the double compression may be bearable, but this module
        uses an assumption that the images are packed with content to their
        full potential (typically large sprite sheets) so it is necessary to
        upload them as JPEG to comply with the upload size limit, but the
        degradation of quality caused by the double compression would not be
        acceptable.
        """
        if image_format == "PNG":
            logger.debug("Source format: PNG / Target format: PNG")
            result = self._subreddit.stylesheet.upload(reddit_name, path)
        else:
            logger.debug("Source format: JPEG / Target format: PNG")
            result = self._upload_image_as_png(reddit_name, path)

        if "img_src" not in result:
            raise ImageUploadException(
                path,
                "Reddit API has not returned the URL of the uploaded image."
            )

        return result["img_src"]

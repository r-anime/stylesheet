import logging
import os

import click
import mintotp
import verboselogs
from ruamel.yaml import YAML

from config import Config
from stylesheet import StylesheetAssetsUpdater
from stylesheet_exceptions import StylesheetException
from subreddit import Subreddit


@click.command()
@click.option(
    "--config_file",
    type=click.Path(dir_okay=False),
    help="Path to the config file.",
)
@click.option(
    "--client_id",
    required=True,
    envvar="REDDIT_CLIENT_ID",
    help="The OAuth client id associated with the registered Reddit "
    "application. Can be set by REDDIT_CLIENT_ID environment variable.",
)
@click.option(
    "--client_secret",
    required=True,
    envvar="REDDIT_CLIENT_SECRET",
    help="The OAuth client secret associated with your registered Reddit "
    "application. Can be set by REDDIT_CLIENT_SECRET environment variable.",
)
@click.option(
    "--username",
    required=True,
    envvar="REDDIT_USERNAME",
    help="The username of the Reddit account. Can be set by "
    "REDDIT_USERNAME environment variable.",
)
@click.option(
    "--password",
    required=True,
    envvar="REDDIT_PASSWORD",
    help="The password of the Reddit account. Can be set by "
    "REDDIT_PASSWORD environment variable.",
)
@click.option(
    "--redirect_uri",
    required=True,
    envvar="REDDIT_REDIRECT_URI",
    help="The redirect URI associated with your registered Reddit "
    "application. Can be set by REDDIT_REDIRECT_URI environment variable.",
)
@click.option(
    "--totp_secret",
    required=False,
    envvar="REDDIT_TOTP_SECRET",
    help="The TOTP hex secret of the Reddit account if 2FA is enabled. Can be set by "
         "REDDIT_TOTP_SECRET environment variable.",
)
def main(
    config_file,
    client_id,
    client_secret,
    username,
    password,
    redirect_uri,
    totp_secret=None,
):
    config = Config(config_file)
    config.setup_logging()

    logger = verboselogs.VerboseLogger("update")

    try:
        logger.info("Initializing the update.")
        updater = StylesheetAssetsUpdater(config)

        logger.info("Loading the Subreddit Data file:")
        updater.load()
        data = updater.stylesheet_data
        logger.verbose(f"Loaded data for /r/{data.subreddit_name}")
        logger.verbose(f"Revision comment: {data.revision_comment}")
        logger.verbose(f"CSS size: {len(updater.css_content)} bytes")

        logger.info("Authenticating to Reddit:")

        if totp_secret:
            password = f"{password}:{mintotp.totp(totp_secret)}"

        subreddit = Subreddit(
            subreddit_name=data.subreddit_name,
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            redirect_uri=redirect_uri,
        )
        logger.verbose(f"Logged in as: {username}")

        if updater.unused_images:
            logger.info("Removing unused images:")
            for unused_image in updater.unused_images.by_reddit_name:
                logger.verbose(f"Removing image '{unused_image.reddit_name}'")
                updater.remove_image(subreddit, unused_image)

        if updater.new_images:
            logger.info("Uploading new images:")
            for new_image in updater.new_images.by_reddit_name:
                logger.verbose("Uploading image '{}' as '{}'".format(
                    new_image.filename,
                    new_image.reddit_name,
                ))
                updater.upload_image(subreddit, new_image)

        logger.info("Updating the Stylesheet:")
        updater.update_stylesheet(subreddit)
        logger.verbose("Stylesheet updated successfully.")

        logger.info("Saving the Data Page (/r/{}/wiki/{}):".format(
            data.subreddit_name,
            data.data_page_name,
        ))
        updater.save_data_page(subreddit, client_secret)
        logger.verbose("The Data Page saved successfully.")

        logger.info("The Reddit Stylesheet update has been completed. Please "
                    "perform a manual validation.")
        logger.verbose("Make sure there are enough cute anime girls featured "
                       "in the Stylesheet!")

    except StylesheetException as error:
        show_traceback = logger.getEffectiveLevel() == logging.DEBUG
        logger.error(f"Update procedure failed: {error}",
                     exc_info=show_traceback)
        exit(1)
    except Exception as error:
        logger.error(f"An unexpected error has occurred.", exc_info=True)
        exit(1)


if __name__ == '__main__':
    main()

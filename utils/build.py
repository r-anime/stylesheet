import logging
import os

import click
import verboselogs

from config import Config
from stylesheet import (StylesheetAssets, StylesheetAssetsBuilder,
                        StylesheetData)
from stylesheet_exceptions import StylesheetException
from subreddit import Subreddit


def travis_revision_comment():
    if not os.environ.get("TRAVIS_REPO_SLUG"):
        return None

    if os.environ.get("TRAVIS_COMMIT_RANGE"):
        return "https://github.com/{}/compare/{}".format(
            os.environ["TRAVIS_REPO_SLUG"],
            os.environ["TRAVIS_COMMIT_RANGE"])

    if os.environ.get("TRAVIS_COMMIT"):
        return "https://github.com/{}/commit/{}".format(
            os.environ["TRAVIS_REPO_SLUG"],
            os.environ["TRAVIS_COMMIT"])

    return None


@click.command()
@click.option(
    "--subreddit_name",
    required=True,
    envvar="REDDIT_SUBREDDIT",
    help="The name of the target subreddit. Note that this sub's theme will "
    "be overwritten. Can be set by REDDIT_SUBREDDIT environment variable.",
)
@click.option(
    "--revision_comment",
    "-r",
    required=True,
    default=travis_revision_comment(),
    help="Reason for the revision. Defaults to GitHub link to the changes if "
    "launched by Travis.",
)
@click.option(
    "--sass_file",
    "-s",
    default="main.scss",
    type=click.File("r"),
    help="Path to the Sass file.",
)
@click.option(
    "--images_dir",
    "-i",
    default="images",
    type=click.Path(file_okay=False, exists=True, resolve_path=True),
    help="Path to the directory with the images.",
)
@click.option(
    "--css_file",
    "-c",
    default="stylesheet.css",
    type=click.Path(dir_okay=False, resolve_path=True),
    help="Path to the output CSS file.",
)
@click.option(
    "--config_file",
    type=click.Path(dir_okay=False),
    help="Path to the config file.",
)
@click.option(
    "--data_page_name",
    default="stylesheet/data",
    help="The name of the wiki page of the Subreddit that is used as a "
    "storage for the data about images.",
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
    "--skip_css_validation",
    is_flag=True,
    help="Skip the validation performed by W3C CSS Validator Web Service.",
)
def main(
    subreddit_name,
    revision_comment,
    sass_file,
    images_dir,
    css_file,
    config_file,
    data_page_name,
    client_id,
    client_secret,
    username,
    password,
    redirect_uri,
    skip_css_validation,
):
    config = Config(config_file)
    config.setup_logging()

    logger = verboselogs.VerboseLogger("build")

    try:
        logger.info(f"Preparing update for /r/{subreddit_name}.")
        data = StylesheetData(
            subreddit_name=subreddit_name,
            css_file=css_file,
            data_page_name=data_page_name,
            revision_comment=revision_comment,
        )
        assets = StylesheetAssets(config, css_file)
        builder = StylesheetAssetsBuilder(config, assets, data)

        logger.info("Building CSS:")
        builder.build_css(sass_file)
        logger.verbose(f"Compressed CSS size: {assets.css_size} bytes")

        logger.info("Loading local images:")
        builder.load_local_images(images_dir)
        logger.verbose(f"Loaded {len(assets.local_images)} images")

        logger.info("Validating images:")
        builder.validate_images()
        logger.verbose("All images are unique and fit the Reddit criteria.")
        logger.verbose(
            "All image references in the CSS are matching with image files.")

        logger.info("Connecting to Reddit:")
        subreddit = Subreddit(
            subreddit_name=subreddit_name,
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            redirect_uri=redirect_uri,
        )
        logger.verbose(f"Logged in as /u/{username}")

        logger.info(
            f"Loading Data Page (/r/{subreddit_name}/wiki/{data_page_name}):")
        page_content = subreddit.load_data_page(data_page_name)
        if not page_content:
            logger.warning("The Data Page is empty. All the existing images "
                           "will be re-uploaded.")
        elif not data.parse_data_page(page_content, client_secret):
            logger.warning("The data integrity check has failed and the Data "
                           "Page has not been loaded. All the existing images "
                           "will be re-uploaded.")
        else:
            logger.verbose("Loaded data about {} images.".format(
                len(data.stored_images)
            ))

        logger.info("Loading remote images:")
        builder.load_remote_images(subreddit.images)
        logger.verbose(f"Loaded {len(data.remote_images)} images")

        logger.info("Mapping images:")
        builder.map_images()
        logger.verbose(f"New images added: {len(data.local_images.new)}")
        logger.verbose(
            f"Old images removed: {len(data.remote_images.removed)}")

        logger.info("Adapting CSS:")
        builder.adapt()
        logger.verbose(f"Adapted CSS size: {assets.adapted_css_size} bytes")

        logger.info("Saving output files:")
        builder.save()
        logger.verbose("Saved Subreddit Data file")
        logger.verbose("Saved CSS file")

        logger.info("Validating CSS:")
        builder.validate_css(skip_css_validation)
        logger.verbose("CSS has been validated")
    except StylesheetException as error:
        show_traceback = logger.getEffectiveLevel() == logging.DEBUG
        logger.error(f"Build procedure failed: {error}",
                     exc_info=show_traceback)
        exit(1)
    except Exception as error:
        logger.error(f"An unexpected error has occurred.", exc_info=True)
        exit(1)


if __name__ == '__main__':
    main()

import logging

import click
import verboselogs

from config import Config
from stylesheet import (StylesheetAssets, StylesheetAssetsBuilder,
                        StylesheetData)
from stylesheet_exceptions import StylesheetException


@click.command()
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
    "--skip_css_validation",
    is_flag=True,
    help="Skip the validation performed by W3C CSS Validator Web Service.",
)
def main(
    sass_file,
    images_dir,
    css_file,
    config_file,
    skip_css_validation,
):
    config = Config(config_file)
    config.setup_logging()

    logger = verboselogs.VerboseLogger("validate")

    try:
        logger.info(f"Validating Stylesheet.")
        data = StylesheetData(
            subreddit_name=None,
            css_file=css_file,
            data_page_name=None,
            revision_comment=None,
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

        logger.info("Mapping images:")
        builder.map_images()
        logger.verbose(f"Mapped {len(data.local_images.new)} images")

        logger.info("Adapting CSS:")
        builder.adapt()
        logger.verbose(f"Adapted CSS size: {assets.adapted_css_size} bytes")

        logger.info("Validating CSS:")
        builder.validate_css(skip_css_validation)
        logger.verbose("CSS has been validated")

        logger.info("Validation completed successfully.")

    except StylesheetException as error:
        show_traceback = logger.getEffectiveLevel() == logging.DEBUG
        logger.error(f"Validation procedure failed: {error}",
                     exc_info=show_traceback)
        exit(1)
    except Exception as error:
        logger.error(f"An unexpected error has occurred.", exc_info=True)
        exit(1)


if __name__ == '__main__':
    main()

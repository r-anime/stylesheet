# Contributing

Hi there! Interested in contributing to /r/anime's theme? We appreciate the help, but there are a few things to keep in mind:

## Issues

- Include screenshots if you're reporting a visual bug or other discrepancy.
- List any browser extensions you're using to make our lives easier when debugging.

## Pull requests

- When submitting pull requests for new features or significant changes, open an issue first so we can talk about it. They'll have to be discussed by the mod team and likely voted on internally before we merge or close. These types of contributins can take a while.
- Test your change by building the stylesheet locally and applying it to a Reddit page to ensure that everything works as expected.
- When a PR is merged, it'll be immediately pushed live to the subreddit. Check the Actions tab in Github for build and deploy status.

## Project structure overview

The stylesheet's entry point is the `main.scss` file in the project root, and it contains nothing but imports. Most of the actual stylesheet code lives in the `src` directory, with a couple files in the root directory for commonly-changed customization options. The `src/util` directory has utilities mostly used by the comment face code.

The `images` directory is where images referenced by the stylesheet live. To reference images in here from code, use `url("images/FILENAME")`. Note that the name of this directory and the image reference format aren't real path specifiers, they're hardcoded - you can't make another directory outside `images` and reference it from code right now.

The `util` directory holds the Python code for building and uploading the stylesheet. The Github Actions definition in `.github/workflows` runs various scripts from that directory. Note that currently, building the stylesheet requires Reddit API credentials, so for testing purposes it's generally easier to use another tool for building and testing changes, e.g. the official Sass CLI. In the future this will hopefully not be the case.

## Build process

The rough outline of the build step is something like this:

- Build Sass to CSS
- Scan CSS for image references
- Map image references in code to image files on disk
- Check Reddit for any required files that already exist on the target subreddit, using a wiki page to store and track file hashes, etc.
- Shorten the names of all images that need to be uploaded

Once the build is done, all the relevant files can be pushed to Reddit.

(TODO: document this better when the deploy script is reworked)

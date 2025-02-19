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

Images are referenced in the stylesheet using a custom Sass function `i`, which is used like `i("images/sidebar.png")`. The path points to the image file you want to use, including file extension, and is interpreted relative to the repository root. The function also accepts optional `$width` and `$height` arguments which can be used to indicate the desired image size in either dimensions; if you use these arguments, the build script will scale the given image to fit within those dimensions before uploading it to the subreddit.

The `build` directory holds the Node script for building and uploading the stylesheet, which can be run with `npm run build`. By default, without any credentials, it will compile the stylesheet and spit it out in the `out` directory, alongside all the transformed images it referenced - this is useful for debugging.

If you want to actually deploy your local copy to a subreddit to test it live, you'll need a script-type OAuth application from https://www.reddit.com/prefs/apps. Set the environment variables `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USERNAME`, `REDDIT_PASSWORD`, and if necessary, `REDDIT_TOTP_SECRET`. Then, pass the `--deploy-to-subreddit="YOUR_SUB"` flag to have the script attempt to upload the stylesheet to that subreddit. Note that when running in this mode, the script will assume that it's the _only thing_ that will ever modify the images on your subreddit, and it will keep a record of the images it's saved in the `stylesheet/data` wiki page on the subreddit. It may not cooperate if you have existing images in the subreddit or if the image list gets out of sync. If you're having persistent issues, try manually deleting all the images from your sub via https://old.reddit.com/r/YOUR_SUB/about/stylesheet, emptying the `stylesheet/data` wiki page, and rerunning the script.

The Github Actions definition in `.github/workflows` run the build script every time changes are pushed to the repository. Any time the `main` branch is updated, those changes get pushed to /r/anime; changes on other branches within the organization get pushed to /r/animestaging. Changes in pull requests from outside the /r/anime organization won't get pushed anywhere.

# this-is-a-repo [![Build Status](https://travis-ci.org/Geo1088/this-is-a-repo.svg?branch=master)](https://travis-ci.org/Geo1088/this-is-a-repo)

## To use

- Copy `.update` into your repo
- Rename `.update/config.sample.json` to `.update/config.json` and fill it out with your information.
- `$ travis encrypt-file .update/config.json .update/config.json.enc`
- Paste the resulting command into `.travis.yml` in the `before_install` section
- If you want, change the deployment branch from `.travis.yml`
- Edit `main.scss`
- Commit and push to GitHub

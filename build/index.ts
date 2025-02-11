import {mkdir, stat} from 'node:fs/promises';
import {dirname, join} from 'node:path';

import * as sass from 'sass';
import jsonImporter from 'sass-importer-json';

import {LocalBackend} from './backend/LocalBackend';
import {RedditBackend} from './backend/RedditBackend';
import {StylesheetUploadBackend} from './backend/StorageBackend';
import {Image} from './Image';

const thisFolderPath = dirname(new URL(import.meta.url).pathname);
const repoRootPath = join(thisFolderPath, '..');

const sassEntryFilePath = join(repoRootPath, 'main.scss');

const backend: StylesheetUploadBackend = process.env.NODE_ENV === 'production'
	? await RedditBackend({
		auth: {
			userAgent: process.env['REDDIT_USER_AGENT']!,
			clientId: process.env['REDDIT_CLIENT_ID'],
			clientSecret: process.env['REDDIT_CLIENT_SECRET'],
			username: process.env['REDDIT_USERNAME'],
			password: process.env['REDDIT_PASSWORD'],
		},
		subreddit: process.env['REDDIT_SUBREDDIT']!,
	})
	: LocalBackend(join(repoRootPath, 'out'));

// compile CSS
const output = await sass.compileAsync(sassEntryFilePath, {
	importers: [jsonImporter()],
	functions: {
		// Custom Sass function which defines a reference to an image.
		async 'i($path, $width: null, $height: null)' ([pathArg, widthArg, heightArg]) {
			const path = pathArg.assertString('path').text;
			const width = widthArg.realNull?.assertNumber('width').assertNoUnits('width').assertInt('width')
				?? undefined;
			const height = heightArg.realNull?.assertNumber('height').assertNoUnits('height').assertInt('height')
				?? undefined;

			// Get our `Image` instance, where all our information comes from
			const image = Image.from(path, {width, height});

			// Replace this call with an appropriate `url()` call (yeah
			// apparently `url()` invocations in Sass are just unquoted strings)
			return new sass.SassString(`url(%%${await backend.mapImageName(image)}%%)`, {quotes: false});
		},
	},
	style: 'compressed',
});

await backend.uploadBuild(output.css, Image.collect());

import {dirname, join} from 'node:path';

import * as sass from 'sass';
import jsonImporter from 'sass-importer-json';

import {LocalBackend} from './backend/LocalBackend';
import {RedditBackend} from './backend/RedditBackend';
import {type StylesheetUploadBackend} from './backend/StylesheetUploadBackend';
import {Image} from './Image';

const thisFolderPath = dirname(new URL(import.meta.url).pathname);
export const repoRootPath = join(thisFolderPath, '..');

// If wehave all the details, we'll actually send the stylesheet to Reddit; if
// not we'll just compile the stylesheet and then write our state to disk
const backend = process.env['REDDIT_SUBREDDIT']
	? await RedditBackend({
		auth: {
			userAgent: process.env['REDDIT_USER_AGENT']!,
			clientId: process.env['REDDIT_CLIENT_ID'],
			clientSecret: process.env['REDDIT_CLIENT_SECRET'],
			username: process.env['REDDIT_USERNAME'],
			password: process.env['REDDIT_PASSWORD'],
		},
		subreddit: process.env['REDDIT_SUBREDDIT'],
	})
	: LocalBackend(join(repoRootPath, 'out'));

// compile CSS
console.group('Compiling CSS...');
const output = await sass.compileAsync(join(repoRootPath, 'main.scss'), {
	importers: [jsonImporter()],
	functions: {
		// Custom Sass function which defines a reference to an image.
		async 'i($path, $width: null, $height: null)' ([pathArg, widthArg, heightArg]) {
			const path = pathArg
				.assertString('path')
				.text;
			const width = widthArg
				.realNull
				?.assertNumber('width')
				.assertNoUnits('width')
				.assertInt('width')
				?? undefined;
			const height = heightArg
				.realNull
				?.assertNumber('height')
				.assertNoUnits('height')
				.assertInt('height')
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
console.log('+ Done');
console.groupEnd();

// We have the stylesheet and its images - let's do something with it
await backend.uploadBuild(output.css, Image.collect());

import {dirname, join} from 'node:path';

import minimist from 'minimist';
import * as sass from 'sass';
import jsonImporter from 'sass-importer-json';

import {LocalBackend} from './backend/LocalBackend';
import {RedditBackend} from './backend/RedditBackend';
import {Image} from './Image';

const argv = minimist(process.argv.slice(2), {
	string: ['deploy-to-subreddit', 'reason'],
});

const thisFolderPath = dirname(new URL(import.meta.url).pathname);
export const repoRootPath = join(thisFolderPath, '..');

// If wehave all the details, we'll actually send the stylesheet to Reddit; if
// not we'll just compile the stylesheet and then write our state to disk
const backend = argv['deploy-to-subreddit']
	? new RedditBackend(
		{
			clientID: process.env['REDDIT_CLIENT_ID']!,
			clientSecret: process.env['REDDIT_CLIENT_SECRET']!,
			username: process.env['REDDIT_USERNAME']!,
			password: process.env['REDDIT_PASSWORD']!,
			totpSecret: process.env['REDDIT_TOTP_SECRET'],
		},
		process.env['REDDIT_USER_AGENT']!,
		argv['deploy-to-subreddit'],
		argv['reason'],
	)
	: LocalBackend(join(repoRootPath, 'out'));

// compile CSS
console.group('Compiling CSS...');
let output: sass.CompileResult;
try {
	output = await sass.compileAsync(join(repoRootPath, 'main.scss'), {
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

				// Replace this call with an appropriate `url()` (yep apparently
				// `url()` invocations in Sass are just unquoted strings)
				return new sass.SassString(`url(%%${await backend.mapImageName(image)}%%)`, {quotes: false});
			},
		},
		style: 'compressed',
	});
} catch (error) {
	console.group('! Sass compilation error:');
	console.log(error.message);
	process.exit(1);
}
console.groupEnd();

let css = output.css;
if (process.env['SECRET_CSS']) {
	css += "\n" + process.env['SECRET_CSS'];
}

// We have the stylesheet and its images - let's do something with it
try {
	await backend.uploadBuild(css, Image.collect());
} catch (error) {
	// If something fails, make sure we return non-zero for CI purposes
	process.exit(1);
}

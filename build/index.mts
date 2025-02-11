import {writeFile} from 'node:fs/promises';
import * as path from 'node:path';

import * as sass from 'sass';
import jsonImporter from 'sass-importer-json';

import {Image} from './Image.mts';
import {deleteCachedData, setCachedData} from './ImageCache.mts';
import {
	assignNameForImageKey,
	getSubredditImageData,
	SubredditImageData,
	writeSubredditImageData,
} from './subredditData.mts';

const repoRootPath = path.join(path.dirname(new URL(import.meta.url).pathname), '..');
const sassEntryFilePath = path.join(repoRootPath, 'main.scss');
const cssOutputFilePath = path.join(repoRootPath, 'test_out.css');

// Figure out what images already existed on the subreddit to begin with
const existingSubredditImageData = await getSubredditImageData('the_subreddit');
// Clone that object so we can make our own changes
const newSubredditImageData: SubredditImageData = JSON.parse(JSON.stringify(existingSubredditImageData));

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

			// Assign the image's final name based on what other images are
			// already on the subreddit according to the data we pulled
			const key = await image.getImageKey();
			const finalName = assignNameForImageKey(newSubredditImageData, key);

			// Replace this call with an appropriate `url()` call (yeah
			// apparently `url()` invocations in Sass are just unquoted strings)
			return new sass.SassString(`url(%%${finalName}%%)`, {quotes: false});
		},
	},
	// style: 'compressed',
});

// The CSS is done!
console.group('CSS Output:');
await writeFile(cssOutputFilePath, output.css);
console.log(path.relative(repoRootPath, sassEntryFilePath), '->', path.relative(repoRootPath, cssOutputFilePath));
console.groupEnd();

// Now we just have to draw the rest of the fucking owl
console.group('Resolving image changes...');

// Collect all the images referenced from the current stylesheet
const allImages = await Promise.all(
	Image.collect()
		.map(async image => {
			// tack on the cache key too because it's useful
			const key = await image.getImageKey();
			return {image, key};
		}),
);

// Prune old images from the subreddit
await Promise.all(
	// Images we knew about before
	Object.entries(existingSubredditImageData)
		// Filter to only those not appearing in the current set
		.filter(([key]) => !allImages.some(newImage => key === newImage.key))
		// Remove all of these
		.map(async ([key, imageName]) => {
			console.log('-', key, imageName);
			delete newSubredditImageData[key];
			await deleteCachedData(imageName);
			// TODO: actually remove from the subreddit
		}),
);

// Upload new images to the subreddit
await Promise.all(
	allImages
		// Filter out images that we knew about before
		.filter(({key}) => !existingSubredditImageData[key])
		.map(async ({key, image}) => {
			let imageName = newSubredditImageData[key];
			if (!imageName) {
				// something has gone horribly wrong
				throw new Error(`Image ${image.name} was not assigned a final name somehow`);
			}

			let imageData: Buffer;
			try {
				imageData = await image.getFinalData();
			} catch (error) {
				throw new Error(`Failed to finalize image "${image.name}"`, {cause: error});
			}

			// TODO: do something with [imageName, finalData]
			setCachedData(imageName, imageData);

			console.log('+', key, imageName, '<-', image.name);
		}),
);
console.groupEnd();

console.log('Writing back image metadata...');
await writeSubredditImageData('the_subreddit', newSubredditImageData);

console.log('\nDone!');

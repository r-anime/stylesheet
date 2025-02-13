import {writeFile} from 'node:fs/promises';

import {base62} from '../util/base62';
import {doInParallel} from '../util/parallelTask';
import {RedditAPIClient, type RedditAuthOptions} from '../util/RedditAPIClient';
import {StylesheetUploadBackend} from './StylesheetUploadBackend';

// Map of cache keys to subreddit image names.
export type SubredditImageData = Record<string, string>;

const IMAGE_DATA_WIKI_PAGE = 'stylesheet/data';

export async function RedditBackend ({auth, userAgent, subreddit}: {
	auth: RedditAuthOptions;
	userAgent: string;
	subreddit: string;
}) {
	const apiClient = new RedditAPIClient(auth, userAgent);

	console.group('Retrieving image data...');
	let oldImageData: SubredditImageData;
	try {
		const imageDataJson = await apiClient.getWikiPageContent(subreddit, IMAGE_DATA_WIKI_PAGE);
		if (imageDataJson === '') {
			throw new Error('Wiki page exists but has empty content');
		}
		oldImageData = JSON.parse(imageDataJson);
	} catch (error) {
		console.warn(
			'! Failed to get image data; starting from scratch; this may cause upload errors if there are existing '
				+ 'images we don\'t know about'
				+ '\n ',
			error,
		);
		oldImageData = {};
	}
	console.groupEnd();

	let newImageData: SubredditImageData = JSON.parse(JSON.stringify(oldImageData));

	return {
		async mapImageName (image) {
			const key = await image.getImageKey();
			if (newImageData[key]) {
				return newImageData[key];
			}

			// find the next available name
			const usedNames = Object.values(newImageData);
			let i = 0;
			let nextName: string;
			do {
				nextName = base62(i);

				i += 1;
			} while (usedNames.includes(nextName));

			newImageData[key] = nextName;
			return nextName;
		},
		async uploadBuild (css, images) {
			// im sorry for my crimes @nex3 but reddit doesnt allow us to use
			// either @charset or a BOM in the styles we upload so we're just
			// rawdogging the encoding crimes here. see sass/sass#1395 and
			// sass/dart-sass#568 to learn why this is a bad idea
			if (css.charCodeAt(0) === 0xFEFF) {
				css = css.slice(1);
			}

			console.group('Resolving modified images...');

			// Make sure we're below the limit for total images
			if (images.length > 50) {
				console.error(`! Stylesheet references too many distinct images (max 50, currently ${images.length})`);
				throw new Error(`Too many images: ${images.length}`);
			}

			// Get a list of all the images we referenced from the stylesheet,
			// and also fetch their keys while we're here so we can reference
			// the subreddit image data synchronously
			const allImages = await Promise.all(images.map(async image => {
				// tack on the cache key too because it's useful
				const key = await image.getImageKey();
				return {image, key};
			}));

			// Get only the images that we haven't already uploaded
			const newImages = allImages.filter(({key}) => !oldImageData[key]);

			// Finalize new images - resize, compress, map names
			const finalizedImages = await doInParallel(newImages.map(async ({key, image}) => {
				try {
					return {
						key,
						image,
						name: await this.mapImageName(image),
						data: await image.getFinalData(),
					};
				} catch (error) {
					console.error('! Failed to transform image', image.name, '\n ', error);
					throw new Error(`Failed to transform image "${image.name}"`, {cause: error});
				}
			}));

			// Prune old images from the subreddit
			const oldImages = Object.entries(oldImageData)
				// Filter to only those not appearing in the current set
				.filter(([key]) => !allImages.some(newImage => key === newImage.key));
			await doInParallel(oldImages.map(async ([key, imageName]) => {
				try {
					delete newImageData[key];
					await apiClient.deleteImage(subreddit, imageName);
					console.log('-', key, imageName);
				} catch (error) {
					console.error('!', key, imageName, '\n  Failed to delete old image:', error);
					throw new Error(`Failed to delete old image "${imageName}"`, {cause: error});
				}
			}));

			// Upload new images to the subreddit
			await doInParallel(finalizedImages.map(async ({key, image, name, data}) => {
				// attempt to delete the image's name before uploading, just in
				// case - we don't care if this fails or does nothing
				try {
					await apiClient.deleteImage(subreddit, name);
				} catch {}

				// upload the image
				try {
					await apiClient.uploadImage(subreddit, name, data);
					console.log('+', key, name, '<-', image.name);
				} catch (error) {
					console.warn('!', key, name, '<-', image.name, '\n  Failed to upload:', error);
					throw new Error(`Failed to upload image "${image.name}" as "${name}"`, {
						cause: error,
					});
				}
			}));

			await console.groupEnd();

			console.group('Writing CSS...');
			try {
				await apiClient.updateStylesheet(subreddit, css, 'beep boop');
				console.log(`+ /r/${subreddit}/config/stylesheet`);
			} catch (error) {
				console.error('! Failed to write stylesheet\n ', error);
				// TODO: do something more permanent here
				await writeFile('failed.css', css);
			}
			console.groupEnd();

			console.group('Writing back image data...');
			try {
				await apiClient.updateWikiPage(
					subreddit,
					IMAGE_DATA_WIKI_PAGE,
					JSON.stringify(newImageData, null, '\t'),
					'update image data',
				);
				console.log(`+ /r/${subreddit}/wiki/stylesheet/data`);
			} catch (error) {
				console.error('! Failed to write image data\n ', error);
				throw new Error('Failed to write image data', {cause: error});
			}
			console.groupEnd();
		},
	} satisfies StylesheetUploadBackend;
}

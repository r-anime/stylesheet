import {writeFile} from 'node:fs/promises';

import {Image} from '../Image';
import {base62} from '../util/base62';
import {doInParallel} from '../util/doInParallel';
import {memoize} from '../util/memoize';
import {RedditAPIClient, type RedditAuthOptions} from '../util/RedditAPIClient';
import {StylesheetUploadBackend} from './StylesheetUploadBackend';

/** Map of image keys to subreddit image names. */
export type SubredditImageData = Record<string, string>;

/** The name of the wiki page where image data is persisted across runs. */
const IMAGE_DATA_WIKI_PAGE = 'stylesheet/data';

/**
 * Backend that uploads compiled CSS and associated images to a subreddit's
 * stylesheet.
 */
export class RedditBackend implements StylesheetUploadBackend {
	private apiClient: RedditAPIClient;

	private oldImageData: SubredditImageData;
	private newImageData: SubredditImageData;

	constructor (
		auth: RedditAuthOptions,
		userAgent: string,
		public subreddit: string,
	) {
		this.apiClient = new RedditAPIClient(auth, userAgent);
	}

	/**
	 * Gets stored image data from the target subreddit, so we can know which
	 * images are already present and what their names are.
	 */
	@memoize
	private async getImageData () {
		console.group('Retrieving image data...');
		try {
			const imageDataJson = await this.apiClient.getWikiPageContent(this.subreddit, IMAGE_DATA_WIKI_PAGE);
			if (imageDataJson === '') {
				throw new Error('Wiki page exists but has empty content');
			}
			this.oldImageData = JSON.parse(imageDataJson);
		} catch (error) {
			console.warn(
				'! Failed to get image data; starting from scratch; this may cause upload errors if there are existing '
					+ 'images we don\'t know about'
					+ '\n ',
				error,
			);
			this.oldImageData = {};
		}
		this.newImageData = JSON.parse(JSON.stringify(this.oldImageData));
		console.groupEnd();
	}

	/**
	 * Maps an image named in the stylesheet to the name it will use when
	 * uploaded to the subreddit.
	 */
	async mapImageName (image: Image) {
		// ensure we have image data
		await this.getImageData();

		const key = await image.getImageKey();
		if (this.newImageData[key]) {
			return this.newImageData[key];
		}

		// find the next available name
		const usedNames = Object.values(this.newImageData);
		let i = 0;
		let nextName: string;
		do {
			nextName = base62(i);

			i += 1;
		} while (usedNames.includes(nextName));

		this.newImageData[key] = nextName;
		return nextName;
	}

	async uploadBuild (css: string, images: Image[]) {
		console.group('Resolving modified images...');

		// Make sure we're below the limit for total images
		if (images.length > 50) {
			console.error(
				`! Stylesheet references too many distinct images (max 50, currently ${images.length})`,
			);
			throw new Error(`Too many images: ${images.length}`);
		}

		// Get a list of all the images we referenced from the stylesheet,
		// and also fetch their keys while we're here so we can reference
		// the subreddit image data synchronously
		const allImages = await Promise.all(images.map(async image => ({image, key: await image.getImageKey()})));

		// Get only the images that we haven't already uploaded
		const newImages = allImages.filter(({key}) => !this.oldImageData[key]);

		// Finalize those new images - resize, compress, map names
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

		// Get images from the map which are unused by the new stylesheet
		const unusedImages = Object.entries(this.oldImageData)
			.filter(([key]) => !allImages.some(newImage => key === newImage.key));

		// Delete these since we no longer need them
		await doInParallel(unusedImages.map(async ([key, imageName]) => {
			try {
				delete this.newImageData[key];
				await this.apiClient.deleteImage(this.subreddit, imageName);
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
				await this.apiClient.deleteImage(this.subreddit, name);
			} catch {}

			// upload the image
			try {
				await this.apiClient.uploadImage(this.subreddit, name, data);
				console.log('+', key, name, '<-', image.name);
			} catch (error) {
				console.warn('!', key, name, '<-', image.name, '\n  Failed to upload:', error);
				throw new Error(`Failed to upload image "${image.name}" as "${name}"`, {
					cause: error,
				});
			}
		}));

		await console.groupEnd();

		// Now that all the referenced images are present, we can update the CSS
		console.group('Writing CSS...');
		try {
			await this.apiClient.updateStylesheet(this.subreddit, css, 'beep boop');
			console.log(`+ /r/${this.subreddit}/config/stylesheet`);
		} catch (error) {
			console.error('! Failed to write stylesheet\n ', error);
			// TODO: do something more permanent here
			await writeFile('failed.css', css);
		}
		console.groupEnd();

		// Persist the image data so we can work with it next time
		console.group('Writing back image data...');
		try {
			await this.apiClient.updateWikiPage(
				this.subreddit,
				IMAGE_DATA_WIKI_PAGE,
				JSON.stringify(this.newImageData, null, '\t'),
				'update image data',
			);
			console.log(`+ /r/${this.subreddit}/wiki/stylesheet/data`);
		} catch (error) {
			console.error('! Failed to write image data\n ', error);
			throw new Error('Failed to write image data', {cause: error});
		}
		console.groupEnd();
	}
}

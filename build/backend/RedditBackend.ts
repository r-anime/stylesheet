import {default as Snoowrap, SnoowrapOptions} from 'snoowrap';

import {writeFile} from 'node:fs/promises';
import {base62} from '../util/base62';
import {StylesheetUploadBackend} from './StorageBackend';

// Map of cache keys to subreddit image names.
export type SubredditImageData = Record<string, string>;

export async function RedditBackend ({
	auth: authOptions,
	subreddit: subredditName,
}: {
	auth: SnoowrapOptions;
	subreddit: string;
}) {
	const reddit = new Snoowrap(authOptions);
	const subreddit = reddit.getSubreddit(subredditName);
	const imageDataWikiPage = subreddit.getWikiPage('stylesheet/data');

	let oldImageData: SubredditImageData;
	try {
		const imageDataJson = await (imageDataWikiPage.content_md as unknown as Promise<string>); // AAAAA
		oldImageData = JSON.parse(imageDataJson);
	} catch (error) {
		if (error.error.reason === 'PAGE_NOT_CREATED') {
			await (imageDataWikiPage.edit({
				text: '{}',
				reason: 'beeeeeeeep',
			}) as unknown as Promise<void>);
		}
		oldImageData = {};
	}

	let newImageData: SubredditImageData = JSON.parse(JSON.stringify(oldImageData));

	// await new Promise(resolve => setTimeout(resolve, 50000));

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

			// we're just stealing this from snoowrap until i implement my own
			const accessToken = reddit.accessToken;

			console.group('Resolving modified images...');
			const allImages = await Promise.all(images.map(async image => {
				// tack on the cache key too because it's useful
				const key = await image.getImageKey();
				return {image, key};
			}));

			// Prune old images from the subreddit
			await Promise.all(
				// Images we knew about before
				Object.entries(oldImageData)
					// Filter to only those not appearing in the current set
					.filter(([key]) => !allImages.some(newImage => key === newImage.key))
					// Remove all of these
					.map(async ([key, imageName]) => {
						delete newImageData[key];
						await (subreddit.deleteImage({
							imageName,
						}) as unknown as Promise<void>); // AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAa
						console.log('-', key, imageName);
					}),
			);

			// Upload new images to the subreddit
			await Promise.all(
				allImages
					// Filter out images that we knew about before
					.filter(({key}) => !oldImageData[key])
					.map(async ({key, image}) => {
						let mappedName = await this.mapImageName(image);
						if (!mappedName) {
							// something has gone horribly wrong
							throw new Error(`Image ${image.name} was not assigned a final name somehow`);
						}

						let finalData: Buffer;
						try {
							finalData = await image.getFinalData();
						} catch (error) {
							throw new Error(`Failed to finalize image "${image.name}"`, {cause: error});
						}

						try {
							// doesnt work
							// await (subreddit.uploadStylesheetImage({
							// 	name: mappedName,
							// 	file: stream.Readable.from(finalData) as unknown as ReadableStream, // AAAAAAAAAAAAAA
							// 	imageType: 'jpg', // TODO
							//  }) as unknown as Promise<void>); // AAAAAAAAAAAAAAAAAAAAAAAA

							// HACK: FUCK IT. I DONT CARE. ILL WRITE THE GODDAMN REQUEST MYSELF YOU PIECE OF SHIT
							// await reddit.updateAccessToken();
							const body = new FormData();
							body.set('name', mappedName);
							body.set('imageType', 'jpg');
							body.set('file', new Blob([finalData]));
							const response = await fetch(
								`https://oauth.reddit.com/r/${subredditName}/api/upload_sr_img`,
								{
									method: 'POST',
									headers: {
										Authorization: `bearer ${accessToken}`,
									},
									body,
								},
							);
							if (response.status !== 200) {
								throw new Error(`Bad response code ${response.status}`);
							}
							const responseData = await response.json();
							if (responseData.errors && responseData.errors.length) {
								throw new AggregateError(responseData.errors);
							}
							console.log('+', key, mappedName, '<-', image.name);
						} catch (error) {
							console.warn(
								'!',
								key,
								mappedName,
								'<-',
								image.name,
								'\n ',
								'Error uploading image:',
								error.error || error.errors || error, // idek
							);
						}
					}),
			);
			console.groupEnd();

			console.group('Writing CSS...');
			try {
				// also doesnt work
				// await (subreddit.updateStylesheet({
				// 	css,
				// 	reason: 'beep boop',
				// }) as unknown as Promise<void>); //
				// aAAAAAAAAaaAAaAAaaaaAaaaAAaaaAAAaAaAAaAAaA
				const response = await fetch(
					`https://oauth.reddit.com/r/${subredditName}/api/subreddit_stylesheet?raw_json=1`,
					{
						method: 'POST',
						headers: {
							'Authorization': `bearer ${accessToken}`,
							'Content-Type': 'application/x-www-form-urlencoded',
						},
						body: new URLSearchParams({
							api_type: 'json',
							op: 'save',
							reason: 'beep boop',
							stylesheet_contents: css,
						}),
					},
				);
				if (response.status !== 200) {
					throw new Error(`bad response status ${response.status}`);
				}
				const responseData = await response.json();
				if (responseData.json.errors && responseData.json.errors.length) {
					throw new AggregateError(responseData.json.errors);
				}
				console.log(`+ /r/${subredditName}/config/stylesheet`);
			} catch (error) {
				console.error('! Failed to write stylesheet:', error);
				// TODO: do something more permanent here
				await writeFile('failed.css', css);
			}
			console.groupEnd();

			console.group('Writing back image data...');
			await (imageDataWikiPage.edit({
				text: JSON.stringify(newImageData, null, '\t'),
				reason: 'update image data',
			}) as unknown as Promise<void>); // AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
			console.log(`+ /r/${subredditName}/wiki/stylesheet/data`);
			console.groupEnd();

			console.log('All done.');
		},
	} satisfies StylesheetUploadBackend;
}

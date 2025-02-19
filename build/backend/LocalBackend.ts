import {mkdir, rm, stat, writeFile} from 'node:fs/promises';
import {dirname, join, relative} from 'node:path';

import {repoRootPath} from '..';
import {Image} from '../Image';
import {doInParallel} from '../util/doInParallel';
import {StylesheetUploadBackend} from './StylesheetUploadBackend';

// The mapped image names might have slashes, so here's a poor girl's `mkdir -p`
async function writeFileInQuestionableTree (path: string, data: Buffer) {
	await mkdir(dirname(path), {recursive: true});
	return writeFile(path, data);
}

/** Backend that dumps all the generated files to a folder for debugging. */
export const LocalBackend = (path: string): StylesheetUploadBackend => ({
	// Don't touch image names
	mapImageName: (image: Image) => Promise.resolve(image.name),
	// Write everything we have to a directory
	async uploadBuild (css, images) {
		// Clear out the folder if it already exists and then recreate it
		try {
			await rm(path, {recursive: true});
		} catch {}
		await mkdir(path);

		console.group('Writing state out to files...');
		await doInParallel([
			// Dump all the images
			...images.map(async image => {
				const mappedName = await this.mapImageName(image);
				await writeFileInQuestionableTree(join(path, mappedName), await image.getFinalData());
				console.log('+', join(relative(repoRootPath, path), mappedName));
			}),
			// Dump the CSS file at the same time
			(async () => {
				await writeFile(join(path, 'out.css'), css, 'utf8');
				console.log('+', join(relative(repoRootPath, path), 'out.css'));
			})(),
		]);
		console.groupEnd();
		console.log('All done.');
	},
});

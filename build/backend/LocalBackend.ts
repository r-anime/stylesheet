import {mkdir, rm, stat, writeFile} from 'node:fs/promises';
import {dirname, join, relative} from 'node:path';

import {repoRootPath} from '..';
import {Image} from '../Image';
import {StylesheetUploadBackend} from './StylesheetUploadBackend';

/** This backend's mapped filenames might have slashes, so... */
async function writeFileInQuestionableTree (path: string, data: Buffer) {
	await mkdir(dirname(path), {recursive: true});
	return writeFile(path, data);
}

export const LocalBackend = (path: string): StylesheetUploadBackend => ({
	async mapImageName (image: Image) {
		return image.name;
	},
	async uploadBuild (css, images) {
		try {
			await rm(path, {recursive: true});
		} catch {}
		await mkdir(path);

		console.group('Writing state out to files...');
		await Promise.all(
			images.map(async image => {
				const mappedName = await this.mapImageName(image);
				await writeFileInQuestionableTree(
					join(path, mappedName),
					await image.getFinalData(),
				);
				console.log('+', join(relative(repoRootPath, path), mappedName));
			}).concat([
				writeFile(
					join(path, 'out.css'),
					css,
					'utf8',
				).then(() => {
					console.log('+', join(relative(repoRootPath, path), 'out.css'));
				}),
			]),
		);
		console.groupEnd();
		console.log('All done.');
	},
});

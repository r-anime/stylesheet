import {mkdir, rm, stat, writeFile} from 'node:fs/promises';
import {dirname, join} from 'node:path';

import {Image} from '../Image';
import {StylesheetUploadBackend} from './StorageBackend';

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
		await Promise.all(
			images.map(async image =>
				writeFileInQuestionableTree(
					join(path, await this.mapImageName(image)),
					await image.getFinalData(),
				)
			).concat([
				writeFile(
					join(path, 'out.css'),
					css,
					'utf8',
				),
			]),
		);
	},
});

import * as path from 'node:path';

import {mkdir, readFile, rm, stat, writeFile} from 'node:fs/promises';

/** Folder where final images are stored for future runs */
// TODO: integrate this with the GHA cache somehow
export const cacheFolderPath = path.join(new URL(import.meta.url).pathname, '../../out');

// Ensure the image cache folder exists
try {
	await stat(cacheFolderPath);
} catch (error) {
	await mkdir(cacheFolderPath);
}

const cacheFilePath = key => path.join(cacheFolderPath, `${key}.jpg`)

export async function getCachedData(key: string) {
	const path = cacheFilePath(key);
	try {
		let statResult = await stat(path);
		if (!statResult.isFile) throw new Error('here but not a file??');
	} catch (error) {
		return null;
	}
	return readFile(path);
}

export async function setCachedData(key: string, data: Buffer) {
	const path = cacheFilePath(key);
	await writeFile(path, data);
}

export async function deleteCachedData(key: string) {
	try {
		await rm(cacheFilePath(key), {recursive: true});
	} catch {}
}

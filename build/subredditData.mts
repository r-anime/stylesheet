import {readFile, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {cacheFolderPath} from './ImageCache.mts';

// Map of cache keys to subreddit image names.
export type SubredditImageData = Record<string, string>;

export async function getSubredditImageData (subreddit: string): Promise<SubredditImageData> {
	let contents;
	try {
		contents = await readFile(path.join(cacheFolderPath, `${subreddit}-data.json`), 'utf8');
	} catch {
		return {};
	}
	return JSON.parse(contents);
}

export async function writeSubredditImageData (subreddit: string, data: SubredditImageData) {
	await writeFile(path.join(cacheFolderPath, `${subreddit}-data.json`), JSON.stringify(data, null, '\t'), 'utf8');
}

// the cool thing about base62 is that it's totally unreadable. however it *is*
// nice that it allows us to map more than 50 images cleanly - as long as 12 or
// fewer images change during each commit, we'll never even have to dip into
// double-letter image names! >:3
const base62chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';
function base62 (n, base = 62) {
	let leastSignificant = n % base;
	let rest = Math.floor(n / base);
	return `${rest == 0 ? '' : base62(rest, base)}${base62chars[leastSignificant]}`;
}

/**
 * Assigns the given image key a canonical subreddit image name that's not
 * currently in use by any other image. Mutates the passed `subredditData`
 * object to add the new image key and name to the record.
 */
export function assignNameForImageKey (subredditData: SubredditImageData, key: string) {
	if (subredditData[key]) {
		return subredditData[key];
	}

	// find the next available name
	const usedNames = Object.values(subredditData);
	let i = 0;
	let nextName: string;
	do {
		nextName = base62(i);
		i += 1;
	} while (usedNames.includes(nextName));

	subredditData[key] = nextName;
	return nextName;
}

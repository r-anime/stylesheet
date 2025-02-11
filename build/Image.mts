import {createHash, type BinaryLike} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import path from 'node:path';

import sharp from 'sharp';

/** Computes the hex sha1sum of the given data. */
function sha1sum(buf: BinaryLike) {
	const hash = createHash('sha1');
	hash.update(buf);
	return hash.digest('hex');
}

/**
 * Finds the highest JPEG quality setting for a given image that keeps it under
 * the given byte size, and returns the resulting image data.
 */
async function autoCompress(imageData: Buffer, thresholdBytes: number) {
	// Skip all this if we don't need to change anything
	if (imageData.byteLength <= thresholdBytes) {
		return imageData;
	}

	// jpeg quality is a number between 1 and 100 inclusive
	let min = 1;
	let max = 100;

	// This is read once, where it just needs to not compare equal to `newMid`,
	// before immediately being assigned a normal number value, trust
	let mid: number = undefined as any;
	// These values are always set to something else before they're read, trust
	let newImageData: Buffer = undefined as any;
	let newImageSize: number = undefined as any;
	while (true) {
		let newMid = Math.floor((max - min + 1) / 2) + min;
		// If we're checking the same value again, we have nowhere else to go
		if (newMid === mid) {
			break;
		}
		mid = newMid;

		// Reload image, set new quality and write out to buffer
		newImageData = await sharp(imageData).jpeg({quality: mid}).toBuffer();
		// Record the new compressed size
		newImageSize = newImageData.byteLength; // actually computes the score

		if (newImageSize <= thresholdBytes) {
			min = mid; // under the target is okay, keep that value
		} else if (newImageSize > thresholdBytes) {
			max = mid - 1; // over target is not okay, exclude this value
		}
	}

	if (newImageSize > thresholdBytes) {
		// there's no value that gives a size under the threshold
		throw new Error(`Can't compress enough; ${newImageSize} bytes at quality ${mid} (target <= ${thresholdBytes} bytes). This really shouldn't happen, yell at Erin, consider manually resizing the image to fix the issue in the meantime`);
	}

	return newImageData;
}

/**
 * An image referenced in the stylesheet by a call to the custom
 * `i($name, $width, $height)` Sass function.
 */
export class Image {
	/**
	 * The maximum number of bytes an image's final data can be. Image files
	 * larger than this are rejected by Reddit.
	 */
	static MAX_BYTE_SIZE = 512_000 - 500;

	/** Static register of all `Image` instances relevant to the stylesheet */
	static images: Record<string, Image> = Object.create(null);

	/**
	 * Gets an `Image` instance for the given image filename, with given target
	 * dimensions. If this image has already been referenced, the existing
	 * `Image` instance is returned - the dimensions must be the same across all
	 * references; as long as that's the case, all the references to the same
	 * image name will end up pointing at the same file.
	 */
	static from(name: string, targetDimensions: {width?: number; height?: number} = {}): Image {
		let existing = Image.images[name];
		if (existing) {
			if ((targetDimensions.width !== existing.targetDimensions.width || targetDimensions.height !== existing.targetDimensions.height)) {
				// two requests for the same image with differing dimensions - we
				// don't handle that
				throw new Error(`Multiple references to image "${name}" with differing target dimensions: ${targetDimensions}, ${existing.targetDimensions}`);
			}
			return existing;
		}

		let created = new Image(name, targetDimensions);
		Image.images[name] = created;
		return created;
	}

	/**
	 * Perform some action on all referenced images. To be called after the
	 * stylesheet is rendered so additional processing can occur for each
	 * selected image file.
	 */
	static collect() {
		return Object.values(Image.images);
	};

	/** The image's name. */
	get name () {return this.#name}
	#name: string;

	/**
	 * The dimensions requested for this image by the stylesheet. If the source
	 * image on disk is larger than these dimensions and needs to be compressed
	 * in order to meet the Reddit filesize limit, then the image will be
	 * scaled within these dimensions, to attempt to reduce its filesize
	 * without introducing JPEG compression artifacts.
	*/
	get targetDimensions () {return this.#targetDimensions}
	#targetDimensions: {width?: number; height?: number};

	private constructor (name: string, targetDimensions: {width?: number; height?: number} = {}) {
		this.#name = name;
		this.#targetDimensions = targetDimensions;
	}

	/** The fully-qualified path to this image's source file on disk. */
	get fullSourcePath () {
		// TODO
		return path.join(new URL(import.meta.url).pathname, '../..', this.name);
	}

	/** The contents of this image's source file on disk. */
	getSourceData () {
		if (!this.#sourceDataPromise) {
			this.#sourceDataPromise = this.#getSourceData();
		}
		return this.#sourceDataPromise;
	}
	#sourceDataPromise: Promise<Buffer> | null;
	#getSourceData () {
		return readFile(this.fullSourcePath)
	}

	/** SHA1 hash of this image's source file. */
	getSourceHash() {
		if (!this.#sourceHashPromise) {
			this.#sourceHashPromise = this.#getSourceHash();
		}
		return this.#sourceHashPromise
	}
	#sourceHashPromise: Promise<string> | null;
	async #getSourceHash () {
		return sha1sum(await this.getSourceData());
	}

	/**
	 * The key for this image. Computed from the source image's hash and the
	 * requested dimensions - if the contents of the file change, or if the file
	 * is used in a location where its expected size is different, the key will
	 * change and the image will be reuploaded to the subreddit.
	 */
	async getImageKey () {
		return `${
			await this.getSourceHash()
		}${
			this.targetDimensions?.width ? `_w${this.targetDimensions.width}` : ''
		}${
			this.targetDimensions?.height ? `_h${this.targetDimensions.height}` : ''
		}`;
	}

	/**
	 *
	 * @returns
	 */
	getFinalData () {
		if (!this.#finalDataPromise) {
			this.#finalDataPromise = this.#getFinalData();
		}
		return this.#finalDataPromise;
	}
	#finalDataPromise: Promise<Buffer> | null;
	async #getFinalData () {
		// Start with the source image
		let imageData = await this.getSourceData();

		// ensure image is within requested dimensions
		if (this.targetDimensions.width || this.targetDimensions.height) {
			imageData = await sharp(imageData)
				.resize({
					width: this.targetDimensions.width,
					height: this.targetDimensions.height,
					fit: 'inside',
					withoutEnlargement: true,
				})
				.toBuffer();
		}

		// ensure we're within the filesize limit
		return autoCompress(imageData, Image.MAX_BYTE_SIZE);
	}
}

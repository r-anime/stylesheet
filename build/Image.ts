import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import * as path from 'node:path';

import sharp from 'sharp';

import {autoCompress} from './util/autoCompress';

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
	static from (name: string, targetDimensions: {width?: number; height?: number} = {}): Image {
		let existing = Image.images[name];
		if (existing) {
			if (
				targetDimensions.width !== existing.targetDimensions.width
				|| targetDimensions.height !== existing.targetDimensions.height
			) {
				// two requests for the same image with differing dimensions - we
				// don't handle that
				throw new Error(
					`Multiple references to image "${name}" with differing target dimensions: ${targetDimensions}, ${existing.targetDimensions}`,
				);
			}
			return existing;
		}

		let created = new Image(name, targetDimensions);
		Image.images[name] = created;
		return created;
	}

	/**
	 * Collect all referenced images. To be called after the stylesheet is
	 * rendered so additional processing can occur for each referenced image.
	 */
	static collect () {
		return Object.values(Image.images);
	}

	/** The image's name. */
	get name () {
		return this.#name;
	}
	#name: string;

	/**
	 * The dimensions requested for this image by the stylesheet. If the source
	 * image on disk is larger than these dimensions and needs to be compressed
	 * in order to meet the Reddit filesize limit, then the image will be
	 * scaled within these dimensions, to attempt to reduce its filesize
	 * without introducing JPEG compression artifacts.
	 */
	get targetDimensions () {
		return this.#targetDimensions;
	}
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
		return (this.#sourceDataPromise ??= this.#getSourceData());
	}
	#sourceDataPromise: Promise<Buffer> | null;
	#getSourceData () {
		return readFile(this.fullSourcePath);
	}

	/** SHA1 hash of this image's source file. */
	getSourceHash () {
		return (this.#sourceHashPromise ??= this.#getSourceHash());
	}
	#sourceHashPromise: Promise<string> | null;
	async #getSourceHash () {
		const hash = createHash('sha1');
		hash.update(await this.getSourceData());
		return hash.digest('hex');
	}

	/**
	 * The key for this image. Computed from the source image's hash and the
	 * requested dimensions - if the contents of the file change, or if the file
	 * is used in a location where its expected size is different, the key will
	 * change and the image will be reuploaded to the subreddit.
	 */
	async getImageKey () {
		return `${await this.getSourceHash()}${this.targetDimensions?.width ? `_w${this.targetDimensions.width}` : ''}${
			this.targetDimensions?.height ? `_h${this.targetDimensions.height}` : ''
		}`;
	}

	/**
	 * XXX
	 * @returns
	 */
	getFinalData () {
		return (this.#finalDataPromise ??= this.#getFinalData());
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

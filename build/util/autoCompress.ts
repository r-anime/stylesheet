import sharp from 'sharp';

/**
 * Finds the highest JPEG quality setting for a given image that keeps it under
 * the given byte size, and returns the resulting image data.
 */
export async function autoCompress (imageData: Buffer, thresholdBytes: number) {
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
		throw new Error(
			`Can't compress enough; ${newImageSize} bytes at quality ${mid} (target <= ${thresholdBytes} bytes). This`
				+ `shouldn't happen, yell at Erin, consider manually resizing the image to fix this in the meantime`,
		);
	}

	return newImageData;
}

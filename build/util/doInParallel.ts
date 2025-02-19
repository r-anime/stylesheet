/**
 * Runs an asynchronous function on every item in a given array in parallel.
 * Allows all calls to finish before resolving or rejecting. Then, if one or
 * more calls have rejected, rejects with an array of the rejected values. If no
 * calls rejected, returns an array of all the resulting values.
 *
 * Similar to `Promise.all(promises)`, except that insteadof rejecting
 * immediately if any one promise rejects, this function waits for all promises
 * to settle before rejecting with an `AggregateError` containing all the
 * rejections.
 */
export async function doInParallel<T> (promises: Promise<T>[]) {
	const results = await Promise.allSettled(promises);

	const failureReasons = results
		.filter((result): result is PromiseRejectedResult => result.status === 'rejected')
		.map(result => result.reason);
	if (failureReasons.length) {
		throw new AggregateError(failureReasons);
	}

	return results.map(result => (result as PromiseFulfilledResult<T>).value);
}

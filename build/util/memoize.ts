/**
 * Memoizes the decorated method. Its body will be called at most one time per
 * instance (one time *ever* for static methods). The return value will be
 * cached, and subsequent calls to the method will return the cached value
 * without executing the body of the method.
 *
 * You probably don't want to return a mutable object from a memoized method;
 * the same object reference will be returned by all calls to the method, so it
 * will be possible for callers to mutate the object and affect the value
 * received by other callers. Consider freezing any objects you return (and keep
 * in mind that `Object.freeze()` is shallow).
 */
export function memoize<This extends object, Return> (
	target: (this: This) => Return,
	context: ClassMethodDecoratorContext,
) {
	if (context.kind !== 'method') {
		throw new Error('only class methods can be memoized');
	}

	// The return value is cached in a WeakMap keyed by `this` (the instance the
	// method is being called on). We don't want multiple instances sharing a
	// static cached return value for their instance methods, and static methods
	// are always called with the class itself as `this` so they will correctly
	// share a static cached value independent of any instance.
	let results = new WeakMap<This, Return>();
	return function (this: This) {
		if (!results.has(this)) {
			results.set(this, target.call(this));
		}
		return results.get(this)!;
	};
}

// the cool thing about base62 is that it's totally unreadable. however it *is*
// nice that it allows us to map more than 50 images cleanly - as long as 12 or
// fewer images change during each commit, we'll never even have to dip into
// double-letter image names! >:3
const base62chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';
/** Returns the base-62 representation of the given number. */
export function base62 (n: number) {
	const lastDigitValue = n % base62chars.length;
	const rest = Math.floor(n / base62chars.length);
	return `${rest == 0 ? '' : base62(rest)}${base62chars[lastDigitValue]}`;
}

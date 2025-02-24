import {TOTP} from 'totp-generator';

import {memoize} from './memoize';

/** Authentication details for talking with Reddit */
export interface RedditAuthOptions {
	clientID: string;
	clientSecret: string;
	username: string;
	password: string;
	totpSecret?: string;
}

/** The value of the `Authorization` header for HTTP basic auth. */
const basicAuth = (username, password) => `Basic ${Buffer.from(`${username}:${password}`).toString('base64')}`;

/** Helper for constructing `FormData` bodies inline. */
function multipartFormDataBody (values: Record<string, string | Blob>) {
	const body = new FormData();
	Object.entries(values).forEach(([key, value]) => body.set(key, value));
	return body;
}

/**
 * Handles errors for API endpoints whose error responses look like
 * `{"json": {"errors": [["CODE", "message", "field"], ...]}}`. Throws errors as
 * appropriate if the given response contains errors; otherwise returns the same
 * response object for further processing.
 */
async function handleArrayOfArrayErrors (response: Response): Promise<Response> {
	if (response.status !== 200) {
		throw new Error(`${response.status}: ${await response.text()}`);
	}

	const responseData = await response.json();
	if (responseData.json.errors && responseData.json.errors.length) {
		throw new Error(
			`${responseData.json.errors.length > 1 ? 'Multiple errors:\n' : ''}${
				responseData.json.errors
					.map(([code, message, field]) => `${field ? `in "${field}": ` : ''}${message} (${code})`)
					.join('\n')
			}`,
		);
	}

	return response;
}

/** Helper class for making requests against the Reddit API. */
export class RedditAPIClient {
	constructor (
		/** Authentication details for acting as a script-type OAuth app. */
		private auth: RedditAuthOptions,
		/** The value of the `User-Agent` header for all outgoing requests. */
		public userAgent: string,
	) {}

	/** Retrieves an access token via the `password` grant flow. */
	// In theory our access token could expire and we'd need to get another one,
	// but this isn't a very long-lived process, so we're just assuming that
	// won't happen and memoizing the function for simplicity
	@memoize
	private async getAccessToken (): Promise<string> {
		// If we have a TOTP secret, generate OTP and append to password
		let password = this.auth.password;
		if (this.auth.totpSecret) {
			const {otp} = TOTP.generate(this.auth.totpSecret);
			password += ':' + otp;
		}

		// Request access token
		const response = await this.fetch('https://oauth.reddit.com/api/v1/access_token', {
			method: 'POST',
			headers: {
				'Authorization': basicAuth(this.auth.clientID, this.auth.clientSecret),
				'Content-Type': 'application/x-www-form-urlencoded',
			},
			body: new URLSearchParams({
				grant_type: 'password',
				username: this.auth.username,
				password,
			}),
		});

		if (response.status !== 200) {
			throw new Error(await response.text());
		}
		let responseData = await response.json();
		if (responseData.error_description || responseData.error) {
			throw new Error(responseData.error_description || responseData.error);
		}

		return responseData.access_token;
	}

	/** Performs a fetch request with our `User-Agent` header. */
	private async fetch (url: string, init: RequestInit = {}) {
		const headers = new Headers(init.headers);
		headers.set('User-Agent', this.userAgent);
		return fetch(url, {...init, headers});
	}

	/**
	 * Performs a fetch request against the Reddit OAuth API with our
	 * `User-Agent` header and authorized with our access token.
	 */
	private async apiFetch (endpoint: `/${string}`, init: RequestInit = {}) {
		const headers = new Headers(init.headers);
		headers.set('Authorization', `Bearer ${await this.getAccessToken()}`);
		return this.fetch(`https://oauth.reddit.com${endpoint}`, {...init, headers});
	}

	/** Gets the contents of a wiki page. Throws if the page doesn't exist. */
	async getWikiPageContent (subreddit: string, page: string) {
		const response = await this.apiFetch(`/r/${subreddit}/wiki/${page}?raw_json=1`);
		const responseData = await response.json();

		if (responseData.message) {
			throw new Error(
				`${response.status}: ${responseData.message} ${responseData.reason ? `(${responseData.reason})` : ''}`,
			);
		}
		if (response.status !== 200 || responseData.data?.content_md == null) {
			throw new Error(`${response.status}: ${JSON.stringify(responseData)}`);
		}

		return responseData.data.content_md;
	}

	/** Updates the contents of a wiki page, creating it if it doesn't exist. */
	async updateWikiPage (subreddit: string, page: string, content: string, reason?: string) {
		const response = await this.apiFetch(`/r/${subreddit}/api/wiki/edit`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/x-www-form-urlencoded',
			},
			body: new URLSearchParams([
				['page', page],
				['content', content],
				...(reason ? [['reason', reason]] : []),
			]),
		});

		// this endpoint's error responses are fucked. it seems like they use
		// the same array-of-arrays format as the stylesheet stuff, except for
		// some reason it doesn't respond to `api_type` and always returns the
		// error wrapped in an HTML page embedded in a <script> tag. so whatever
		if (response.status !== 200) {
			throw new Error(`${response.status}: ${await response.text()}`);
		}
	}

	/** Uploads an image to a subreddit's stylesheet. */
	async uploadImage (subreddit: string, name: string, data: Buffer) {
		const response = await this.apiFetch(`/r/${subreddit}/api/upload_sr_img`, {
			method: 'POST',
			body: multipartFormDataBody({
				upload_type: 'img',
				name: name,
				file: new Blob([data]),
			}),
		});

		if (response.status !== 200) {
			throw new Error(`${response.status}: ${await response.text()}`);
		}
		const responseData = await response.json();
		if (responseData.errors && responseData.errors.length) {
			const errorMessages = responseData.errors_values;
			const readableErrors = responseData.errors.map((error, i) => `${errorMessages[i]} (${error})`);
			throw new Error(`${readableErrors.length > 1 ? 'Multiple errors:\n' : ''}${readableErrors.join('\n')}`);
		}
	}

	/**
	 * Deletes an image from a subreddit's stylesheet. Does nothing if the
	 * image already doesn't exist.
	 */
	async deleteImage (subreddit: string, name: string) {
		await this.apiFetch(`/r/${subreddit}/api/delete_sr_img`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/x-www-form-urlencoded',
			},
			body: new URLSearchParams({
				api_type: 'json',
				img_name: name,
			}),
		}).then(handleArrayOfArrayErrors);
	}

	/** Updates the CSS of a subreddit. */
	async updateCSS (subreddit: string, css: string, reason?: string) {
		await this.apiFetch(`/r/${subreddit}/api/subreddit_stylesheet`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/x-www-form-urlencoded',
			},
			body: new URLSearchParams([
				['api_type', 'json'],
				['op', 'save'],
				['stylesheet_contents', css],
				...(reason ? [['reason', reason]] : []),
			]),
		}).then(handleArrayOfArrayErrors);
	}
}

import {Image} from '../Image';

export interface StylesheetUploadBackend {
	mapImageName(image: Image): Promise<string>;
	uploadBuild(css: string, images: Image[]): Promise<void>;
}

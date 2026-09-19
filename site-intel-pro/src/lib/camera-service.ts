export type CameraMedia = {
  mediaType: "photo" | "video";
  file: File;
  capturedAt: string;
};

export interface CameraService {
  capturePhoto(): Promise<CameraMedia>;
  recordVideo(): Promise<CameraMedia>;
  selectFromGallery(): Promise<CameraMedia>;
}

export type CameraErrorCode = "PERMISSION_DENIED" | "CAPTURE_FAILED";

export class CameraServiceError extends Error {
  constructor(public readonly code: CameraErrorCode, message: string) {
    super(message);
    this.name = "CameraServiceError";
  }
}

export const cameraService: CameraService = {
  capturePhoto: () => selectFile("image/*", "environment"),
  recordVideo: () => selectFile("video/mp4", undefined),
  selectFromGallery: () => selectFile("image/*", undefined),
};

function selectFile(accept: string, capture: "environment" | undefined): Promise<CameraMedia> {
  return new Promise((resolve, reject) => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = accept;
    if (capture) input.setAttribute("capture", capture);
    input.onchange = () => {
      const file = input.files?.[0];
      if (!file) {
        reject(new CameraServiceError("CAPTURE_FAILED", "No evidence file was selected."));
        return;
      }
      resolve({
        mediaType: file.type.startsWith("video/") ? "video" : "photo",
        file,
        capturedAt: new Date(file.lastModified || Date.now()).toISOString(),
      });
    };
    input.onerror = () => reject(new CameraServiceError("CAPTURE_FAILED", "The evidence file could not be selected."));
    input.click();
  });
}

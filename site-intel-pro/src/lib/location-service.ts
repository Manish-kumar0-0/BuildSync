export type Location = {
  latitude: number | null;
  longitude: number | null;
  gpsAccuracy: number | null;
};

export interface LocationService {
  getCurrentLocation(): Promise<Location>;
  getGPSAccuracy(): Promise<number | null>;
}

export type LocationErrorCode = "GPS_UNAVAILABLE" | "LOW_ACCURACY";

export class LocationServiceError extends Error {
  constructor(public readonly code: LocationErrorCode, message: string) {
    super(message);
    this.name = "LocationServiceError";
  }
}

export const locationService: LocationService = {
  async getCurrentLocation() {
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      return { latitude: null, longitude: null, gpsAccuracy: null };
    }
    return new Promise(resolve => {
      navigator.geolocation.getCurrentPosition(
        position => resolve({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          gpsAccuracy: position.coords.accuracy,
        }),
        () => resolve({ latitude: null, longitude: null, gpsAccuracy: null }),
        { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 },
      );
    });
  },
  async getGPSAccuracy() {
    return (await this.getCurrentLocation()).gpsAccuracy;
  },
};

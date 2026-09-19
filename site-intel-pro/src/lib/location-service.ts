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
    const readPosition = (enableHighAccuracy: boolean, timeout: number) =>
      new Promise<GeolocationPosition | null>(resolve => {
        navigator.geolocation.getCurrentPosition(resolve, () => resolve(null), {
          enableHighAccuracy,
          timeout,
          maximumAge: enableHighAccuracy ? 0 : 60_000,
        });
      });
    const position = await readPosition(true, 10_000) ?? await readPosition(false, 10_000);
    return position
      ? {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          gpsAccuracy: position.coords.accuracy,
        }
      : { latitude: null, longitude: null, gpsAccuracy: null };
  },
  async getGPSAccuracy() {
    return (await this.getCurrentLocation()).gpsAccuracy;
  },
};

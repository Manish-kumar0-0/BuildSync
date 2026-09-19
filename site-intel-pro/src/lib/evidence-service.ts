import { api } from "@/services/api";
import type { CameraMedia } from "./camera-service";
import type { Location } from "./location-service";

export type UploadedEvidence = {
  id: string;
  activityId: string;
  mediaType: "photo" | "video";
  fileName: string;
  status: string;
  reportedProgress: number | null;
  capturedAt: string | null;
  latitude: number | null;
  longitude: number | null;
  gpsAccuracy: number | null;
};

export type ComparisonResult = {
  comparisonId: number;
  currentEvidenceId: number;
  previousEvidenceId: number;
  comparisonStatus: string;
  overallChange: string;
  confidence: number;
  constructionChangeScore: number;
  observations: Array<Record<string, unknown>>;
  possibleIssues: string[];
  notes: string | null;
  model: string;
  opencvDifference?: Record<string, number | string>;
  detections?: Record<string, Array<Record<string, unknown>>>;
  comparison?: Record<string, Array<Record<string, unknown>>>;
  geminiExplanation?: string | null;
  limitations: string[];
};

export async function uploadEvidence(
  activityId: string,
  media: CameraMedia,
  progress: number,
  notes: string,
  location: Location,
): Promise<UploadedEvidence> {
  const form = new FormData();
  form.append("file", media.file, media.file.name);
  form.append("reported_progress", String(progress));
  if (notes.trim()) form.append("notes", notes.trim());
  if (location.latitude !== null && location.longitude !== null) {
    form.append("latitude", String(location.latitude));
    form.append("longitude", String(location.longitude));
    if (location.gpsAccuracy !== null) form.append("gps_accuracy", String(location.gpsAccuracy));
  }
  form.append("captured_at", media.capturedAt);
  const response = await api.postForm<{
    id: number;
    activity_id: number;
    evidence_type: string;
    file_name: string;
    reported_progress: number | null;
    latitude: number | null;
    longitude: number | null;
    gps_accuracy: number | null;
    captured_at: string | null;
    status: string;
  }>(`/api/activities/${activityId}/evidence`, form);
  return {
    id: String(response.id),
    activityId: String(response.activity_id),
    mediaType: response.evidence_type === "VIDEO" ? "video" : "photo",
    fileName: response.file_name,
    status: response.status,
    reportedProgress: response.reported_progress,
    capturedAt: response.captured_at,
    latitude: response.latitude,
    longitude: response.longitude,
    gpsAccuracy: response.gps_accuracy,
  };
}

export function compareWithPrevious(evidenceId: string): Promise<ComparisonResult> {
  return api.post<ComparisonResult>(`/api/evidence/${evidenceId}/compare-with-previous`, {});
}

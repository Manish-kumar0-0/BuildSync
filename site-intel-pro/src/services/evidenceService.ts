import type { Evidence } from "@/app/types";
import { api } from "./api";

export const evidenceService = {
  async listEvidence(projectId?: string): Promise<Evidence[]> {
    if (!projectId) return [];
    const response = await api.get<{ items: Array<Record<string, unknown>> }>(`/api/projects/${projectId}/evidence`);
    return response.items.map(item => ({
      id: String(item.id),
      activityId: String(item.activity_id ?? ""),
      activity: String(item.activity_id ?? ""),
      project: projectId,
      zone: String(item.zone ?? ""),
      gpsAccuracy: String(item.gps_accuracy ?? ""),
      timestamp: String(item.captured_at ?? item.uploaded_at ?? ""),
      currentProgress: Number(item.reported_progress ?? 0),
      previousProgress: 0,
      fieldNotes: String(item.notes ?? ""),
      mediaType: item.evidence_type === "VIDEO" ? "video" : "photo",
      status: item.status === "VERIFIED" ? "Approved" : item.status === "REJECTED" ? "Rejected" : "Pending review",
    }));
  },
  async createEvidence(payload: Partial<Evidence>): Promise<Evidence> {
    return {
      id: payload.id ?? "evidence-1",
      activityId: payload.activityId ?? "activity-1",
      activity: payload.activity ?? "Sample activity",
      project: payload.project ?? "Metro Line 6",
      zone: payload.zone ?? "Zone B",
      gpsAccuracy: payload.gpsAccuracy ?? "2m",
      timestamp: payload.timestamp ?? "now",
      currentProgress: payload.currentProgress ?? 0,
      previousProgress: payload.previousProgress ?? 0,
      fieldNotes: payload.fieldNotes ?? "",
      mediaType: payload.mediaType ?? "photo",
      status: payload.status ?? "Pending review",
    };
  },
};

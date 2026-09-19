import type { Inspection } from "@/app/types";
import { api } from "./api";

export const qualityService = {
  async listInspections(projectId?: string): Promise<Inspection[]> {
    if (!projectId) return [];
    const response = await api.get<Array<Record<string, unknown>>>(`/api/projects/${projectId}/quality/inspections`);
    return response.map(item => ({
      id: String(item.id),
      title: String(item.title ?? item.inspection_type ?? "Inspection"),
      activityId: String(item.activity_id ?? ""),
      type: "Quality",
      result: item.status === "PASSED" ? "Pass" : item.status === "FAILED" ? "Fail" : "Needs attention",
      date: String(item.inspected_at ?? item.created_at ?? ""),
      inspector: String(item.inspector_id ?? ""),
    }));
  },
};

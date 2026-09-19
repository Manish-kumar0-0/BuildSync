import type { Issue } from "@/app/types";
import { api } from "./api";

export const safetyService = {
  async listIssues(projectId?: string): Promise<Issue[]> {
    if (!projectId) return [];
    const response = await api.get<Array<Record<string, unknown>>>(`/api/projects/${projectId}/safety/incidents`);
    return response.map(item => ({
      id: String(item.id),
      title: String(item.title ?? item.incident_type ?? "Safety incident"),
      severity: item.severity === "CRITICAL" ? "Critical" : item.severity === "HIGH" ? "High" : "Medium",
      projectId,
      location: String(item.location ?? ""),
      description: String(item.description ?? ""),
      status: item.status === "CLOSED" ? "Resolved" : "Open",
      reportedAt: String(item.occurred_at ?? item.created_at ?? ""),
    }));
  },
};

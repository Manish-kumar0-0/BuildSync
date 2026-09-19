import type { Worker } from "@/app/types";
import { api } from "./api";

export const workforceService = {
  async listWorkers(projectId?: string): Promise<Worker[]> {
    if (!projectId) return [];
    const response = await api.get<Record<string, unknown>>(`/api/projects/${projectId}/workforce/summary`);
    const workers = Array.isArray(response.workers) ? response.workers : [];
    return workers.map(worker => {
      const item = worker as Record<string, unknown>;
      return {
        id: String(item.id ?? ""),
        name: String(item.name ?? item.full_name ?? "Worker"),
        role: "Worker",
        crew: String(item.crew ?? ""),
        attendanceStatus: "Present",
        projectId,
        hoursToday: String(item.hours_today ?? ""),
      };
    });
  },
};

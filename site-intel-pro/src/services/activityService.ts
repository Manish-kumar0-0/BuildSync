import type { Activity } from "@/app/types";
import { api } from "./api";

export const activityService = {
  async listActivities(projectId?: string): Promise<Activity[]> {
    if (!projectId) return [];
    const activities = await api.get<Array<Record<string, unknown>>>(`/api/projects/${projectId}/activities`);
    return activities.map(activity => ({
      id: String(activity.id),
      title: String(activity.name ?? "Untitled activity"),
      projectId,
      project: String(activity.project_id ?? projectId),
      zone: String(activity.zone ?? ""),
      assignee: "",
      status: String(activity.status ?? "NOT_STARTED") as Activity["status"],
      progress: Number(activity.reported_progress ?? activity.progress_percentage ?? 0),
      dueDate: String(activity.updated_at ?? ""),
      priority: "Medium",
    }));
  },
  async getActivity(id: string): Promise<Activity | undefined> {
    try {
      const activity = await api.get<Record<string, unknown>>(`/api/activities/${id}`);
      return {
        id,
        title: String(activity.name ?? "Untitled activity"),
        projectId: String(activity.project_id ?? ""),
        project: String(activity.project_id ?? ""),
        zone: String(activity.zone ?? ""),
        assignee: "",
        status: String(activity.status ?? "NOT_STARTED") as Activity["status"],
        progress: Number(activity.reported_progress ?? 0),
        dueDate: String(activity.updated_at ?? ""),
        priority: "Medium",
      };
    } catch {
      return undefined;
    }
  },
};

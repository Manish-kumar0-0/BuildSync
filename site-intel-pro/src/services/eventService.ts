import type { Event } from "@/app/types";
import { api } from "./api";

export const eventService = {
  async listEvents(projectId?: string): Promise<Event[]> {
    if (!projectId) return [];
    const response = await api.get<{ items: Array<Record<string, unknown>> }>(`/api/projects/${projectId}/events`);
    return response.items.map(event => ({
      id: String(event.id),
      title: String(event.title ?? "Construction event"),
      type: "Schedule",
      projectId,
      timestamp: String(event.event_timestamp ?? ""),
      description: String(event.description ?? ""),
    }));
  },
};

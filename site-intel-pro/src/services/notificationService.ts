import type { Notification, Role } from "@/app/types";
import { api } from "./api";

interface ApiNotification {
  id: number;
  type: string;
  priority: string;
  title: string;
  message: string;
  created_at: string;
  is_read: boolean;
  project_id?: number | null;
  activity_id?: number | null;
}

export const notificationService = {
  async getByRole(_role: Role): Promise<Notification[]> {
    const response = await api.get<{ items: ApiNotification[] }>("/api/notifications");
    return response.items.map(notification => ({
      id: String(notification.id),
      type: notification.type,
      priority: (["Critical", "High", "Medium", "Low"].includes(notification.priority)
        ? notification.priority
        : "Medium") as Notification["priority"],
      title: notification.title,
      description: notification.message,
      timestamp: notification.created_at,
      relatedProject: notification.project_id ? String(notification.project_id) : "",
      relatedActivity: notification.activity_id ? String(notification.activity_id) : "",
      read: notification.is_read,
      userRole: "Project Manager",
    }));
  },
  async markAllAsRead(): Promise<void> {
    await api.patch("/api/notifications/read-all", {});
  },
  async markAsRead(notificationId: string): Promise<void> {
    await api.patch(`/api/notifications/${notificationId}/read`, {});
  },
};

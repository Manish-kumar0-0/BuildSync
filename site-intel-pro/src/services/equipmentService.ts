import type { Equipment } from "@/app/types";
import { api } from "./api";

export const equipmentService = {
  async listEquipment(projectId?: string): Promise<Equipment[]> {
    if (!projectId) return [];
    const response = await api.get<Array<Record<string, unknown>>>(`/api/projects/${projectId}/equipment`);
    return response.map(item => ({
      id: String(item.id),
      code: String(item.code ?? ""),
      name: String(item.name ?? "Equipment"),
      status: item.status === "MAINTENANCE" ? "Maintenance" : item.status === "UNAVAILABLE" ? "Service" : "Operational",
      projectId,
      nextServiceDate: String(item.next_service_date ?? ""),
    }));
  },
};

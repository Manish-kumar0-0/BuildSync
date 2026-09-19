import type { Material } from "@/app/types";
import { api } from "./api";

export const materialService = {
  async listMaterials(projectId?: string): Promise<Material[]> {
    if (!projectId) return [];
    const response = await api.get<Array<Record<string, unknown>>>(`/api/projects/${projectId}/materials`);
    return response.map(item => ({
      id: String(item.id),
      name: String(item.name ?? item.material_name ?? "Material"),
      unit: String(item.unit ?? ""),
      stock: Number(item.current_stock ?? item.quantity ?? 0),
      threshold: Number(item.minimum_stock ?? 0),
      supplier: String(item.supplier ?? ""),
      projectId,
      status: Number(item.current_stock ?? item.quantity ?? 0) <= Number(item.minimum_stock ?? 0) ? "Low" : "Healthy",
    }));
  },
};

import { api, type AssistantResult } from "./api";

export const aiService = {
  async ask(projectId: string, message: string): Promise<AssistantResult> {
    return api.post<AssistantResult>(`/api/projects/${projectId}/assistant/query`, { message });
  },
};

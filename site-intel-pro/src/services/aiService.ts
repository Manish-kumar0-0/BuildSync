import { api, type AssistantResult } from "./api";

export const aiService = {
  async ask(projectId: string, message: string): Promise<AssistantResult> {
    const request = api.post<AssistantResult>(`/api/projects/${projectId}/assistant/query`, { question: message });
    const timeout = new Promise<never>((_, reject) => {
      window.setTimeout(() => reject(new Error("Project assistant request timed out")), 8000);
    });
    return Promise.race([request, timeout]);
  },
};

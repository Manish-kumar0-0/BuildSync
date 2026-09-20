import { api, type AssistantResult } from "./api";

export const aiService = {
  async ask(projectId: string, message: string): Promise<AssistantResult> {
    const request = api.post<AssistantResult>(
      `/api/projects/${projectId}/assistant/query`,
      { question: message },
    );
    let timeoutId: number | undefined;
    const timeout = new Promise<never>((_, reject) => {
      timeoutId = window.setTimeout(
        () => reject(new Error("Project assistant timed out while waiting for the backend")),
        30_000,
      );
    });
    try {
      return await Promise.race([request, timeout]);
    } finally {
      if (timeoutId !== undefined) window.clearTimeout(timeoutId);
    }
  },
};

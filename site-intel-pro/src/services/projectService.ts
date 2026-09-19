import type { Project } from "@/app/types";
import { api, type ApiProject } from "./api";

function toProject(project: ApiProject): Project {
  return {
    id: String(project.id),
    name: project.name,
    packageName: project.package_name ?? project.project_code,
    zone: project.location ?? "Project site",
    progress: 0,
    status: project.status === "DELAYED" ? "Delayed" : project.status === "CRITICAL" ? "Critical" : "On track",
    projectManager: "Project team",
    startDate: project.start_date,
    endDate: project.planned_end_date,
    activeWorkers: 0,
    openIssues: 0,
    scheduleVariance: 0,
  };
}

export const projectService = {
  async getProjects(): Promise<Project[]> {
    const projects = await api.get<ApiProject[]>("/api/projects");
    return projects.map(toProject);
  },
  async getProject(projectId: string): Promise<Project | undefined> {
    try {
      return toProject(await api.get<ApiProject>(`/api/projects/${projectId}`));
    } catch {
      return undefined;
    }
  },
};

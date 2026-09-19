import type { Project } from "@/app/types";

export const mockProjects: Project[] = [
  {
    id: "proj-01",
    name: "Metro Line 6",
    packageName: "Package C3",
    zone: "North Viaduct",
    progress: 68,
    status: "On track",
    projectManager: "Elena",
    startDate: "2026-01-15",
    endDate: "2027-05-22",
    activeWorkers: 428,
    openIssues: 3,
    scheduleVariance: -3.2,
  },
  {
    id: "proj-02",
    name: "Metro Line 6",
    packageName: "Package D2",
    zone: "Deck South",
    progress: 54,
    status: "At risk",
    projectManager: "Elena",
    startDate: "2026-02-07",
    endDate: "2027-06-05",
    activeWorkers: 312,
    openIssues: 5,
    scheduleVariance: -2.1,
  },
];

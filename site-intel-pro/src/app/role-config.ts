import { BriefcaseBusiness, Construction, HardHat } from "lucide-react";
import type { ComponentType } from "react";
import type { NotificationPriority, Role } from "@/app/types";

export type Category = "WORKFORCE" | "SITE OPERATIONS" | "MANAGEMENT";

export const roleCopy: Record<Role, { first: string; title: string; subtitle: string }> = {
  Worker: { first: "Ravi", title: "Good morning, Ravi", subtitle: "Zone B · Pier package" },
  Foreman: { first: "Joseph", title: "Team command", subtitle: "Civil crew · 42 workers" },
  "Field Engineer": { first: "Arjun", title: "Field operations", subtitle: "Evidence & site progress" },
  "Site Engineer": { first: "Nadia", title: "Site control", subtitle: "North viaduct package" },
  "Safety Officer": { first: "Omar", title: "Safety overview", subtitle: "Site compliance and actions" },
  "QA/QC Engineer": { first: "Meera", title: "Quality control", subtitle: "Inspections & test records" },
  "Material Manager": { first: "Amin", title: "Material control", subtitle: "Central store · Zone 02" },
  Driver: { first: "Farid", title: "Current assignment", subtitle: "Vehicle MH-12-KL-4821" },
  "Equipment Manager": { first: "Lucas", title: "Equipment fleet", subtitle: "38 assets tracked" },
  "Project Manager": { first: "Elena", title: "Project overview", subtitle: "Metro Line 6 · Package C3" },
  "Planning Engineer": { first: "Priya", title: "Planning control", subtitle: "Baseline schedule · North Viaduct" },
  Admin: { first: "Admin", title: "Administration", subtitle: "BuildSync project control" },
};

export const categoryDetails: Record<Category, {
  description: string;
  icon: ComponentType<{ className?: string }>;
  roles: Role[];
}> = {
  WORKFORCE: {
    description: "Manage workers, crews, attendance and field deliveries.",
    icon: HardHat,
    roles: ["Worker", "Foreman", "Driver"],
  },
  "SITE OPERATIONS": {
    description: "Monitor site execution, engineering, safety, quality, materials and equipment.",
    icon: Construction,
    roles: ["Field Engineer", "Site Engineer", "Safety Officer", "QA/QC Engineer", "Material Manager", "Equipment Manager"],
  },
  MANAGEMENT: {
    description: "Control project performance, users, risks and overall project operations.",
    icon: BriefcaseBusiness,
    roles: ["Project Manager", "Planning Engineer"],
  },
};

export const rolePaths: Record<Role, string> = {
  Worker: "/worker",
  Foreman: "/foreman",
  Driver: "/driver",
  "Field Engineer": "/field-engineer",
  "Site Engineer": "/site-engineer",
  "Safety Officer": "/safety-officer",
  "QA/QC Engineer": "/qaqc",
  "Material Manager": "/material-manager",
  "Equipment Manager": "/equipment-manager",
  "Project Manager": "/project-manager",
  "Planning Engineer": "/planning-engineer",
  Admin: "/admin",
};

export const notificationPriorityOrder: NotificationPriority[] = ["Critical", "High", "Medium", "Low"];

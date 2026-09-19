export type Role = "Worker" | "Foreman" | "Field Engineer" | "Site Engineer" | "Safety Officer" | "QA/QC Engineer" | "Material Manager" | "Driver" | "Equipment Manager" | "Project Manager" | "Planning Engineer" | "Admin";

export type Screen = "welcome" | "login" | "forgot" | "otp" | "home" | "activities" | "sih-intelligence" | "planning" | "capture" | "evidence" | "analytics" | "ai" | "timeline" | "replay" | "inventory" | "inspection" | "trip" | "notifications" | "profile" | "settings";

export type Tone = "primary" | "success" | "warning" | "danger" | "muted";
export type NotificationPriority = "Critical" | "High" | "Medium" | "Low";

export interface User {
  id: string;
  name: string;
  email: string;
  phone: string;
  role: Role;
  firstName: string;
  projectId?: string;
  avatarUrl?: string;
  status?: "online" | "offline";
}

export interface Project {
  id: string;
  name: string;
  packageName: string;
  zone: string;
  progress: number;
  status: "On track" | "At risk" | "Delayed" | "Critical";
  projectManager: string;
  startDate: string;
  endDate: string;
  activeWorkers: number;
  openIssues: number;
  scheduleVariance: number;
}

export interface Activity {
  id: string;
  title: string;
  projectId: string;
  project: string;
  zone: string;
  assignee: string;
  status: "Planned" | "In progress" | "Delayed" | "Completed" | "Needs review";
  progress: number;
  dueDate: string;
  priority: NotificationPriority;
}

export interface Evidence {
  id: string;
  activityId: string;
  activity: string;
  project: string;
  zone: string;
  gpsAccuracy: string;
  timestamp: string;
  currentProgress: number;
  previousProgress: number;
  fieldNotes: string;
  mediaType: "photo" | "video";
  status: "Pending review" | "Approved" | "Rejected";
}

export interface Worker {
  id: string;
  name: string;
  role: Role;
  crew: string;
  attendanceStatus: "Present" | "Late" | "Absent";
  projectId: string;
  hoursToday: string;
}

export interface Material {
  id: string;
  name: string;
  unit: string;
  stock: number;
  threshold: number;
  supplier: string;
  projectId: string;
  status: "Healthy" | "Low" | "Critical";
}

export interface Delivery {
  id: string;
  vehicleId: string;
  material: string;
  destination: string;
  status: "Assigned" | "In transit" | "Delivered" | "Delayed";
  eta: string;
  driver: string;
}

export interface Vehicle {
  id: string;
  plate: string;
  type: string;
  assignedDriver: string;
  status: "Operational" | "Service" | "Unavailable";
  lastCheck: string;
}

export interface Equipment {
  id: string;
  code: string;
  name: string;
  status: "Operational" | "Service" | "Maintenance";
  projectId: string;
  nextServiceDate: string;
}

export interface Inspection {
  id: string;
  title: string;
  activityId: string;
  type: "Safety" | "Quality" | "Progress";
  result: "Pass" | "Fail" | "Needs attention";
  date: string;
  inspector: string;
}

export interface Issue {
  id: string;
  title: string;
  severity: NotificationPriority;
  projectId: string;
  location: string;
  description: string;
  status: "Open" | "Monitoring" | "Resolved";
  reportedAt: string;
}

export interface Event {
  id: string;
  title: string;
  type: "Schedule" | "Safety" | "Material" | "Equipment" | "Quality";
  projectId: string;
  timestamp: string;
  description: string;
}

export interface Prediction {
  id: string;
  projectId: string;
  title: string;
  riskLevel: "Low" | "Medium" | "High" | "Critical";
  confidence: number;
  summary: string;
  impact: string;
}

export interface Notification {
  id: string;
  type: string;
  priority: NotificationPriority;
  title: string;
  description: string;
  timestamp: string;
  relatedProject: string;
  relatedActivity: string;
  read: boolean;
  userRole: Role;
}

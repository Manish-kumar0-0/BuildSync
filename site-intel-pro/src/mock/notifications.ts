import type { Notification, Role } from "@/app/types";

export const mockNotificationsByRole: Record<Role, Notification[]> = {
  Worker: [
    { id: "w-1", type: "Crew update", priority: "Medium", title: "Site handoff completed.", description: "The morning crew has logged the rebar placement and the next shift is ready to continue.", timestamp: "3 min ago", relatedProject: "Metro Line 6", relatedActivity: "Pier P3 · Zone B", read: false, userRole: "Worker" },
    { id: "w-2", type: "Task alert", priority: "Low", title: "Safety briefing scheduled.", description: "A toolbox talk is scheduled before the 14:00 concrete pour to review lifting points and PPE checks.", timestamp: "26 min ago", relatedProject: "Metro Line 6", relatedActivity: "Deck D2 · Safety briefing", read: true, userRole: "Worker" },
  ],
  Foreman: [
    { id: "f-1", type: "Shift coordination", priority: "High", title: "Crew availability updated.", description: "Three laborers are assigned to the night shift and one crane team is pending confirmation.", timestamp: "7 min ago", relatedProject: "Metro Line 6", relatedActivity: "Pier P3", read: false, userRole: "Foreman" },
    { id: "f-2", type: "Site order", priority: "Medium", title: "Delivery window confirmed.", description: "Concrete delivery is moving to the 16:30 slot with no material variance expected.", timestamp: "49 min ago", relatedProject: "Metro Line 6", relatedActivity: "Zone B delivery", read: true, userRole: "Foreman" },
  ],
  "Field Engineer": [
    { id: "fe-1", type: "Evidence analysis", priority: "High", title: "Evidence analysis completed.", description: "Progress evidence has been processed and flagged for final QA review before closeout.", timestamp: "2 min ago", relatedProject: "Metro Line 6 · Package C3", relatedActivity: "Pier P3 reinforcement", read: false, userRole: "Field Engineer" },
    { id: "fe-2", type: "Progress update", priority: "Medium", title: "Inspection notes synced.", description: "The revised as-built notes have been shared with site control and project controls.", timestamp: "40 min ago", relatedProject: "Metro Line 6 · Package C3", relatedActivity: "Deck D2 shuttering", read: true, userRole: "Field Engineer" },
  ],
  "Site Engineer": [
    { id: "se-1", type: "Verification", priority: "High", title: "3 activities require verification.", description: "Three field activities have been marked for verification before the end-of-shift handoff.", timestamp: "5 min ago", relatedProject: "Metro Line 6 · Package C3", relatedActivity: "Pier P3 · Zone B", read: false, userRole: "Site Engineer" },
    { id: "se-2", type: "Sequence alert", priority: "Medium", title: "Sequence adjusted.", description: "The formwork sequence was updated to avoid the concrete pour conflict at the north span.", timestamp: "26 min ago", relatedProject: "Metro Line 6 · Package C3", relatedActivity: "North viaduct sequence", read: true, userRole: "Site Engineer" },
  ],
  "Safety Officer": [
    { id: "so-1", type: "Hazard report", priority: "Critical", title: "Critical hazard reported.", description: "A missing guardrail at the access ramp requires immediate inspection and control enforcement.", timestamp: "1 min ago", relatedProject: "Metro Line 6 · Package C3", relatedActivity: "Ramp access · Zone C", read: false, userRole: "Safety Officer" },
    { id: "so-2", type: "Compliance", priority: "Medium", title: "Toolbox talk logged.", description: "The tunnel ventilation briefing was recorded and passed with zero follow-up actions.", timestamp: "44 min ago", relatedProject: "Metro Line 6 · Package C3", relatedActivity: "Safety briefing", read: true, userRole: "Safety Officer" },
  ],
  "QA/QC Engineer": [
    { id: "qaqc-1", type: "Quality review", priority: "High", title: "Concrete batch review pending.", description: "The latest pour sample is under review for moisture and compressive variance.", timestamp: "12 min ago", relatedProject: "Metro Line 6 · Package C3", relatedActivity: "Pier P3 pour", read: false, userRole: "QA/QC Engineer" },
    { id: "qaqc-2", type: "Inspection", priority: "Medium", title: "Surface finish check passed.", description: "The latest finish inspection passed with only minor cosmetic comments for final control.", timestamp: "1 hr ago", relatedProject: "Metro Line 6 · Package C3", relatedActivity: "Deck D2", read: true, userRole: "QA/QC Engineer" },
  ],
  "Material Manager": [
    { id: "mm-1", type: "Inventory threshold", priority: "High", title: "Steel stock below threshold.", description: "Rebar stock is below the replenishment trigger for the next concrete cycle on Zone B.", timestamp: "4 min ago", relatedProject: "Metro Line 6 · Package C3", relatedActivity: "Steel laydown · Zone B", read: false, userRole: "Material Manager" },
    { id: "mm-2", type: "Delivery update", priority: "Medium", title: "Aggregate delivery in transit.", description: "The next aggregate batch is due in 28 minutes and expected to meet current demand.", timestamp: "31 min ago", relatedProject: "Metro Line 6 · Package C3", relatedActivity: "Aggregate supply", read: true, userRole: "Material Manager" },
  ],
  Driver: [
    { id: "d-1", type: "Assignment", priority: "High", title: "New delivery assigned.", description: "Vehicle MH-12-KL-4821 has a new delivery sequence for the concrete plant and crew handoff.", timestamp: "8 min ago", relatedProject: "Metro Line 6 · Package C3", relatedActivity: "Concrete plant route", read: false, userRole: "Driver" },
    { id: "d-2", type: "Route update", priority: "Low", title: "Load list confirmed.", description: "Your next load is confirmed and will be routed to the north viaduct access lane.", timestamp: "52 min ago", relatedProject: "Metro Line 6 · Package C3", relatedActivity: "North viaduct route", read: true, userRole: "Driver" },
  ],
  "Equipment Manager": [
    { id: "em-1", type: "Maintenance", priority: "High", title: "Excavator EQ-04 requires maintenance.", description: "The undercarriage inspection flagged a service condition that should be resolved before the next night shift.", timestamp: "11 min ago", relatedProject: "Metro Line 6 · Package C3", relatedActivity: "Excavator EQ-04", read: false, userRole: "Equipment Manager" },
    { id: "em-2", type: "Fleet status", priority: "Medium", title: "Crane utilization updated.", description: "The fleet availability report is now current and all cranes remain within operating limits.", timestamp: "1 hr ago", relatedProject: "Metro Line 6 · Package C3", relatedActivity: "Crane fleet", read: true, userRole: "Equipment Manager" },
  ],
  "Project Manager": [
    { id: "pm-1", type: "Delay risk", priority: "Critical", title: "Pier P3 has entered HIGH delay risk.", description: "The latest schedule forecast indicates a high probability of delay if workfront access remains constrained.", timestamp: "3 min ago", relatedProject: "Metro Line 6 · Package C3", relatedActivity: "Pier P3", read: false, userRole: "Project Manager" },
    { id: "pm-2", type: "Overview", priority: "Medium", title: "Weekly site summary published.", description: "The PM pack for week 36 has been shared with engineering, safety, and site operations.", timestamp: "2 hr ago", relatedProject: "Metro Line 6 · Package C3", relatedActivity: "Weekly summary", read: true, userRole: "Project Manager" },
  ],
  Admin: [
    { id: "admin-1", type: "Delay risk", priority: "Critical", title: "Pier P3 has entered HIGH delay risk.", description: "The latest schedule forecast indicates a high probability of delay if workfront access remains constrained.", timestamp: "3 min ago", relatedProject: "Metro Line 6 · Package C3", relatedActivity: "Pier P3", read: false, userRole: "Admin" },
    { id: "admin-2", type: "Overview", priority: "Medium", title: "Weekly site summary published.", description: "The PM pack for week 36 has been shared with engineering, safety, and site operations.", timestamp: "2 hr ago", relatedProject: "Metro Line 6 · Package C3", relatedActivity: "Weekly summary", read: true, userRole: "Admin" },
  ],
  "Planning Engineer": [
    { id: "pe-1", type: "Schedule approval", priority: "High", title: "Baseline ready for approval.", description: "Version 1.0 for Metro Line 6 — Package C3 is ready for Project Manager review.", timestamp: "6 min ago", relatedProject: "Metro Line 6 · Package C3", relatedActivity: "Baseline schedule", read: false, userRole: "Planning Engineer" },
    { id: "pe-2", type: "Schedule change", priority: "Medium", title: "Revision 1.1 draft created.", description: "Delayed steel delivery has been recorded as a pending schedule revision.", timestamp: "42 min ago", relatedProject: "Metro Line 6 · Package C3", relatedActivity: "Pier P3 reinforcement", read: true, userRole: "Planning Engineer" },
  ],
};

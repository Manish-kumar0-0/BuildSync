import { useState } from "react";
import {
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock3,
  Flag,
  History,
  Link2,
  LockKeyhole,
  Plus,
  ShieldCheck,
  Upload,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Role, Screen, Tone } from "@/app/types";

const activities = [
  { id: "ACT-0032", name: "Pier P3 Reinforcement", wbs: "WBS-03.02", start: "05 Sep", end: "12 Sep", duration: "8 Days", quantity: "20", unit: "MT", dependency: "ACT-0028", milestone: "No", progress: 75, reported: 62, ai: 64, verified: 63, status: "At risk", boq: "BOQ-245 · Steel Reinforcement", team: "Civil Crew A", responsible: "Foreman Joseph" },
  { id: "ACT-0028", name: "Pier P3 Foundation", wbs: "WBS-03.01", start: "01 Sep", end: "05 Sep", duration: "5 Days", quantity: "1", unit: "LS", dependency: "ACT-0018", milestone: "Yes", progress: 100, reported: 100, ai: 100, verified: 100, status: "Complete", boq: "BOQ-212 · Concrete Works", team: "Civil Crew A", responsible: "Foreman Joseph" },
  { id: "ACT-0041", name: "Pier P3 Shuttering", wbs: "WBS-03.03", start: "12 Sep", end: "16 Sep", duration: "5 Days", quantity: "180", unit: "M2", dependency: "ACT-0032", milestone: "No", progress: 0, reported: 0, ai: 0, verified: 0, status: "Planned", boq: "BOQ-251 · Formwork", team: "Formwork Crew", responsible: "Foreman Joseph" },
];

const previewRows = activities.map(activity => ({
  ...activity,
  name: activity.name,
}));

const toneClasses: Record<Tone, string> = {
  primary: "border-primary/25 bg-primary/10 text-primary",
  success: "border-success/25 bg-success/10 text-success",
  warning: "border-warning/25 bg-warning/10 text-warning",
  danger: "border-danger/25 bg-danger/10 text-danger",
  muted: "border-border bg-secondary text-muted-foreground",
};

function Card({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("rounded-lg border border-border bg-card p-4 shadow-sm", className)}>{children}</div>;
}

function Badge({ children, tone = "muted" }: { children: React.ReactNode; tone?: Tone }) {
  return <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase", toneClasses[tone])}>{children}</span>;
}

function ProgressBar({ value, tone = "primary" }: { value: number; tone?: Tone }) {
  const color = tone === "danger" ? "bg-danger" : tone === "warning" ? "bg-warning" : tone === "success" ? "bg-success" : "bg-primary";
  return <div className="h-1.5 overflow-hidden rounded-full bg-secondary"><div className={cn("h-full rounded-full", color)} style={{ width: `${value}%` }} /></div>;
}

function Metric({ label, value, detail, tone = "muted" }: { label: string; value: string; detail?: string; tone?: Tone }) {
  return <div className="rounded-xl border border-border bg-secondary p-3"><p className="text-[9px] font-bold uppercase tracking-[0.1em] text-muted-foreground">{label}</p><p className={cn("mt-1 text-xl font-extrabold", tone === "danger" ? "text-danger" : tone === "warning" ? "text-warning" : tone === "success" ? "text-success" : "text-foreground")}>{value}</p>{detail && <p className="mt-1 text-[10px] leading-4 text-muted-foreground">{detail}</p>}</div>;
}

export function PlanningEngineerDashboard({ onScreen }: { onScreen: (screen: Screen) => void }) {
  return <div className="space-y-5">
    <Card className="border-primary/25 bg-primary/5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div><Badge tone="primary"><CalendarDays className="h-3 w-3" /> Planning workspace</Badge><h2 className="mt-3 text-2xl font-extrabold">Planning &amp; Schedule</h2><p className="mt-1 text-sm text-muted-foreground">Build the approved baseline that Progress Control uses to compare field execution.</p></div>
        <Button onClick={() => onScreen("planning")}><Upload /> Import schedule</Button>
      </div>
    </Card>
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      <Metric label="Baseline progress" value="72%" detail="Approved plan" tone="primary" />
      <Metric label="Schedule health" value="82%" detail="Healthy with watch items" tone="success" />
      <Metric label="Activities planned" value="428" detail="86 WBS · 214 BOQ" />
      <Metric label="At risk" value="8" detail="3 need action" tone="warning" />
    </div>
    <div className="grid gap-5 lg:grid-cols-2">
      <Card><div className="flex items-center justify-between"><div><p className="text-[10px] font-bold uppercase tracking-widest text-primary">Upcoming milestones</p><h3 className="mt-1 text-lg font-extrabold">North Viaduct</h3></div><Badge tone="primary">32 total</Badge></div><div className="mt-4 space-y-3"><div className="flex items-center gap-3"><div className="grid h-8 w-8 place-items-center rounded-lg bg-primary/10 text-primary"><CheckCircle2 className="h-4 w-4" /></div><div className="min-w-0 flex-1"><p className="text-xs font-bold">Pier P3 foundation complete</p><p className="text-[10px] text-muted-foreground">05 Sep · achieved</p></div><Badge tone="success">Done</Badge></div><div className="flex items-center gap-3"><div className="grid h-8 w-8 place-items-center rounded-lg bg-warning/10 text-warning"><Clock3 className="h-4 w-4" /></div><div className="min-w-0 flex-1"><p className="text-xs font-bold">Pier P3 reinforcement</p><p className="text-[10px] text-muted-foreground">12 Sep · 75% baseline</p></div><Badge tone="warning">Watch</Badge></div></div></Card>
      <Card><div className="flex items-center justify-between"><div><p className="text-[10px] font-bold uppercase tracking-widest text-warning">Schedule variance</p><h3 className="mt-1 text-lg font-extrabold">-6%</h3></div><Badge tone="danger">At risk</Badge></div><div className="mt-4"><ProgressBar value={63} tone="danger" /></div><p className="mt-3 text-xs leading-5 text-muted-foreground">Verified field progress is 63% against 75% planned for Pier P3 Reinforcement. Predicted completion is 14 Sep.</p></Card>
    </div>
    <Card><div className="flex items-center justify-between gap-3"><div><p className="text-[10px] font-bold uppercase tracking-widest text-primary">Pending schedule changes</p><h3 className="mt-1 text-lg font-extrabold">Revision 1.1 · Delayed steel delivery</h3></div><Badge tone="warning">Pending approval</Badge></div><div className="mt-4 flex flex-wrap gap-2"><Button size="sm" onClick={() => onScreen("planning")}>Review revision</Button><Button size="sm" variant="outline" onClick={() => onScreen("planning")}>View baseline</Button></div></Card>
  </div>;
}

function ScheduleImport({ onImported }: { onImported: () => void }) {
  const [showPreview, setShowPreview] = useState(false);
  return <Card className="border-primary/20 bg-primary/5">
    <div className="flex items-start justify-between gap-3"><div><p className="text-[10px] font-bold uppercase tracking-widest text-primary">Import / upload schedule</p><h2 className="mt-1 text-lg font-extrabold">Choose a mock planning source</h2><p className="mt-1 text-xs text-muted-foreground">Frontend prototype only — no file or external integration is connected.</p></div><Upload className="h-5 w-5 text-primary" /></div>
    <div className="mt-4 grid gap-2 sm:grid-cols-5">{["Import Excel", "Import CSV", "Import Primavera P6", "Import MS Project", "Create Manually"].map(label => <Button key={label} size="sm" variant={label === "Create Manually" ? "outline" : "default"} onClick={() => { setShowPreview(true); onImported(); }}><Upload />{label}</Button>)}</div>
    <p className="mt-3 text-[10px] text-muted-foreground">Mock import options only. No file or external integration is connected.</p>
    {showPreview && <div className="mt-5 rounded-xl border border-border bg-card p-3"><div className="flex items-center justify-between gap-3"><h3 className="text-sm font-extrabold">Schedule Import Preview</h3><Badge tone="success">Mock file loaded</Badge></div><div className="mt-3 overflow-x-auto"><table className="w-full min-w-[760px] text-left text-[10px]"><thead className="border-b border-border text-muted-foreground"><tr>{["Activity ID", "Activity Name", "WBS", "Start Date", "End Date", "Duration", "Planned Quantity", "Unit", "Dependency", "Milestone"].map(header => <th key={header} className="px-2 py-2 font-bold">{header}</th>)}</tr></thead><tbody>{previewRows.map(row => <tr key={row.id} className="border-b border-border last:border-0"><td className="px-2 py-2 font-bold">{row.id}</td><td className="px-2 py-2">{row.name}</td><td className="px-2 py-2">{row.wbs}</td><td className="px-2 py-2">{row.start}</td><td className="px-2 py-2">{row.end}</td><td className="px-2 py-2">{row.duration}</td><td className="px-2 py-2">{row.quantity}</td><td className="px-2 py-2">{row.unit}</td><td className="px-2 py-2">{row.dependency}</td><td className="px-2 py-2">{row.milestone}</td></tr>)}</tbody></table></div></div>}
  </Card>;
}

function PlanningTools({ canPlan }: { canPlan: boolean }) {
  const [activeTool, setActiveTool] = useState<"activity" | "milestone" | "dependency" | null>(null);
  return <Card><div className="flex items-start justify-between gap-3"><div><p className="text-[10px] font-bold uppercase tracking-widest text-primary">Plan construction logic</p><h2 className="mt-1 text-lg font-extrabold">Activities, milestones &amp; dependencies</h2><p className="mt-1 text-xs text-muted-foreground">Build the sequence that will become the approved baseline.</p></div><CalendarDays className="h-5 w-5 text-primary" /></div><div className="mt-4 grid gap-2 sm:grid-cols-3"><Button size="sm" disabled={!canPlan} onClick={() => setActiveTool("activity")}><Plus /> Create Activity</Button><Button size="sm" variant="outline" disabled={!canPlan} onClick={() => setActiveTool("milestone")}><Flag /> Add Milestone</Button><Button size="sm" variant="outline" disabled={!canPlan} onClick={() => setActiveTool("dependency")}><Link2 /> Add Dependency</Button></div>{activeTool === "activity" && <div className="mt-4 grid gap-3 rounded-xl border border-primary/20 bg-primary/5 p-3 sm:grid-cols-2"><label className="text-[10px] font-bold text-muted-foreground">ACTIVITY NAME<input className="mt-1 h-10 w-full rounded-xl border border-border bg-card px-3 text-xs" placeholder="e.g. Pier P4 reinforcement" /></label><label className="text-[10px] font-bold text-muted-foreground">WBS<select className="mt-1 h-10 w-full rounded-xl border border-border bg-card px-3 text-xs"><option>WBS-03.02 · Pier Construction</option><option>WBS-03.03 · Formwork</option></select></label><label className="text-[10px] font-bold text-muted-foreground">START DATE<input type="text" className="mt-1 h-10 w-full rounded-xl border border-border bg-card px-3 text-xs" placeholder="18 Sep 2026" /></label><label className="text-[10px] font-bold text-muted-foreground">BOQ LINK<input className="mt-1 h-10 w-full rounded-xl border border-border bg-card px-3 text-xs" placeholder="BOQ-260 · Reinforcement" /></label><Button size="sm" className="sm:col-span-2" onClick={() => setActiveTool(null)}>Save mock activity</Button></div>}{activeTool === "milestone" && <div className="mt-4 rounded-xl border border-border bg-secondary p-3"><p className="text-xs font-extrabold">Milestone register</p><div className="mt-3 grid gap-2 sm:grid-cols-3 text-[10px]"><span><b>Pier P3 foundation</b><br />05 Sep · Complete</span><span><b>North Viaduct deck start</b><br />20 Sep · Planned</span><span><b>Package C3 handover</b><br />30 Nov · Planned</span></div></div>}{activeTool === "dependency" && <div className="mt-4 rounded-xl border border-border bg-secondary p-3"><p className="text-xs font-extrabold">Dependency map</p><p className="mt-2 text-[10px] text-muted-foreground">ACT-0028 Foundation → ACT-0032 Reinforcement → ACT-0041 Shuttering</p></div>}</Card>;
}

function BaselineCard({ status, canEdit, onSubmit, onApprove, onRevision }: { status: "DRAFT" | "PENDING APPROVAL" | "APPROVED"; canEdit: boolean; onSubmit: () => void; onApprove: () => void; onRevision: () => void }) {
  const approved = status === "APPROVED";
  return <Card className={cn(approved && "border-success/30 bg-success/5")}>
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"><div><p className="text-[10px] font-bold uppercase tracking-widest text-primary">Baseline schedule</p><h2 className="mt-1 text-xl font-extrabold">Metro Line 6 — Package C3</h2><p className="mt-1 text-xs text-muted-foreground">North Viaduct · Version {approved ? "1.0" : "Draft"}</p></div><Badge tone={approved ? "success" : status === "PENDING APPROVAL" ? "warning" : "muted"}>{status}</Badge></div>
    <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4"><Metric label="Created by" value="Planning Engineer" /><Metric label="Created" value="05 Sep 2026" /><Metric label="Activities" value="428" /><Metric label="WBS / BOQ" value="86 / 214" /></div>
    <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3"><Metric label="Milestones" value="32" /><Metric label="Baseline progress" value="72%" tone="primary" /><Metric label="Field bridge" value="Active" tone="success" /></div>
    {approved && <div className="mt-4 flex items-center gap-2 rounded-xl border border-success/30 bg-success/10 p-3 text-xs font-bold text-success"><LockKeyhole className="h-4 w-4" /> Baseline Locked — official planned schedule for comparison</div>}
    <div className="mt-4 flex flex-wrap gap-2"><Button size="sm" variant="outline">View Schedule</Button>{approved ? <Button size="sm" onClick={onRevision}><History /> Create Revision</Button> : canEdit ? <><Button size="sm" variant="outline">Edit</Button><Button size="sm" onClick={onSubmit}>Submit for Approval</Button></> : <><Button size="sm" onClick={onApprove}><Check /> Approve</Button><Button size="sm" variant="outline">Request Changes</Button></>}</div>
    {status === "PENDING APPROVAL" && <p className="mt-3 text-xs text-warning">Awaiting Project Manager review. Approval locks Version 1.0 for field comparison.</p>}
    {status === "APPROVED" && <p className="mt-3 text-xs text-muted-foreground">Approved baselines cannot be edited. Create a revision to preserve the original plan and historical comparison.</p>}
    {status === "PENDING APPROVAL" && <div className="mt-4 border-t border-border pt-4"><p className="text-[10px] font-bold uppercase tracking-widest text-primary">Project Manager approval</p><div className="mt-2 flex flex-wrap gap-2"><Button size="sm" onClick={onApprove}><Check /> Approve Baseline</Button><Button size="sm" variant="outline">Request Changes</Button><Button size="sm" variant="outline">Review</Button></div></div>}
  </Card>;
}

function WbsAndBoq() {
  const [open, setOpen] = useState(true);
  return <div className="grid gap-5 lg:grid-cols-2"><Card><button type="button" onClick={() => setOpen(value => !value)} className="flex w-full items-center justify-between text-left"><div><p className="text-[10px] font-bold uppercase tracking-widest text-primary">WBS management</p><h2 className="mt-1 text-lg font-extrabold">North Viaduct work breakdown</h2></div><ChevronDown className={cn("h-4 w-4 transition-transform", open && "rotate-180")} /></button>{open && <div className="mt-4 space-y-2 text-xs"><div className="rounded-xl bg-secondary p-3 font-extrabold">WBS-01 · North Viaduct</div><div className="ml-3 rounded-xl border border-border p-3"><p className="font-bold">WBS-01.01 · Foundation</p><div className="mt-2 space-y-2 border-l border-border pl-3 text-muted-foreground"><p>WBS-01.01.01 · Excavation</p><p>WBS-01.01.02 · Reinforcement</p></div></div><div className="ml-3 rounded-xl border border-border p-3"><p className="font-bold">WBS-01.02 · Pier Construction</p><div className="mt-2 space-y-2 border-l border-border pl-3 text-muted-foreground"><p>WBS-01.02.01 · Pier P3 Reinforcement</p><p>WBS-01.02.02 · Pier P3 Shuttering</p></div></div></div>}</Card><Card><p className="text-[10px] font-bold uppercase tracking-widest text-primary">BOQ linking</p><h2 className="mt-1 text-lg font-extrabold">Pier P3 Reinforcement</h2><div className="mt-4 grid grid-cols-2 gap-2"><Metric label="Linked BOQ" value="BOQ-245" /><Metric label="Item" value="Steel Reinforcement" /><Metric label="Planned" value="20 MT" tone="primary" /><Metric label="Consumed" value="12 MT" /><Metric label="Remaining" value="8 MT" tone="success" /><Metric label="Unit" value="MT" /></div><p className="mt-3 rounded-xl border border-primary/20 bg-primary/5 p-3 text-xs leading-5 text-muted-foreground"><span className="font-bold text-foreground">WBS → Activity → BOQ → Planned quantity</span> stays connected in this mock baseline.</p></Card></div>;
}

function ActivityTable() {
  return <Card><div className="flex items-center justify-between gap-3"><div><p className="text-[10px] font-bold uppercase tracking-widest text-primary">Activity planning</p><h2 className="mt-1 text-lg font-extrabold">Baseline activities</h2></div><Badge tone="primary">428 activities</Badge></div><div className="mt-4 space-y-3 md:hidden">{activities.map(activity => <div key={activity.id} className="rounded-xl border border-border p-3"><div className="flex items-start justify-between gap-2"><div><p className="text-xs font-extrabold">{activity.name}</p><p className="mt-1 text-[10px] text-muted-foreground">{activity.id} · {activity.wbs}</p></div><Badge tone={activity.status === "At risk" ? "danger" : activity.status === "Complete" ? "success" : "muted"}>{activity.status}</Badge></div><div className="mt-3 grid grid-cols-2 gap-2 text-[10px]"><span><b>BOQ:</b> {activity.boq}</span><span><b>Planned:</b> {activity.quantity} {activity.unit}</span><span><b>Window:</b> {activity.start} → {activity.end}</span><span><b>Dependency:</b> {activity.dependency}</span><span><b>Responsible:</b> {activity.responsible}</span><span><b>Milestone:</b> {activity.milestone}</span></div><div className="mt-3"><div className="flex justify-between text-[10px]"><span>Baseline progress</span><b>{activity.progress}%</b></div><ProgressBar value={activity.progress} tone={activity.status === "At risk" ? "danger" : "primary"} /></div></div>)}</div><div className="mt-4 hidden overflow-x-auto md:block"><table className="w-full min-w-[800px] text-left text-[10px]">  <thead className="border-b border-border text-muted-foreground"><tr>{["Activity ID", "Activity", "WBS", "BOQ", "Start", "End", "Duration", "Quantity", "Unit", "Dependency", "Responsible person"].map(header => <th key={header} className="px-2 py-2 font-bold">{header}</th>)}</tr></thead><tbody>{activities.map(activity => <tr key={activity.id} className="border-b border-border last:border-0"><td className="px-2 py-3 font-bold">{activity.id}</td><td className="px-2 py-3 font-bold">{activity.name}</td><td className="px-2 py-3">{activity.wbs}</td><td className="px-2 py-3">{activity.boq}</td><td className="px-2 py-3">{activity.start}</td><td className="px-2 py-3">{activity.end}</td><td className="px-2 py-3">{activity.duration}</td><td className="px-2 py-3">{activity.quantity}</td><td className="px-2 py-3">{activity.unit}</td><td className="px-2 py-3">{activity.dependency}</td><td className="px-2 py-3">{activity.responsible}</td></tr>)}</tbody></table></div></Card>;
}

function GanttView() {
  const rows = [["Pier Foundation", "01 Sep → 05 Sep", "left-[4%] w-[22%]", "100%", "success"], ["Pier Reinforcement", "05 Sep → 12 Sep", "left-[26%] w-[38%]", "63%", "danger"], ["Shuttering", "12 Sep → 16 Sep", "left-[64%] w-[27%]", "0%", "primary"]] as const;
  return <Card><div className="flex items-center justify-between"><div><p className="text-[10px] font-bold uppercase tracking-widest text-primary">Gantt / schedule view</p><h2 className="mt-1 text-lg font-extrabold">Construction sequence</h2></div><Badge tone="muted">Mock timeline</Badge></div><div className="mt-4 space-y-4">{rows.map(([label, dates, position, progress, tone]) => <div key={label}><div className="flex items-center justify-between gap-3 text-xs"><span className="font-bold">{label}</span><span className="text-[10px] text-muted-foreground">{dates} · {progress}</span></div><div className="relative mt-2 h-6 rounded-lg bg-secondary"><div className={cn("absolute top-1 h-4 rounded-md", position, tone === "danger" ? "bg-danger" : tone === "success" ? "bg-success" : "bg-primary")} /></div></div>)}</div><div className="mt-4 flex justify-between text-[9px] text-muted-foreground"><span>01 Sep</span><span>05 Sep</span><span>12 Sep</span><span>16 Sep</span></div></Card>;
}

function PlannedVsActual() {
  return <div className="space-y-5"><Card className="border-primary/25"><div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"><div><p className="text-[10px] font-bold uppercase tracking-widest text-primary">Planning-to-execution bridge</p><h2 className="mt-1 text-xl font-extrabold">Planned vs actual</h2><p className="mt-1 text-xs text-muted-foreground">Pier P3 Reinforcement · ACT-0032 · 05 Sep → 12 Sep</p></div><Badge tone="danger">AT RISK</Badge></div><div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-5"><Metric label="Planned" value="75%" tone="primary" /><Metric label="Reported" value="62%" tone="warning" /><Metric label="AI estimated" value="64%" tone="warning" /><Metric label="Verified actual" value="63%" tone="success" /><Metric label="Variance" value="-12%" tone="danger" /></div><div className="mt-4 space-y-3"><div><div className="mb-1 flex justify-between text-[10px]"><span>Planned</span><b>75%</b></div><ProgressBar value={75} /></div><div><div className="mb-1 flex justify-between text-[10px]"><span>Verified actual</span><b className="text-success">63%</b></div><ProgressBar value={63} tone="success" /></div></div><div className="mt-4 grid gap-2 sm:grid-cols-3"><Metric label="Predicted completion" value="14 Sep" tone="warning" /><Metric label="Baseline completion" value="12 Sep" /><Metric label="Delay risk" value="HIGH" tone="danger" /></div></Card><Card className="border-danger/25 bg-danger/5"><div className="flex items-start gap-3"><div className="grid h-9 w-9 place-items-center rounded-xl bg-danger/10 text-danger"><Clock3 className="h-5 w-5" /></div><div><p className="text-[10px] font-bold uppercase tracking-widest text-danger">Delay prediction</p><h2 className="mt-1 text-lg font-extrabold">2 day predicted delay</h2><p className="mt-1 text-xs leading-5 text-muted-foreground">Baseline schedule + verified actual + field history + material, workforce, equipment and weather mock data indicate a high risk of missing the 12 Sep finish.</p></div></div></Card><Card><div className="flex items-center justify-between gap-3"><div><p className="text-[10px] font-bold uppercase tracking-widest text-primary">Recovery recommendation</p><h2 className="mt-1 text-lg font-extrabold">AI recommendation</h2></div><Badge tone="warning">Mock recommendation</Badge></div><div className="mt-4 grid gap-2 sm:grid-cols-3"><div className="rounded-xl border border-border p-3"><p className="text-xs font-extrabold">Option 1 · +6 workers</p><p className="mt-2 text-[10px] text-muted-foreground">Expected recovery</p><p className="mt-1 text-lg font-extrabold text-success">1.5 Days</p></div><div className="rounded-xl border border-border p-3"><p className="text-xs font-extrabold">Option 2 · +1 shift</p><p className="mt-2 text-[10px] text-muted-foreground">Expected recovery</p><p className="mt-1 text-lg font-extrabold text-success">2 Days</p></div><div className="rounded-xl border border-border p-3"><p className="text-xs font-extrabold">Option 3 · Equipment</p><p className="mt-2 text-[10px] text-muted-foreground">Expected recovery</p><p className="mt-1 text-lg font-extrabold text-success">1 Day</p></div></div><p className="mt-3 text-[10px] text-muted-foreground">AI RECOMMENDATION is a mock planning aid and is not connected to a real AI service.</p></Card></div>;
}

export function PlanningScheduleScreen({ role, onScreen }: { role: Role; onScreen: (screen: Screen) => void }) {
  const [status, setStatus] = useState<"DRAFT" | "PENDING APPROVAL" | "APPROVED">(role === "Planning Engineer" ? "DRAFT" : "PENDING APPROVAL");
  const [revision, setRevision] = useState(false);
  const [imported, setImported] = useState(false);
  const [tab, setTab] = useState<"overview" | "activities" | "comparison">("overview");
  const isApprover = role === "Project Manager";
  const canPlan = role === "Planning Engineer";
  return <div className="space-y-5">
    <Card className="border-primary/25 bg-primary/5"><div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between"><div><div className="flex flex-wrap items-center gap-2"><Badge tone="primary">Progress Control</Badge><Badge tone="muted">Mock data · frontend only</Badge></div><h2 className="mt-3 text-2xl font-extrabold">Planning &amp; Schedule</h2><p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">Source of planned and baseline data for field progress comparison, variance, delay prediction and recovery.</p></div><Button variant="outline" onClick={() => onScreen("sih-intelligence")}>Open Progress Control <ChevronRight /></Button></div></Card>
    <div className="space-y-2"><p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Progress Control modules</p><div className="flex gap-2 overflow-x-auto pb-1">{["Planning & Schedule", "WBS / BOQ", "Field Progress", "Evidence", "Verification", "Planned vs Actual", "Schedule Variance", "Delay Risk", "Recovery"].map(module => <span key={module} className={cn("whitespace-nowrap rounded-full border px-2.5 py-1 text-[10px] font-bold", module === "Planning & Schedule" ? "border-primary/30 bg-primary/10 text-primary" : "border-border bg-card text-muted-foreground")}>{module}</span>)}</div></div>
    <div className="flex gap-2 overflow-x-auto border-b border-border pb-2">{[["overview", "Baseline"], ["activities", "Activities & WBS"], ["comparison", "Planned vs Actual"]] .map(([value, label]) => <button type="button" key={value} onClick={() => setTab(value as typeof tab)} className={cn("whitespace-nowrap rounded-lg px-3 py-2 text-xs font-bold", tab === value ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground")}>{label}</button>)}</div>
    {tab === "overview" && <>{canPlan && <ScheduleImport onImported={() => setImported(true)} />}<PlanningTools canPlan={canPlan} /><BaselineCard status={status} canEdit={canPlan} onSubmit={() => setStatus("PENDING APPROVAL")} onApprove={() => setStatus("APPROVED")} onRevision={() => { setRevision(true); setStatus("DRAFT"); }} />{revision && <Card className="border-warning/25 bg-warning/5"><div className="flex items-center gap-3"><History className="h-5 w-5 text-warning" /><div><p className="text-[10px] font-bold uppercase tracking-widest text-warning">Schedule revision</p><h3 className="mt-1 text-sm font-extrabold">Version 1.1 · Delayed steel delivery</h3><p className="mt-1 text-xs text-muted-foreground">Original Baseline 1.0 is preserved. Created by Planning Engineer · Approval Pending.</p></div></div></Card>}<WbsAndBoq /><GanttView /></>}
    {tab === "activities" && <><ActivityTable /><WbsAndBoq /><GanttView /></>}
    {tab === "comparison" && <PlannedVsActual />}
    {isApprover && status === "PENDING APPROVAL" && <Card className="border-warning/30 bg-warning/5"><p className="text-[10px] font-bold uppercase tracking-widest text-warning">Project Manager view</p><h3 className="mt-1 text-lg font-extrabold">Schedule Awaiting Approval</h3><p className="mt-1 text-xs text-muted-foreground">Review the Planning Engineer submission, then approve to lock the baseline.</p><div className="mt-3 flex flex-wrap gap-2"><Button size="sm" onClick={() => setStatus("APPROVED")}><ShieldCheck /> Approve</Button><Button size="sm" variant="outline">Request Changes</Button></div></Card>}
    {imported && <p className="text-center text-[10px] text-muted-foreground">Mock schedule data loaded locally. No backend or external integration is connected.</p>}
  </div>;
}

import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState, type ComponentType } from "react";
import {
  Activity, AlertTriangle, ArrowLeft, ArrowRight, BarChart3, Bell, Bot, Box,
  BriefcaseBusiness, CalendarDays, Camera, Check, CheckCircle2, ChevronDown,
  ChevronRight, CircleUserRound, Clock3, CloudRain, Compass, Construction,
  FileCheck2, Gauge, HardHat, History, Home, ListChecks, LocateFixed, Map,
  MapPin, Menu, MessageSquareText, Package, Play, Plus, Radio, Route as RouteIcon,
  ScanLine, Search, Send, Settings, ShieldCheck, Sparkles, TimerReset, Truck,
  Upload, UserRound, Users, Video, Warehouse, Wrench, X, Zap, LoaderCircle, Eye, EyeOff,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { compareWithPrevious, uploadEvidence, type ComparisonResult, type UploadedEvidence } from "@/lib/evidence-service";
import { cameraService, CameraServiceError } from "@/lib/camera-service";
import { locationService, LocationServiceError } from "@/lib/location-service";
import { getOfflineItems, retryOfflineItem, saveOfflineItem, syncOfflineItems, type OfflineItem, type SyncStatus } from "@/lib/offline-sync-service";
import type { Role, Screen, Tone } from "@/app/types";
import { roleCopy, rolePaths } from "@/app/role-config";
import { notificationService } from "@/services/notificationService";
import { PlanningEngineerDashboard, PlanningScheduleScreen } from "@/components/PlanningSchedule";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { authService } from "@/services/authService";
import { aiService } from "@/services/aiService";
import { ApiError, api, type AnalyticsOverview } from "@/services/api";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "BuildSync — Construction Intelligence" },
      { name: "description", content: "A practical field operations platform for recording progress, managing issues, and keeping project teams aligned." },
      { property: "og:title", content: "BuildSync Mobile" },
      { property: "og:description", content: "Keep site records, progress updates, and project decisions in one place." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: ConstructionApp,
});

const toneClasses: Record<Tone, string> = {
  primary: "bg-primary/12 text-primary border-primary/25",
  success: "bg-success/12 text-success border-success/25",
  warning: "bg-warning/12 text-warning border-warning/25",
  danger: "bg-danger/12 text-danger border-danger/25",
  muted: "bg-secondary text-muted-foreground border-border",
};

function BuildSyncMark({ className = "h-5 w-5" }: { className?: string }) {
  return <svg aria-hidden="true" className={className} viewBox="0 0 24 24" fill="none">
    <path d="M4 18V7l5-3 5 3v11M14 18V9l5-3 1 1v11" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M4 18h16M9 12h5M9 8h5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    <circle cx="4" cy="7" r="1.5" fill="currentColor" />
    <circle cx="19" cy="6" r="1.5" fill="currentColor" />
  </svg>;
}

function StatusBadge({ children, tone = "muted" }: { children: React.ReactNode; tone?: Tone }) {
  return <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase", toneClasses[tone])}>{children}</span>;
}

function SectionTitle({ title, action, onAction }: { title: string; action?: string; onAction?: () => void }) {
  return <div className="mb-3 flex items-center justify-between"><h2 className="text-[15px] font-bold">{title}</h2>{action && <Button variant="ghost" size="sm" onClick={onAction} className="h-7 px-1 text-[11px] text-primary">{action}<ChevronRight /></Button>}</div>;
}

function MetricCard({ label, value, icon: Icon, tone = "primary", detail }: { label: string; value: string; icon: ComponentType<{ className?: string }>; tone?: Tone; detail?: string }) {
  return <div className="rounded-2xl border border-border bg-card p-3.5"><div className="mb-4 flex items-start justify-between"><span className="text-[11px] leading-tight text-muted-foreground">{label}</span><Icon className={cn("h-4 w-4", toneClasses[tone].split(" ")[1])} /></div><div className="text-2xl font-extrabold">{value}</div>{detail && <p className="mt-1 text-[10px] text-muted-foreground">{detail}</p>}</div>;
}

function Progress({ value, tone = "primary" }: { value: number; tone?: Tone }) {
  const bar = tone === "danger" ? "bg-danger" : tone === "warning" ? "bg-warning" : tone === "success" ? "bg-success" : "bg-primary";
  return <div className="h-1.5 overflow-hidden rounded-full bg-secondary"><div className={cn("h-full rounded-full transition-all duration-700", bar)} style={{ width: `${value}%` }} /></div>;
}

function Card({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("rounded-lg border border-border bg-card p-4 shadow-sm", className)}>{children}</div>;
}

function CollapsibleSection({ title, children, defaultOpen = true }: { title: string; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return <section className="space-y-3"><button type="button" onClick={() => setOpen(current => !current)} className="flex w-full items-center justify-between gap-3 text-left"><SectionTitle title={title} /></button>{open && <div className="space-y-3">{children}</div>}</section>;
}

function ActivityRow({ title, meta, status, tone = "muted", icon: Icon = Construction }: { title: string; meta: string; status: string; tone?: Tone; icon?: ComponentType<{ className?: string }> }) {
  return <div className="flex items-center gap-3 py-3 first:pt-0 last:pb-0"><div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-secondary"><Icon className="h-4 w-4 text-muted-foreground" /></div><div className="min-w-0 flex-1"><p className="truncate text-sm font-bold">{title}</p><p className="mt-0.5 truncate text-[11px] text-muted-foreground">{meta}</p></div><StatusBadge tone={tone}>{status}</StatusBadge></div>;
}

function ActivityLifecycle({ currentStep }: { currentStep: string }) {
  const steps = ["NOT STARTED", "STARTED", "IN PROGRESS", "SUBMITTED", "AI ANALYZED", "VERIFIED", "COMPLETED"];
  const currentIndex = steps.indexOf(currentStep);

  return <div className="mt-4" aria-label={`Activity lifecycle: ${currentStep}`}><div className="grid grid-cols-2 gap-2 sm:grid-cols-7">{steps.map((step, index) => {
    const isDone = index < currentIndex;
    const isCurrent = index === currentIndex;
    return <div key={step} aria-current={isCurrent ? "step" : undefined} className="flex min-w-0 flex-col gap-1.5"><div className={cn("h-2 w-full rounded-full", isDone ? "bg-success" : isCurrent ? "bg-primary" : "bg-secondary")} /><span className={cn("block text-[9px] font-bold uppercase leading-tight tracking-[0.04em]", isCurrent ? "text-primary" : isDone ? "text-success" : "text-muted-foreground")}>{step}</span></div>;
  })}</div></div>;
}

function StageFlow({ steps, currentStep }: { steps: string[]; currentStep: string }) {
  const currentIndex = steps.indexOf(currentStep);

  return <div className="mt-4"><div className="grid gap-2 sm:grid-cols-8">{steps.map((step, index) => {
    const isDone = index < currentIndex;
    const isCurrent = index === currentIndex;
    return <div key={step} className="flex items-center gap-2 sm:flex-col sm:items-start"> <span className={cn("inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[9px] font-extrabold", isDone ? "bg-success text-white" : isCurrent ? "bg-primary text-white" : "bg-secondary text-muted-foreground")} >{index + 1}</span><span className={cn("text-[9px] font-bold uppercase tracking-[0.08em]", isCurrent ? "text-primary" : isDone ? "text-success" : "text-muted-foreground")}>{step}</span></div>;
  })}</div></div>;
}

type ConstructionLifecycleState = "NOT STARTED" | "STARTED" | "IN PROGRESS" | "SUBMITTED" | "AI ANALYZED" | "VERIFIED" | "COMPLETED";

type ConstructionActivity = {
  id: string;
  title: string;
  state: ConstructionLifecycleState;
  plannedStart?: string;
  plannedCompletion?: string;
  plannedProgress?: number;
  reportedProgress?: number;
  aiEstimatedProgress?: number;
  verifiedProgress?: number;
  fieldUpdate?: string;
  aiConfidence?: string;
  evidenceAssessment?: string;
  engineerVerification?: string;
  predictedCompletion?: string;
  scheduleVariance?: string;
  delayRisk?: string;
  team?: string;
  assignedBy?: string;
  location?: string;
  responsible?: string;
  startTime?: string;
  lastUpdate?: string;
  evidence?: string;
  aiAnalysis?: string;
  verification?: string;
  tone: Tone;
};

function ConstructionActivityCard({ activity }: { activity: ConstructionActivity }) {
  return <Card className="overflow-hidden">
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-primary">Construction activity</p>
        <h2 className="mt-2 text-base font-extrabold sm:text-lg">{activity.title}</h2>
      </div>
      <StatusBadge tone={activity.tone}>{activity.state}</StatusBadge>
    </div>
    <div className="mt-4 flex items-end justify-between gap-3">
      <div>
        <p className="text-[10px] text-muted-foreground">Reported progress</p>
        <p className="text-2xl font-extrabold text-foreground">{displayValue(activity.reportedProgress, "%")}</p>
      </div>
      <div className="text-right">
        <p className="text-[10px] text-muted-foreground">Assigned team</p>
        <p className="text-sm font-extrabold text-foreground">{displayValue(activity.team)}</p>
      </div>
    </div>
    <div className="mt-4">{activity.reportedProgress === undefined ? <p className="text-xs text-muted-foreground">Progress unavailable</p> : <Progress value={activity.reportedProgress} tone={activity.tone} />}</div>
    <div className="mt-5 rounded-xl border border-border bg-surface-elevated p-3">
      <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-primary">Planning to execution</p>
      <div className="mt-3 grid gap-2 text-[10px] text-muted-foreground sm:grid-cols-4">
        {["Planned activity", "Field execution", "Evidence", "AI analysis", "Progress comparison", "Engineer verification", "Schedule impact", "Project health"].map((step, index) => <div key={step} className="flex items-center gap-2">
          <span className={cn("grid h-5 w-5 shrink-0 place-items-center rounded-full text-[9px] font-extrabold", index < 4 ? "bg-primary text-primary-foreground" : index === 5 && activity.verifiedProgress !== undefined ? "bg-success text-success-foreground" : "bg-secondary text-muted-foreground")}>{index + 1}</span>
          <span className={cn(index === 5 && activity.verifiedProgress !== undefined ? "text-success" : "text-foreground")}>{step}</span>
        </div>)}
      </div>
    </div>
    <ActivityLifecycle currentStep={activity.state} />
    <div className="mt-4 grid gap-2 text-[10px] text-muted-foreground sm:grid-cols-2">
      <div className="rounded-xl bg-secondary p-2.5"><p className="font-bold uppercase tracking-[0.08em] text-foreground">Planned activity</p><p className="mt-1 text-xs text-foreground">Start {displayValue(activity.plannedStart)}</p><p className="mt-1 text-xs text-foreground">Complete {displayValue(activity.plannedCompletion)}</p></div>
      <div className="rounded-xl bg-secondary p-2.5"><p className="font-bold uppercase tracking-[0.08em] text-foreground">Field execution</p><p className="mt-1 text-xs text-foreground">{displayValue(activity.fieldUpdate)}</p></div>
      <div className="rounded-xl border border-warning/30 bg-warning/8 p-2.5"><p className="font-bold uppercase tracking-[0.08em] text-foreground">AI analysis</p><p className="mt-1 text-xs text-warning">AI Estimated: {displayValue(activity.aiEstimatedProgress, "%")} · {displayValue(activity.aiConfidence)}</p><p className="mt-1 text-xs text-muted-foreground">{displayValue(activity.evidenceAssessment)}</p></div>
      <div className="rounded-xl border border-success/30 bg-success/8 p-2.5"><p className="font-bold uppercase tracking-[0.08em] text-foreground">Engineer verification</p><p className="mt-1 text-xs text-success">{displayValue(activity.engineerVerification)}</p><p className="mt-1 text-xs text-foreground">Engineer Verified: {displayValue(activity.verifiedProgress, "%")}</p></div>
      <div className="rounded-xl bg-secondary p-2.5 sm:col-span-2"><p className="font-bold uppercase tracking-[0.08em] text-foreground">Schedule impact</p><div className="mt-1 grid grid-cols-2 gap-2 sm:grid-cols-4"><span>Planned: {displayValue(activity.plannedCompletion)}</span><span>Predicted: {displayValue(activity.predictedCompletion)}</span><span>Variance: {displayValue(activity.scheduleVariance)}</span><span>Delay risk: {displayValue(activity.delayRisk)}</span></div></div>
    </div>
    <div className="mt-4 grid grid-cols-2 gap-2 text-[10px] text-muted-foreground sm:grid-cols-4">
      <div className="rounded-xl bg-secondary p-2.5"><p className="font-bold uppercase tracking-[0.08em] text-foreground">Planned</p><p className="mt-1 text-xs text-foreground">{displayValue(activity.plannedProgress, "%")}</p></div>
      <div className="rounded-xl bg-secondary p-2.5"><p className="font-bold uppercase tracking-[0.08em] text-foreground">Reported</p><p className="mt-1 text-xs text-foreground">{displayValue(activity.reportedProgress, "%")}</p></div>
      <div className="rounded-xl bg-secondary p-2.5"><p className="font-bold uppercase tracking-[0.08em] text-foreground">AI estimate</p><p className="mt-1 text-xs text-warning">{activity.aiEstimatedProgress === undefined ? "—" : `${activity.aiEstimatedProgress}%`}</p></div>
      <div className="rounded-xl bg-secondary p-2.5"><p className="font-bold uppercase tracking-[0.08em] text-foreground">Verified</p><p className={cn("mt-1 text-xs", activity.verifiedProgress === undefined ? "text-muted-foreground" : "text-success")}>{activity.verifiedProgress === undefined ? "Pending" : `${activity.verifiedProgress}%`}</p></div>
      {activity.startTime && <div className="rounded-xl bg-secondary p-2.5"><p className="font-bold uppercase tracking-[0.08em] text-foreground">Start time</p><p className="mt-1 text-xs text-foreground">{activity.startTime}</p></div>}
      <div className="rounded-xl bg-secondary p-2.5"><p className="font-bold uppercase tracking-[0.08em] text-foreground">Last update</p><p className="mt-1 text-xs text-foreground">{displayValue(activity.lastUpdate)}</p></div>
      <div className="rounded-xl bg-secondary p-2.5"><p className="font-bold uppercase tracking-[0.08em] text-foreground">Evidence</p><p className="mt-1 text-xs text-foreground">{displayValue(activity.evidence)}</p></div>
      <div className="rounded-xl bg-secondary p-2.5"><p className="font-bold uppercase tracking-[0.08em] text-foreground">AI analysis</p><p className={cn("mt-1 text-xs", activity.aiAnalysis ? "text-warning" : "text-muted-foreground")}>{displayValue(activity.aiAnalysis)}</p></div>
      <div className="rounded-xl bg-secondary p-2.5"><p className="font-bold uppercase tracking-[0.08em] text-foreground">Verification</p><p className={cn("mt-1 text-xs", activity.verification === "Verified" ? "text-success" : "text-muted-foreground")}>{displayValue(activity.verification)}</p></div>
    </div>
    <div className="mt-4 space-y-2 text-xs text-muted-foreground">
      <div className="flex items-start justify-between gap-3"><span className="font-bold text-foreground">Assigned by</span><span className="text-right">{displayValue(activity.assignedBy)}</span></div>
      <div className="flex items-start justify-between gap-3"><span className="font-bold text-foreground">Location</span><span className="text-right">{displayValue(activity.location)}</span></div>
      <div className="flex items-start justify-between gap-3"><span className="font-bold text-foreground">Responsible</span><span className="text-right">{displayValue(activity.responsible)}</span></div>
    </div>
  </Card>;
}

function ActivitiesScreen() {
  const projectId = projectIdFromStorage();
  const [activities, setActivities] = useState<ConstructionActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!projectId) {
      setLoading(false);
      setError("Project context is unavailable.");
      return;
    }
    let active = true;
    void api.get<Array<Record<string, unknown>>>(`/api/projects/${projectId}/activities`)
      .then(items => {
        if (!active) return;
        setActivities(items.map(item => {
          const progress = typeof item.reported_progress === "number"
            ? item.reported_progress
            : typeof item.progress_percentage === "number" ? item.progress_percentage : undefined;
          const status = String(item.status ?? "NOT_STARTED").toUpperCase();
          const state: ConstructionLifecycleState = ["NOT STARTED", "STARTED", "IN PROGRESS", "SUBMITTED", "AI ANALYZED", "VERIFIED", "COMPLETED"].includes(status)
            ? status as ConstructionLifecycleState
            : "NOT STARTED";
          return {
            id: String(item.id),
            title: String(item.name ?? "Untitled activity"),
            state,
            plannedProgress: undefined,
            reportedProgress: progress,
            fieldUpdate: String(item.description ?? ""),
            location: String(item.location ?? ""),
            team: "",
            tone: state === "COMPLETED" ? "success" : state === "IN PROGRESS" ? "primary" : "muted",
          };
        }));
      })
      .catch(() => { if (active) setError("Activities could not be loaded."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [projectId]);
  return <div className="space-y-4">
    <div className="flex gap-2">
      <div className="flex h-11 min-w-0 flex-1 items-center gap-2 rounded-xl border border-border bg-card px-3"><Search className="h-4 w-4 shrink-0 text-muted-foreground" /><input placeholder="Search activities" className="min-w-0 flex-1 bg-transparent text-sm outline-none" /></div>
      <Button size="icon" variant="outline" aria-label="Filter activities"><Menu /></Button>
    </div>
    {loading && <Card><p className="text-sm text-muted-foreground">Loading activities…</p></Card>}
    {error && <Card><p role="alert" className="text-sm text-danger">{error}</p></Card>}
    {!loading && !error && <div className="space-y-3">{activities.length ? activities.map(activity => <ConstructionActivityCard key={activity.id} activity={activity} />) : <Card><p className="text-sm text-muted-foreground">No activities were returned.</p></Card>}</div>}
    <OfflineOperations />
  </div>;
}

function SitePlanCard({ progress = "68%", zone = "Zone B • Pier P3" }: { progress?: string; zone?: string }) {
  const [zoom, setZoom] = useState(1);

  return (
    <Card className="overflow-hidden rounded-2xl bg-[#FFFFFF] p-0 text-[#111315]">
      <div className="site-plan-map relative overflow-hidden rounded-t-2xl bg-[#EEF0ED]">
        <svg
          aria-label="Construction GIS site plan"
          className="absolute inset-0 h-full w-full"
          viewBox="0 0 800 420"
          preserveAspectRatio="xMidYMid slice"
          style={{ transform: `scale(${zoom})`, transformOrigin: "center" }}
        >
          <rect width="800" height="420" fill="#EEF0ED" />
          <path d="M-20 65 C180 105 270 30 470 78 S690 112 820 48 L820 0 L-20 0Z" fill="#DCE8E5" />
          <path d="M-20 315 C150 270 260 350 430 308 S660 245 820 300 L820 420 L-20 420Z" fill="#E5EADB" />
          <g fill="#D7DAD7" stroke="#C5CAC5" strokeWidth="2">
            <path d="M70 58h92v58H70zM188 42h72v72h-72zM287 66h108v46H287zM520 42h92v62h-92z" />
            <path d="M86 278h88v58H86zM210 300h120v54H210zM492 280h92v64h-92zM628 300h106v58H628z" />
          </g>
          <g fill="none" stroke="#B9BFBA" strokeWidth="9" strokeLinecap="round">
            <path d="M-20 188 C150 156 244 210 382 176 S650 132 820 184" />
            <path d="M396 -20 C372 104 430 188 398 270 S370 370 386 440" />
            <path d="M-20 372 C140 334 236 376 370 350 S620 330 820 372" />
          </g>
          <g fill="none" stroke="#F8F9F7" strokeWidth="4" strokeLinecap="round">
            <path d="M-20 188 C150 156 244 210 382 176 S650 132 820 184" />
            <path d="M396 -20 C372 104 430 188 398 270 S370 370 386 440" />
            <path d="M-20 372 C140 334 236 376 370 350 S620 330 820 372" />
          </g>
          <g fill="none" stroke="#C2C8C2" strokeWidth="3">
            <path d="M42 145L154 114L212 186L120 234Z" />
            <path d="M470 120L590 98L684 168L594 226L470 198Z" />
            <path d="M470 252L594 226L684 270L594 328L470 304Z" />
          </g>
          <path d="M244 92 L560 116 L636 278 L548 354 L224 326 L174 188 Z" fill="#6C4DFF" fillOpacity=".08" stroke="#6C4DFF" strokeWidth="4" strokeDasharray="12 8" />
          <path d="M238 116 L390 128 L374 270 L214 252 Z" fill="#6C4DFF" fillOpacity=".18" stroke="#6C4DFF" strokeWidth="2" />
          <path d="M406 142 L548 152 L590 270 L412 256 Z" fill="#3F8A5B" fillOpacity=".2" stroke="#3F8A5B" strokeWidth="2" />
          <path d="M420 270 L566 282 L544 334 L422 320 Z" fill="#D9A52E" fillOpacity=".22" stroke="#D9A52E" strokeWidth="2" />
          <g fill="#6C4DFF" stroke="#FFFFFF" strokeWidth="3">
            <circle cx="300" cy="174" r="9" /><circle cx="352" cy="190" r="9" /><circle cx="438" cy="184" r="9" /><circle cx="500" cy="210" r="9" />
          </g>
          <g fontFamily="Inter, sans-serif" fontSize="13" fontWeight="700" fill="#4F5650">
            <text x="270" y="112">PROJECT BOUNDARY · C3</text>
            <text x="258" y="220">ZONE B · ACTIVE WORK</text>
            <text x="454" y="232">ZONE C · VERIFIED</text>
            <text x="436" y="310">MATERIAL HOLD</text>
            <text x="100" y="150">NORTH VIADUCT</text>
            <text x="615" y="132">GRID P4</text>
          </g>
          <g stroke="#C7463A" strokeWidth="4" strokeLinecap="round">
            <path d="M610 236l12 12m0-12l-12 12" />
          </g>
        </svg>

        <div className="absolute left-3 top-3 rounded-md border border-[#FFFFFF] bg-[#FFFFFF]/90 px-2 py-1 text-[9px] font-bold uppercase tracking-[0.12em] text-[#111315] shadow-sm">
          Live site plan
        </div>
        <div className="absolute right-3 top-3 flex flex-col overflow-hidden rounded-md border border-[#D7DAD7] bg-[#FFFFFF]/95 shadow-sm">
          <button type="button" aria-label="Zoom in" className="grid h-7 w-7 place-items-center border-b border-[#D7DAD7] text-sm font-bold text-[#111315] hover:bg-[#F3F3F3]" onClick={() => setZoom(value => Math.min(1.12, value + 0.04))}>+</button>
          <button type="button" aria-label="Zoom out" className="grid h-7 w-7 place-items-center text-sm font-bold text-[#111315] hover:bg-[#F3F3F3]" onClick={() => setZoom(value => Math.max(1, value - 0.04))}>−</button>
        </div>
        <div className="absolute bottom-3 left-3 flex items-center gap-2 rounded-md border border-[#FFFFFF] bg-[#FFFFFF]/95 px-2.5 py-1.5 text-[10px] font-bold text-[#111315] shadow-sm">
          <MapPin className="h-3.5 w-3.5 text-[#6C4DFF]" />
          {zone}
        </div>
        <div className="absolute bottom-3 right-3 rounded-md border border-[#FFFFFF] bg-[#FFFFFF]/95 px-2 py-1 text-[9px] font-bold text-[#4F5650] shadow-sm">
          ACT-0032 · Grid P3
        </div>
      </div>

      <div className="grid grid-cols-3 divide-x divide-[#DDDED8]/15 px-4 py-3">
        <div>
          <p className="text-[9px] uppercase tracking-[0.14em] text-[#DDDED8] opacity-70">Progress</p>
          <p className="mt-1 text-lg font-extrabold text-[#FFFFFF]">{progress}</p>
        </div>
        <div className="pl-3">
          <p className="text-[9px] uppercase tracking-[0.14em] text-[#DDDED8] opacity-70">Open issues</p>
          <p className="mt-1 text-lg font-extrabold text-[#C74634]">—</p>
        </div>
        <div className="pl-3">
          <p className="text-[9px] uppercase tracking-[0.14em] text-[#DDDED8] opacity-70">Updated</p>
          <p className="mt-1 text-lg font-extrabold text-[#FFFFFF]">—</p>
        </div>
      </div>
    </Card>
  );
}

function AppHeader({ role, onScreen, onMenu }: { role: Role; onScreen: (screen: Screen) => void; onMenu: () => void }) {
  const info = roleCopy[role];
  const [hasUnreadNotifications, setHasUnreadNotifications] = useState(false);
  useEffect(() => {
    let active = true;
    notificationService.getByRole(role)
      .then(notifications => {
        if (active) setHasUnreadNotifications(notifications.some(notification => !notification.read));
      })
      .catch(() => {
        if (active) setHasUnreadNotifications(false);
      });
    return () => { active = false; };
  }, [role]);
  return <header className="sticky top-0 z-30 border-b border-border/80 bg-background/95 px-5 pb-3 pt-4 backdrop-blur"><div className="mx-auto flex max-w-lg items-center gap-3"><Button variant="ghost" size="icon" aria-label="Open navigation" className="min-[900px]:hidden" onClick={onMenu}><Menu /></Button><div className="grid h-10 w-10 place-items-center rounded-xl border border-primary/30 bg-primary/10 text-primary"><BuildSyncMark className="h-5 w-5" /></div><div className="min-w-0 flex-1"><p className="truncate text-sm font-extrabold">{info.title}</p><p className="truncate text-[10px] text-muted-foreground">{info.subtitle}</p></div><SyncStatusIndicator /><Button variant="ghost" size="icon" aria-label="Notifications" className="relative" onClick={() => onScreen("notifications")}><Bell />{hasUnreadNotifications && <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-danger ring-2 ring-background" />}</Button><Button variant="ghost" size="icon" aria-label="Profile" onClick={() => onScreen("profile")}><CircleUserRound /></Button></div></header>;
}

function SyncStatusIndicator() {
  const [status, setStatus] = useState<SyncStatus>(() => typeof navigator !== "undefined" && navigator.onLine ? "ONLINE" : "OFFLINE");
  const [pending, setPending] = useState<OfflineItem[]>([]);
  useEffect(() => {
    const refresh = () => setPending(getOfflineItems());
    const online = () => { setStatus("SYNCING"); void syncOfflineItems().then(items => { setPending(items); setStatus("SYNCED"); }); };
    const offline = () => setStatus("OFFLINE");
    refresh();
    window.addEventListener("online", online);
    window.addEventListener("offline", offline);
    return () => { window.removeEventListener("online", online); window.removeEventListener("offline", offline); };
  }, []);
  const tone: Tone = status === "OFFLINE" || status === "SYNC FAILED" ? "danger" : status === "SYNCING" ? "warning" : status === "SYNCED" ? "success" : "primary";
  return <StatusBadge tone={tone}>{status === "SYNCING" && <LoaderCircle className="h-3 w-3 animate-spin" />}{status}{pending.some(item => item.status === "PENDING SYNC") && " · Pending Sync"}</StatusBadge>;
}

function OfflineQueue({ items, onRetry }: { items: OfflineItem[]; onRetry: (id: string) => void }) {
  if (items.length === 0) return null;
  return <Card><SectionTitle title="Offline items" /><div className="space-y-3">{items.map(item => <div key={item.id} className="flex items-center gap-3"><div className="min-w-0 flex-1"><p className="text-xs font-bold">{item.title}</p><p className="mt-1 text-[10px] text-muted-foreground">{item.type} · Saved offline</p></div><StatusBadge tone={item.status === "SYNCED" ? "success" : item.status === "SYNC FAILED" ? "danger" : "warning"}>{item.status}</StatusBadge>{item.status === "SYNC FAILED" && <Button size="sm" variant="outline" onClick={() => onRetry(item.id)}>Retry</Button>}</div>)}</div></Card>;
}

function BottomNav({ role, screen, onScreen }: { role: Role; screen: Screen; onScreen: (screen: Screen) => void }) {
  const sets: Partial<Record<Role, [Screen, string, ComponentType<{ className?: string }>][]>> = {
    Worker: [["home", "Home", Home], ["activities", "Tasks", ListChecks], ["capture", "Report", AlertTriangle], ["profile", "Profile", UserRound]],
    "Field Engineer": [["home", "Home", Home], ["activities", "Activities", ListChecks], ["capture", "Capture", Camera], ["evidence", "Evidence", History], ["profile", "Profile", UserRound]],
    "Project Manager": [["home", "Overview", Home], ["sih-intelligence", "Progress", Activity], ["activities", "Projects", Construction], ["analytics", "Reports", BarChart3], ["profile", "Profile", UserRound]],
    "Planning Engineer": [["home", "Plan", Home], ["planning", "Schedule", CalendarDays], ["sih-intelligence", "Progress", Activity], ["profile", "Profile", UserRound]],
    "Material Manager": [["home", "Home", Home], ["inventory", "Inventory", Package], ["capture", "Movement", ScanLine], ["profile", "Profile", UserRound]],
    Driver: [["home", "Trip", RouteIcon], ["trip", "Map", Map], ["activities", "History", History], ["profile", "Profile", UserRound]],
    "QA/QC Engineer": [["home", "Home", Home], ["inspection", "Inspect", FileCheck2], ["evidence", "Evidence", Camera], ["profile", "Profile", UserRound]],
  };
  const items = sets[role] ?? [["home", "Home", Home], ["activities", "Activity", ListChecks], ["timeline", "Timeline", History], ["ai", "Recommendations", Sparkles], ["profile", "Profile", UserRound]];
  return <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-surface/95 px-3 pb-[max(10px,env(safe-area-inset-bottom))] pt-2 backdrop-blur"><div className="mx-auto flex max-w-lg justify-around">{items.map(([target, label, Icon]) => <button type="button" key={label} onClick={() => onScreen(target)} className={cn("flex min-w-14 flex-col items-center gap-1 rounded-xl px-2 py-1.5 text-[9px] font-bold transition-colors", screen === target ? "text-primary" : "text-muted-foreground")}><Icon className="h-[19px] w-[19px]" />{label}</button>)}</div></nav>;
}

function WorkspaceRail({ role, screen, onScreen, open, onClose }: { role: Role; screen: Screen; onScreen: (screen: Screen) => void; open: boolean; onClose: () => void }) {
  const items: [Screen, string, ComponentType<{ className?: string }>][] = [
    ["home", "Overview", Home],
    ["sih-intelligence", "Progress Control", Activity],
    ["planning", "Planning & Schedule", CalendarDays],
    ["activities", "Activities", ListChecks],
    ["timeline", "Timeline", History],
    ["analytics", "Reports", BarChart3],
  ];
  const visibleItems = role === "Planning Engineer" ? items.filter(([target]) => roleScreens[role].includes(target)) : items;
  return <aside className={cn("workspace-rail z-[60] w-64", open ? "fixed inset-y-0 left-0 flex flex-col p-5 shadow-2xl" : "hidden", "min-[900px]:relative min-[900px]:w-auto min-[900px]:shadow-none")}><div className="mb-12 flex items-center gap-3"><div className="grid h-9 w-9 place-items-center rounded-md bg-primary text-primary-foreground"><BuildSyncMark className="h-5 w-5" /></div><span className="text-lg font-extrabold">BuildSync</span><Button variant="ghost" size="icon" aria-label="Close navigation" className="ml-auto min-[900px]:hidden" onClick={onClose}><X /></Button></div><p className="mb-3 px-3 text-[10px] font-bold uppercase tracking-widest opacity-45">Workspace</p><nav className="space-y-1">{visibleItems.map(([target, label, Icon]) => <button type="button" key={target} data-active={screen === target} onClick={() => onScreen(target)} className={cn("flex w-full items-center gap-3 rounded-md py-3 text-left text-sm font-semibold transition-colors hover:bg-sidebar-accent", target === "planning" ? "pl-8 text-[13px]" : "px-3")}><Icon className="h-4 w-4" />{label}</button>)}</nav><div className="mt-auto border-t border-sidebar-border pt-5"><p className="px-3 text-[10px] uppercase tracking-widest opacity-45">Signed in as</p><p className="mt-2 px-3 text-sm font-bold">{role}</p><button type="button" onClick={() => onScreen("profile")} className="mt-3 flex w-full items-center gap-3 rounded-md px-3 py-3 text-left text-sm font-semibold hover:bg-sidebar-accent"><CircleUserRound className="h-4 w-4" />Profile</button></div></aside>;
}

function WorkspaceSummary() {
  return <aside className="workspace-summary hidden"><div className="mb-10"><p className="text-[10px] font-bold uppercase tracking-widest opacity-50">Active project</p><h2 className="mt-3 text-xl font-extrabold">Metro Line 6</h2><p className="mt-1 text-xs opacity-60">Package C3 · North Viaduct</p></div><div className="border-b border-white/15 pb-6"><p className="text-[10px] uppercase tracking-widest opacity-50">Overall progress</p><div className="mt-4 flex items-end justify-between"><span className="text-5xl font-extrabold">—</span><span className="mb-1 text-xs text-primary">—</span></div><div className="mt-5 h-1.5 overflow-hidden rounded-full bg-white/15"><div className="h-full w-0 bg-primary" /></div></div><div className="space-y-4 py-6"><div className="flex items-center justify-between"><span className="text-xs opacity-60">Open issues</span><span className="font-bold text-danger">—</span></div><div className="flex items-center justify-between"><span className="text-xs opacity-60">Active workers</span><span className="font-bold">—</span></div><div className="flex items-center justify-between"><span className="text-xs opacity-60">Schedule variance</span><span className="font-bold text-warning">—</span></div></div><div className="mt-auto rounded-md border border-white/15 p-4"><p className="text-xs font-bold">Site status</p><p className="mt-2 text-xs leading-5 opacity-60">Project status is available from the authenticated backend workspace.</p></div></aside>;
}

function Welcome({ onLogin, onDemo }: { onLogin: () => void; onDemo: () => void }) {
  const capabilities = [
    ["Field Evidence", "Capture & verify", Camera],
    ["Live Progress", "Plan vs actual", Activity],
    ["Early Risk", "Predict & recover", AlertTriangle],
  ] as const;

  return <main className="mobile-screen flex min-h-screen items-center overflow-x-hidden bg-[#FAFAF8] px-5 py-8 text-foreground sm:px-8 sm:py-12">
    <section className="mx-auto flex w-full max-w-[520px] flex-col items-center text-center">
      <div className="grid h-14 w-14 place-items-center rounded-2xl bg-primary text-primary-foreground">
        <BuildSyncMark className="h-7 w-7" />
      </div>
      <p className="mt-4 text-xl font-extrabold tracking-tight">Build<span className="text-primary">Sync</span></p>

      <div className="mt-12 sm:mt-16">
        <h1 className="text-[2.15rem] font-extrabold leading-[1.1] tracking-tight sm:text-5xl">Keep every <span className="text-primary">site decision</span> moving.</h1>
        <p className="mx-auto mt-5 max-w-md text-base leading-7 text-muted-foreground">Connect planning, field execution and project intelligence.</p>
      </div>

      <div className="mt-8 flex w-full flex-col gap-3 sm:mt-10">
        <Button size="lg" className="h-13 w-full bg-[#0D3BFF] text-white hover:bg-[#0835E6]" onClick={onLogin}>Sign in →</Button>
        <Button size="lg" variant="outline" className="h-13 w-full border-border bg-white text-muted-foreground hover:border-primary/40 hover:bg-white hover:text-foreground" onClick={onDemo}>View demo workspace</Button>
      </div>

      <div className="mt-12 w-full border-t border-border pt-7 text-left sm:mt-16">
        <div className="grid gap-4 sm:grid-cols-3 sm:gap-6">
          {capabilities.map(([title, detail, Icon]) => <div key={title} className="flex items-center gap-3 sm:block sm:text-center">
            <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-primary/8 text-primary sm:mx-auto"><Icon className="h-4 w-4" /></div>
            <div className="sm:mt-3"><p className="text-xs font-extrabold uppercase tracking-wide">{title}</p><p className="mt-1 text-xs text-muted-foreground">{detail}</p></div>
          </div>)}
        </div>
      </div>

      <div className="mt-12 border-t border-border pt-5 text-center sm:mt-16">
        <p className="text-xs font-bold text-foreground">BuildSync</p>
        <p className="mt-1 text-[11px] text-muted-foreground">Metro Line 6 • Package C3 • North Viaduct</p>
      </div>
    </section>
  </main>;
}

function LoginFlow({ screen, setScreen, onAuthenticated, loginError }: { screen: Screen; setScreen: (s: Screen) => void; onAuthenticated: (identifier: string, password: string) => void | Promise<void>; loginError?: string }) {
  const isOtp = screen === "otp";
  const isForgot = screen === "forgot";
  const [resetStage, setResetStage] = useState<"otp" | "password">("otp");
  const [loginIdentifier, setLoginIdentifier] = useState("worker@buildsync.demo");
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [otpError, setOtpError] = useState("");
  const [secondsRemaining, setSecondsRemaining] = useState(30);
  const [verificationState, setVerificationState] = useState<"idle" | "verified">("idle");
  const [formError, setFormError] = useState("");
  const [loading, setLoading] = useState(false);
  const [resetToken, setResetToken] = useState("");
  const [demoOpen, setDemoOpen] = useState(false);
  const demoAccounts: [Role, string][] = [["Worker", "worker@buildsync.demo"], ["Field Engineer", "engineer@buildsync.demo"], ["Site Engineer", "site@buildsync.demo"], ["Project Manager", "pm@buildsync.demo"], ["Safety Officer", "safety@buildsync.demo"], ["QA/QC Engineer", "qa@buildsync.demo"], ["Material Manager", "material@buildsync.demo"], ["Driver", "driver@buildsync.demo"], ["Equipment Manager", "equipment@buildsync.demo"], ["Admin", "admin@buildsync.demo"]];
  const submit = async () => {
    if (loading) return;
    if (isForgot) {
      if (!loginIdentifier.trim()) {
        setFormError("Enter your work email or phone to continue.");
        return;
      }
      setFormError("");
      setLoading(true);
      try {
        await authService.requestPasswordReset(loginIdentifier.trim());
        setScreen("otp");
        setOtpError("");
        setSecondsRemaining(600);
      } catch (error) {
        setFormError(error instanceof ApiError ? error.message : "Unable to send a verification code.");
      } finally {
        setLoading(false);
      }
      return;
    }
    if (isOtp) {
      if (resetStage === "otp") {
        setLoading(true);
        try {
          const response = await authService.verifyPasswordReset(loginIdentifier.trim(), otp);
          setResetToken(response.reset_token);
          setOtpError("");
          setVerificationState("verified");
          setResetStage("password");
        } catch (error) {
          setOtpError(error instanceof ApiError ? error.message : "That verification code is not valid. Check the code and try again.");
        } finally {
          setLoading(false);
        }
      } else if (password.length < 8 || password !== confirmPassword) {
        setOtpError(password.length < 8 ? "Use at least 8 characters for your new password." : "Passwords do not match.");
      } else {
        setLoading(true);
        try {
          await authService.completePasswordReset(loginIdentifier.trim(), resetToken, password);
          setOtpError("");
          setScreen("login");
          setPassword("");
          setConfirmPassword("");
        } catch (error) {
          setOtpError(error instanceof ApiError ? error.message : "Unable to update your password.");
        } finally {
          setLoading(false);
        }
      }
      return;
    }
    if (!loginIdentifier.trim() || !password.trim()) {
      setFormError("Enter your work email or password to continue.");
      return;
    }
    setFormError("");
    setLoading(true);
    try {
      await Promise.all([
        onAuthenticated(loginIdentifier, password),
        new Promise<void>(resolve => window.setTimeout(resolve, 350)),
      ]);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    if (!isOtp || resetStage !== "otp" || secondsRemaining <= 0) return;
    const timer = window.setInterval(() => setSecondsRemaining(value => Math.max(0, value - 1)), 1000);
    return () => window.clearInterval(timer);
  }, [isOtp, resetStage, secondsRemaining]);
  const title = isOtp ? (resetStage === "otp" ? "Verify your code" : "Create a new password") : isForgot ? "Reset access" : "Welcome to BuildSync";
  const description = isOtp ? (resetStage === "otp" ? "Enter the six-digit code sent to your registered email." : "Choose a secure password for your BuildSync account.") : isForgot ? "Enter your registered work email and we'll send a secure verification code." : "Sign in to continue to your construction workspace.";
  return <main className="mobile-screen flex min-h-screen flex-col items-center overflow-y-auto bg-[#FAFAF8] px-5 py-8 text-foreground sm:justify-center sm:py-12">
    <section className="w-full max-w-[440px]">
      <button type="button" aria-label="Back" className="mb-8 grid h-10 w-10 place-items-center rounded-full text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:absolute sm:left-6 sm:top-6" onClick={() => setScreen(screen === "login" ? "welcome" : "login")}><ArrowLeft className="h-5 w-5" /></button>
      <div className="text-center">
        <div className="mx-auto grid h-16 w-16 place-items-center rounded-2xl bg-primary text-primary-foreground shadow-sm"><BuildSyncMark className="h-8 w-8" /></div>
        <p className="mt-4 text-xl font-extrabold tracking-tight">Build<span className="text-primary">Sync</span></p>
        <h1 className="mt-10 text-3xl font-extrabold tracking-tight sm:text-[34px]">{title}</h1>
        <p className="mx-auto mt-3 max-w-sm text-sm leading-6 text-muted-foreground">{description}</p>
      </div>
      <div className="mt-9">
        {isOtp ? resetStage === "otp" ? <div><label className="block text-sm font-bold text-foreground">Verification code<input inputMode="numeric" maxLength={6} value={otp} onChange={event => { setOtp(event.target.value.replace(/\D/g, "")); setOtpError(""); }} className="mt-2 h-13 w-full rounded-xl border border-border bg-card px-4 text-center text-lg font-bold tracking-[0.4em] outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20" /></label><div className="mt-3 flex items-center justify-between text-xs"><span className={cn(verificationState === "verified" ? "text-success" : "text-muted-foreground")}>{verificationState === "verified" ? "Code verified" : secondsRemaining > 0 ? `Code expires in ${Math.floor(secondsRemaining / 60)}:${String(secondsRemaining % 60).padStart(2, "0")}` : "Code expired"}</span><button type="button" disabled={secondsRemaining > 0 || loading} onClick={() => void (async () => { setLoading(true); try { await authService.requestPasswordReset(loginIdentifier.trim()); setOtp(""); setOtpError(""); setSecondsRemaining(600); setVerificationState("idle"); } catch (error) { setOtpError(error instanceof ApiError ? error.message : "Unable to resend the verification code."); } finally { setLoading(false); } })()} className="font-bold text-primary disabled:text-muted-foreground">Resend OTP</button></div></div> : <div className="space-y-5"><p className="rounded-xl border border-success/25 bg-success/5 px-3 py-3 text-xs font-bold text-success">Verification successful. Create a new password.</p><label className="block text-sm font-bold text-foreground">New password<div className="relative mt-2"><input type={passwordVisible ? "text" : "password"} value={password} onChange={event => setPassword(event.target.value)} className="h-13 w-full rounded-xl border border-border bg-card px-4 pr-12 text-sm outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20" /><button type="button" aria-label={passwordVisible ? "Hide password" : "Show password"} onClick={() => setPasswordVisible(value => !value)} className="absolute right-1 top-1 grid h-11 w-11 place-items-center rounded-lg text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">{passwordVisible ? <EyeOff /> : <Eye />}</button></div></label><label className="block text-sm font-bold text-foreground">Confirm new password<input type="password" value={confirmPassword} onChange={event => setConfirmPassword(event.target.value)} className="mt-2 h-13 w-full rounded-xl border border-border bg-card px-4 text-sm outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20" /></label></div> : <div className="space-y-5">
          <label className="block text-sm font-bold text-foreground">{isForgot ? "Work email" : "Work email / phone number"}<input id="login-identifier" value={loginIdentifier} onChange={event => setLoginIdentifier(event.target.value)} placeholder={isForgot ? "name@company.com" : "name@company.com or phone number"} className="mt-2 h-13 w-full rounded-xl border border-border bg-card px-4 text-sm outline-none transition-colors placeholder:text-muted-foreground/60 focus:border-primary focus:ring-2 focus:ring-primary/20" /></label>
          <label className="block text-sm font-bold text-foreground">Password<div className="relative mt-2"><input type={passwordVisible ? "text" : "password"} value={password} onChange={event => setPassword(event.target.value)} className="h-13 w-full rounded-xl border border-border bg-card px-4 pr-12 text-sm outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20" /><button type="button" aria-label={passwordVisible ? "Hide password" : "Show password"} onClick={() => setPasswordVisible(value => !value)} className="absolute right-1 top-1 grid h-11 w-11 place-items-center rounded-lg text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">{passwordVisible ? <EyeOff /> : <Eye />}</button></div></label>
          <div className="flex justify-end"><button type="button" className="text-sm font-bold text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" onClick={() => setScreen("forgot")}>Forgot password?</button></div>
        </div>}
        {(loginError || otpError || formError) && <p role="alert" className="mt-5 rounded-xl border border-danger/25 bg-danger/5 px-3 py-2.5 text-xs font-semibold text-danger">{otpError || formError || "Unable to sign in. Check your credentials and try again."}</p>}
        <Button size="lg" className="mt-7 h-13 w-full justify-center rounded-xl bg-[#0D3BFF] text-sm text-white hover:bg-[#0835E6]" disabled={loading} onClick={() => void submit()}>{loading ? <><LoaderCircle className="animate-spin" /> Processing...</> : isOtp ? (resetStage === "otp" ? "Verify and continue" : "Update password") : isForgot ? "Send verification code" : "Sign in"}</Button>
        {!isOtp && !isForgot && <><div className="my-7 flex items-center gap-4 text-[11px] font-bold uppercase tracking-[0.16em] text-muted-foreground/70"><div className="h-px flex-1 bg-border" />OR<div className="h-px flex-1 bg-border" /></div><button type="button" className="h-13 w-full rounded-xl border border-border bg-card text-sm font-bold text-foreground transition-colors hover:border-primary/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" onClick={() => document.getElementById("login-identifier")?.focus()}>Continue with email</button><button type="button" className="mt-4 w-full text-sm font-bold text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" onClick={() => setDemoOpen(value => !value)}>View demo workspace <ChevronDown className={cn("ml-1 inline h-4 w-4 transition-transform", demoOpen && "rotate-180")} /></button>{demoOpen && <div className="mt-3 grid grid-cols-2 gap-2 rounded-xl border border-border bg-secondary/40 p-2 sm:grid-cols-3">{demoAccounts.map(([demoRole, identifier]) => <button type="button" key={demoRole} className="rounded-lg border border-border bg-card px-2 py-2.5 text-left text-[10px] font-bold transition-colors hover:border-primary hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" onClick={() => { setLoginIdentifier(identifier); setDemoOpen(false); }}>{demoRole}</button>)}</div>}</>}
        {isForgot && <button type="button" className="mt-5 w-full text-center text-sm font-bold text-muted-foreground hover:text-foreground" onClick={() => setScreen("login")}>Back to Sign In</button>}
      </div>
      <p className="mt-12 pb-2 text-center text-[11px] text-muted-foreground">BuildSync • Construction Intelligence</p>
    </section>
  </main>;
}

function Chart({ values = [32, 44, 41, 57, 62, 71, 68, 78], danger = false }: { values?: number[]; danger?: boolean }) {
  return <div className="relative mt-5 flex h-28 items-end gap-2 border-b border-border pb-1">{values.map((v, i) => <div key={i} className="flex h-full flex-1 items-end"><div className={cn("w-full rounded-t-sm", danger && i > 5 ? "bg-danger" : "bg-primary", i % 2 ? "opacity-60" : "opacity-100")} style={{ height: `${v}%` }} /></div>)}</div>;
}

type DashboardActivity = {
  id: number;
  name: string;
  zone?: string | null;
  status?: string;
  progress_percentage?: number;
  last_updated_at?: string;
};

type DashboardSnapshot = {
  activities: DashboardActivity[];
  assignments: Array<{ activity_id: number; user_id: number; assignment_role?: string }>;
  notifications: Array<{ id: number; title: string; message?: string; is_read?: boolean }>;
  overview: AnalyticsOverview | null;
  attendance: { present_workers?: number; assigned_workers?: number; checked_in_workers?: number } | null;
  materials: Array<{ id: number; name: string; current_quantity?: number; minimum_stock_level?: number; unit?: string }>;
  equipment: Array<{ id: number; name: string; status?: string }>;
  trips: Array<{ id: number; status?: string; material_description?: string; quantity?: number; vehicle_id?: number }>;
  safety: { total_incidents?: number; open_incidents?: number; critical_incidents?: number; ppe_compliance?: { percentage?: number | null } } | null;
  quality: { total_inspections?: number; passed?: number; failed?: number; open_defects?: number } | null;
  safetyIncidents: Array<{ id: number; incident_type?: string; severity?: string; status?: string }>;
  inspections: Array<{ id: number; inspection_type?: string; status?: string; score?: number }>;
  productivity: { value?: number | null } | null;
  workforceAnalytics: { worker_hours_today?: number; workforce_shortage?: { required_workers?: number | null; shortage_count?: number | null } } | null;
  equipmentAnalytics: { historical_utilization?: { value?: number | null } } | null;
  loading: boolean;
};

function useDashboardSnapshot(role: Role): DashboardSnapshot {
  const [snapshot, setSnapshot] = useState<DashboardSnapshot>({
    activities: [], assignments: [], notifications: [], overview: null, attendance: null,
    materials: [], equipment: [], trips: [], safety: null, quality: null, safetyIncidents: [], inspections: [], productivity: null, workforceAnalytics: null, equipmentAnalytics: null, loading: true,
  });

  useEffect(() => {
    const projectId = typeof window !== "undefined"
      ? window.sessionStorage.getItem("constructiq-project") ?? window.localStorage.getItem("constructiq-project")
      : null;
    const userId = typeof window !== "undefined"
      ? Number(JSON.parse(window.sessionStorage.getItem("constructiq-session") ?? window.localStorage.getItem("constructiq-session") ?? "{}").id)
      : 0;
    if (!projectId) {
      setSnapshot(current => ({ ...current, loading: false }));
      return;
    }
    const projectPath = `/api/projects/${projectId}`;
    const get = <T,>(path: string) => api.get<T>(path).catch(() => null);
    void Promise.all([
      get<DashboardActivity[]>(`${projectPath}/activities`),
      get<DashboardSnapshot["assignments"]>(`${projectPath}/workforce/assignments`),
      get<{ items: DashboardSnapshot["notifications"] }>(`/api/notifications?project_id=${projectId}&page_size=10`),
      get<AnalyticsOverview>(`${projectPath}/analytics/overview`),
      get<DashboardSnapshot["attendance"]>(`${projectPath}/workforce/summary`),
      get<DashboardSnapshot["materials"]>(`${projectPath}/materials`),
      get<DashboardSnapshot["equipment"]>(`${projectPath}/equipment`),
      get<DashboardSnapshot["trips"]>(`${projectPath}/vehicle-trips`),
      get<DashboardSnapshot["safety"]>(`${projectPath}/safety/summary`),
      get<DashboardSnapshot["quality"]>(`${projectPath}/quality/summary`),
      get<DashboardSnapshot["safetyIncidents"]>(`${projectPath}/safety/incidents`),
      get<DashboardSnapshot["inspections"]>(`${projectPath}/quality/inspections`),
      get<DashboardSnapshot["productivity"]>(`${projectPath}/analytics/productivity`),
      get<DashboardSnapshot["workforceAnalytics"]>(`${projectPath}/analytics/workforce`),
      get<DashboardSnapshot["equipmentAnalytics"]>(`${projectPath}/analytics/equipment`),
    ]).then(([activities, assignments, notifications, overview, attendance, materials, equipment, trips, safety, quality, safetyIncidents, inspections, productivity, workforceAnalytics, equipmentAnalytics]) => {
      const assigned = (activities ?? []).filter(activity =>
        role === "Project Manager" || role === "Admin" || role === "Planning Engineer"
          ? true
          : (assignments ?? []).some(item => item.activity_id === activity.id && item.user_id === userId),
      );
      setSnapshot({
        activities: assigned,
        assignments: assignments ?? [],
        notifications: notifications?.items ?? [],
        overview,
        attendance,
        materials: materials ?? [],
        equipment: equipment ?? [],
        trips: trips ?? [],
        safety,
        quality,
        safetyIncidents: safetyIncidents ?? [],
        inspections: inspections ?? [],
        productivity,
        workforceAnalytics,
        equipmentAnalytics,
        loading: false,
      });
    });
  }, [role]);
  return snapshot;
}

function dashboardPercent(value: number | undefined | null): string {
  return value === undefined || value === null ? "—" : `${Number(value).toFixed(1)}%`;
}

function DashboardNotifications({ data }: { data: DashboardSnapshot }) {
  if (data.notifications.length === 0) return <p className="py-4 text-center text-xs text-muted-foreground">No notifications were returned.</p>;
  return <div className="space-y-2">{data.notifications.slice(0, 3).map(item => <ActivityRow key={item.id} title={item.title} meta={item.message ?? "Backend notification"} status={item.is_read ? "Read" : "Unread"} tone={item.is_read ? "muted" : "warning"} icon={Bell} />)}</div>;
}

function RoleDataDashboard({ role, onScreen, data }: { role: Role; onScreen: (screen: Screen) => void; data: DashboardSnapshot }) {
  const isSafety = role === "Safety Officer";
  const isQuality = role === "QA/QC Engineer";
  const isMaterials = role === "Material Manager";
  const isEquipment = role === "Equipment Manager";
  const isDriver = role === "Driver";
  const title = isSafety ? "Safety incidents" : isQuality ? "Quality inspections" : isMaterials ? "Materials" : isEquipment ? "Equipment" : isDriver ? "Assigned trips" : "Assigned activities";
  const items = isMaterials ? data.materials.map(item => ({ title: item.name, meta: `${item.current_quantity ?? "—"} ${item.unit ?? ""} available`, status: item.minimum_stock_level !== undefined && (item.current_quantity ?? 0) <= item.minimum_stock_level ? "LOW" : "OK" })) :
    isEquipment ? data.equipment.map(item => ({ title: item.name, meta: "Backend equipment record", status: item.status ?? "—" })) :
    isDriver ? data.trips.map(item => ({ title: item.material_description ?? `Trip ${item.id}`, meta: `Vehicle ${item.vehicle_id ?? "—"}`, status: item.status ?? "—" })) :
    isSafety ? data.safetyIncidents.map(item => ({ title: item.incident_type ?? `Incident ${item.id}`, meta: item.severity ?? "—", status: item.status ?? "—" })) :
    isQuality ? data.inspections.map(item => ({ title: item.inspection_type ?? `Inspection ${item.id}`, meta: item.score === undefined ? "Score unavailable" : `Score ${item.score}`, status: item.status ?? "—" })) :
    data.activities.map(item => ({ title: item.name, meta: item.zone ?? "—", status: dashboardPercent(item.progress_percentage) }));
  return <div className="space-y-5"><SitePlanCard progress={dashboardPercent(data.overview?.progress?.overall_progress)} zone={role} /><Card><SectionTitle title={title} /><div className="grid grid-cols-2 gap-3"><MetricCard label="Records" value={String(items.length)} icon={ListChecks} /><MetricCard label="Notifications" value={String(data.notifications.length)} icon={Bell} tone="warning" />{isSafety && <MetricCard label="Open incidents" value={data.safety?.open_incidents === undefined ? "—" : String(data.safety.open_incidents)} icon={AlertTriangle} tone="danger" />}{isQuality && <MetricCard label="Open defects" value={data.quality?.open_defects === undefined ? "—" : String(data.quality.open_defects)} icon={AlertTriangle} tone="danger" />}{isMaterials && <MetricCard label="Low stock" value={String(data.materials.filter(item => item.minimum_stock_level !== undefined && (item.current_quantity ?? 0) <= item.minimum_stock_level).length)} icon={Package} tone="danger" />}{isEquipment && <MetricCard label="Equipment issues" value={String(data.equipment.filter(item => ["MAINTENANCE", "OUT_OF_SERVICE"].includes(item.status ?? "")).length)} icon={Wrench} tone="warning" />}{isDriver && <MetricCard label="Trips" value={String(data.trips.length)} icon={RouteIcon} tone="primary" />}</div></Card><Card><SectionTitle title="Live records" />{items.length ? items.slice(0, 6).map(item => <ActivityRow key={`${item.title}-${item.status}`} title={item.title} meta={item.meta} status={item.status} tone={item.status === "LOW" || item.status === "OUT_OF_SERVICE" ? "danger" : "primary"} />) : <p className="py-6 text-center text-xs text-muted-foreground">No records were returned.</p>}</Card><Card><SectionTitle title="Notifications" /><DashboardNotifications data={data} /></Card>{!isDriver && <Button className="w-full" onClick={() => onScreen("activities")}><ListChecks /> Open assigned work</Button>}</div>;
}

function WorkerDashboard({ onScreen, data }: { onScreen: (screen: Screen) => void; data: DashboardSnapshot }) {
  const task = data.activities[0];
  const progress = task?.progress_percentage;
  const completed = data.activities.filter(item => ["COMPLETED", "VERIFIED"].includes(item.status ?? "")).length;
  return <div className="space-y-5"><SitePlanCard progress={dashboardPercent(progress)} zone={task?.zone ?? "Assigned work"} /><Card className="border-primary/30 bg-primary/8"><div className="flex items-start justify-between"><div><p className="text-xs text-muted-foreground">Attendance</p><p className="mt-2 text-xl font-extrabold">{data.attendance?.checked_in_workers === undefined ? "—" : `${data.attendance.checked_in_workers} checked in`}</p><p className="mt-1 text-xs text-muted-foreground"><MapPin className="mr-1 inline h-3 w-3" />Backend attendance record</p></div><CheckCircle2 className="text-success" /></div></Card><section><SectionTitle title="Today's task" /><Card>{task ? <><div className="flex justify-between"><StatusBadge tone="primary">{task.status ?? "—"}</StatusBadge><span className="text-sm font-extrabold">{dashboardPercent(progress)}</span></div><h3 className="mt-4 font-extrabold">{task.name}</h3><p className="mt-1 text-xs text-muted-foreground">{task.zone ?? "—"}</p><div className="mt-5"><Progress value={Math.max(0, Math.min(100, progress ?? 0))} /></div></> : <p className="py-6 text-center text-xs text-muted-foreground">No assigned activities were returned.</p>}</Card></section><div className="grid grid-cols-2 gap-3"><MetricCard label="Assigned tasks" value={String(data.activities.length)} icon={ListChecks} /><MetricCard label="Tasks completed" value={String(completed)} icon={CheckCircle2} tone="success" /></div><Card><SectionTitle title="Notifications" /><DashboardNotifications data={data} /></Card><Button className="w-full" onClick={() => onScreen("capture")}><AlertTriangle /> Report issue</Button></div>;
}

function FieldDashboard({ onScreen, data }: { onScreen: (s: Screen) => void; data: DashboardSnapshot }) {
  const progress = data.overview?.progress?.overall_progress;
  return <div className="space-y-5"><SitePlanCard progress={dashboardPercent(progress)} zone="Assigned field work" /><Button className="pulse-ring h-20 w-full justify-between px-5 text-left" onClick={() => onScreen("capture")}><span><span className="block text-[10px] uppercase opacity-70">Primary action</span><span className="mt-1 block text-base font-extrabold">Capture site evidence</span></span><span className="grid h-10 w-10 place-items-center rounded-xl bg-primary-foreground/10"><Camera className="h-5 w-5" /></span></Button><div className="grid grid-cols-3 gap-2"><MetricCard label="Assigned" value={String(data.activities.length)} icon={ListChecks} /><MetricCard label="Evidence" value={data.overview?.evidence?.total === undefined ? "—" : String(data.overview.evidence.total)} icon={Upload} tone="success" /><MetricCard label="Pending" value={data.overview?.evidence?.pending === undefined ? "—" : String(data.overview.evidence.pending)} icon={Clock3} tone="warning" /></div><Card><div className="flex items-center justify-between"><div><p className="text-[10px] text-muted-foreground">CURRENT PROGRESS</p><p className="mt-1 text-xl font-extrabold">{dashboardPercent(progress)}</p></div><StatusBadge tone="muted">GPS unavailable</StatusBadge></div><div className="mt-4"><Progress value={Math.max(0, Math.min(100, progress ?? 0))} /></div></Card><section><SectionTitle title="Assigned activities" action="View all" onAction={() => onScreen("activities")} /><Card>{data.activities.length ? data.activities.slice(0, 4).map(item => <ActivityRow key={item.id} title={item.name} meta={item.zone ?? "—"} status={dashboardPercent(item.progress_percentage)} tone="primary" />) : <p className="py-6 text-center text-xs text-muted-foreground">No assigned activities were returned.</p>}</Card></section><Card><SectionTitle title="Notifications" /><DashboardNotifications data={data} /></Card></div>;
}

function EvidenceCard() {
  return <Card className="overflow-hidden p-0"><div className="relative h-36 overflow-hidden bg-surface-elevated map-grid"><div className="absolute inset-0 grid place-items-center"><Construction className="h-14 w-14 text-muted-foreground/30" /></div><div className="absolute left-3 top-3"><StatusBadge tone="success"><Check className="h-3 w-3" /> Verified</StatusBadge></div><div className="absolute bottom-3 right-3 rounded-lg bg-background/80 px-2 py-1 text-[10px]"><Camera className="mr-1 inline h-3 w-3" />3 photos</div></div><div className="p-4"><div className="flex justify-between gap-2"><div><p className="text-sm font-extrabold">Pier P3 · Rebar installation</p><p className="mt-1 text-[11px] text-muted-foreground">Zone B · 01 Sep, 13:15 · Arjun Patel</p></div><span className="text-sm font-extrabold text-primary">65%</span></div></div></Card>;
}

function ProjectDashboard({ onScreen, data }: { onScreen: (s: Screen) => void; data: DashboardSnapshot }) {
  const analytics = data.overview;
  const progress = analytics?.progress?.overall_progress;
  const plannedProgress = analytics?.progress?.planned_progress;
  const variance = analytics?.progress?.variance;
  const delayedActivities = analytics?.activities?.delayed;
  return <div className="space-y-5">
    <SitePlanCard progress={progress === undefined ? "—" : `${progress}%`} zone={analytics?.project.name ?? "Current project"} />
    <Card className="relative overflow-hidden border-primary/20"><div className="absolute right-0 top-0 h-full w-1 bg-primary" /><div className="flex items-start justify-between"><div><p className="text-[10px] font-bold text-muted-foreground">PROJECT HEALTH</p><h2 className="mt-2 text-2xl font-extrabold">{analytics?.project.status ?? "—"}</h2><p className="mt-1 text-xs text-muted-foreground">Backend project status</p></div><StatusBadge tone={analytics?.project.status === "ON_TRACK" ? "success" : "warning"}>{analytics?.project.status ?? "—"}</StatusBadge></div></Card>
    <CollapsibleSection title="Project KPIs"><div className="grid grid-cols-2 gap-3 md:grid-cols-4"><MetricCard label="Overall progress" value={progress === undefined ? "—" : `${progress}%`} detail="Backend analytics" icon={Activity} /><MetricCard label="Planned progress" value={plannedProgress === undefined ? "—" : `${plannedProgress}%`} detail="Schedule baseline" icon={CalendarDays} /><MetricCard label="Verified actual progress" value={progress === undefined ? "—" : `${progress}%`} detail={variance === undefined ? "Backend analytics" : `${variance}% variance`} icon={BarChart3} tone="warning" /><MetricCard label="Total workforce" value={analytics?.workforce?.total === undefined ? "—" : String(analytics.workforce.total)} detail="Active project workers" icon={Users} tone="success" />    <MetricCard label="Attendance" value={analytics?.workforce?.attendance_rate === undefined ? "—" : `${analytics.workforce.attendance_rate}%`} detail="Present today" icon={CheckCircle2} tone="success" /><MetricCard label="Worker hours today" value={data.workforceAnalytics?.worker_hours_today == null ? "—" : String(data.workforceAnalytics.worker_hours_today)} detail="Completed attendance intervals" icon={Clock3} tone="success" /><MetricCard label="PPE compliance" value={data.safety?.ppe_compliance?.percentage == null ? "—" : `${data.safety.ppe_compliance.percentage.toFixed(1)}%`} detail="Inspected workers" icon={ShieldCheck} tone="success" /><MetricCard label="Productivity" value={data.productivity?.value == null ? "—" : `${data.productivity.value.toFixed(1)}%`} detail="Actual / planned progress" icon={Gauge} tone="success" /><MetricCard label="Workforce shortage" value={data.workforceAnalytics?.workforce_shortage?.shortage_count == null ? "—" : String(data.workforceAnalytics.workforce_shortage.shortage_count)} detail="Required minus available" icon={AlertTriangle} tone="danger" /><MetricCard label="Workforce requirement" value={data.workforceAnalytics?.workforce_shortage?.required_workers == null ? "—" : String(data.workforceAnalytics.workforce_shortage.required_workers)} detail="Backend workforce data" icon={Users} tone="warning" /><MetricCard label="Active activities" value={analytics?.activities?.in_progress === undefined ? "—" : String(analytics.activities.in_progress)} detail="In progress now" icon={ListChecks} /><MetricCard label="Delayed activities" value={delayedActivities === undefined ? "—" : String(delayedActivities)} detail="Backend analytics" icon={TimerReset} tone="danger" /><MetricCard label="Critical issues" value="—" detail="Backend analytics" icon={AlertTriangle} tone="warning" /></div></CollapsibleSection>
    <Card className="border-warning/25 bg-warning/5"><div className="flex items-center justify-between gap-3"><div><p className="text-[10px] font-bold uppercase tracking-widest text-warning">Schedule review</p><h3 className="mt-1 text-sm font-extrabold">Planning workspace</h3><p className="mt-1 text-xs text-muted-foreground">Review the current project baseline and activities.</p></div><Button size="sm" onClick={() => onScreen("planning")}>Review</Button></div></Card>
    <section><SectionTitle title="Planned vs Actual" action="View reports" onAction={() => onScreen("analytics")} /><Card><div className="flex items-center justify-between"><div><p className="text-xs text-muted-foreground">Current schedule variance</p><p className="mt-1 text-xl font-extrabold">{variance === undefined ? "—" : `${variance}%`}</p></div><StatusBadge tone="warning">Backend analytics</StatusBadge></div><Chart values={[progress ?? 0, plannedProgress ?? 0]} /><div className="mt-3 flex gap-4 text-[10px] text-muted-foreground"><span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-primary" />Actual {dashboardPercent(progress)}</span><span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-muted-foreground" />Planned {dashboardPercent(plannedProgress)}</span></div></Card></section>
    <CollapsibleSection title="Operational status"><Card><ActivityRow title="Activity progress" meta={`Backend activities · ${analytics?.activities?.in_progress ?? "—"} in progress`} status={dashboardPercent(progress)} tone="warning" icon={Activity} /><ActivityRow title="Workforce" meta={`${analytics?.workforce?.total ?? "—"} assigned workers`} status={analytics?.workforce?.attendance_rate === undefined ? "—" : `${analytics.workforce.attendance_rate}%`} tone="success" icon={Users} /><ActivityRow title="Material status" meta={`${analytics?.materials?.total_material_types ?? "—"} material types`} status={`${analytics?.materials?.low_stock_count ?? "—"} low`} tone="warning" icon={Package} /><ActivityRow title="Equipment status" meta={`${analytics?.equipment?.total_equipment ?? "—"} equipment records`} status={`${analytics?.equipment?.active_equipment_issues ?? "—"} issues`} tone="warning" icon={Wrench} /><ActivityRow title="Safety status" meta={`${analytics?.safety?.total_incidents ?? "—"} incidents`} status={`${analytics?.safety?.open_incidents ?? "—"} open`} tone="warning" icon={ShieldCheck} /><ActivityRow title="Quality status" meta={`${analytics?.quality?.inspections ?? "—"} inspections`} status={`${analytics?.quality?.open_defects ?? "—"} open defects`} tone="success" icon={CheckCircle2} /></Card></CollapsibleSection>
    <button type="button" onClick={() => onScreen("ai")} className="w-full rounded-2xl border border-primary/25 bg-primary/8 p-4 text-left"><div className="flex items-start gap-3"><div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-primary/15"><Bot className="h-5 w-5 text-primary" /></div><div><p className="text-sm font-extrabold">AI Copilot</p><p className="mt-1 text-xs leading-5 text-muted-foreground">Ask about project health, risks, workforce, materials, and recovery actions.</p><p className="mt-3 text-xs font-bold text-primary">Open construction intelligence →</p></div></div></button>
    <section><SectionTitle title="Construction Replay" action="Open replay" onAction={() => onScreen("replay")} /><Card><div className="flex items-center justify-between"><div><p className="text-sm font-extrabold">{analytics?.project.name ?? "Current project"}</p><p className="mt-1 text-xs text-muted-foreground">Review recorded site events and interruptions.</p></div><Button size="icon" onClick={() => onScreen("replay")}><Play /></Button></div></Card></section>
    <section><SectionTitle title="Recent notifications" action="View all" onAction={() => onScreen("notifications")} /><Card><DashboardNotifications data={data} /></Card></section>
  </div>;
}

function MapPanel() {
  const [location, setLocation] = useState("Location unavailable");
  useEffect(() => {
    let active = true;
    void locationService.getCurrentLocation().then(currentLocation => {
      if (!active || currentLocation.latitude === null || currentLocation.longitude === null) return;
      setLocation(`${currentLocation.latitude.toFixed(5)}, ${currentLocation.longitude.toFixed(5)}`);
    });
    return () => { active = false; };
  }, []);
  return <div className="relative h-60 overflow-hidden rounded-2xl border border-border bg-surface-elevated map-grid"><div className="absolute left-[10%] top-[68%] h-1 w-[77%] -rotate-12 rounded-full bg-primary/20" /><div className="absolute left-[10%] top-[68%] h-1 w-[54%] -rotate-12 rounded-full bg-primary" /><div className="absolute left-[8%] top-[62%] grid h-8 w-8 place-items-center rounded-full bg-success text-white"><MapPin className="h-4 w-4" /></div><div className="absolute left-[47%] top-[42%] grid h-11 w-11 place-items-center rounded-full bg-primary text-primary-foreground ring-8 ring-primary/10"><Truck className="h-5 w-5" /></div><div className="absolute right-[8%] top-[18%] grid h-8 w-8 place-items-center rounded-full bg-danger text-white"><Warehouse className="h-4 w-4" /></div><div className="absolute left-3 top-3"><StatusBadge tone="primary"><Radio className="h-3 w-3" /> GPS · {location}</StatusBadge></div><div className="absolute bottom-3 left-3 right-3 flex items-center justify-between rounded-xl border border-border bg-background/90 p-3"><div><p className="text-[10px] font-bold uppercase text-muted-foreground">Apex Steel Yard → Store B</p><p className="text-sm font-extrabold">ETA unavailable</p></div><LocateFixed className="text-primary" /></div></div>;
}

function CaptureFlow({ onBack }: { onBack: () => void }) {
  const [step, setStep] = useState(0);
  const [mode, setMode] = useState<"photo" | "video">("photo");
  const [progress, setProgress] = useState(0);
  const [notes, setNotes] = useState("");
  const [location, setLocation] = useState("Location unavailable");
  const [date, setDate] = useState("");
  const [responsible, setResponsible] = useState("Foreman Joseph");
  const [media, setMedia] = useState<import("@/lib/camera-service").CameraMedia | null>(null);
  const [capturedLocation, setCapturedLocation] = useState<import("@/lib/location-service").Location>({ latitude: null, longitude: null, gpsAccuracy: null });
  const [activity, setActivity] = useState<{ id: string; name: string; zone: string; progress: number | null } | null>(null);
  const [uploadedEvidence, setUploadedEvidence] = useState<UploadedEvidence | null>(null);
  const [comparison, setComparison] = useState<ComparisonResult | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [captureError, setCaptureError] = useState("");
  const [gpsAccuracy, setGpsAccuracy] = useState<number | null>(null);
  const [uploadError, setUploadError] = useState("");
  const [savedOffline, setSavedOffline] = useState(false);
  const steps = ["Activity", "Capture", "Details", "Review"];
  useEffect(() => {
    const projectId = window.localStorage.getItem("constructiq-project");
    if (!projectId) {
      setCaptureError("No project is selected for evidence capture.");
      return;
    }
    void api.get<Array<Record<string, unknown>>>(`/api/projects/${projectId}/activities`)
      .then(activities => {
        const first = activities[0];
        if (!first) {
          setCaptureError("No assigned activity is available for evidence capture.");
          return;
        }
        setActivity({
          id: String(first.id),
          name: String(first.name ?? "Activity"),
          zone: String(first.zone ?? ""),
          progress: typeof first.progress_percentage === "number" ? first.progress_percentage : null,
        });
        if (typeof first.progress_percentage === "number") setProgress(first.progress_percentage);
      })
      .catch(() => setCaptureError("Assigned activities could not be loaded."));
  }, []);
  const capture = async (mediaType = mode, fromGallery = false) => {
    setCaptureError("");
    try {
      const media = fromGallery ? await cameraService.selectFromGallery() : mediaType === "video" ? await cameraService.recordVideo() : await cameraService.capturePhoto();
      const currentLocation = await locationService.getCurrentLocation();
      setMedia(media);
      setCapturedLocation(currentLocation);
      setGpsAccuracy(currentLocation.gpsAccuracy);
      setDate(media.capturedAt);
      setLocation(currentLocation.latitude === null || currentLocation.longitude === null
        ? "Location unavailable"
        : `${currentLocation.latitude.toFixed(5)}, ${currentLocation.longitude.toFixed(5)}`);
    } catch (error) {
      if (error instanceof CameraServiceError && error.code === "PERMISSION_DENIED") setCaptureError("Camera permission is denied. Enable camera access or choose evidence from your gallery.");
      else if (error instanceof LocationServiceError && error.code === "GPS_UNAVAILABLE") setCaptureError("GPS is unavailable. Check location services; you can save this evidence as a draft.");
      else setCaptureError("We could not capture evidence. Please try again.");
    }
  };
  const submit = async () => {
    if (!media || !activity) return;
    setUploadError("");
    if (typeof navigator !== "undefined" && !navigator.onLine) {
      saveOfflineItem({ type: "Evidence", title: "Pier P3 reinforcement evidence" });
      setUploadError("You are offline. Evidence is saved locally as a draft and can be uploaded when you reconnect.");
      setSavedOffline(true);
      setSubmitted(true);
      return;
    }

    try {
      const uploaded = await uploadEvidence(activity.id, media, progress, notes, capturedLocation);
      setUploadedEvidence(uploaded);
      if (uploaded.mediaType === "photo") {
        try {
          setComparison(await compareWithPrevious(uploaded.id));
        } catch (error) {
          const apiError = error instanceof ApiError ? error : undefined;
          setUploadError(apiError?.message ?? "Evidence was uploaded, but comparison could not be completed.");
        }
      }
      setSubmitted(true);
    } catch (error) {
      const apiError = error instanceof ApiError ? error : undefined;
      setUploadError(apiError?.message ?? "Evidence upload failed. Please check the file and try again.");
    }
  };
  const preview = {
    mediaType: media?.mediaType ?? mode,
    activity: activity?.name ?? "—",
    wbs: "—",
    location: location === "Location unavailable" ? null : location,
    zone: activity?.zone || "—",
    gpsAccuracy: gpsAccuracy === null ? "Unavailable" : `${gpsAccuracy}m`,
    date: date ? new Date(date).toLocaleDateString() : "—",
    timestamp: date ? new Date(date).toLocaleString() : "—",
    currentProgress: progress,
    responsible,
    fieldNotes: notes || "—",
  };
  if (submitted && uploadedEvidence) return <div className="flex min-h-[70vh] flex-col items-center justify-center text-center"><div className="grid h-20 w-20 place-items-center rounded-full bg-success/15"><Check className="h-9 w-9 text-success" /></div><h2 className="mt-6 text-2xl font-extrabold">Evidence submitted successfully</h2><p className="mt-2 text-sm text-muted-foreground">Evidence ID {uploadedEvidence.id} · {uploadedEvidence.status}</p>{uploadError && <p role="alert" className="mt-3 text-sm text-warning">{uploadError}</p>}{comparison && <div className="mt-4 max-w-md text-left text-xs"><StatusBadge tone="success">COMPARISON {comparison.comparisonStatus}</StatusBadge><p className="mt-2">OpenCV: {comparison.opencvDifference ? "completed" : "not returned"} · YOLO: {comparison.detections ? "completed" : "not returned"}</p><p className="mt-1">Gemini: {comparison.geminiExplanation ?? "provider result not returned"}</p></div>}<div className="mt-4 flex flex-wrap justify-center gap-2"><StatusBadge tone="success">{uploadedEvidence.status}</StatusBadge></div><Button className="mt-8" onClick={onBack}>Return to dashboard</Button></div>;
  return <div className="space-y-5">
    {captureError && <div role="alert" className="rounded-xl border border-warning/30 bg-warning/8 px-3 py-2 text-xs leading-5 text-warning">{captureError}</div>}
    {uploadError && <div role="alert" className="rounded-xl border border-danger/30 bg-danger/8 px-3 py-2 text-xs leading-5 text-danger">{uploadError}</div>}
    <div className="grid grid-cols-4 gap-2">{steps.map((label, i) => <div key={label}><div className={cn("h-1 rounded-full", i <= step ? "bg-primary" : "bg-border")} /><p className={cn("mt-2 text-center text-[9px]", i === step ? "text-primary" : "text-muted-foreground")}>{label}</p></div>)}</div>
    {step === 0 && <><h2 className="text-xl font-extrabold">Select Activity</h2><Card>{activity ? <ActivityRow title={activity.name} meta={`Activity ${activity.id} · ${activity.zone || "Zone unavailable"}`} status="Selected" tone="primary" /> : <p className="py-4 text-center text-xs text-muted-foreground">Loading assigned activities...</p>}</Card><Button className="w-full" disabled={!activity} onClick={() => setStep(1)}>Continue <ArrowRight /></Button></>}
    {step === 1 && <><h2 className="text-xl font-extrabold">Capture Evidence</h2><div className="relative h-[clamp(240px,75vw,330px)] overflow-hidden rounded-2xl border border-border bg-surface-elevated map-grid"><div className="absolute inset-8 border border-foreground/20" /><div className="absolute left-3 top-3"><StatusBadge tone={gpsAccuracy !== null && gpsAccuracy <= 10 ? "success" : "warning"}><LocateFixed className="h-3 w-3" /> GPS · {gpsAccuracy === null ? "Unavailable" : `${gpsAccuracy}m`}</StatusBadge></div><div className="absolute right-3 top-3 rounded-lg bg-background/80 px-2 py-1 text-[10px]">01 Sep · 13:42:18</div><div className="absolute inset-x-0 bottom-5 flex flex-wrap items-center justify-center gap-3 px-3"><Button size="sm" variant="secondary" onClick={async () => { setMode("photo"); await capture("photo"); setStep(2); }}><Camera /> Take Photo</Button><Button size="sm" variant="secondary" onClick={async () => { setMode("video"); await capture("video"); setStep(2); }}><Video /> Record Video</Button></div></div><Button variant="outline" className="w-full" onClick={async () => { await capture("photo", true); setStep(2); }}><Upload /> Select from Gallery</Button><Button variant="outline" className="w-full" onClick={() => setStep(1)}><Camera /> Retake</Button></>}
    {step === 2 && <><h2 className="text-xl font-extrabold">Add Progress and Field Notes</h2><Card><div className="grid gap-4 sm:grid-cols-2"><label className="text-xs font-bold text-muted-foreground">WBS<select className="mt-2 h-11 w-full rounded-xl border border-border bg-secondary px-3 text-sm text-foreground outline-none focus:border-primary"><option>WBS-03.02 · Pier Construction</option></select></label><label className="text-xs font-bold text-muted-foreground">Responsible person<select value={responsible} onChange={event => setResponsible(event.target.value)} className="mt-2 h-11 w-full rounded-xl border border-border bg-secondary px-3 text-sm text-foreground outline-none focus:border-primary"><option>Foreman Joseph</option><option>Site Engineer Nisha</option></select></label><label className="text-xs font-bold text-muted-foreground">Location<input value={location} onChange={event => setLocation(event.target.value)} className="mt-2 h-11 w-full rounded-xl border border-border bg-secondary px-3 text-sm text-foreground outline-none focus:border-primary" /></label><label className="text-xs font-bold text-muted-foreground">Date<input value={date} onChange={event => setDate(event.target.value)} className="mt-2 h-11 w-full rounded-xl border border-border bg-secondary px-3 text-sm text-foreground outline-none focus:border-primary" /></label></div><div className="mt-5 flex justify-between"><p className="text-sm font-bold">Progress percentage</p><span className="text-xl font-extrabold text-primary">{progress}%</span></div><input aria-label="Progress percentage" type="range" min="0" max="100" value={progress} onChange={event => setProgress(Number(event.target.value))} className="mt-5 w-full accent-primary" /><div className="mt-3 flex flex-wrap justify-between gap-2 text-xs text-muted-foreground"><span>Previous progress: 58%</span><span>GPS accuracy: {gpsAccuracy === null ? "Unavailable" : `${gpsAccuracy}m (mock)`}</span><span>Timestamp: 13:42:18 (mock)</span></div><label className="mt-6 block text-xs font-bold text-muted-foreground">Field notes<textarea value={notes} onChange={event => setNotes(event.target.value)} className="mt-2 h-28 w-full resize-none rounded-xl border border-border bg-secondary p-3 text-sm leading-6 text-foreground outline-none focus:border-primary" /></label></Card><Button className="w-full" onClick={() => setStep(3)}>Review</Button></>}
    {step === 3 && <><h2 className="text-xl font-extrabold">Review Evidence</h2><Card className="overflow-hidden p-0"><div className="grid h-36 place-items-center bg-surface-elevated map-grid"><div className="text-center"><Construction className="mx-auto h-10 w-10 text-muted-foreground/50" /><p className="mt-2 text-xs font-bold">{preview.mediaType === "photo" ? "Photo preview" : "Video preview"}</p></div></div><div className="space-y-3 p-4 text-xs"><div className="flex justify-between gap-3"><b>Activity</b><span className="text-right">{preview.activity}</span></div><div className="flex justify-between gap-3"><b>WBS</b><span className="text-right">{preview.wbs}</span></div><div className="flex justify-between gap-3"><b>Location</b><span className="text-right">{preview.location ?? preview.zone}</span></div><div className="flex justify-between gap-3"><b>GPS accuracy</b><span className="text-right">{preview.gpsAccuracy}</span></div><div className="flex justify-between gap-3"><b>Date</b><span className="text-right">{preview.date ?? preview.timestamp.split(" · ")[0]}</span></div><div className="flex justify-between gap-3"><b>Timestamp</b><span className="text-right">{preview.timestamp}</span></div><div className="flex justify-between gap-3"><b>Progress percentage</b><span className="text-right">{preview.currentProgress}%</span></div><div className="flex justify-between gap-3"><b>Responsible person</b><span className="text-right">{preview.responsible ?? responsible}</span></div><div><b>Field notes</b><p className="mt-1 text-muted-foreground">{preview.fieldNotes}</p></div></div></Card><Button variant="outline" className="w-full" onClick={() => setStep(1)}><Camera /> Retake</Button><Button className="w-full" onClick={submit}><Upload /> Submit</Button></>}
  </div>;
}

function OfflineOperations() {
  const [items, setItems] = useState<OfflineItem[]>(() => getOfflineItems());
  const save = (type: OfflineItem["type"], title: string) => setItems(current => [...current, saveOfflineItem({ type, title })]);
  const retry = (id: string) => { retryOfflineItem(id); void syncOfflineItems().then(setItems); };
  return <div className="space-y-4"><Card><SectionTitle title="Offline capture" /><p className="mb-3 text-xs leading-5 text-muted-foreground">Capture work safely when connectivity is unavailable. Items stay on this device until they sync.</p><div className="grid grid-cols-2 gap-2 sm:grid-cols-4"><Button size="sm" variant="outline" onClick={() => save("Field notes", "Field note · Pier P3")}>Field notes</Button><Button size="sm" variant="outline" onClick={() => save("Progress update", "Progress update · Pier P3")}>Progress</Button><Button size="sm" variant="outline" onClick={() => save("Attendance", "Attendance · Civil crew")}>Attendance</Button><Button size="sm" variant="outline" onClick={() => save("Issue", "Issue report · Zone B")}>Issue</Button></div></Card><OfflineQueue items={items} onRetry={retry} /></div>;
}

function RealEvidenceScreen() {
  const [items, setItems] = useState<Array<Record<string, unknown>>>([]);
  const [comparison, setComparison] = useState<ComparisonResult | null>(null);
  const [error, setError] = useState("");
  const projectId = typeof window === "undefined" ? "" : window.localStorage.getItem("constructiq-project") ?? "";

  useEffect(() => {
    if (!projectId) return;
    void api.get<Array<Record<string, unknown>>>(`/api/projects/${projectId}/evidence`)
      .then(response => setItems(response))
      .catch(() => setError("Evidence records could not be loaded."));
  }, [projectId]);

  const latest = items[0];
  const runComparison = async () => {
    if (!latest?.id) return;
    setError("");
    try {
      setComparison(await compareWithPrevious(String(latest.id)));
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Evidence comparison could not be completed.");
    }
  };

  return <div className="space-y-5">
    {error && <div role="alert" className="rounded-xl border border-danger/30 bg-danger/8 px-3 py-2 text-xs text-danger">{error}</div>}
    <Card><p className="text-[10px] font-bold uppercase tracking-[0.12em] text-primary">Evidence records</p><h2 className="mt-2 text-xl font-extrabold">Evidence Verification</h2><p className="mt-1 text-xs text-muted-foreground">Records and comparison results returned by the backend.</p></Card>
    {!latest && <Card><p className="text-sm text-muted-foreground">No evidence records are available for this project.</p></Card>}
    {latest && <Card><div className="grid gap-3 text-xs sm:grid-cols-2"><div><b>Evidence ID</b><p className="mt-1">{String(latest.id)}</p></div><div><b>Activity ID</b><p className="mt-1">{String(latest.activity_id ?? "Unavailable")}</p></div><div><b>Status</b><p className="mt-1">{String(latest.status ?? "Unavailable")}</p></div><div><b>Reported progress</b><p className="mt-1">{latest.reported_progress == null ? "Unavailable" : `${String(latest.reported_progress)}%`}</p></div><div><b>Captured at</b><p className="mt-1">{String(latest.captured_at ?? latest.uploaded_at ?? "Unavailable")}</p></div><div><b>Uploaded by</b><p className="mt-1">{String((latest.uploaded_by as Record<string, unknown> | undefined)?.full_name ?? "Unavailable")}</p></div></div><Button className="mt-5 w-full" onClick={runComparison}>Run comparison</Button></Card>}
    {comparison && <Card><div className="flex items-center justify-between"><h2 className="text-lg font-extrabold">Backend comparison</h2><StatusBadge tone="success">{comparison.comparisonStatus}</StatusBadge></div><div className="mt-4 grid gap-3 text-xs sm:grid-cols-2"><div><b>Current evidence</b><p className="mt-1">{comparison.currentEvidenceId}</p></div><div><b>Previous evidence</b><p className="mt-1">{comparison.previousEvidenceId}</p></div><div><b>OpenCV image difference</b><p className="mt-1">{comparison.opencvDifference ? "Returned" : "Not returned"}</p></div><div><b>YOLO detections</b><p className="mt-1">{comparison.detections ? "Returned" : "Not returned"}</p></div><div><b>Gemini explanation</b><p className="mt-1">{comparison.geminiExplanation ?? "Not returned"}</p></div><div><b>Limitations</b><p className="mt-1">{comparison.limitations.length ? comparison.limitations.join(", ") : "None returned"}</p></div></div></Card>}
  </div>;
}

type AnalyticsProgressResponse = {
  overall?: { planned?: number; actual?: number; variance?: number };
  activities?: Array<{ activity_id: number; name: string; planned: number | null; actual: number | null; variance: number | null; status?: string; risk_status?: string | null }>;
};
type AnalyticsActivitiesResponse = AnalyticsProgressResponse & { total?: number; completed?: number; in_progress?: number; delayed?: number; not_started?: number; critical_activities?: number[] };
type AnalyticsWorkforceResponse = { total_workers?: number; present?: number; absent?: number; attendance_rate?: number; active_crews?: number; worker_hours_today?: number; workforce_gap_total?: number; workforce_shortage?: { required_workers?: number | null; shortage_count?: number | null } };
type AnalyticsMaterialsResponse = { total_material_types?: number; low_stock_materials?: string[]; critical_stock_materials?: string[] };
type AnalyticsEquipmentResponse = { total_equipment?: number; active_equipment_issues?: number; utilization?: { value?: number | null; basis?: string; historical?: boolean }; historical_utilization?: { value?: number | null; usage_hours?: number; observation_hours?: number } };
type AnalyticsSafetyResponse = { total_incidents?: number; open_incidents?: number; critical_incidents?: number; ppe_compliance?: { percentage?: number | null; compliant_count?: number | null; non_compliant_count?: number | null; total_inspected?: number } };
type AnalyticsQualityResponse = { inspections?: number; passed?: number; failed?: number; conditional?: number; open_defects?: number; critical_defects?: number };
type AnalyticsDisruptionResponse = { total_disruptions?: number; active_disruptions?: number; total_interruption_minutes?: number };
type AnalyticsEvidenceResponse = { total_evidence?: number; verified?: number; pending?: number; rejected?: number };
type AnalyticsProductivityResponse = { value?: number | null; average_planned_progress?: number; average_actual_progress?: number };
type AnalyticsData = {
  overview: AnalyticsOverview;
  progress: AnalyticsProgressResponse;
  activities: AnalyticsActivitiesResponse;
  risks: { high_risk_activities?: unknown[]; critical_risk_activities?: unknown[]; activities?: unknown[] };
  delays: { delayed_activities?: unknown[] };
  workforce: AnalyticsWorkforceResponse;
  materials: AnalyticsMaterialsResponse;
  equipment: AnalyticsEquipmentResponse;
  safety: AnalyticsSafetyResponse;
  quality: AnalyticsQualityResponse;
  disruption: AnalyticsDisruptionResponse;
  evidence: AnalyticsEvidenceResponse;
  productivity: AnalyticsProductivityResponse;
};

function AnalyticsScreen() {
  const projectId = projectIdFromStorage();
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!projectId) { setError("Project context is unavailable."); setLoading(false); return; }
    let active = true;
    void Promise.all([
      api.get<AnalyticsOverview>(`/api/projects/${projectId}/analytics/overview`),
      api.get<AnalyticsProgressResponse>(`/api/projects/${projectId}/analytics/progress`),
      api.get<AnalyticsActivitiesResponse>(`/api/projects/${projectId}/analytics/activities`),
      api.get<AnalyticsData["risks"]>(`/api/projects/${projectId}/analytics/risks`),
      api.get<AnalyticsData["delays"]>(`/api/projects/${projectId}/analytics/delays`),
      api.get<AnalyticsWorkforceResponse>(`/api/projects/${projectId}/analytics/workforce`),
      api.get<AnalyticsMaterialsResponse>(`/api/projects/${projectId}/analytics/materials`),
      api.get<AnalyticsEquipmentResponse>(`/api/projects/${projectId}/analytics/equipment`),
      api.get<AnalyticsSafetyResponse>(`/api/projects/${projectId}/analytics/safety`),
      api.get<AnalyticsQualityResponse>(`/api/projects/${projectId}/analytics/quality`),
      api.get<AnalyticsDisruptionResponse>(`/api/projects/${projectId}/analytics/disruptions`),
      api.get<AnalyticsEvidenceResponse>(`/api/projects/${projectId}/analytics/evidence`),
      api.get<AnalyticsProductivityResponse>(`/api/projects/${projectId}/analytics/productivity`),
    ]).then(([overview, progress, activities, risks, delays, workforce, materials, equipment, safety, quality, disruption, evidence, productivity]) => {
      if (active) setData({ overview, progress, activities, risks, delays, workforce, materials, equipment, safety, quality, disruption, evidence, productivity });
    }).catch(requestError => { if (active) setError(analyticsErrorMessage(requestError, "Analytics data could not be loaded.")); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [projectId]);
  if (loading) return <Card><p className="text-sm text-muted-foreground">Loading analytics…</p></Card>;
  if (error) return <Card><p role="alert" className="text-sm text-danger">{error}</p></Card>;
  if (!data) return <Card><p className="text-sm text-muted-foreground">No analytics data is available.</p></Card>;
  const progressValues = (data.progress.activities ?? []).map(item => item.actual).filter((value): value is number => value !== null);
  const overall = data.progress.overall;
  const overviewProgress = data.overview.progress;
  const plannedProgress = overviewProgress?.planned_progress ?? overall?.planned;
  const actualProgress = overviewProgress?.overall_progress ?? overall?.actual;
  const variance = overviewProgress?.variance ?? overall?.variance;
  const formatPercent = (value?: number) => value === undefined || value === null ? "—" : `${value.toFixed(1)}%`;
  const formatNumber = (value?: number) => value === undefined || value === null ? "—" : String(value);
  const statusTone = (status?: string): Tone => status === "COMPLETED" ? "success" : status === "DELAYED" ? "danger" : status === "IN_PROGRESS" ? "warning" : "muted";
  return <div className="space-y-5"><div className="flex gap-2 overflow-x-auto scrollbar-none">{["7 Days", "30 Days", "Quarter", "All"].map((x, i) => <Button key={x} size="sm" variant={i === 1 ? "default" : "outline"}>{x}</Button>)}</div><Card><div className="flex justify-between"><div><p className="text-xs text-muted-foreground">Planned vs actual</p><p className="mt-1 text-2xl font-extrabold">{formatPercent(actualProgress)}</p></div><StatusBadge tone={(variance ?? 0) < 0 ? "warning" : "success"}>{formatPercent(variance)} variance</StatusBadge></div><Chart values={progressValues.length ? progressValues : [0]} /><div className="mt-3 flex gap-4 text-[10px] text-muted-foreground"><span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-primary" />Actual {formatPercent(actualProgress)}</span><span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-muted-foreground" />Planned {formatPercent(plannedProgress)}</span></div></Card><div className="grid grid-cols-2 gap-3"><MetricCard label="Schedule performance" value={plannedProgress && actualProgress !== undefined ? (actualProgress / plannedProgress).toFixed(2) : "—"} icon={Gauge} tone="warning" />  <MetricCard label="Productivity index" value={formatPercent(data.productivity.value)} icon={Activity} tone="success" /></div><Card><SectionTitle title="Operational analytics" /><div className="grid grid-cols-2 gap-2 sm:grid-cols-4"><SihDataCard label="Activities" value={formatNumber(data.overview.activities?.total ?? data.activities.total)} detail={`${formatNumber(data.overview.activities?.completed ?? data.activities.completed)} completed · ${formatNumber(data.overview.activities?.delayed ?? data.activities.delayed)} delayed`} /><SihDataCard label="Risks" value={formatNumber(data.risks.activities?.length)} detail={`${formatNumber(data.risks.high_risk_activities?.length)} high · ${formatNumber(data.risks.critical_risk_activities?.length)} critical`} tone="warning" /><SihDataCard label="Delays" value={formatNumber(data.delays.delayed_activities?.length)} tone="danger" /><SihDataCard label="Workforce" value={formatNumber(data.overview.workforce?.total_workers ?? data.workforce.total_workers)} detail={`${formatNumber(data.overview.workforce?.present_today ?? data.workforce.present)} present`} tone="success" /><SihDataCard label="Materials" value={formatNumber(data.materials.total_material_types)} detail={`${formatNumber(data.materials.low_stock_materials?.length)} low stock`} /><SihDataCard label="Equipment" value={formatNumber(data.equipment.total_equipment)} detail={`${formatNumber(data.equipment.active_equipment_issues)} active issues`} /><SihDataCard label="Safety" value={formatNumber(data.safety.total_incidents)} detail={`${formatNumber(data.safety.open_incidents)} open · ${formatNumber(data.safety.critical_incidents)} critical`} tone="danger" /><SihDataCard label="Quality" value={formatNumber(data.quality.inspections)} detail={`${formatNumber(data.quality.passed)} passed · ${formatNumber(data.quality.open_defects)} open defects`} tone="success" /><SihDataCard label="Disruptions" value={formatNumber(data.disruption.total_disruptions)} detail={`${formatNumber(data.disruption.active_disruptions)} active`} tone="warning" /><SihDataCard label="Evidence" value={formatNumber(data.evidence.total_evidence)} detail={`${formatNumber(data.evidence.verified)} verified · ${formatNumber(data.evidence.pending)} pending`} tone="success" /></div></Card><section><SectionTitle title="Activity performance" /><Card>{data.activities.activities?.length ? data.activities.activities.map(item => <ActivityRow key={item.activity_id} title={item.name} meta={`${formatPercent(item.actual ?? undefined)} actual · ${formatPercent(item.planned ?? undefined)} planned`} status={item.status ?? (item.variance === null ? "—" : formatPercent(item.variance))} tone={statusTone(item.status)} />) : <p className="py-6 text-center text-xs text-muted-foreground">No activity analytics were returned.</p>}</Card></section></div>;
}

type PredictionInput = [string, string, ComponentType<{ className?: string }>];

type AnalyticsRisk = { activity_id: number; risk_level: string; risk_score: number | null; primary_risk: string | null; risk_factors: unknown };
type AnalyticsDelay = { activity_id: number; name: string; zone: string | null; predicted_delay_days: number | null; risk_factors: unknown };
type ExecutionIntelligence = { planned_progress: number | null; actual_progress: number | null; actual_progress_source: string; actual_progress_confidence: number | null; actual_progress_reason: string; variance: number | null; variance_status: string; productivity_rate: number | null; productivity_observation_ids: number[]; productivity_source_assessment_ids: number[]; productivity_source_observation_ids: number[]; productivity_status: string; productivity_reason: string; expected_completion_date: string | null; predicted_delay_days: number | null; delay_status: string; delay_reason: string; delay_source_assessment_ids: number[]; delay_source_observation_ids: number[]; risk_prediction_id: number | null; recovery_recommendation_id: number | null };
type MeasuredProgress = { id: number; activity_id: number; assessment_date: string; planned_quantity: number; completed_quantity: number; unit: string; notes: string | null; verification_status: "PENDING" | "VERIFIED" | "REJECTED"; recorded_by: number; verified_by: number | null };
type RecoveryRecommendation = { id: number; activity_id: number; priority: string; title: string; description: string; expected_impact: string; implementation_effort: string; status: string };
type ProgressAssessment = { activity_id: number; evidence_id: number | null; comparison_id: number | null; assessment_date: string; planned_progress: number | null; reported_progress: number | null; ai_estimated_progress: number | null; ai_confidence: number | null; fused_progress: number | null; variance_from_plan: number | null; assessment_status: string };
type EvidenceComparison = { comparison_id: number; current_evidence_id: number; previous_evidence_id: number; comparison_status: string; overall_change: string; confidence: number; construction_change_score: number; absolute_progress_estimate: number | null; absolute_progress_confidence: number | null; observations: Array<{ category?: string; observation?: string; change?: string; confidence?: number }>; notes: string | null };

function projectIdFromStorage() {
  return typeof window === "undefined" ? "" : window.sessionStorage.getItem("constructiq-project") ?? window.localStorage.getItem("constructiq-project") ?? "";
}

function displayValue(value: unknown, suffix = "") {
  return value === null || value === undefined || value === "" ? "—" : `${String(value)}${suffix}`;
}

function analyticsErrorMessage(error: unknown, fallback: string) {
  return error instanceof ApiError ? error.message : fallback;
}

function AIDelayPrediction() {
  const projectId = projectIdFromStorage();
  const [progress, setProgress] = useState<{ overall?: { planned?: number; actual?: number; variance?: number }; activities?: Array<{ activity_id: number; name: string; planned: number | null; actual: number | null; variance: number | null }> } | null>(null);
  const [assessment, setAssessment] = useState<ProgressAssessment | null>(null);
  const [risks, setRisks] = useState<AnalyticsRisk[]>([]);
  const [delays, setDelays] = useState<AnalyticsDelay[]>([]);
  const [recovery, setRecovery] = useState<RecoveryRecommendation[]>([]);
  const [execution, setExecution] = useState<ExecutionIntelligence | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [measured, setMeasured] = useState<MeasuredProgress[]>([]);
  const [measurementForm, setMeasurementForm] = useState({ assessment_date: new Date().toISOString().slice(0, 10), planned_quantity: "", completed_quantity: "", unit: "", notes: "" });
  const [measurementError, setMeasurementError] = useState("");
  const [measurementMessage, setMeasurementMessage] = useState("");
  const [submittingMeasurement, setSubmittingMeasurement] = useState(false);
  const currentRole = typeof window === "undefined" ? "" : window.sessionStorage.getItem("constructiq-role") ?? window.localStorage.getItem("constructiq-role") ?? "";

  useEffect(() => {
    if (!projectId) { setLoading(false); setError("Project context is unavailable."); return; }
    let active = true;
    void (async () => {
      try {
        const [progressResponse, riskResponse, delayResponse] = await Promise.all([
          api.get<typeof progress>(`/api/projects/${projectId}/analytics/progress`),
          api.get<{ activities?: AnalyticsRisk[] }>(`/api/projects/${projectId}/analytics/risks`),
          api.get<{ delayed_activities?: AnalyticsDelay[] }>(`/api/projects/${projectId}/analytics/delays`),
        ]);
        const firstActivity = progressResponse.activities?.[0];
        let latestAssessment: ProgressAssessment | null = null;
        let recommendations: RecoveryRecommendation[] = [];
        if (firstActivity) {
          const assessmentResponse = await api.get<ProgressAssessment>(`/api/activities/${firstActivity.activity_id}/progress-assessment/latest`).catch(() => null);
          const recoveryResponse = await api.get<{ items?: RecoveryRecommendation[] }>(`/api/activities/${firstActivity.activity_id}/recovery-recommendations`).catch(() => null);
          latestAssessment = assessmentResponse;
          recommendations = recoveryResponse?.items ?? [];
          const measuredResponse = await api.get<MeasuredProgress[]>(`/api/activities/${firstActivity.activity_id}/measured-progress`).catch(() => []);
          setMeasured(measuredResponse);
        }
        if (!active) return;
        setProgress(progressResponse);
        setAssessment(latestAssessment);
        setRisks(riskResponse.activities ?? []);
        setDelays(delayResponse.delayed_activities ?? []);
        setRecovery(recommendations);
      } catch (requestError) {
        if (active) setError(analyticsErrorMessage(requestError, "Project intelligence data could not be loaded."));
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => { active = false; };
  }, [projectId]);

  const firstActivity = progress?.activities?.[0];
  const risk = risks.find(item => item.activity_id === firstActivity?.activity_id) ?? risks[0];
  const delay = delays.find(item => item.activity_id === firstActivity?.activity_id) ?? delays[0];
  const toneForRisk = risk?.risk_level === "CRITICAL" || risk?.risk_level === "HIGH" ? "danger" : risk ? "warning" : "muted";
  if (loading) return <Card><p className="text-sm text-muted-foreground">Loading project intelligence…</p></Card>;
  if (error) return <Card><p role="alert" className="text-sm text-danger">{error}</p></Card>;
  const submitMeasurement = async () => {
    if (!firstActivity) return;
    setSubmittingMeasurement(true);
    setMeasurementError("");
    setMeasurementMessage("");
    try {
      const created = await api.post<MeasuredProgress>(`/api/activities/${firstActivity.activity_id}/measured-progress`, {
        assessment_date: measurementForm.assessment_date,
        planned_quantity: measurementForm.planned_quantity,
        completed_quantity: measurementForm.completed_quantity,
        unit: measurementForm.unit,
        notes: measurementForm.notes || null,
      });
      setMeasured(items => [created, ...items]);
      setMeasurementMessage("Measured progress submitted for verification. It is not actual progress until approved.");
      setMeasurementForm(form => ({ ...form, planned_quantity: "", completed_quantity: "", notes: "" }));
    } catch (requestError) {
      setMeasurementError(analyticsErrorMessage(requestError, "Measured progress could not be submitted."));
    } finally {
      setSubmittingMeasurement(false);
    }
  };
  const verifyMeasurement = async (id: number, decision: "VERIFIED" | "REJECTED") => {
    setMeasurementError("");
    try {
      const updated = await api.post<MeasuredProgress>(`/api/measured-progress/${id}/verify`, { decision });
      setMeasured(items => items.map(item => item.id === id ? updated : item));
      setMeasurementMessage(decision === "VERIFIED" ? "Measured progress verified. Intelligence values will refresh on reload." : "Measured progress rejected.");
    } catch (requestError) {
      setMeasurementError(analyticsErrorMessage(requestError, "Measured progress verification failed."));
    }
  };

  return <div className="space-y-5">
    <Card className="border-primary/20 bg-primary/5"><p className="text-[10px] font-bold uppercase tracking-[0.12em] text-primary">Live project intelligence</p><h2 className="mt-2 text-xl font-extrabold">Progress, risk, delay and recovery</h2><p className="mt-1 text-xs text-muted-foreground">Values below are returned by the authenticated project APIs.</p></Card>
    <Card><div className="grid grid-cols-2 gap-3 sm:grid-cols-4"><SihDataCard label="Planned progress" value={displayValue(assessment?.planned_progress ?? progress?.overall?.planned, "%")} /><SihDataCard label="Reported progress" value={displayValue(assessment?.reported_progress ?? progress?.overall?.actual, "%")} tone="warning" /><SihDataCard label="AI estimated" value={displayValue(assessment?.ai_estimated_progress, "%")} tone="warning" /><SihDataCard label="Fused progress" value={displayValue(assessment?.fused_progress, "%")} tone="success" /></div><div className="mt-4 grid grid-cols-2 gap-3 text-xs"><div><b>Assessment status</b><p className="mt-1 text-muted-foreground">{displayValue(assessment?.assessment_status)}</p></div><div><b>Assessment date</b><p className="mt-1 text-muted-foreground">{displayValue(assessment?.assessment_date)}</p></div><div><b>Schedule variance</b><p className="mt-1 text-muted-foreground">{displayValue(assessment?.variance_from_plan ?? progress?.overall?.variance, "%")}</p></div><div><b>Activity</b><p className="mt-1 text-muted-foreground">{displayValue(firstActivity?.name)}</p></div></div></Card>{firstActivity && <MeasuredProgressPanel activityId={firstActivity.activity_id} />}
    <Card><SectionTitle title="Verified measured progress" /><p className="text-xs text-muted-foreground">Submit real field quantities for independent verification. Pending and rejected quantities never become actual progress.</p>{(currentRole === "Field Engineer" || currentRole === "Site Engineer") && firstActivity && <div className="mt-4 grid gap-3 sm:grid-cols-2"><label className="text-[10px] font-bold text-muted-foreground">DATE<input type="date" value={measurementForm.assessment_date} onChange={event => setMeasurementForm(form => ({ ...form, assessment_date: event.target.value }))} className="mt-2 h-10 w-full rounded-xl border border-border bg-background px-3 text-xs" /></label><label className="text-[10px] font-bold text-muted-foreground">UNIT<input value={measurementForm.unit} onChange={event => setMeasurementForm(form => ({ ...form, unit: event.target.value }))} placeholder="m3, kg, m" className="mt-2 h-10 w-full rounded-xl border border-border bg-background px-3 text-xs" /></label><label className="text-[10px] font-bold text-muted-foreground">PLANNED QUANTITY<input type="number" min="0.001" step="0.001" value={measurementForm.planned_quantity} onChange={event => setMeasurementForm(form => ({ ...form, planned_quantity: event.target.value }))} className="mt-2 h-10 w-full rounded-xl border border-border bg-background px-3 text-xs" /></label><label className="text-[10px] font-bold text-muted-foreground">COMPLETED QUANTITY<input type="number" min="0" step="0.001" value={measurementForm.completed_quantity} onChange={event => setMeasurementForm(form => ({ ...form, completed_quantity: event.target.value }))} className="mt-2 h-10 w-full rounded-xl border border-border bg-background px-3 text-xs" /></label><label className="text-[10px] font-bold text-muted-foreground sm:col-span-2">NOTES<textarea value={measurementForm.notes} onChange={event => setMeasurementForm(form => ({ ...form, notes: event.target.value }))} className="mt-2 min-h-16 w-full rounded-xl border border-border bg-background p-3 text-xs" /></label><Button type="button" onClick={() => void submitMeasurement()} disabled={submittingMeasurement || !measurementForm.unit || !measurementForm.planned_quantity || !measurementForm.completed_quantity}>{submittingMeasurement ? "Submitting…" : "Submit for verification"}</Button></div>}{measurementError && <p role="alert" className="mt-3 text-xs text-danger">{measurementError}</p>}{measurementMessage && <p className="mt-3 text-xs text-success">{measurementMessage}</p>}<div className="mt-4 space-y-2">{measured.length ? measured.map(item => <div key={item.id} className="rounded-xl border border-border bg-secondary p-3 text-xs"><div className="flex items-center justify-between gap-2"><b>{item.assessment_date} · {item.completed_quantity} / {item.planned_quantity} {item.unit}</b><StatusBadge tone={item.verification_status === "VERIFIED" ? "success" : item.verification_status === "REJECTED" ? "danger" : "warning"}>{item.verification_status}</StatusBadge></div>{item.notes && <p className="mt-1 text-muted-foreground">{item.notes}</p>}{item.verification_status === "PENDING" && ["Site Engineer", "QA/QC Engineer", "Project Manager", "Admin"].includes(currentRole) && <div className="mt-2 flex gap-2"><Button size="sm" onClick={() => void verifyMeasurement(item.id, "VERIFIED")}>Verify</Button><Button size="sm" variant="outline" onClick={() => void verifyMeasurement(item.id, "REJECTED")}>Reject</Button></div>}</div>) : <p className="mt-4 text-xs text-muted-foreground">No measured progress submissions exist for this activity.</p>}</div></Card>
    <Card className={cn("border", toneForRisk === "danger" ? "border-danger/30 bg-danger/5" : "border-warning/30 bg-warning/5")}><div className="flex items-start justify-between gap-3"><div><p className="text-[10px] font-bold uppercase tracking-[0.12em] text-danger">Risk</p><h2 className="mt-2 text-xl font-extrabold">{displayValue(firstActivity?.name)}</h2></div><StatusBadge tone={toneForRisk}>{displayValue(risk?.risk_level)}</StatusBadge></div><div className="mt-4 grid gap-3 text-xs sm:grid-cols-2"><div><b>Risk score</b><p className="mt-1">{displayValue(risk?.risk_score)}</p></div><div><b>Primary risk</b><p className="mt-1">{displayValue(risk?.primary_risk)}</p></div><div className="sm:col-span-2"><b>Risk factors</b><p className="mt-1 text-muted-foreground">{risk?.risk_factors ? JSON.stringify(risk.risk_factors) : "—"}</p></div></div></Card>
    <Card><p className="text-[10px] font-bold uppercase tracking-[0.12em] text-primary">Delay</p>{delay ? <div className="mt-3 grid gap-3 text-xs sm:grid-cols-2"><div><b>Affected activity</b><p className="mt-1">{delay.name}</p></div><div><b>Predicted delay</b><p className="mt-1">{displayValue(delay.predicted_delay_days, " days")}</p></div><div><b>Zone</b><p className="mt-1">{displayValue(delay.zone)}</p></div><div><b>Cause / factors</b><p className="mt-1">{delay.risk_factors ? JSON.stringify(delay.risk_factors) : "—"}</p></div></div> : <p className="mt-3 text-sm text-muted-foreground">No delayed activities were returned.</p>}</Card>
    <Card><p className="text-[10px] font-bold uppercase tracking-[0.12em] text-primary">Recovery recommendations</p>{recovery.length ? <div className="mt-3 space-y-3">{recovery.map(item => <div key={item.id} className="rounded-xl border border-border bg-secondary p-3 text-xs"><div className="flex items-start justify-between gap-2"><div><p className="font-extrabold">{item.title}</p><p className="mt-1 text-muted-foreground">{item.description}</p></div><StatusBadge tone={item.priority === "HIGH" || item.priority === "CRITICAL" ? "danger" : "primary"}>{item.priority}</StatusBadge></div><div className="mt-3 grid grid-cols-2 gap-2"><span><b>Expected impact:</b> {item.expected_impact}</span><span><b>Effort:</b> {item.implementation_effort}</span><span><b>Status:</b> {item.status}</span><span><b>Activity:</b> {item.activity_id}</span></div></div>)}</div> : <p className="mt-3 text-sm text-muted-foreground">No recovery recommendations were returned.</p>}</Card>
  </div>;
}
function AIScreen({ onReplay }: { onReplay: () => void }) {
  const [tab, setTab] = useState<"Risk" | "Recovery" | "Copilot">("Risk");
  const [question, setQuestion] = useState("");
  return <div className="space-y-5"><div className="grid grid-cols-3 rounded-xl bg-secondary p-1">{(["Risk", "Recovery", "Copilot"] as const).map(t => <button type="button" key={t} onClick={() => setTab(t)} className={cn("rounded-lg py-2 text-[11px] font-bold", tab === t ? "bg-primary text-primary-foreground" : "text-muted-foreground")}>{t}</button>)}</div>{tab === "Risk" && <><Card className="border-danger/30"><div className="flex justify-between"><StatusBadge tone="danger">Activity at risk</StatusBadge><Sparkles className="text-danger" /></div><h2 className="mt-5 text-xl font-extrabold">Pier P3 Construction</h2><div className="mt-5 grid grid-cols-2 gap-3"><div><p className="text-[10px] text-muted-foreground">RISK LEVEL</p><p className="mt-1 text-lg font-extrabold text-danger">HIGH</p></div><div><p className="text-[10px] text-muted-foreground">PREDICTED DELAY</p><p className="mt-1 text-lg font-extrabold">3 Days</p></div></div><div className="mt-5 border-t border-border pt-4"><p className="text-xs font-bold">Primary causes</p>{["Worker shortage", "Steel delivery delay", "Rain interruption"].map((x, i) => <div key={x} className="mt-3 flex items-center gap-3"><span className="text-xs font-bold text-danger">0{i + 1}</span><span className="text-xs text-muted-foreground">{x}</span></div>)}</div></Card><Button className="w-full" onClick={() => setTab("Recovery")}><TimerReset /> Generate recovery plan</Button></>}{tab === "Recovery" && <><Card><p className="text-[10px] text-danger">AI RECOMMENDED RECOVERY</p><h2 className="mt-2 text-xl font-extrabold">Close a 3-day variance</h2><div className="mt-4"><div className="flex justify-between text-xs"><span>Current progress</span><b>62%</b></div><Progress value={62} tone="danger" /><div className="mt-4 flex justify-between text-xs"><span>Planned progress</span><b>75%</b></div><Progress value={75} /></div></Card>{[["Option 1", "+8 workers", "Recover in 3 days"], ["Option 2", "+4 workers · +1 machine", "Recover in 2 days"], ["Option 3", "+2.5 hours per shift", "Recover in 2 days"]].map((o, i) => <button type="button" key={o[0]} className={cn("w-full rounded-2xl border p-4 text-left", i === 1 ? "border-primary bg-primary/8" : "border-border bg-card")}><div className="flex justify-between"><p className="text-[10px] font-bold text-muted-foreground">{o[0]}</p>{i === 1 && <StatusBadge tone="primary">Recommended</StatusBadge>}</div><p className="mt-2 text-base font-extrabold">{o[1]}</p><p className="mt-1 text-xs text-success">{o[2]}</p></button>)}<div className="grid grid-cols-2 gap-3"><Button variant="outline">Modify</Button><Button><Check /> Approve plan</Button></div></>}{tab === "Copilot" && <><Card className="border-primary/20"><div className="flex gap-3"><div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-primary text-primary-foreground"><Bot /></div><div><p className="text-sm font-extrabold">Construction Intelligence Copilot</p><p className="mt-1 text-xs leading-5 text-muted-foreground">Grounded in live project evidence, schedules, resources, and events.</p></div></div></Card><ProjectMemoryPanel /><div className="flex flex-wrap gap-2">{["Why is P3 delayed?", "Highest risk activity?", "What happened yesterday?"].map(q => <button type="button" key={q} onClick={() => setQuestion(q)} className="rounded-full border border-border bg-card px-3 py-2 text-[10px] text-muted-foreground">{q}</button>)}</div><div className="ml-8 rounded-2xl rounded-tr-sm bg-primary p-4 text-sm text-primary-foreground">{question || "Why is Pier P3 delayed?"}</div><Card><div className="flex gap-2"><Sparkles className="h-4 w-4 shrink-0 text-primary" /><div><p className="text-sm font-bold">Pier P3 is trending 3 days late.</p><p className="mt-2 text-xs leading-6 text-muted-foreground">The primary drivers are a 14% workforce shortfall, steel delivery arriving 9 hours late, and 4.5 hours of rain interruption yesterday.</p><button type="button" onClick={onReplay} className="mt-3 text-xs font-bold text-primary">View supporting events →</button></div></div></Card><div className="fixed bottom-24 left-4 right-4 z-30 mx-auto flex max-w-lg gap-2 rounded-2xl border border-border bg-surface p-2"><input value={question} onChange={e => setQuestion(e.target.value)} placeholder="Ask about the project…" className="min-w-0 flex-1 bg-transparent px-2 text-sm outline-none placeholder:text-muted-foreground" /><Button size="icon" aria-label="Send"><Send /></Button></div></>}</div>;
}

type EventType = "Worker arrival" | "Attendance" | "Work started" | "Progress update" | "Evidence captured" | "Evidence submitted" | "AI analysis completed" | "Verification completed" | "Material delivery" | "Equipment deployed" | "Equipment breakdown" | "Inspection" | "Issue reported" | "Safety incident" | "Weather interruption" | "Activity completed";
type TimelineEvent = {
  id: string;
  time: string;
  date: string;
  person: string;
  role: Role;
  activity: string;
  location: string;
  zone: string;
  type: EventType;
  evidence: string;
  status: string;
  tone: Tone;
  icon: ComponentType<{ className?: string }>;
  gps?: string;
  material?: string;
  quantity?: string;
  destination?: string;
  details?: string;
};

function useProjectEvents(source: "timeline" | "replay" = "timeline") {
  const projectId = projectIdFromStorage();
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  useEffect(() => {
    let active = true;
    if (!projectId) return () => { active = false; };
    const endpoint = source === "replay"
      ? `/api/projects/${projectId}/replay?date=${new Date().toISOString().slice(0, 10)}`
      : `/api/projects/${projectId}/timeline`;
    void api.get<{ events?: Array<Record<string, unknown>> }>(endpoint).then(response => {
      if (!active) return;
      const items = response.events ?? [];
      setEvents(items.map((item, index) => {
        const timestamp = String(item.event_timestamp ?? item.timestamp ?? "");
        const parsed = timestamp ? new Date(timestamp) : null;
        const type = String(item.event_type ?? item.type ?? "Construction event") as EventType;
        return {
          id: String(item.id ?? `event-${index}`),
          time: parsed && !Number.isNaN(parsed.getTime()) ? parsed.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—",
          date: parsed && !Number.isNaN(parsed.getTime()) ? parsed.toLocaleDateString([], { day: "2-digit", month: "short", year: "numeric" }) : "—",
          person: String(item.actor_name ?? item.user_name ?? "—"), role: String(item.actor_role ?? "—") as Role,
          activity: String(item.activity_name ?? item.title ?? type), location: String(item.location ?? "—"), zone: String(item.zone ?? "—"),
          type, evidence: String(item.evidence_id ?? "—"), status: String(item.status ?? "Recorded"), tone: "primary", icon: Activity,
          details: String(item.description ?? item.details ?? ""),
        };
      }));
    }).catch(() => { if (active) setEvents([]); });
    return () => { active = false; };
  }, [projectId, source]);
  return events;
}

function TimelineEventRow({ event, selected, onSelect, showDetails }: { event: TimelineEvent; selected: boolean; onSelect: () => void; showDetails: boolean }) {
  const Icon = event.icon;
  return <button type="button" onClick={onSelect} className={cn("relative flex w-full gap-3 pb-5 text-left last:pb-0", selected && "rounded-xl bg-secondary p-3")}><div className="relative z-10 grid h-8 w-8 shrink-0 place-items-center rounded-full border border-border bg-surface-elevated"><Icon className={cn("h-3.5 w-3.5", toneClasses[event.tone].split(" ")[1])} /></div><div className="flex-1"><div className="flex items-start justify-between gap-3"><div><p className="text-xs font-bold">{event.activity}</p><p className="mt-1 text-[10px] text-muted-foreground">{event.person} · {event.role}</p></div><span className="shrink-0 text-[10px] font-bold text-muted-foreground">{event.time}</span></div>{showDetails && <div className="mt-3 space-y-2 text-[10px] text-muted-foreground"><div className="grid gap-2 sm:grid-cols-2"><span><b className="text-foreground">Who:</b> {event.person}</span><span><b className="text-foreground">What:</b> {event.activity}</span><span><b className="text-foreground">Where:</b> {event.location} · {event.zone}</span><span><b className="text-foreground">When:</b> {event.date} · {event.time}</span>{event.material && <span><b className="text-foreground">Material:</b> {event.material}</span>}{event.quantity && <span><b className="text-foreground">Quantity:</b> {event.quantity}</span>}{event.destination && <span className="sm:col-span-2"><b className="text-foreground">Destination:</b> {event.destination}</span>}<span><b className="text-foreground">GPS:</b> {event.gps ?? "N/A"}</span><span><b className="text-foreground">Status:</b> {event.status}</span></div><div className="rounded-xl bg-background p-2.5"><b className="text-foreground">Evidence:</b> {event.evidence}</div>{event.details && <div className="rounded-xl bg-background p-2.5"><b className="text-foreground">Details:</b> {event.details}</div>}<div className="pt-1"><StatusBadge tone={event.tone}>{event.status}</StatusBadge></div></div>}</div></button>;
}

function TimelineFilters({ events, onChange }: { events: TimelineEvent[]; onChange: (filtered: TimelineEvent[]) => void }) {
  const [filters, setFilters] = useState({ date: "All dates", activity: "All activities", person: "All people", type: "All event types", zone: "All zones" });
  const values = {
    date: ["All dates", ...new Set(events.map(event => event.date))],
    activity: ["All activities", ...new Set(events.map(event => event.activity))],
    person: ["All people", ...new Set(events.map(event => event.person))],
    type: ["All event types", ...new Set(events.map(event => event.type))],
    zone: ["All zones", ...new Set(events.map(event => event.zone))],
  };
  const update = (key: keyof typeof filters, value: string) => {
    const next = { ...filters, [key]: value };
    setFilters(next);
    onChange(events.filter(event => (next.date === "All dates" || event.date === next.date) && (next.activity === "All activities" || event.activity === next.activity) && (next.person === "All people" || event.person === next.person) && (next.type === "All event types" || event.type === next.type) && (next.zone === "All zones" || event.zone === next.zone)));
  };
  return <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">{(Object.keys(filters) as (keyof typeof filters)[]).map(key => <select key={key} value={filters[key]} onChange={event => update(key, event.target.value)} aria-label={key} className="h-10 rounded-xl border border-border bg-card px-3 text-xs outline-none focus:border-primary">{values[key].map(value => <option key={value}>{value}</option>)}</select>)}</div>;
}

function Timeline({ compact = false, interactive = false }: { compact?: boolean; interactive?: boolean }) {
  const projectEvents = useProjectEvents();
  const [selected, setSelected] = useState("evidence");
  const [filteredEvents, setFilteredEvents] = useState(projectEvents);
  useEffect(() => setFilteredEvents(projectEvents), [projectEvents]);
  const events = compact ? projectEvents.slice(0, 3) : filteredEvents;
  return <div className="space-y-4">{!compact && <TimelineFilters events={projectEvents} onChange={setFilteredEvents} />}<Card>{events.length === 0 ? <p className="py-6 text-center text-xs text-muted-foreground">No events match the selected filters.</p> : events.map((event, index) => <div key={event.id} className="relative">{index < events.length - 1 && <span className="absolute left-[15px] top-8 h-[calc(100%-28px)] w-px bg-border" />}<TimelineEventRow event={event} selected={interactive && selected === event.id} onSelect={() => setSelected(event.id)} showDetails={!compact && interactive && selected === event.id} /></div>)}</Card></div>;
}

function ReplayScreen() {
  const projectEvents = useProjectEvents("replay");
  const [project, setProject] = useState("Metro Line 6 · Package C3");
  const [date, setDate] = useState("01 Sep 2026");
  const [zone, setZone] = useState("All zones");
  const [activity, setActivity] = useState("All activities");
  const [selectedId, setSelectedId] = useState("evidence");
  const events = projectEvents.filter(event => event.date === date && (zone === "All zones" || event.zone === zone) && (activity === "All activities" || event.activity === activity));
  const selected = events.find(event => event.id === selectedId) ?? events[0];
  return <div className="space-y-5"><Card><div className="mb-4"><p className="text-[10px] font-bold uppercase tracking-widest text-primary">Construction replay</p><h2 className="mt-2 text-xl font-extrabold">What happened on site?</h2><p className="mt-1 text-xs text-muted-foreground">Reconstruct the day from recorded project events and evidence.</p></div><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><label className="text-[10px] font-bold text-muted-foreground">PROJECT<select value={project} onChange={event => setProject(event.target.value)} className="mt-2 h-10 w-full rounded-xl border border-border bg-background px-3 text-xs text-foreground outline-none focus:border-primary"><option>Metro Line 6 · Package C3</option><option>Metro Line 6 · Package C4</option></select></label><label className="text-[10px] font-bold text-muted-foreground">DATE<select value={date} onChange={event => setDate(event.target.value)} className="mt-2 h-10 w-full rounded-xl border border-border bg-background px-3 text-xs text-foreground outline-none focus:border-primary"><option>01 Sep 2026</option></select></label><label className="text-[10px] font-bold text-muted-foreground">ZONE<select value={zone} onChange={event => setZone(event.target.value)} className="mt-2 h-10 w-full rounded-xl border border-border bg-background px-3 text-xs text-foreground outline-none focus:border-primary"><option>All zones</option><option>Zone B</option></select></label><label className="text-[10px] font-bold text-muted-foreground">ACTIVITY<select value={activity} onChange={event => setActivity(event.target.value)} className="mt-2 h-10 w-full rounded-xl border border-border bg-background px-3 text-xs text-foreground outline-none focus:border-primary"><option>All activities</option><option>Pier P3 Reinforcement</option><option>Material delivery</option></select></label></div></Card><div className="flex items-center justify-between"><div><p className="text-[10px] font-bold text-muted-foreground">CHRONOLOGICAL RECONSTRUCTION</p><p className="mt-1 text-sm font-extrabold">{project} · {date} · {zone}</p></div><Button size="icon" aria-label="Play construction replay"><Play /></Button></div><div className="grid gap-5 lg:grid-cols-2"><Card><div className="space-y-1">{events.map((event, index) => <div key={event.id} className="relative">{index < events.length - 1 && <span className="absolute left-[15px] top-8 h-[calc(100%-28px)] w-px bg-border" />}<TimelineEventRow event={event} selected={selected?.id === event.id} onSelect={() => setSelectedId(event.id)} showDetails={false} /></div>)}</div></Card><div className="space-y-5"><MapPanel /><Card>{selected ? <><div className="flex items-start justify-between gap-3"><div><p className="text-[10px] font-bold uppercase text-primary">Selected event · {selected.time}</p><h3 className="mt-2 text-lg font-extrabold">{selected.activity}</h3><p className="mt-1 text-xs text-muted-foreground">{selected.person} · {selected.role}</p></div><StatusBadge tone={selected.tone}>{selected.status}</StatusBadge></div><div className="mt-5 space-y-3 text-xs"><div className="grid grid-cols-2 gap-3"><div><p className="text-[10px] text-muted-foreground">WHO</p><p className="mt-1 font-bold">{selected.person}</p></div><div><p className="text-[10px] text-muted-foreground">WHAT</p><p className="mt-1 font-bold">{selected.activity}</p></div><div><p className="text-[10px] text-muted-foreground">WHERE</p><p className="mt-1 font-bold">{selected.location} · {selected.zone}</p></div><div><p className="text-[10px] text-muted-foreground">WHEN</p><p className="mt-1 font-bold">{selected.date} · {selected.time}</p></div>{selected.material && <div><p className="text-[10px] text-muted-foreground">MATERIAL</p><p className="mt-1 font-bold">{selected.material}</p></div>}{selected.quantity && <div><p className="text-[10px] text-muted-foreground">QUANTITY</p><p className="mt-1 font-bold">{selected.quantity}</p></div>}{selected.destination && <div className="col-span-2"><p className="text-[10px] text-muted-foreground">DESTINATION</p><p className="mt-1 font-bold">{selected.destination}</p></div>}<div><p className="text-[10px] text-muted-foreground">GPS</p><p className="mt-1 font-bold">{selected.gps ?? "Not available"}</p></div><div><p className="text-[10px] text-muted-foreground">EVIDENCE</p><p className="mt-1 font-bold">{selected.evidence}</p></div></div></div><div className="mt-5 grid h-28 place-items-center rounded-xl border border-border bg-surface-elevated map-grid"><div className="text-center">{selected.type === "Evidence captured" || selected.type === "Evidence submitted" || selected.type === "AI analysis completed" || selected.type === "Verification completed" ? <Camera className="mx-auto h-7 w-7 text-primary" /> : selected.type === "Weather interruption" ? <CloudRain className="mx-auto h-7 w-7 text-primary" /> : selected.type === "Material delivery" ? <Truck className="mx-auto h-7 w-7 text-primary" /> : <Video className="mx-auto h-7 w-7 text-primary" />}<p className="mt-2 text-[10px] font-bold text-muted-foreground">{selected.type === "Evidence captured" || selected.type === "Evidence submitted" || selected.type === "AI analysis completed" || selected.type === "Verification completed" ? "Photo evidence preview" : selected.type === "Material delivery" ? "Delivery record" : "Related media placeholder"}</p></div></div><div className="mt-4 rounded-xl bg-secondary p-3 text-xs text-muted-foreground"><span className="font-bold text-foreground">Event notes:</span> {selected.details ?? "Construction event captured as part of the activity log."}</div></> : <p className="text-sm text-muted-foreground">No events match this replay selection.</p>}</Card></div></div></div>;
}

function InspectionScreen() {
  const [checked, setChecked] = useState([true, true, false, false]);
  return <div className="space-y-5"><Card><StatusBadge tone="warning">Inspection due</StatusBadge><h2 className="mt-4 text-xl font-extrabold">Rebar before concrete pour</h2><p className="mt-1 text-xs text-muted-foreground">Pier P3 · ITP-CIV-021 · Hold point</p></Card><section><SectionTitle title="Inspection checklist" /><Card>{["Bar diameter and spacing", "Concrete cover blocks", "Lap length verified", "Area cleaned before pour"].map((item, i) => <button type="button" key={item} onClick={() => setChecked(v => v.map((x, j) => j === i ? !x : x))} className="flex w-full items-center gap-3 border-b border-border py-4 text-left last:border-0"><span className={cn("grid h-6 w-6 place-items-center rounded-md border", checked[i] ? "border-primary bg-primary text-primary-foreground" : "border-border")} >{checked[i] && <Check className="h-4 w-4" />}</span><span className="flex-1 text-sm font-medium">{item}</span></button>)}</Card></section><Button className="w-full"><Camera /> Add inspection evidence</Button><Button variant="outline" className="w-full">Save as draft</Button></div>;
}

function InventoryScreen() {
  return <div className="space-y-5"><div className="flex gap-2 overflow-x-auto scrollbar-none">{["All stock", "Low stock", "Received", "Issued"].map((x, i) => <Button key={x} size="sm" variant={i === 0 ? "default" : "outline"}>{x}</Button>)}</div>{[["Steel Bars", "TMT 32mm · Store B", 68, "15 Tons", "Healthy"], ["Ready-mix M40", "Batch RM-42 · Zone B", 18, "42 m³", "Low stock"], ["Cement OPC 53", "Warehouse A · Rack 04", 46, "380 Bags", "Watch"]].map(([n, m, p, q, s]) => <Card key={String(n)}><div className="flex items-start gap-3"><div className="grid h-11 w-11 place-items-center rounded-xl bg-secondary"><Box className="h-5 w-5 text-primary" /></div><div className="flex-1"><div className="flex justify-between"><div><p className="text-sm font-extrabold">{n}</p><p className="mt-1 text-[10px] text-muted-foreground">{m}</p></div><StatusBadge tone={s === "Healthy" ? "success" : s === "Low stock" ? "danger" : "warning"}>{s}</StatusBadge></div><div className="mt-4 flex items-end justify-between"><span className="text-lg font-extrabold">{q}</span><span className="text-[10px] text-muted-foreground">remaining</span></div><div className="mt-2"><Progress value={Number(p)} tone={s === "Low stock" ? "danger" : "primary"} /></div></div></div></Card>)}<Button className="w-full"><Plus /> Add material</Button></div>;
}

function SihDataCard({ label, value, detail, tone = "muted" }: { label: string; value: string; detail?: string; tone?: Tone }) {
  return <div className={cn("rounded-xl border p-3", tone === "success" ? "border-success/25 bg-success/8" : tone === "warning" ? "border-warning/25 bg-warning/8" : tone === "danger" ? "border-danger/25 bg-danger/8" : "border-border bg-secondary")}>
    <p className="text-[9px] font-bold uppercase tracking-[0.1em] text-muted-foreground">{label}</p>
    <p className={cn("mt-1 text-lg font-extrabold", tone === "success" ? "text-success" : tone === "warning" ? "text-warning" : tone === "danger" ? "text-danger" : "text-foreground")}>{value}</p>
    {detail && <p className="mt-1 text-[10px] leading-4 text-muted-foreground">{detail}</p>}
  </div>;
}

function MeasuredProgressPanel({ activityId }: { activityId: number }) {
  const [items, setItems] = useState<MeasuredProgress[]>([]);
  const [form, setForm] = useState({ assessment_date: new Date().toISOString().slice(0, 10), planned_quantity: "", completed_quantity: "", unit: "", notes: "" });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const role = typeof window === "undefined" ? "" : window.sessionStorage.getItem("constructiq-role") ?? window.localStorage.getItem("constructiq-role") ?? "";
  useEffect(() => {
    void api.get<MeasuredProgress[]>(`/api/activities/${activityId}/measured-progress`).then(setItems).catch(() => setItems([]));
  }, [activityId]);
  const submit = async () => {
    setError("");
    setMessage("");
    try {
      const created = await api.post<MeasuredProgress>(`/api/activities/${activityId}/measured-progress`, { ...form, planned_quantity: form.planned_quantity, completed_quantity: form.completed_quantity, notes: form.notes || null });
      setItems(current => [created, ...current]);
      setMessage("Submitted for verification. It is not actual progress until approved.");
      setForm(current => ({ ...current, planned_quantity: "", completed_quantity: "", notes: "" }));
    } catch (requestError) {
      setError(analyticsErrorMessage(requestError, "Measured progress could not be submitted."));
    }
  };
  const verify = async (id: number, decision: "VERIFIED" | "REJECTED") => {
    try {
      const updated = await api.post<MeasuredProgress>(`/api/measured-progress/${id}/verify`, { decision });
      setItems(current => current.map(item => item.id === id ? updated : item));
      setMessage(decision === "VERIFIED" ? "Verified measured progress saved. Refreshing intelligence is required." : "Measured progress rejected.");
    } catch (requestError) {
      setError(analyticsErrorMessage(requestError, "Measured progress verification failed."));
    }
  };
  const canSubmit = role === "Field Engineer" || role === "Site Engineer";
  const canVerify = ["Site Engineer", "QA/QC Engineer", "Project Manager", "Admin"].includes(role);
  return <Card><SectionTitle title="Verified measured progress" /><p className="text-xs text-muted-foreground">Submit real field quantities for independent verification. Pending and rejected quantities never become actual progress.</p>{canSubmit && <div className="mt-4 grid gap-3 sm:grid-cols-2"><label className="text-[10px] font-bold text-muted-foreground">DATE<input type="date" value={form.assessment_date} onChange={event => setForm(current => ({ ...current, assessment_date: event.target.value }))} className="mt-2 h-10 w-full rounded-xl border border-border bg-background px-3 text-xs" /></label><label className="text-[10px] font-bold text-muted-foreground">UNIT<input value={form.unit} onChange={event => setForm(current => ({ ...current, unit: event.target.value }))} placeholder="m3, kg, m" className="mt-2 h-10 w-full rounded-xl border border-border bg-background px-3 text-xs" /></label><label className="text-[10px] font-bold text-muted-foreground">PLANNED QUANTITY<input type="number" min="0.001" step="0.001" value={form.planned_quantity} onChange={event => setForm(current => ({ ...current, planned_quantity: event.target.value }))} className="mt-2 h-10 w-full rounded-xl border border-border bg-background px-3 text-xs" /></label><label className="text-[10px] font-bold text-muted-foreground">COMPLETED QUANTITY<input type="number" min="0" step="0.001" value={form.completed_quantity} onChange={event => setForm(current => ({ ...current, completed_quantity: event.target.value }))} className="mt-2 h-10 w-full rounded-xl border border-border bg-background px-3 text-xs" /></label><label className="text-[10px] font-bold text-muted-foreground sm:col-span-2">NOTES<textarea value={form.notes} onChange={event => setForm(current => ({ ...current, notes: event.target.value }))} className="mt-2 min-h-16 w-full rounded-xl border border-border bg-background p-3 text-xs" /></label><Button type="button" onClick={() => void submit()} disabled={!form.unit || !form.planned_quantity || !form.completed_quantity}>Submit for verification</Button></div>}{error && <p role="alert" className="mt-3 text-xs text-danger">{error}</p>}{message && <p className="mt-3 text-xs text-success">{message}</p>}<div className="mt-4 space-y-2">{items.length ? items.map(item => <div key={item.id} className="rounded-xl border border-border bg-secondary p-3 text-xs"><div className="flex items-center justify-between gap-2"><b>{item.assessment_date} · {item.completed_quantity} / {item.planned_quantity} {item.unit}</b><StatusBadge tone={item.verification_status === "VERIFIED" ? "success" : item.verification_status === "REJECTED" ? "danger" : "warning"}>{item.verification_status}</StatusBadge></div>{item.notes && <p className="mt-1 text-muted-foreground">{item.notes}</p>}{canVerify && item.verification_status === "PENDING" && <div className="mt-2 flex gap-2"><Button size="sm" onClick={() => void verify(item.id, "VERIFIED")}>Verify</Button><Button size="sm" variant="outline" onClick={() => void verify(item.id, "REJECTED")}>Reject</Button></div>}</div>) : <p className="mt-4 text-xs text-muted-foreground">No measured progress submissions exist for this activity.</p>}</div></Card>;
}

function SihIntelligenceScreen({ onScreen }: { onScreen?: (screen: Screen) => void }) {
  const projectId = projectIdFromStorage();
  const [data, setData] = useState<{ overall?: { planned?: number; actual?: number; variance?: number }; activities?: Array<{ activity_id: number; name: string; planned: number | null; actual: number | null; variance: number | null }> } | null>(null);
  const [assessment, setAssessment] = useState<ProgressAssessment | null>(null);
  const [comparison, setComparison] = useState<EvidenceComparison | null>(null);
  const [risk, setRisk] = useState<AnalyticsRisk | null>(null);
  const [delay, setDelay] = useState<AnalyticsDelay | null>(null);
  const [recovery, setRecovery] = useState<RecoveryRecommendation[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!projectId) { setError("Project context is unavailable."); return; }
    let active = true;
    void api.get<typeof data>(`/api/projects/${projectId}/analytics/progress`).then(async response => {
      const activity = response.activities?.[0];
      const latest = activity ? await api.get<ProgressAssessment>(`/api/activities/${activity.activity_id}/progress-assessment/latest`).catch(() => null) : null;
      const [riskResponse, delayResponse, recoveryResponse, comparisonResponse, executionResponse] = activity ? await Promise.all([
        api.get<{ activities?: AnalyticsRisk[] }>(`/api/projects/${projectId}/analytics/risks`).catch(() => null),
        api.get<{ delayed_activities?: AnalyticsDelay[] }>(`/api/projects/${projectId}/analytics/delays`).catch(() => null),
        api.get<{ items?: RecoveryRecommendation[] }>(`/api/activities/${activity.activity_id}/recovery-recommendations`).catch(() => null),
        latest?.evidence_id ? api.get<EvidenceComparison>(`/api/evidence/${latest.evidence_id}/comparison-analysis`).catch(() => null) : Promise.resolve(null),
        api.get<ExecutionIntelligence>(`/api/activities/${activity.activity_id}/execution-intelligence?assessment_date=${latest?.assessment_date ?? ""}`).catch(() => null),
      ]) : [null, null, null, null, null];
      if (active) {
        setData(response);
        setAssessment(latest);
        setRisk(riskResponse?.activities?.find(item => item.activity_id === activity?.activity_id) ?? null);
        setDelay(delayResponse?.delayed_activities?.find(item => item.activity_id === activity?.activity_id) ?? null);
        setRecovery(recoveryResponse?.items ?? []);
        setComparison(comparisonResponse);
        setExecution(executionResponse);
      }
    }).catch(requestError => { if (active) setError(analyticsErrorMessage(requestError, "Progress data could not be loaded.")); });
    return () => { active = false; };
  }, [projectId]);
  if (error) return <Card><p role="alert" className="text-sm text-danger">{error}</p></Card>;
  if (!data) return <Card><p className="text-sm text-muted-foreground">Loading progress data…</p></Card>;
  const activity = data.activities?.[0];
  return <div className="space-y-5"><Card className="border-primary/25 bg-primary/5"><StatusBadge tone="primary">PLANNING → EXECUTION</StatusBadge><h2 className="mt-3 text-2xl font-extrabold">Progress Control</h2><p className="mt-1 text-xs leading-5 text-muted-foreground">Live progress, comparison, risk, delay, and recovery values from backend APIs.</p></Card><section><SectionTitle title="Project Progress Overview" /><div className="grid grid-cols-2 gap-2 sm:grid-cols-3"><SihDataCard label="Overall planned progress" value={displayValue(assessment?.planned_progress ?? data.overall?.planned, "%")} /><SihDataCard label="Overall reported progress" value={displayValue(assessment?.reported_progress ?? data.overall?.actual, "%")} tone="success" /><SihDataCard label="Schedule variance" value={displayValue(assessment?.variance_from_plan ?? data.overall?.variance, "%")} tone="danger" /><SihDataCard label="Activity" value={displayValue(activity?.name)} /><SihDataCard label="AI estimated progress" value={displayValue(assessment?.ai_estimated_progress, "%")} tone="warning" /><SihDataCard label="Fused progress" value={displayValue(assessment?.fused_progress, "%")} tone="success" /></div></section><Card><div className="flex items-start justify-between gap-3"><div><p className="text-[10px] font-bold uppercase tracking-[0.12em] text-primary">Latest assessment</p><h2 className="mt-2 text-lg font-extrabold">{displayValue(activity?.name)}</h2></div><StatusBadge tone={assessment ? "success" : "muted"}>{displayValue(assessment?.assessment_status, "")}</StatusBadge></div><div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4"><SihDataCard label="Planned" value={displayValue(execution?.planned_progress ?? assessment?.planned_progress ?? activity?.planned, "%")} /><SihDataCard label="Actual" value={displayValue(execution?.actual_progress, "%")} /><SihDataCard label="Source" value={displayValue(execution?.actual_progress_source)} /><SihDataCard label="AI confidence" value={displayValue(execution?.actual_progress_confidence, "%")} /><SihDataCard label="Assessment date" value={displayValue(assessment?.assessment_date)} /><p className="col-span-2 text-xs text-muted-foreground">{execution?.actual_progress_reason ?? "Actual progress explanation unavailable."}</p></div><div className="mt-4 flex flex-wrap gap-2"><Button size="sm" onClick={() => onScreen?.("ai")}>View risk and recovery <ChevronRight /></Button></div></Card><Card><SectionTitle title="Evidence comparison" /><div className="grid grid-cols-2 gap-2"><SihDataCard label="Comparison ID" value={displayValue(comparison?.comparison_id)} /><SihDataCard label="Evidence pair" value={comparison ? `${comparison.current_evidence_id} → ${comparison.previous_evidence_id}` : "—"} /><SihDataCard label="Change" value={displayValue(comparison?.overall_change)} /><SihDataCard label="Confidence" value={comparison ? `${(comparison.confidence * 100).toFixed(1)}%` : "—"} /><SihDataCard label="Absolute progress" value={displayValue(comparison?.absolute_progress_estimate, "%")} /><SihDataCard label="Estimate confidence" value={comparison?.absolute_progress_confidence != null ? `${comparison.absolute_progress_confidence.toFixed(1)}%` : "—"} /></div><div className="mt-3 space-y-1 text-xs text-muted-foreground">{comparison?.observations?.filter(item => item.observation).slice(0, 4).map((item, index) => <p key={`${item.category ?? "observation"}-${index}`}>• {item.observation}</p>)}</div><p className="mt-3 text-xs text-muted-foreground">{comparison?.notes ?? "No comparison result is available."}</p></Card><Card><SectionTitle title="Decision outputs" /><div className="grid grid-cols-2 gap-2"><SihDataCard label="Risk" value={displayValue(risk?.risk_level)} tone={risk?.risk_level === "HIGH" || risk?.risk_level === "CRITICAL" ? "danger" : "warning"} detail={risk ? `${displayValue(risk.primary_risk)} · score ${displayValue(risk.risk_score)}` : undefined} />  <SihDataCard label="Delay" value={displayValue(execution?.predicted_delay_days, " days")} tone="danger" detail={execution?.delay_reason ?? "Delay unavailable — insufficient verified productivity history"} /><SihDataCard label="Expected completion" value={displayValue(execution?.expected_completion_date)} /><SihDataCard label="Recovery" value={displayValue(recovery[0]?.title)} detail={recovery[0]?.description} /></div><div className="mt-3 grid grid-cols-2 gap-2"><SihDataCard label="Actual / fused" value={displayValue(execution?.actual_progress, "%")} tone="success" /><SihDataCard label="Variance" value={displayValue(execution?.variance, "%")} tone={execution?.variance_status === "BEHIND" ? "danger" : "success"} /><SihDataCard label="Productivity" value={displayValue(execution?.productivity_rate, "% / day")} detail={execution?.productivity_reason} /></div></Card><Card><p className="text-[10px] font-bold uppercase tracking-[0.12em] text-primary">Reported activity progress</p><div className="mt-3 space-y-3">{data.activities?.length ? data.activities.map(item => <div key={item.activity_id} className="rounded-xl bg-secondary p-3"><div className="flex items-center justify-between gap-2 text-xs"><b>{item.name}</b><span>{displayValue(item.actual, "%")}</span></div><div className="mt-2"><Progress value={item.actual ?? 0} /></div><p className="mt-2 text-[10px] text-muted-foreground">Planned {displayValue(item.planned, "%")} · Variance {displayValue(item.variance, "%")}</p></div>) : <p className="text-sm text-muted-foreground">No progress activities were returned.</p>}</div></Card></div>;
}
const roleScreens: Record<Role, Screen[]> = {
  Worker: ["home", "activities", "sih-intelligence", "capture", "notifications", "profile", "settings"],
  Foreman: ["home", "sih-intelligence", "activities", "timeline", "notifications", "profile", "settings"],
  "Field Engineer": ["home", "activities", "sih-intelligence", "capture", "evidence", "timeline", "replay", "notifications", "profile", "settings"],
  "Site Engineer": ["home", "activities", "sih-intelligence", "evidence", "ai", "timeline", "replay", "notifications", "profile", "settings"],
  "Safety Officer": ["home", "sih-intelligence", "activities", "inspection", "timeline", "notifications", "profile", "settings"],
  "QA/QC Engineer": ["home", "sih-intelligence", "activities", "inspection", "evidence", "notifications", "profile", "settings"],
  "Material Manager": ["home", "sih-intelligence", "activities", "inventory", "notifications", "profile", "settings"],
  Driver: ["home", "sih-intelligence", "activities", "trip", "replay", "notifications", "profile", "settings"],
  "Equipment Manager": ["home", "sih-intelligence", "activities", "timeline", "notifications", "profile", "settings"],
  "Project Manager": ["home", "sih-intelligence", "planning", "activities", "analytics", "ai", "timeline", "replay", "notifications", "profile", "settings"],
  "Planning Engineer": ["home", "planning", "sih-intelligence", "notifications", "profile", "settings"],
  Admin: ["home", "sih-intelligence", "planning", "activities", "analytics", "ai", "timeline", "replay", "notifications", "profile", "settings"],
};

type NotificationPriority = "Critical" | "High" | "Medium" | "Low";

type AppNotification = {
  id: string;
  type: string;
  priority: NotificationPriority;
  title: string;
  description: string;
  timestamp: string;
  related: string;
  relatedProject?: string;
  relatedActivity?: string;
  read: boolean;
  tone: Tone;
  icon: ComponentType<{ className?: string }>;
};

const priorityFilterOptions = ["All", "Critical", "High", "Medium", "Low"] as const;
type PriorityFilter = (typeof priorityFilterOptions)[number];

const notificationPriorityTone: Record<NotificationPriority, Tone> = {
  Critical: "danger",
  High: "warning",
  Medium: "primary",
  Low: "success",
};

function getRoleNotifications(notifications: import("@/app/types").Notification[]): AppNotification[] {
  return notifications.map(notification => ({
    ...notification,
    related: `${notification.relatedProject} · ${notification.relatedActivity}`,
    tone: notification.priority === "Critical" ? "danger" : notification.priority === "High" ? "warning" : notification.priority === "Medium" ? "primary" : "success",
    icon: notification.priority === "Critical" ? AlertTriangle : notification.priority === "High" ? Bell : notification.priority === "Medium" ? Activity : CheckCircle2,
  }));
}

function IssueLifecycle({ currentStep }: { currentStep: string }) {
  const steps = ["REPORTED", "ASSIGNED", "INVESTIGATING", "ACTION TAKEN", "RESOLVED", "VERIFIED"];
  const currentIndex = steps.indexOf(currentStep);

  return <div className="mt-4"><div className="grid grid-cols-6 gap-1.5">{steps.map((step, index) => {
    const done = index < currentIndex;
    const active = index === currentIndex;
    return <div key={step} className="flex flex-col items-center gap-1.5"><div className={cn("h-2 w-full rounded-full", done ? "bg-success" : active ? "bg-primary" : "bg-secondary")} /><span className={cn("text-[7px] font-bold uppercase tracking-[0.08em]", active ? "text-primary" : done ? "text-success" : "text-muted-foreground")}>{step === "ACTION TAKEN" ? "ACTION" : step === "INVESTIGATING" ? "INV" : step === "VERIFIED" ? "VER" : step.slice(0, 3)}</span></div>;
  })}</div></div>;
}

function NotificationCenter({ role }: { role: Role }) {
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [priorityFilter, setPriorityFilter] = useState<PriorityFilter>("All");

  useEffect(() => {
    let active = true;
    notificationService.getByRole(role)
      .then(items => { if (active) setNotifications(getRoleNotifications(items)); })
      .catch(() => { if (active) setNotifications([]); });
    setPriorityFilter("All");
    return () => { active = false; };
  }, [role]);

  const unreadCount = notifications.filter(notification => !notification.read).length;
  const visibleNotifications = notifications.filter(notification => priorityFilter === "All" || notification.priority === priorityFilter);

  const markAsRead = (id: string) => {
    void notificationService.markAsRead(id).then(() => {
      setNotifications(current => current.map(notification => notification.id === id ? { ...notification, read: true } : notification));
    });
  };

  const markAllAsRead = () => {
    void notificationService.markAllAsRead().then(() => {
      setNotifications(current => current.map(notification => ({ ...notification, read: true })));
    });
  };

  const issueHistory = [
    { label: "REPORTED", time: "08:10", done: true },
    { label: "ASSIGNED", time: "08:14", done: true },
    { label: "INVESTIGATING", time: "08:20", done: true },
    { label: "ACTION TAKEN", time: "08:32", done: true },
    { label: "RESOLVED", time: "08:38", done: false },
    { label: "VERIFIED", time: "08:42", done: false },
  ];

  return <div className="space-y-4">
    <Card className="border-danger/30 bg-danger/8">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-danger">Issue management</p>
          <h2 className="mt-2 text-lg font-extrabold">Steel material shortage</h2>
        </div>
        <StatusBadge tone="danger">CRITICAL</StatusBadge>
      </div>
      <p className="mt-3 text-xs leading-5 text-muted-foreground">The TMT 32mm steel stock for Pier P3 is below the minimum threshold and is delaying the next reinforcement cycle.</p>
      <div className="mt-4 grid grid-cols-2 gap-2 text-[10px] text-muted-foreground">
        <div className="rounded-xl bg-secondary p-2.5"><p className="font-bold uppercase tracking-[0.08em] text-foreground">Location</p><p className="mt-1 text-xs text-foreground">Zone B • Pier P3</p></div>
        <div className="rounded-xl bg-secondary p-2.5"><p className="font-bold uppercase tracking-[0.08em] text-foreground">Reported by</p><p className="mt-1 text-xs text-foreground">Field Engineer Ravi</p></div>
        <div className="rounded-xl bg-secondary p-2.5"><p className="font-bold uppercase tracking-[0.08em] text-foreground">Assigned to</p><p className="mt-1 text-xs text-foreground">Material Manager</p></div>
        <div className="rounded-xl bg-secondary p-2.5"><p className="font-bold uppercase tracking-[0.08em] text-foreground">Reported time</p><p className="mt-1 text-xs text-foreground">08:10</p></div>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-2 text-[10px] text-muted-foreground">
        <div className="rounded-xl bg-secondary p-2.5"><p className="font-bold uppercase tracking-[0.08em] text-foreground">Photo / Evidence</p><p className="mt-1 text-xs text-foreground">Photo + GPS</p></div>
        <div className="rounded-xl bg-secondary p-2.5"><p className="font-bold uppercase tracking-[0.08em] text-foreground">Current status</p><p className="mt-1 text-xs text-warning">ACTION TAKEN</p></div>
      </div>
      <div className="mt-4 rounded-xl border border-primary/20 bg-primary/5 p-3 text-xs leading-5 text-muted-foreground"><span className="font-bold text-foreground">Description:</span> Steel delivery is delayed by 9 hours and current stock is 41% of required quantity for the next pour window.</div>
      <IssueLifecycle currentStep="ACTION TAKEN" />
      <div className="mt-4 space-y-2">
        {issueHistory.map((item, index) => <div key={item.label} className="flex items-center gap-3"><span className={cn("h-2.5 w-2.5 rounded-full", item.done ? "bg-success" : index === 4 ? "bg-warning" : "bg-secondary")} /><div className="flex flex-1 items-center justify-between rounded-lg bg-secondary px-2.5 py-1.5 text-[10px]"><span className="font-bold uppercase tracking-[0.08em] text-foreground">{item.label}</span><span className="text-muted-foreground">{item.time}</span></div></div>)}
      </div>
    </Card>
    <Card>
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-widest text-primary">Inbox</p>
          <h2 className="mt-1 text-xl font-extrabold">Notifications</h2>
        </div>
        <StatusBadge tone={unreadCount > 0 ? "warning" : "success"}>{unreadCount} unread</StatusBadge>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {priorityFilterOptions.map(option => <button key={option} type="button" onClick={() => setPriorityFilter(option)} className={cn("rounded-full border px-2.5 py-1.5 text-[10px] font-bold transition-colors", priorityFilter === option ? "border-primary bg-primary text-primary-foreground" : "border-border bg-secondary text-muted-foreground")}>{option}</button>)}
      </div>
      <Button className="mt-4 w-full" variant="outline" onClick={markAllAsRead} disabled={unreadCount === 0}>Mark all as read</Button>
    </Card>
    <div className="space-y-3">
      {visibleNotifications.length === 0 ? <Card><p className="text-center text-sm text-muted-foreground">No notifications match this priority.</p></Card> : visibleNotifications.map(notification => {
        const Icon = notification.icon;
        const priorityTone = notificationPriorityTone[notification.priority];
        return <Card key={notification.id} className={cn("transition-colors", !notification.read && "border-primary/30 bg-primary/5")}>
          <div className="flex items-start gap-3">
            <div className={cn("grid h-11 w-11 shrink-0 place-items-center rounded-xl border", toneClasses[notification.tone])}><Icon className="h-4 w-4" /></div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge tone={notification.tone}>{notification.type}</StatusBadge>
                  <StatusBadge tone={priorityTone}>{notification.priority}</StatusBadge>
                </div>
                <StatusBadge tone={notification.read ? "muted" : "primary"}>{notification.read ? "Read" : "Unread"}</StatusBadge>
              </div>
              <h3 className="mt-3 text-base font-extrabold leading-5">{notification.title}</h3>
              <p className="mt-2 text-xs leading-5 text-muted-foreground">{notification.description}</p>
              <div className="mt-3 grid grid-cols-2 gap-3 text-[10px] text-muted-foreground">
                <div>
                  <p className="font-bold uppercase tracking-wider text-foreground">Timestamp</p>
                  <p className="mt-1">{notification.timestamp}</p>
                </div>
                <div>
                  <p className="font-bold uppercase tracking-wider text-foreground">Related project</p>
                  <p className="mt-1">{notification.relatedProject ?? "Metro Line 6 · Package C3"}</p>
                </div>
                <div>
                  <p className="font-bold uppercase tracking-wider text-foreground">Related activity</p>
                  <p className="mt-1">{notification.relatedActivity ?? notification.related}</p>
                </div>
              </div>
              <div className="mt-4 flex justify-end">
                <Button size="sm" variant={notification.read ? "secondary" : "default"} onClick={() => markAsRead(notification.id)} disabled={notification.read}>{notification.read ? "Read" : "Mark as read"}</Button>
              </div>
            </div>
          </div>
        </Card>;
      })}
    </div>
  </div>;
}

function StandardScreen({ screen, role, onScreen, onLogout }: { screen: Screen; role: Role; onScreen: (s: Screen) => void; onLogout: () => void }) {
  if (screen === "capture") return <CaptureFlow onBack={() => onScreen("home")} />;
  if (screen === "sih-intelligence") return <SihIntelligenceScreen onScreen={onScreen} />;
  if (screen === "planning") return <PlanningScheduleScreen role={role} onScreen={onScreen} />;
  if (screen === "evidence") return <RealEvidenceScreen />;
  if (screen === "analytics") return <AnalyticsScreen />;
  if (screen === "ai") return <SihIntelligenceScreen onScreen={onScreen} />;
  if (screen === "timeline") return <><div className="mb-5 flex gap-2"><Button variant="outline"><CalendarDays /> Today</Button><Button onClick={() => onScreen("replay")}><Play /> Replay</Button></div><ProjectMemoryPanel /><Timeline interactive /></>;
  if (screen === "replay" || screen === "trip") return <ReplayScreen />;
  if (screen === "inspection") return <InspectionScreen />;
  if (screen === "inventory") return <InventoryScreen />;
  if (screen === "notifications") return <NotificationCenter role={role} />;
  if (screen === "profile" || screen === "settings") return <ProfileScreen role={role} settings={screen === "settings"} onSettings={() => onScreen("settings")} onLogout={onLogout} />;
  if (screen === "activities") return <ActivitiesScreen />;
  return null;
}

function ProfileScreen({ role, settings, onSettings, onLogout }: { role: Role; settings: boolean; onSettings: () => void; onLogout: () => void }) {
  const [logoutOpen, setLogoutOpen] = useState(false);
  const info = roleCopy[role];
  const [profileData, setProfileData] = useState({
    workerId: "—", name: "—", email: "—", company: "—", project: "—", assignment: "—", status: "—",
    attendance: [["Attendance %", "—"], ["Days present", "—"], ["Recent attendance", "—"]],
    safety: [["Safety training", "—"], ["PPE compliance", "—"], ["Certifications", "—"], ["Training status", "—"]],
    work: [["Assigned activities", "—"], ["Completed activities", "—"], ["Work history", "—"], ["Current assignment", "—"]],
    site: [["Projects worked on", "—"], ["Zones worked on", "—"], ["Recent activities", "—"]],
    reports: [["Issues reported", "—"], ["Safety reports", "—"]],
  });
  useEffect(() => {
    const projectId = projectIdFromStorage();
    if (!projectId) return;
    let active = true;
    void Promise.all([
      api.get<Record<string, unknown>>("/api/auth/me"),
      api.get<Record<string, unknown>>(`/api/projects/${projectId}/attendance/summary`),
      api.get<Record<string, unknown>>(`/api/projects/${projectId}/analytics/safety`),
      api.get<Record<string, unknown>>(`/api/projects/${projectId}/activities`),
    ]).then(([user, attendanceSummary, safetySummary, activities]) => {
      if (!active) return;
      const activityItems = Array.isArray(activities) ? activities : [];
      const present = Number(attendanceSummary.present_workers ?? attendanceSummary.present ?? NaN);
      const assigned = Number(attendanceSummary.assigned_workers ?? attendanceSummary.total_workers ?? NaN);
      const compliance = safetySummary.ppe_compliance_percentage ?? safetySummary.compliance_rate;
      setProfileData({
        workerId: user.id == null ? "—" : String(user.id),
        name: String(user.full_name ?? "—"),
        email: String(user.email ?? "—"),
        company: String(user.company ?? "—"),
        project: String(user.project_name ?? "—"),
        assignment: activityItems.length ? String((activityItems[0] as Record<string, unknown>).name ?? "—") : "—",
        status: String(user.status ?? "—"),
        attendance: [["Attendance %", Number.isFinite(present) && Number.isFinite(assigned) && assigned > 0 ? `${Math.round((present / assigned) * 100)}%` : "—"], ["Days present", Number.isFinite(present) && Number.isFinite(assigned) ? `${present} / ${assigned}` : "—"], ["Recent attendance", "—"]],
        safety: [["Safety training", "—"], ["PPE compliance", compliance == null ? "—" : `${compliance}%`], ["Certifications", "—"], ["Training status", "—"]],
        work: [["Assigned activities", String(activityItems.length)], ["Completed activities", "—"], ["Work history", "—"], ["Current assignment", activityItems.length ? String((activityItems[0] as Record<string, unknown>).name ?? "—") : "—"]],
        site: [["Projects worked on", "—"], ["Zones worked on", "—"], ["Recent activities", activityItems.slice(0, 3).map(item => String((item as Record<string, unknown>).name ?? "")).filter(Boolean).join(" · ") || "—"]],
        reports: [["Issues reported", "—"], ["Safety reports", String(safetySummary.total_incidents ?? "—")]],
      });
    }).catch(() => undefined);
    return () => { active = false; };
  }, []);
  const passportProfile = [["Worker ID", profileData.workerId], ["Name", profileData.name], ["Role", role], ["Contractor / company", profileData.company], ["Skills", "—"], ["Current Project", profileData.project], ["Current assignment", profileData.assignment], ["Current status", profileData.status]];
  const workHistory = profileData.work;
  const attendance = profileData.attendance;
  const safety = profileData.safety;
  const siteHistory = profileData.site;
  const reports = profileData.reports;

  if (settings) return <div className="space-y-5"><Card>{[["Project notifications", true], ["Critical alerts", true], ["Evidence updates", false], ["Offline capture", true]].map(([x, on]) => <div key={String(x)} className="flex items-center justify-between border-b border-border py-4 last:border-0"><span className="text-sm font-bold">{x}</span><span className={cn("relative h-6 w-11 rounded-full", on ? "bg-primary" : "bg-secondary")}><i className={cn("absolute top-1 h-4 w-4 rounded-full bg-foreground transition-all", on ? "left-6" : "left-1")} /></span></div>)}</Card><Card><ActivityRow title="Location accuracy" meta="High accuracy · recommended" status="High" tone="success" icon={LocateFixed} /><ActivityRow title="Media upload quality" meta="Optimized for site networks" status="Auto" icon={Upload} /></Card><LogoutButton onClick={() => setLogoutOpen(true)} /><LogoutDialog open={logoutOpen} onOpenChange={setLogoutOpen} onConfirm={onLogout} /></div>;
  const profileName = profileData.name === "—" ? info.first : profileData.name;
  return <div className="space-y-5"><div className="flex flex-col items-center py-5"><div className="grid h-24 w-24 place-items-center rounded-3xl bg-primary text-3xl font-extrabold text-primary-foreground">{profileName.slice(0, 2).toUpperCase()}</div><h2 className="mt-4 text-xl font-extrabold">{profileName}</h2><p className="mt-1 text-xs text-muted-foreground">{role} · {profileData.project}</p><StatusBadge tone="muted">{profileData.status}</StatusBadge></div><Card><ActivityRow title="Employee ID" meta={profileData.workerId} status={profileData.status} tone="muted" icon={UserRound} /><ActivityRow title="Current shift" meta="—" status="—" icon={Clock3} /></Card>
    <Card className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-primary">CONSTRUCTION DIGITAL PASSPORT</p>
          <h3 className="mt-1 text-lg font-extrabold">Worker identity</h3>
        </div>
        <StatusBadge tone="success">Verified</StatusBadge>
      </div>

      <div className="space-y-3">
        <div className="grid gap-2 sm:grid-cols-2">
          {passportProfile.map(([label, value]) => <div key={label} className="rounded-xl bg-secondary p-2.5"><p className="text-[9px] font-bold uppercase tracking-[0.08em] text-muted-foreground">{label}</p><p className="mt-1 text-sm font-extrabold text-foreground">{value}</p></div>)}
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-border bg-card p-3">
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-primary">Work history</p>
          <div className="mt-3 space-y-2 text-xs text-muted-foreground">
            {workHistory.map(([label, value]) => <div key={label} className="flex items-center justify-between gap-3"><span className="font-bold text-foreground">{label}</span><span className="text-right">{value}</span></div>)}
          </div>
        </div>
        <div className="rounded-xl border border-border bg-card p-3">
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-primary">Attendance</p>
          <div className="mt-3 space-y-2 text-xs text-muted-foreground">
            {attendance.map(([label, value]) => <div key={label} className="flex items-center justify-between gap-3"><span className="font-bold text-foreground">{label}</span><span>{value}</span></div>)}
          </div>
        </div>
        <div className="rounded-xl border border-border bg-card p-3">
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-primary">Safety</p>
          <div className="mt-3 space-y-2 text-xs text-muted-foreground">
            {safety.map(([label, value]) => <div key={label} className="flex items-center justify-between gap-3"><span className="font-bold text-foreground">{label}</span><span>{value}</span></div>)}
          </div>
        </div>
        <div className="rounded-xl border border-border bg-card p-3">
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-primary">Site history</p>
          <div className="mt-3 space-y-2 text-xs text-muted-foreground">
            {siteHistory.map(([label, value]) => <div key={label} className="flex items-center justify-between gap-3"><span className="font-bold text-foreground">{label}</span><span className="text-right">{value}</span></div>)}
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-border bg-card p-3">
        <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-primary">Reports</p>
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {reports.map(([label, value]) => <div key={label} className="rounded-xl bg-secondary p-2.5"><p className="text-[9px] font-bold uppercase tracking-[0.08em] text-muted-foreground">{label}</p><p className="mt-1 text-sm font-extrabold text-foreground">{value}</p></div>)}
        </div>
      </div>
    </Card>
    <div className="space-y-3"><Button variant="outline" className="w-full justify-between" onClick={onSettings}><span className="flex items-center gap-2"><Settings /> Settings</span><ChevronRight /></Button><LogoutButton onClick={() => setLogoutOpen(true)} /><LogoutDialog open={logoutOpen} onOpenChange={setLogoutOpen} onConfirm={onLogout} /></div></div>;
}

function LogoutButton({ onClick }: { onClick: () => void }) {
  return <Button variant="outline" className="w-full justify-between border-danger/30 text-danger hover:bg-danger/8 hover:text-danger" onClick={onClick}><span className="flex items-center gap-2"><X /> Log Out</span><ChevronRight /></Button>;
}

function LogoutDialog({ open, onOpenChange, onConfirm }: { open: boolean; onOpenChange: (open: boolean) => void; onConfirm: () => void }) {
  return <AlertDialog open={open} onOpenChange={onOpenChange}><AlertDialogContent><AlertDialogHeader><AlertDialogTitle>Log out of BuildSync?</AlertDialogTitle><AlertDialogDescription>You will need to sign in again to access your project.</AlertDialogDescription></AlertDialogHeader><AlertDialogFooter><AlertDialogCancel>Cancel</AlertDialogCancel><AlertDialogAction onClick={onConfirm}>Log Out</AlertDialogAction></AlertDialogFooter></AlertDialogContent></AlertDialog>;
}

function ChatbotAssistant({ role, open, onClose }: { role: Role; open: boolean; onClose: () => void }) {
  const info = roleCopy[role];
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<{ from: "assistant" | "user"; text: string; sections?: { label: string; content: string }[]; context?: { activity: string; evidence: string; event: string } }[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const quickQuestions = ["Why is Pier P3 delayed?", "Which activities are at risk?", "What material is running low?", "Which activities require verification?", "How can we recover the delayed activities?", "How many workers are currently available?", "What happened today on site?", "Which activity has the highest schedule risk?"];

  useEffect(() => {
    if (open && messages.length === 0) {
      setMessages([{ from: "assistant", text: `Hello ${info.first}. I can answer questions about schedule, resources, site events, and recovery actions.`, sections: [{ label: "Suggested starting point", content: "Ask why Pier P3 is delayed or which materials are running low." }] }]);
    }
  }, [info.first, info.subtitle, messages.length, open]);

  const getMockAnswer = (prompt: string) => {
    const lower = prompt.toLowerCase();
    if (lower.includes("pier p3") || lower.includes("delayed")) return { text: "Pier P3 is currently 14% behind planned progress. The main contributing factors are worker shortage, delayed steel delivery, and weather interruption.", sections: [{ label: "Reasons", content: "Six workers were absent, steel arrived 9 hours late, and rain paused external work for 4.5 hours yesterday." }, { label: "Supporting evidence", content: "Planned progress is 78% versus 64% reported. The latest site timeline records the late steel delivery and rain interruption." }, { label: "Recommended action", content: "Reallocate 4 workers or extend working hours; the recommended plan is expected to recover the variance in about 1 day." }], context: { activity: "Pier P3 Reinforcement", evidence: "Steel delivery note DN-104 · 3 site photos", event: "Material delivery delayed · 11:30" } };
    if (lower.includes("risk")) return { text: "Three activities are currently at risk: Pier P3 reinforcement, Deck D2 shuttering, and the utility diversion.", sections: [{ label: "Reasons", content: "Pier P3 has a workforce and material shortfall; Deck D2 is waiting on inspection clearance; the utility diversion is blocked by an unresolved issue." }, { label: "Supporting evidence", content: "Pier P3 is HIGH risk with a predicted 2-day delay. Deck D2 is due at 16:30 and the utility diversion is marked Blocked." }, { label: "Recommended action", content: "Prioritize Pier P3 recovery, clear the Deck D2 hold point, and assign an owner to the utility issue today." }], context: { activity: "Pier P3 Reinforcement", evidence: "Progress update · 64% reported", event: "Delay risk identified · Today" } };
    if (lower.includes("worker")) return { text: "There are currently 36 workers available, against 42 required for the planned production rate.", sections: [{ label: "Workforce information", content: "The six-person gap is concentrated around the Pier P3 reinforcement crew." }, { label: "Recovery recommendation", content: "Mobilize 6 workers for the next shift, or reallocate 4 workers from a lower-priority activity." }], context: { activity: "Pier P3 Reinforcement", evidence: "Crew availability report · 36 available", event: "Workforce shortage flagged · 09:10" } };
    if (lower.includes("material")) return { text: "Ready-mix M40 is running low at 18% remaining.", sections: [{ label: "Reasons", content: "Current pours at Zone B are consuming stock faster than the next scheduled delivery." }, { label: "Supporting evidence", content: "Inventory shows 42 m³ remaining in Batch RM-42, with a Low stock status." }, { label: "Recommended action", content: "Expedite the next ready-mix delivery and confirm the pour sequence with the Site Engineer." }] };
    if (lower.includes("yesterday") || lower.includes("happened")) return { text: "Yesterday, the team started foundation work at Pier P3, received 24 tons of steel, uploaded field evidence, and paused external works during rain.", sections: [{ label: "Reasons", content: "The rain interruption and an equipment issue affected the afternoon work window." }, { label: "Supporting evidence", content: "The timeline records steel delivery at 11:30, evidence upload at 13:15, a crane issue at 14:30, and rain at 16:00." }, { label: "Recommended action", content: "Review the crane inspection and carry forward the weather-affected work into the next available shift." }] };
    if (lower.includes("critical") || lower.includes("issue")) return { text: "Today's critical issues are the Pier P3 delay risk, the Crane TC-02 equipment issue, and low Ready-mix M40 stock.", sections: [{ label: "Reasons", content: "These issues can directly affect today's pour sequence and the recovery schedule." }, { label: "Supporting evidence", content: "Pier P3 is HIGH risk, Crane TC-02 is flagged in Zone B, and Ready-mix M40 is at 18% stock." }, { label: "Recommended action", content: "Confirm the recovery crew, close the crane issue, and expedite ready-mix delivery before the next pour." }] };
    return { text: "The current schedule variance can be recovered with a focused crew and one additional shift.", sections: [{ label: "Reasons", content: "The largest variance is concentrated at Pier P3, where workforce, steel delivery, and weather have reduced production." }, { label: "Supporting evidence", content: "Pier P3 is 8% behind plan and the mock recovery model predicts a 2-day delay." }, { label: "Recommended action", content: "Use the recommended +6 worker plan first; add one shift if material or weather constraints remain." }] };
  };

  const ask = async (text: string) => {
    const prompt = text.trim();
    if (!prompt) return;
    setQuestion("");
    setError("");
    setMessages(current => [...current, { from: "user", text: prompt }]);
    setLoading(true);
    const projectId = typeof window !== "undefined"
      ? window.sessionStorage.getItem("constructiq-project") ?? window.localStorage.getItem("constructiq-project")
      : null;
    if (!projectId) {
      const fallback = getMockAnswer(prompt);
      setMessages(current => [...current, {
        from: "assistant",
        text: fallback.text,
        sections: fallback.sections,
        context: fallback.context,
      }]);
      setError("Live project data is unavailable, so I showed the built-in assistant guidance.");
      setLoading(false);
      return;
    }
    try {
      const answer = await aiService.ask(projectId, prompt);
      const sourceText = answer.sources?.map(source => source.title ?? source.summary ?? String(source.id)).join(" · ");
      setMessages(current => [...current, {
        from: "assistant",
        text: answer.answer,
        sections: [
          ...(answer.intent ? [{ label: "Intent", content: answer.intent }] : []),
          ...(answer.confidence !== undefined ? [{ label: "Confidence", content: `${answer.confidence}%` }] : []),
          ...(sourceText ? [{ label: "Sources", content: sourceText }] : []),
        ],
      }]);
    } catch (error) {
      const fallback = getMockAnswer(prompt);
      setMessages(current => [...current, {
        from: "assistant",
        text: fallback.text,
        sections: fallback.sections,
        context: fallback.context,
      }]);
      setError(error instanceof ApiError
        ? `${error.message} Showing built-in assistant guidance instead.`
        : "The project assistant is unavailable. Showing built-in assistant guidance instead.");
    } finally {
      setLoading(false);
    }
  };

  if (!open) return <button type="button" aria-label="Open project assistant" onClick={() => onClose()} className="fixed bottom-24 right-4 z-40 grid h-12 w-12 place-items-center rounded-full bg-primary text-primary-foreground shadow-lg shadow-primary/20"><Bot className="h-5 w-5" /></button>;
  return <div className="fixed inset-x-4 bottom-24 z-50 mx-auto flex max-h-[min(620px,calc(100vh-7rem))] max-w-lg flex-col overflow-hidden rounded-lg border border-border bg-card shadow-xl"><div className="flex items-center gap-3 border-b border-border bg-primary px-4 py-3 text-primary-foreground"><div className="grid h-9 w-9 place-items-center rounded-md bg-primary-foreground/15"><Bot className="h-5 w-5" /></div><div className="min-w-0 flex-1"><p className="text-sm font-extrabold">Project assistant</p><p className="truncate text-[10px] opacity-80">{role} · Project workspace</p></div><button type="button" aria-label="Close project assistant" onClick={onClose} className="rounded-md p-1 hover:bg-primary-foreground/10"><X className="h-5 w-5" /></button></div><div className="flex-1 space-y-3 overflow-y-auto p-4">    {messages.map((message, index) => <div key={`${message.from}-${index}`} className={cn("max-w-[92%] rounded-lg px-3 py-2 text-xs leading-5", message.from === "user" ? "ml-auto bg-primary text-primary-foreground" : "bg-secondary text-foreground")}>{message.from === "assistant" && <p className="mb-1 text-[10px] font-extrabold uppercase text-primary">Answer</p>}<p>{message.text}</p>{message.sections && <div className="mt-3 space-y-2 border-t border-border/60 pt-2">{message.sections.map(section => <div key={section.label}><p className="text-[10px] font-extrabold uppercase text-primary">{section.label}</p><p className="mt-0.5 text-[11px] leading-5 text-muted-foreground">{section.content}</p></div>)}</div>}{message.context && <div className="mt-3 grid gap-2 border-t border-border/60 pt-2 sm:grid-cols-3">{[["Related Activity", message.context.activity], ["Related Evidence", message.context.evidence], ["Related Timeline Event", message.context.event]].map(([label, content]) => <div key={label} className="rounded-md border border-border bg-background p-2"><p className="text-[9px] font-extrabold uppercase text-primary">{label}</p><p className="mt-1 text-[10px] leading-4 text-muted-foreground">{content}</p></div>)}</div>}</div>)}{loading && <div className="flex items-center gap-2 rounded-lg bg-secondary px-3 py-2 text-xs text-muted-foreground"><Sparkles className="h-4 w-4 animate-pulse text-primary" />Analyzing project records...</div>}{error && <div role="alert" className="rounded-lg border border-danger/30 bg-danger/8 px-3 py-2 text-xs text-danger">{error}</div>}<div><p className="mb-2 text-[10px] font-bold uppercase text-muted-foreground">Suggested questions</p><div className="flex flex-wrap gap-2">{quickQuestions.map(prompt => <button type="button" key={prompt} onClick={() => ask(prompt)} disabled={loading} className="rounded-md border border-border bg-background px-2.5 py-1.5 text-left text-[10px] text-muted-foreground hover:border-primary hover:text-primary disabled:opacity-50">{prompt}</button>)}</div></div></div><form className="flex gap-2 border-t border-border p-3" onSubmit={event => { event.preventDefault(); ask(question); }}><input value={question} onChange={event => setQuestion(event.target.value)} placeholder="Ask about the project..." className="min-w-0 flex-1 rounded-md border border-border bg-background px-3 text-sm outline-none focus:border-primary" /><Button type="submit" size="icon" aria-label="Send message"><Send /></Button></form></div>;
}

function HomeDashboard({ role, onScreen }: { role: Role; onScreen: (s: Screen) => void }) {
  const data = useDashboardSnapshot(role);
  if (role === "Worker") return <WorkerDashboard onScreen={onScreen} data={data} />;
  if (role === "Field Engineer") return <FieldDashboard onScreen={onScreen} data={data} />;
  if (role === "Project Manager") return <ProjectDashboard onScreen={onScreen} data={data} />;
  if (role === "Admin") return <ProjectDashboard onScreen={onScreen} data={data} />;
  if (role === "Planning Engineer") return <PlanningEngineerDashboard onScreen={onScreen} />;
  return <RoleDataDashboard role={role} onScreen={onScreen} data={data} />;
}

export function ConstructionApp() {
  const pathRole = typeof window !== "undefined"
    ? Object.entries(rolePaths).find(([, path]) => path === window.location.pathname)?.[0] as Role | undefined
    : undefined;
  const [screen, setScreen] = useState<Screen>(pathRole ? "home" : "welcome");
  const [role, setRole] = useState<Role | null>(pathRole ?? null);
  const [splash, setSplash] = useState(true);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [navigationOpen, setNavigationOpen] = useState(false);
  const [loginError, setLoginError] = useState("");
  useEffect(() => {
    const restore = async () => {
      try {
        const authenticatedUser = await authService.restoreSession();
        if (!authenticatedUser) {
          setRole(null);
          setScreen("login");
          if (pathRole) window.history.replaceState({}, "", "/");
          return;
        }
        setRole(authenticatedUser.role);
        setScreen("home");
        if (window.location.pathname !== rolePaths[authenticatedUser.role]) {
          window.history.replaceState({}, "", rolePaths[authenticatedUser.role]);
        }
      } catch {
        authService.logout();
        setRole(null);
        setScreen("welcome");
        window.history.replaceState({}, "", "/");
      }
    };
    void restore();
    const handleExpired = () => {
      authService.logout();
      setRole(null);
      setScreen("welcome");
      setLoginError("Your session has expired. Please sign in again.");
      window.history.replaceState({}, "", "/");
    };
    window.addEventListener("buildsync-auth-expired", handleExpired);
    return () => window.removeEventListener("buildsync-auth-expired", handleExpired);
  }, []);
  useEffect(() => { const id = window.setTimeout(() => setSplash(false), 900); return () => window.clearTimeout(id); }, []);
  useEffect(() => {
    document.body.style.overflow = navigationOpen ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [navigationOpen]);
  const title = useMemo(() => {
    const activeRole = role ?? "Project Manager";
    const titles: Partial<Record<Screen, string>> = { activities: "Activities", "sih-intelligence": "Progress Control", planning: "Planning & Schedule", capture: activeRole === "Worker" ? "Report issue" : "Capture evidence", evidence: "Evidence verification", analytics: "Project reports", ai: "Recommendations", timeline: "Event timeline", replay: "Construction replay", inventory: "Inventory", inspection: "Inspection", trip: "Live trip", notifications: "Notifications", profile: "Profile", settings: "Settings" };
    return titles[screen] ?? "";
  }, [screen, role]);
  if (splash) return <main className="mobile-screen grid place-items-center bg-background"><div className="text-center"><div className="mx-auto grid h-20 w-20 place-items-center rounded-3xl bg-primary text-primary-foreground shadow-lg shadow-primary/20"><BuildSyncMark className="h-10 w-10" /></div><h1 className="mt-5 text-2xl font-extrabold">Build<span className="text-primary">Sync</span></h1><p className="mt-2 text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground">Infrastructure project control</p><div className="mt-6 flex items-center justify-center gap-2 text-[10px] font-bold uppercase tracking-widest text-muted-foreground"><LoaderCircle className="h-3.5 w-3.5 animate-spin text-primary" />Loading project workspace</div><p className="mt-2 text-[9px] text-muted-foreground/70">Metro Line 6 · Package C3</p></div></main>;
  const navigate = (nextScreen: Screen) => {
    const activeRole = role ?? "Project Manager";
    if (roleScreens[activeRole].includes(nextScreen)) {
      setScreen(nextScreen);
      setNavigationOpen(false);
    }
  };
  if (screen === "welcome") return <Welcome onLogin={() => { setLoginError(""); setScreen("login"); }} onDemo={() => { setLoginError(""); setScreen("login"); }} />;
  if (["login", "forgot", "otp"].includes(screen)) return <LoginFlow screen={screen} setScreen={setScreen} loginError={loginError} onAuthenticated={async (identifier, password) => {
    try {
      const authenticatedUser = await authService.signIn({ identifier, password });
      setLoginError("");
      setRole(authenticatedUser.role);
      window.history.pushState({}, "", rolePaths[authenticatedUser.role]);
      setScreen("home");
    } catch (error) {
      setLoginError(error instanceof ApiError ? error.message : "Unable to sign in. Check the backend connection.");
      return;
    }
  }} />;
  const isHome = screen === "home";
  const activeRole = role ?? "Project Manager";
  const handleLogout = () => { authService.logout(); setRole(null); setNavigationOpen(false); setAssistantOpen(false); setLoginError(""); window.history.replaceState({}, "", "/"); setScreen("login"); };
  return <div className="workspace-shell min-h-screen">{navigationOpen && <button type="button" aria-label="Close navigation backdrop" className="fixed inset-0 z-50 bg-foreground/40 min-[900px]:hidden" onClick={() => setNavigationOpen(false)} />}<WorkspaceRail role={activeRole} screen={screen} onScreen={navigate} open={navigationOpen} onClose={() => setNavigationOpen(false)} /><div className="workspace-content min-w-0 flex-1"><AppHeader role={activeRole} onScreen={navigate} onMenu={() => setNavigationOpen(true)} /><main className="workspace-main mx-auto max-w-lg px-4 pb-28 pt-5">{!isHome && <div className="mb-5 flex items-center gap-3"><Button variant="ghost" size="icon" onClick={() => navigate("home")}><ArrowLeft /></Button><div><p className="text-[10px] uppercase text-muted-foreground">{activeRole}</p><h1 className="text-xl font-extrabold">{title}</h1></div></div>}{isHome ? <HomeDashboard role={activeRole} onScreen={navigate} /> : <StandardScreen screen={screen} role={activeRole} onScreen={navigate} onLogout={handleLogout} />}</main><BottomNav role={activeRole} screen={screen} onScreen={navigate} /></div><WorkspaceSummary /><ChatbotAssistant role={activeRole} open={assistantOpen} onClose={() => setAssistantOpen(value => !value)} /></div>;
}

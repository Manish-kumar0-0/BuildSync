export type SyncStatus = "ONLINE" | "OFFLINE" | "SYNCING" | "SYNCED" | "SYNC FAILED";
export type OfflineItemType = "Evidence" | "Field notes" | "Progress update" | "Attendance" | "Issue";

export type OfflineItem = {
  id: string;
  type: OfflineItemType;
  title: string;
  createdAt: string;
  status: "PENDING SYNC" | Exclude<SyncStatus, "ONLINE" | "OFFLINE">;
};

const storageKey = "constructiq-offline-items";

function readItems(): OfflineItem[] {
  if (typeof localStorage === "undefined") return [];
  const raw = localStorage.getItem(storageKey);
  if (!raw) return [];
  try {
    return JSON.parse(raw) as OfflineItem[];
  } catch {
    return [];
  }
}

function writeItems(items: OfflineItem[]) {
  localStorage.setItem(storageKey, JSON.stringify(items));
}

export function getOfflineItems(): OfflineItem[] {
  return readItems();
}

export function saveOfflineItem(input: Omit<OfflineItem, "id" | "createdAt" | "status">): OfflineItem {
  const item: OfflineItem = { ...input, id: `OFF-${Date.now()}`, createdAt: new Date().toISOString(), status: "PENDING SYNC" };
  const items = [...readItems(), item];
  writeItems(items);
  return item;
}

export async function syncOfflineItems(): Promise<OfflineItem[]> {
  const syncing = readItems().map(item => ({ ...item, status: "SYNCING" as const }));
  writeItems(syncing);
  await new Promise(resolve => window.setTimeout(resolve, 650));
  const synced = syncing.map(item => ({ ...item, status: "SYNCED" as const }));
  writeItems(synced);
  return synced;
}

export function retryOfflineItem(id: string): OfflineItem[] {
  const items = readItems().map(item => item.id === id ? { ...item, status: "SYNCING" as const } : item);
  writeItems(items);
  return items;
}

import React, { FormEvent, useEffect, useMemo, useState } from "react";
import { dateOnly, pretty, request, todayIso, uploadImage } from "./api";
import type {
  Asset,
  AuthStatus,
  Container,
  Guidance,
  Household,
  HouseholdProfile,
  InventoryItem,
  InventoryTaxonomy,
  Page,
  Plan,
  PlanCheck,
  PlanTemplate,
  Readiness,
  ShoppingItem,
  SystemInfo,
  Target,
  Task,
  User,
  UserRole,
} from "./types";
import { EmptyState, Field, FormActions, GroupedNav, Modal, PageHeader, StatusChip } from "./ui";

const CONTAINER_TYPES: Record<string, string> = {
  bag: "Bag",
  box_crate: "Box / crate",
  water_container: "Water container",
  cabinet_storage: "Cabinet / storage",
  vehicle_storage: "Vehicle storage",
  other: "Other",
};
const ASSET_TYPES: Record<string, string> = {
  water_shutoff: "Water shutoff",
  isolation_valve: "Isolation valve",
  floor_drain: "Floor drain",
  leak_sensor: "Leak sensor",
  backflow_valve: "Backflow valve",
  sump_pump: "Sump pump",
  smoke_alarm: "Smoke alarm",
  fire_extinguisher: "Fire extinguisher",
  electrical_panel: "Electrical panel",
  generator: "Generator",
  other: "Other",
};
const PLAN_TYPES: Record<string, string> = {
  fire: "Fire",
  flood: "Flood / water damage",
  evacuation: "Evacuation",
  power_outage: "Power outage",
  communication: "Communication",
  shelter: "Shelter",
  other: "Other",
};
const TASK_CATEGORIES = ["general", "inventory", "water", "food", "maintenance", "safety", "documents", "other"];

type DomainData = {
  inventory: InventoryItem[];
  containers: Container[];
  assets: Asset[];
  tasks: Task[];
  plans: Plan[];
  targets: Target[];
  shopping: ShoppingItem[];
};

type Editor<T> = { mode: "new"; value: null } | { mode: "edit"; value: T } | null;

type RecurrenceFields = {
  enabled: boolean;
  interval: number;
  period: string;
  reschedule: string;
  reminder: number;
};

function pageFromHash(): Page {
  const raw = window.location.hash.replace(/^#\/?/, "");
  const legacy = raw === "home" || raw === "" ? "overview" : raw;
  const valid: Page[] = ["overview", "inventory", "containers", "shopping", "assets", "tasks", "plans", "targets", "guidance", "household", "access"];
  return valid.includes(legacy as Page) ? (legacy as Page) : "overview";
}

function unitLabel(key: string, taxonomy: InventoryTaxonomy | null): string {
  const meta = taxonomy?.units[key];
  if (!meta) return pretty(key);
  return meta.symbol ? `${meta.label} (${meta.symbol})` : meta.label;
}

function targetUiStatus(status: string): { label: string; tone: string } {
  if (status === "met") return { label: "Ready", tone: "ready" };
  if (status === "below_target") return { label: "Partially ready", tone: "attention" };
  if (status === "below_minimum") return { label: "Not ready", tone: "critical" };
  return { label: "Needs assessment", tone: "attention" };
}

function taskUiStatus(task: Task): string {
  if (!task.enabled) return "disabled";
  if (!task.next_due_at) return "unscheduled";
  const due = new Date(`${task.next_due_at}T00:00:00`);
  const today = new Date(`${todayIso()}T00:00:00`);
  const delta = Math.floor((due.getTime() - today.getTime()) / 86400000);
  if (delta < 0) return "overdue";
  if (delta === 0) return "due";
  if (task.reminder_before_days > 0 && delta <= task.reminder_before_days) return "upcoming";
  return "ok";
}

function recurringTaskFor(tasks: Task[], kind: string, id: string): Task | undefined {
  if (kind === "inventory") return tasks.find((task) => task.task_kind === "inspection" && task.linked_item_id === id);
  if (kind === "container") return tasks.find((task) => task.task_kind === "container_inspection" && task.linked_container_id === id);
  return tasks.find((task) => task.task_kind === "asset_inspection" && task.linked_asset_id === id);
}

function recurrenceFromTask(task?: Task): RecurrenceFields {
  return {
    enabled: Boolean(task),
    interval: task?.recurrence_interval ?? 6,
    period: task?.recurrence_type ?? "months",
    reschedule: task?.reschedule_mode ?? "scheduled",
    reminder: task?.reminder_before_days ?? 7,
  };
}

function AuthCard({ setupRequired, done }: { setupRequired: boolean; done: () => Promise<void> }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const password = String(form.get("password") ?? "");
    if (setupRequired && password !== String(form.get("confirm") ?? "")) {
      setError("Passwords do not match.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await request(setupRequired ? "/api/v1/auth/setup" : "/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ username: String(form.get("username") ?? "").trim(), password }),
      });
      await done();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  }
  return <div className="login-page"><section className="auth-card hp-panel"><img src="/homeprep-logo.png" className="login-logo" alt="HomePrep" />{error && <div className="error">{error}</div>}<form className="edit-form" onSubmit={submit}><Field label="Username"><input name="username" required minLength={3} autoFocus /></Field><Field label="Password"><input name="password" type="password" required minLength={setupRequired ? 12 : 1} /></Field>{setupRequired && <Field label="Confirm password"><input name="confirm" type="password" required minLength={12} /></Field>}<button disabled={busy}>{busy ? "Please wait…" : setupRequired ? "Create owner" : "Sign in"}</button></form></section></div>;
}

function RecurrenceEditor({ prefix, initial }: { prefix: string; initial: RecurrenceFields }) {
  const [enabled, setEnabled] = useState(initial.enabled);
  return <fieldset className="recurrence-box"><label className="check-row"><input type="checkbox" name={`${prefix}_enabled`} defaultChecked={initial.enabled} onChange={(event) => setEnabled(event.currentTarget.checked)} />Recurring check</label>{enabled && <div className="form-grid two"><Field label="Repeat every"><input type="number" name={`${prefix}_interval`} min={1} defaultValue={initial.interval} /></Field><Field label="Period"><select name={`${prefix}_period`} defaultValue={initial.period}><option value="days">Days</option><option value="weeks">Weeks</option><option value="months">Months</option><option value="years">Years</option></select></Field><Field label="After completion"><select name={`${prefix}_reschedule`} defaultValue={initial.reschedule}><option value="scheduled">Keep planned cadence</option><option value="completion">Schedule from completion</option></select></Field><Field label="Reminder before due"><input type="number" name={`${prefix}_reminder`} min={0} defaultValue={initial.reminder} /></Field></div>}</fieldset>;
}

function App() {
  const [page, setPage] = useState<Page>(pageFromHash());
  const [system, setSystem] = useState<SystemInfo | null>(null);
  const [serverReady, setServerReady] = useState(false);
  const [auth, setAuth] = useState<AuthStatus | null>(null);
  const [households, setHouseholds] = useState<Household[]>([]);
  const [householdId, setHouseholdId] = useState("");
  const [profile, setProfile] = useState<HouseholdProfile | null>(null);
  const [taxonomy, setTaxonomy] = useState<InventoryTaxonomy | null>(null);
  const [guidance, setGuidance] = useState<Guidance | null>(null);
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [templates, setTemplates] = useState<PlanTemplate[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [data, setData] = useState<DomainData>({ inventory: [], containers: [], assets: [], tasks: [], plans: [], targets: [], shopping: [] });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const [inventoryEditor, setInventoryEditor] = useState<Editor<InventoryItem>>(null);
  const [containerEditor, setContainerEditor] = useState<Editor<Container>>(null);
  const [assetEditor, setAssetEditor] = useState<Editor<Asset>>(null);
  const [taskEditor, setTaskEditor] = useState<Editor<Task>>(null);
  const [planEditor, setPlanEditor] = useState<Editor<Plan>>(null);
  const [targetEditor, setTargetEditor] = useState<Editor<Target>>(null);
  const [shoppingEditor, setShoppingEditor] = useState<Editor<ShoppingItem>>(null);

  const role: UserRole = auth?.user?.role ?? "viewer";
  const canWrite = role === "owner" || role === "editor";
  const isOwner = role === "owner";
  const activeHousehold = households.find((item) => item.id === householdId) ?? null;

  useEffect(() => {
    const handler = () => setPage(pageFromHash());
    window.addEventListener("hashchange", handler);
    return () => window.removeEventListener("hashchange", handler);
  }, []);

  function navigate(next: Page) {
    window.location.hash = next === "overview" ? "/" : `/${next}`;
    setPage(next);
    setError("");
  }

  function fail(err: unknown, fallback: string) {
    setError(err instanceof Error ? err.message : fallback);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function loadDomain(id: string, currentRole: UserRole) {
    const [inventory, containers, assets, tasks, plans, targets, shopping, tax, planTemplates] = await Promise.all([
      request<InventoryItem[]>(`/api/v1/inventory?household_id=${id}`),
      request<Container[]>(`/api/v1/containers?household_id=${id}`),
      request<Asset[]>(`/api/v1/assets?household_id=${id}`),
      request<Task[]>(`/api/v1/tasks?household_id=${id}`),
      request<Plan[]>(`/api/v1/plans?household_id=${id}`),
      request<Target[]>(`/api/v1/targets?household_id=${id}`),
      request<ShoppingItem[]>(`/api/v1/shopping?household_id=${id}`),
      request<InventoryTaxonomy>("/api/v1/taxonomy/inventory"),
      request<PlanTemplate[]>("/api/v1/plans/templates"),
    ]);
    setData({ inventory, containers, assets, tasks, plans, targets, shopping });
    setTaxonomy(tax);
    setTemplates(planTemplates);
    const [profileResult, readinessResult] = await Promise.all([
      request<HouseholdProfile>(`/api/v1/household-profile/${id}`).catch(() => null),
      request<Readiness>(`/api/v1/readiness/${id}`).catch(() => null),
    ]);
    setProfile(profileResult);
    setReadiness(readinessResult);
    setGuidance(profileResult ? await request<Guidance>(`/api/v1/guidance/${id}`).catch(() => null) : null);
    setUsers(currentRole === "owner" ? await request<User[]>("/api/v1/users") : []);
  }

  async function bootstrap() {
    setLoading(true);
    setError("");
    try {
      const [info, readyState, authState] = await Promise.all([
        request<SystemInfo>("/api/v1/system/info"),
        request<{ status: string }>("/readyz"),
        request<AuthStatus>("/api/v1/auth/status"),
      ]);
      setSystem(info);
      setServerReady(readyState.status === "ready");
      setAuth(authState);
      if (authState.authenticated && authState.user) {
        const list = await request<Household[]>("/api/v1/households");
        setHouseholds(list);
        const id = list[0]?.id ?? "";
        setHouseholdId(id);
        if (id) await loadDomain(id, authState.user.role);
      }
    } catch (err) {
      fail(err, "Unable to connect to HomePrep Server");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void bootstrap(); }, []);
  useEffect(() => { if (page === "access" && !isOwner && auth?.authenticated) navigate("overview"); }, [page, isOwner, auth?.authenticated]);

  async function refresh() {
    if (householdId && auth?.user) await loadDomain(householdId, auth.user.role);
  }

  async function remove(path: string, id: string, revision: number) {
    if (!window.confirm("Delete this HomePrep item?")) return;
    try {
      await request(`/api/v1/${path}/${id}?expected_revision=${revision}`, { method: "DELETE" });
      await refresh();
    } catch (err) { fail(err, "Unable to delete item"); }
  }

  async function saveLinkedRecurring(kind: "inventory" | "container" | "asset", resourceId: string, resourceName: string, form: FormData, existing?: Task) {
    const enabled = form.get("recurring_enabled") === "on";
    if (!enabled && existing) {
      await request(`/api/v1/tasks/${existing.id}?expected_revision=${existing.revision}`, { method: "DELETE" });
      return;
    }
    if (!enabled) return;
    const taskKind = kind === "inventory" ? "inspection" : `${kind}_inspection`;
    const linkField = kind === "inventory" ? "linked_item_id" : kind === "container" ? "linked_container_id" : "linked_asset_id";
    const payload = {
      name: `Check ${resourceName}`,
      task_kind: taskKind,
      category: kind,
      [linkField]: resourceId,
      recurrence_type: String(form.get("recurring_period") ?? "months"),
      recurrence_interval: Number(form.get("recurring_interval") ?? 6),
      reschedule_mode: String(form.get("recurring_reschedule") ?? "scheduled"),
      reminder_before_days: Number(form.get("recurring_reminder") ?? 7),
      enabled: true,
    };
    if (existing) {
      await request(`/api/v1/tasks/${existing.id}`, { method: "PATCH", body: JSON.stringify({ ...payload, expected_revision: existing.revision }) });
    } else {
      await request("/api/v1/tasks", { method: "POST", body: JSON.stringify({ household_id: householdId, ...payload, next_due_at: String(form.get("next_check_at") ?? "") || null }) });
    }
  }

  async function markChecked(kind: "inventory" | "container" | "asset", id: string, revision: number) {
    const linked = recurringTaskFor(data.tasks, kind, id);
    try {
      if (linked) {
        await request(`/api/v1/tasks/${linked.id}/complete`, { method: "POST", body: JSON.stringify({ expected_revision: linked.revision }) });
      } else {
        const field = kind === "inventory" ? "last_checked" : "last_checked_at";
        await request(`/api/v1/${kind === "inventory" ? "inventory" : `${kind}s`}/${id}`, { method: "PATCH", body: JSON.stringify({ [field]: todayIso(), expected_revision: revision }) });
      }
      await refresh();
    } catch (err) { fail(err, "Unable to mark checked"); }
  }

  async function saveInventory(event: FormEvent<HTMLFormElement>, editor: NonNullable<Editor<InventoryItem>>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      let imageFields: Record<string, string | null> = {};
      const imageFile = form.get("image") as File | null;
      if (imageFile?.size) {
        const uploaded = await uploadImage(imageFile);
        imageFields = { image_id: uploaded.image_id, image_token: uploaded.image_token, image_content_type: uploaded.image_content_type, image_filename: uploaded.image_filename };
      }
      if (form.get("remove_image") === "on") imageFields = { image_id: null, image_token: null, image_content_type: null, image_filename: null };
      const body = {
        name: String(form.get("name") ?? "").trim(), category: String(form.get("category") ?? "other"), item_type: String(form.get("item_type") ?? "consumable"), quantity: Number(form.get("quantity") ?? 1), unit: String(form.get("unit") ?? "piece"), container_id: String(form.get("container_id") ?? "") || null, expires_at: String(form.get("expires_at") ?? "") || null, last_checked: String(form.get("last_checked") ?? "") || null, next_check_at: String(form.get("next_check_at") ?? "") || null, notes: String(form.get("notes") ?? "").trim() || null, ...imageFields,
      };
      const item = editor.mode === "new"
        ? await request<InventoryItem>("/api/v1/inventory", { method: "POST", body: JSON.stringify({ household_id: householdId, ...body }) })
        : await request<InventoryItem>(`/api/v1/inventory/${editor.value.id}`, { method: "PATCH", body: JSON.stringify({ ...body, expected_revision: editor.value.revision }) });
      await saveLinkedRecurring("inventory", item.id, item.name, form, editor.mode === "edit" ? recurringTaskFor(data.tasks, "inventory", editor.value.id) : undefined);
      setInventoryEditor(null);
      await refresh();
    } catch (err) { fail(err, "Unable to save inventory item"); }
  }

  async function saveContainer(event: FormEvent<HTMLFormElement>, editor: NonNullable<Editor<Container>>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const body = { name: String(form.get("name") ?? "").trim(), container_type: String(form.get("container_type") ?? "other"), location: String(form.get("location") ?? "").trim() || null, last_checked_at: String(form.get("last_checked_at") ?? "") || null, next_check_at: String(form.get("next_check_at") ?? "") || null, description: String(form.get("description") ?? "").trim() || null, notes: String(form.get("notes") ?? "").trim() || null };
      const container = editor.mode === "new"
        ? await request<Container>("/api/v1/containers", { method: "POST", body: JSON.stringify({ household_id: householdId, ...body }) })
        : await request<Container>(`/api/v1/containers/${editor.value.id}`, { method: "PATCH", body: JSON.stringify({ ...body, expected_revision: editor.value.revision }) });
      await saveLinkedRecurring("container", container.id, container.name, form, editor.mode === "edit" ? recurringTaskFor(data.tasks, "container", editor.value.id) : undefined);
      setContainerEditor(null);
      await refresh();
    } catch (err) { fail(err, "Unable to save container"); }
  }

  async function saveAsset(event: FormEvent<HTMLFormElement>, editor: NonNullable<Editor<Asset>>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      let imageFields: Record<string, string | null> = {};
      const imageFile = form.get("image") as File | null;
      if (imageFile?.size) {
        const uploaded = await uploadImage(imageFile);
        imageFields = { image_id: uploaded.image_id, image_token: uploaded.image_token, image_content_type: uploaded.image_content_type, image_filename: uploaded.image_filename };
      }
      if (form.get("remove_image") === "on") imageFields = { image_id: null, image_token: null, image_content_type: null, image_filename: null };
      const body = { name: String(form.get("name") ?? "").trim(), asset_type: String(form.get("asset_type") ?? "other"), location: String(form.get("location") ?? "").trim() || null, last_checked_at: String(form.get("last_checked_at") ?? "") || null, next_check_at: String(form.get("next_check_at") ?? "") || null, description: String(form.get("description") ?? "").trim() || null, instructions: String(form.get("instructions") ?? "").trim() || null, notes: String(form.get("notes") ?? "").trim() || null, ...imageFields };
      const asset = editor.mode === "new"
        ? await request<Asset>("/api/v1/assets", { method: "POST", body: JSON.stringify({ household_id: householdId, ...body }) })
        : await request<Asset>(`/api/v1/assets/${editor.value.id}`, { method: "PATCH", body: JSON.stringify({ ...body, expected_revision: editor.value.revision }) });
      await saveLinkedRecurring("asset", asset.id, asset.name, form, editor.mode === "edit" ? recurringTaskFor(data.tasks, "asset", editor.value.id) : undefined);
      setAssetEditor(null);
      await refresh();
    } catch (err) { fail(err, "Unable to save asset"); }
  }

  async function saveTask(event: FormEvent<HTMLFormElement>, editor: NonNullable<Editor<Task>>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const body = { name: String(form.get("name") ?? "").trim(), task_kind: editor.mode === "edit" ? editor.value.task_kind : "general", category: String(form.get("category") ?? "general"), recurrence_type: String(form.get("recurrence_type") ?? "months"), recurrence_interval: Number(form.get("recurrence_interval") ?? 1), reschedule_mode: String(form.get("reschedule_mode") ?? "completion"), next_due_at: String(form.get("next_due_at") ?? "") || null, reminder_before_days: Number(form.get("reminder_before_days") ?? 0), enabled: form.get("enabled") === "on", notes: String(form.get("notes") ?? "").trim() || null };
      if (editor.mode === "new") await request("/api/v1/tasks", { method: "POST", body: JSON.stringify({ household_id: householdId, ...body }) });
      else await request(`/api/v1/tasks/${editor.value.id}`, { method: "PATCH", body: JSON.stringify({ ...body, expected_revision: editor.value.revision }) });
      setTaskEditor(null);
      await refresh();
    } catch (err) { fail(err, "Unable to save task"); }
  }

  async function savePlan(event: FormEvent<HTMLFormElement>, editor: NonNullable<Editor<Plan>>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const existingChecks = editor.mode === "edit" ? editor.value.checklist : [];
    const labels = String(form.get("checklist") ?? "").split("\n").map((value) => value.trim()).filter(Boolean);
    const checklist: PlanCheck[] = labels.map((label, index) => ({ ...(existingChecks[index] ?? { id: crypto.randomUUID(), completed: false }), label }));
    try {
      const body = { name: String(form.get("name") ?? "").trim(), plan_type: String(form.get("plan_type") ?? "other"), meeting_point: String(form.get("meeting_point") ?? "").trim() || null, review_interval_months: Number(form.get("review_interval_months") ?? 0), description: String(form.get("description") ?? "").trim() || null, enabled: form.get("enabled") === "on", notes: String(form.get("notes") ?? "").trim() || null, checklist };
      if (editor.mode === "new") await request("/api/v1/plans", { method: "POST", body: JSON.stringify({ household_id: householdId, ...body }) });
      else await request(`/api/v1/plans/${editor.value.id}`, { method: "PATCH", body: JSON.stringify({ ...body, expected_revision: editor.value.revision }) });
      setPlanEditor(null);
      await refresh();
    } catch (err) { fail(err, "Unable to save plan"); }
  }

  async function saveTarget(event: FormEvent<HTMLFormElement>, editor: NonNullable<Editor<Target>>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const targetType = editor.mode === "edit" ? editor.value.target_type : String(form.get("target_type") ?? "quantity");
    const category = String(form.get("category") ?? (editor.mode === "edit" ? editor.value.category ?? "other" : "other"));
    try {
      const body = { name: String(form.get("name") ?? "").trim(), category, target_type: targetType, matcher: editor.mode === "edit" ? editor.value.matcher ?? {} : (["quantity", "count"].includes(targetType) ? { category } : {}), unit: String(form.get("unit") ?? "") || null, current_value: String(form.get("current_value") ?? "") === "" ? null : Number(form.get("current_value")), minimum_value: String(form.get("minimum_value") ?? "") === "" ? null : Number(form.get("minimum_value")), target_value: String(form.get("target_value") ?? "") === "" ? null : Number(form.get("target_value")), priority: String(form.get("priority") ?? "normal"), enabled: form.get("enabled") === "on", notes: String(form.get("notes") ?? "").trim() || null };
      if (editor.mode === "new") await request("/api/v1/targets", { method: "POST", body: JSON.stringify({ household_id: householdId, ...body }) });
      else await request(`/api/v1/targets/${editor.value.id}`, { method: "PATCH", body: JSON.stringify({ ...body, expected_revision: editor.value.revision }) });
      setTargetEditor(null);
      await refresh();
    } catch (err) { fail(err, "Unable to save target"); }
  }

  async function saveShopping(event: FormEvent<HTMLFormElement>, editor: NonNullable<Editor<ShoppingItem>>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const body = { name: String(form.get("name") ?? "").trim(), quantity: Number(form.get("quantity") ?? 1), unit: String(form.get("unit") ?? "piece"), category: String(form.get("category") ?? "other"), container_id: String(form.get("container_id") ?? "") || null, notes: String(form.get("notes") ?? "").trim() || null };
      if (editor.mode === "new") await request("/api/v1/shopping", { method: "POST", body: JSON.stringify({ household_id: householdId, source_type: "manual", status: "pending", ...body }) });
      else await request(`/api/v1/shopping/${editor.value.id}`, { method: "PATCH", body: JSON.stringify({ ...body, expected_revision: editor.value.revision }) });
      setShoppingEditor(null);
      await refresh();
    } catch (err) { fail(err, "Unable to save shopping item"); }
  }

  async function shoppingStatus(item: ShoppingItem, status: "pending" | "purchased" | "ignored") {
    try {
      await request(`/api/v1/shopping/${item.id}`, { method: "PATCH", body: JSON.stringify({ status, expected_revision: item.revision }) });
      await refresh();
    } catch (err) { fail(err, "Unable to update shopping item"); }
  }

  async function toggleRequirement(target: Target, requirementId: string) {
    const completed = new Set(target.completed_requirement_ids);
    completed.has(requirementId) ? completed.delete(requirementId) : completed.add(requirementId);
    try {
      await request(`/api/v1/targets/${target.id}`, { method: "PATCH", body: JSON.stringify({ completed_requirement_ids: [...completed], expected_revision: target.revision }) });
      await refresh();
    } catch (err) { fail(err, "Unable to update target"); }
  }

  async function adoptRecommendation(id: string) {
    try {
      await request("/api/v1/guidance/adopt", { method: "POST", body: JSON.stringify({ household_id: householdId, recommendation_id: id }) });
      await refresh();
    } catch (err) { fail(err, "Unable to add personal target"); }
  }

  async function createFromTemplate(id: string) {
    try {
      await request("/api/v1/plans/from-template", { method: "POST", body: JSON.stringify({ household_id: householdId, template_id: id }) });
      await refresh();
    } catch (err) { fail(err, "Unable to create plan template"); }
  }

  async function markReviewed(plan: Plan) {
    try {
      await request(`/api/v1/plans/${plan.id}/review`, { method: "POST", body: JSON.stringify({ expected_revision: plan.revision }) });
      await refresh();
    } catch (err) { fail(err, "Unable to mark plan reviewed"); }
  }

  async function togglePlanCheck(plan: Plan, item: PlanCheck) {
    try {
      await request(`/api/v1/plans/${plan.id}/checklist/${item.id}/toggle`, { method: "POST", body: JSON.stringify({ expected_revision: plan.revision, completed: !item.completed }) });
      await refresh();
    } catch (err) { fail(err, "Unable to update checklist"); }
  }

  async function saveHousehold(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await request(`/api/v1/household-profile/${householdId}`, { method: "PUT", body: JSON.stringify({ country_code: String(form.get("country_code") ?? "OTHER"), preparedness_days: Number(form.get("preparedness_days") ?? 7), adults: Number(form.get("adults") ?? 0), children: Number(form.get("children") ?? 0), pets: Number(form.get("pets") ?? 0), expected_revision: profile?.revision ?? null }) });
      await refresh();
    } catch (err) { fail(err, "Unable to save household"); }
  }

  async function createUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    try {
      await request("/api/v1/users", { method: "POST", body: JSON.stringify({ username: String(form.get("username") ?? ""), password: String(form.get("password") ?? ""), role: String(form.get("role") ?? "viewer") }) });
      formElement.reset();
      await refresh();
    } catch (err) { fail(err, "Unable to create user"); }
  }

  async function updateUser(user: User, body: object) {
    try {
      await request(`/api/v1/users/${user.id}`, { method: "PATCH", body: JSON.stringify(body) });
      await bootstrap();
    } catch (err) { fail(err, "Unable to update user"); }
  }

  async function logout() {
    await request<void>("/api/v1/auth/logout", { method: "POST" });
    navigate("overview");
    await bootstrap();
  }

  const overview = useMemo(() => {
    const today = todayIso();
    const inventoryAttention = data.inventory.filter((item) => (item.expires_at && item.expires_at < today) || (item.next_check_at && item.next_check_at <= today)).length;
    const inventoryScore = data.inventory.length ? Math.round(100 * (data.inventory.length - inventoryAttention) / data.inventory.length) : 0;
    const containerStates = data.containers.map((container) => {
      const linked = data.inventory.filter((item) => item.container_id === container.id);
      const bad = Boolean(container.next_check_at && dateOnly(container.next_check_at) <= today) || linked.some((item) => (item.expires_at && item.expires_at < today) || (item.next_check_at && item.next_check_at <= today));
      return bad ? "attention" : "ready";
    });
    const containerAttention = containerStates.filter((state) => state !== "ready").length;
    const containerScore = data.containers.length ? Math.round(100 * (data.containers.length - containerAttention) / data.containers.length) : 0;
    const activeTasks = data.tasks.filter((task) => task.enabled);
    const taskReady = activeTasks.filter((task) => taskUiStatus(task) === "ok").length;
    const taskScore = activeTasks.length ? Math.round(100 * taskReady / activeTasks.length) : 0;
    const assetDue = data.assets.filter((asset) => asset.next_check_at && dateOnly(asset.next_check_at) <= today).length;
    const assetScore = data.assets.length ? Math.round(100 * (data.assets.length - assetDue) / data.assets.length) : 0;
    const planAttention = data.plans.filter((plan) => {
      const complete = plan.checklist.length > 0 && plan.checklist.every((item) => item.completed);
      const reviewDue = Boolean(plan.next_review_at && plan.next_review_at <= today);
      return plan.enabled && (!complete || reviewDue);
    }).length;
    const activePlans = data.plans.filter((plan) => plan.enabled);
    const planScore = activePlans.length ? Math.round(100 * (activePlans.length - planAttention) / activePlans.length) : 0;
    const targetScore = readiness?.targets.total ? Math.round(100 * readiness.targets.met / readiness.targets.total) : 0;
    const areas = [
      { key: "inventory", label: "Inventory", score: inventoryScore, detail: `${inventoryAttention} need attention`, tracked: `${data.inventory.length} tracked` },
      { key: "containers", label: "Containers", score: containerScore, detail: `${containerAttention} need attention`, tracked: `${data.containers.length} tracked` },
      { key: "tasks", label: "Tasks", score: taskScore, detail: `${activeTasks.filter((task) => ["overdue", "due", "upcoming"].includes(taskUiStatus(task))).length} due / upcoming`, tracked: `${activeTasks.length} tracked` },
      { key: "assets", label: "Assets", score: assetScore, detail: `${assetDue} checks due`, tracked: `${data.assets.length} tracked` },
      { key: "plans", label: "Plans", score: planScore, detail: `${planAttention} need attention`, tracked: `${activePlans.length} tracked` },
      { key: "targets", label: "Targets", score: targetScore, detail: `${(readiness?.targets.total ?? 0) - (readiness?.targets.met ?? 0)} not fully ready`, tracked: `${readiness?.targets.total ?? 0} tracked` },
    ];
    const overall = Math.round(areas.reduce((sum, area) => sum + area.score, 0) / areas.length);
    return { areas, overall, inventoryAttention, containerAttention, assetDue, planAttention, pendingShopping: data.shopping.filter((item) => item.status === "pending").length };
  }, [data, readiness]);

  if (loading && auth === null) return <div className="boot">Starting HomePrep…</div>;
  if (auth && !auth.authenticated) return <main className="shell"><header className="topbar"><div className="brand"><img src="/homeprep-icon.png" alt="" /><div><strong>HomePrep</strong><small>PREPARE • MONITOR • BE READY</small></div></div><div className={`server-pill ${serverReady ? "online" : "offline"}`}>{serverReady ? "Server online" : "Server unavailable"}</div></header>{error && <div className="error">{error}</div>}<AuthCard setupRequired={auth.setup_required} done={bootstrap} /></main>;

  const groups = [
    { label: "Preparedness", icon: "♢", pages: [{ page: "inventory" as Page, label: "Inventory" }, { page: "containers" as Page, label: "Containers" }, { page: "shopping" as Page, label: "Shopping list" }, { page: "targets" as Page, label: "Personal targets" }] },
    { label: "Maintenance", icon: "⚒", pages: [{ page: "assets" as Page, label: "Assets" }, { page: "tasks" as Page, label: "Tasks" }] },
    { label: "Plans & Guidance", icon: "▣", pages: [{ page: "plans" as Page, label: "Plans" }, { page: "guidance" as Page, label: "Guidance" }] },
    { label: "Household", icon: "⌂", pages: [{ page: "household" as Page, label: "Household" }, ...(isOwner ? [{ page: "access" as Page, label: "Access Control" }] : [])] },
  ];

  const categories = Object.entries(taxonomy?.categories ?? { other: "Other" });
  const itemTypes = Object.entries(taxonomy?.item_types ?? { consumable: "Consumable", equipment: "Equipment" });
  const allUnits = Object.keys(taxonomy?.units ?? { piece: {} });

  function preferredUnits(category: string): string[] {
    const preferred = taxonomy?.category_meta[category]?.preferred_units ?? [];
    const fallback = taxonomy?.category_meta[category]?.default_unit;
    return [...new Set([...(fallback ? [fallback] : []), ...preferred, ...allUnits])];
  }

  function imageUrl(imageId?: string | null) { return imageId ? `/api/v1/media/images/${imageId}` : null; }

  return <main className="shell">
    <header className="topbar"><div className="brand"><img src="/homeprep-icon.png" alt="HomePrep" /><div><strong>HomePrep</strong><small>PREPARE • MONITOR • BE READY</small></div></div><div className={`server-pill ${serverReady ? "online" : "offline"}`}><span />{serverReady ? "Server online" : "Server unavailable"}</div><button className="secondary compact" onClick={() => void logout()}>Sign out</button></header>
    <GroupedNav page={page} groups={groups} navigate={navigate} />
    {error && <div className="error">{error}</div>}

    {page === "overview" && <section className="content-width overview-page">
      <div className={`overview-banner hp-${overview.overall >= 75 ? "ready" : overview.overall >= 50 ? "attention" : "critical"}`}><div className="banner-icon">⌂</div><div><h2>{overview.overall >= 75 ? "Home is ready" : overview.overall >= 50 ? "Requires attention" : "Action required"}</h2><p>Readiness across supplies, storage, maintenance and household plans.</p></div><div className="overall-score"><strong>{overview.overall}%</strong><span>OVERALL READINESS</span></div></div>
      <section className="hp-panel readiness-panel"><h3>⌁ Readiness by area</h3><div className="area-grid">{overview.areas.map((area) => <article className="area-card" key={area.key}><div className="area-head"><strong>{area.label}</strong><b>{area.score}%</b></div><div className="progress"><span style={{ width: `${area.score}%` }} /></div><div className="area-meta"><span>{area.detail}</span><span>{area.tracked}</span></div></article>)}</div></section>
      <div className="overview-bottom"><section className="hp-panel"><div className="section-row"><h3>Next actions</h3><button className="compact" onClick={() => navigate("tasks")}>View tasks</button></div>{data.tasks.filter((task) => ["overdue", "due", "upcoming"].includes(taskUiStatus(task))).length ? <div className="action-list">{data.tasks.filter((task) => ["overdue", "due", "upcoming"].includes(taskUiStatus(task))).slice(0, 6).map((task) => <div className="action-row" key={task.id}><StatusChip status={taskUiStatus(task)}>{pretty(taskUiStatus(task))}</StatusChip><strong>{task.name}</strong><span>{task.next_due_at ?? "No due date"}</span></div>)}</div> : <EmptyState>No tasks need attention.</EmptyState>}</section><section className="hp-panel"><h3>Attention queue</h3><div className="attention-list"><button onClick={() => navigate("shopping")}>🛒 <strong>{overview.pendingShopping}</strong> Shopping items</button><button onClick={() => navigate("plans")}>▣ <strong>{overview.planAttention}</strong> Plans to review</button><button onClick={() => navigate("assets")}>⚒ <strong>{overview.assetDue}</strong> Asset checks due</button><button onClick={() => navigate("containers")}>▤ <strong>{overview.containerAttention}</strong> Containers need attention</button></div></section></div>
    </section>}

    {page === "inventory" && <section className="content-width"><PageHeader title="Inventory" subtitle={`${data.inventory.length} items currently tracked.`} action={canWrite && <button onClick={() => setInventoryEditor({ mode: "new", value: null })}>＋ Add item</button>} /><div className="info-strip">▣ Inventory is for supplies and movable equipment you store, consume or replace. <strong>Assets</strong> are fixed or semi-permanent points in the home.</div>{data.inventory.length === 0 ? <EmptyState>No inventory items yet.</EmptyState> : <div className="category-sections">{categories.map(([category, categoryLabel]) => { const items = data.inventory.filter((item) => item.category === category); if (!items.length) return null; return <section className="hp-panel category-card" key={category}><div className="category-title"><h3>{categoryLabel}</h3><strong>{items.length}</strong></div>{items.map((item) => <div className="resource-row" key={item.id}>{imageUrl(item.image_id) ? <img className="resource-thumb" src={imageUrl(item.image_id) ?? ""} alt="" /> : <div className="resource-icon">▣</div>}<div className="resource-main"><strong>{item.name}</strong><span>{item.quantity} {unitLabel(item.unit, taxonomy)}{item.expires_at ? ` · Expires ${item.expires_at}` : ""}{item.container_id ? ` · ${data.containers.find((container) => container.id === item.container_id)?.name ?? "Container"}` : ""}</span></div>{canWrite && <div className="row-actions"><button className="compact" onClick={() => setInventoryEditor({ mode: "edit", value: item })}>Edit</button><button className="danger compact" onClick={() => void remove("inventory", item.id, item.revision)}>Delete</button></div>}</div>)}</section>; })}</div>}</section>}

    {page === "containers" && <section className="content-width"><PageHeader title="Preparedness containers" subtitle="Group supplies by where they are stored or what they are packed for." action={canWrite && <button onClick={() => setContainerEditor({ mode: "new", value: null })}>＋ Add container</button>} /><div className="card-grid">{data.containers.map((container) => { const items = data.inventory.filter((item) => item.container_id === container.id); const due = Boolean(container.next_check_at && dateOnly(container.next_check_at) <= todayIso()) || items.some((item) => (item.expires_at && item.expires_at < todayIso()) || (item.next_check_at && item.next_check_at <= todayIso())); return <article className="hp-panel entity-card" key={container.id}><div className="entity-card-head"><div className="entity-icon">▤</div><div><h3>{container.name}</h3><p>{CONTAINER_TYPES[container.container_type] ?? pretty(container.container_type)}{container.location ? ` · ${container.location}` : ""}</p></div><StatusChip status={due ? "critical" : "ready"}>{due ? "Needs attention" : "Ready"}</StatusChip></div><div className="metadata-line"><span>{items.length} items</span><span>Last checked: <strong>{dateOnly(container.last_checked_at) || "Never"}</strong></span><span>Next check: <strong>{dateOnly(container.next_check_at) || "Not scheduled"}</strong></span></div><div className="contained-items">{items.length ? items.map((item) => <div key={item.id}><strong>{item.name}</strong><span>{item.quantity} {unitLabel(item.unit, taxonomy)}{item.expires_at ? ` · Expires ${item.expires_at}` : ""}</span></div>) : <EmptyState>No inventory items assigned.</EmptyState>}</div>{canWrite && <div className="row-actions"><button className="compact" onClick={() => void markChecked("container", container.id, container.revision)}>Mark checked</button><button className="compact" onClick={() => setContainerEditor({ mode: "edit", value: container })}>Edit</button><button className="danger compact" onClick={() => void remove("containers", container.id, container.revision)}>Delete</button></div>}</article>; })}</div></section>}

    {page === "shopping" && <section className="content-width"><PageHeader title="Shopping list" subtitle="Expired inventory is added automatically. You can also add things manually." action={canWrite && <button onClick={() => setShoppingEditor({ mode: "new", value: null })}>＋ Add shopping item</button>} />{["pending", "purchased", "ignored"].map((status) => { const items = data.shopping.filter((item) => item.status === status); if (!items.length && status !== "pending") return null; return <section className="hp-panel list-section" key={status}><div className="category-title"><h3>{status === "pending" ? "🛒 Pending" : pretty(status)}</h3><strong>{items.length}</strong></div>{items.length ? items.map((item) => <div className="resource-row" key={item.id}><div className="resource-icon">{item.source_type === "inventory_expired" ? "↻" : "＋"}</div><div className="resource-main"><strong>{item.name}</strong><span>{item.quantity} {unitLabel(item.unit, taxonomy)}{item.reason ? ` · ${item.reason}` : item.source_type !== "manual" ? ` · ${pretty(item.source_type)}` : ""}</span></div>{canWrite && <div className="row-actions">{item.status === "pending" && <><button className="compact" onClick={() => void shoppingStatus(item, "purchased")}>Mark purchased</button><button className="secondary compact" onClick={() => void shoppingStatus(item, "ignored")}>Ignore</button></>}<button className="compact" onClick={() => setShoppingEditor({ mode: "edit", value: item })}>Edit</button><button className="danger compact" onClick={() => void remove("shopping", item.id, item.revision)}>Delete</button></div>}</div>) : <EmptyState>No pending shopping items.</EmptyState>}</section>; })}</section>}

    {page === "assets" && <section className="content-width"><PageHeader title="Household assets" subtitle="Assets are fixed or semi-permanent preparedness points in the home. Inventory is for supplies and movable equipment." action={canWrite && <button onClick={() => setAssetEditor({ mode: "new", value: null })}>＋ Add asset</button>} /><div className="card-grid">{data.assets.map((asset) => { const due = Boolean(asset.next_check_at && dateOnly(asset.next_check_at) <= todayIso()); return <article className="hp-panel entity-card" key={asset.id}><div className="entity-card-head">{imageUrl(asset.image_id) ? <img className="asset-image" src={imageUrl(asset.image_id) ?? ""} alt="" /> : <div className="entity-icon">⚒</div>}<div><h3>{asset.name}</h3><p>{ASSET_TYPES[asset.asset_type] ?? pretty(asset.asset_type)}{asset.location ? ` · ${asset.location}` : ""}</p></div><StatusChip status={due ? "critical" : "ready"}>{due ? "Needs attention" : "Ready"}</StatusChip></div>{asset.description && <p className="body-copy">{asset.description}</p>}{asset.instructions && <div className="info-strip">ⓘ {asset.instructions}</div>}<div className="metadata-line"><span>Last checked: <strong>{dateOnly(asset.last_checked_at) || "Never"}</strong></span><span>Next check: <strong>{dateOnly(asset.next_check_at) || "Not scheduled"}</strong></span></div>{canWrite && <div className="row-actions"><button className="compact" onClick={() => void markChecked("asset", asset.id, asset.revision)}>Mark checked</button><button className="compact" onClick={() => setAssetEditor({ mode: "edit", value: asset })}>Edit</button><button className="danger compact" onClick={() => void remove("assets", asset.id, asset.revision)}>Delete</button></div>}</article>; })}</div></section>}

    {page === "tasks" && <section className="content-width"><PageHeader title="Tasks" subtitle="Recurring checks and standalone preparedness tasks." action={canWrite && <button onClick={() => setTaskEditor({ mode: "new", value: null })}>＋ Add task</button>} /><section className="hp-panel task-list">{data.tasks.length ? data.tasks.map((task) => { const status = taskUiStatus(task); const linkedName = task.linked_item_id ? data.inventory.find((item) => item.id === task.linked_item_id)?.name : task.linked_container_id ? data.containers.find((item) => item.id === task.linked_container_id)?.name : task.linked_asset_id ? data.assets.find((item) => item.id === task.linked_asset_id)?.name : null; return <div className="task-row" key={task.id}><div className="resource-icon">✓</div><div className="resource-main"><strong>{task.name}</strong><span>{linkedName ? `${linkedName} · Managed from ${task.task_kind.replace("_inspection", "")}` : `${pretty(task.category ?? "General")} · Every ${task.recurrence_interval} ${task.recurrence_type}`}{task.next_due_at ? ` · Due ${task.next_due_at}` : " · No due date"}</span></div><StatusChip status={status}>{pretty(status)}</StatusChip>{canWrite && <div className="row-actions"><button className="compact" onClick={() => setTaskEditor({ mode: "edit", value: task })}>Edit</button><button className="compact" onClick={() => void request(`/api/v1/tasks/${task.id}/complete`, { method: "POST", body: JSON.stringify({ expected_revision: task.revision }) }).then(refresh).catch((err: unknown) => fail(err, "Unable to complete task"))}>Complete</button>{linkedName ? <button className="secondary compact" onClick={() => navigate(task.linked_item_id ? "inventory" : task.linked_container_id ? "containers" : "assets")}>Manage item</button> : <button className="danger compact" onClick={() => void remove("tasks", task.id, task.revision)}>Delete</button>}</div>}</div>; }) : <EmptyState>No recurring or standalone tasks yet.</EmptyState>}</section></section>}

    {page === "plans" && <section className="content-width"><PageHeader title="Preparedness plans" subtitle="Use checklists for the things your household needs to know or have ready before an emergency happens." action={canWrite && <button onClick={() => setPlanEditor({ mode: "new", value: null })}>＋ Add plan</button>} />{canWrite && <section className="hp-panel templates"><h3>Start from a template</h3><div className="template-buttons">{templates.filter((template) => ["flood", "evacuation", "fire"].includes(template.id)).map((template) => <button className="secondary" key={template.id} onClick={() => void createFromTemplate(template.id)}>▧ {template.name}</button>)}</div></section>}<div className="card-grid">{data.plans.map((plan) => { const completeCount = plan.checklist.filter((item) => item.completed).length; const reviewDue = Boolean(plan.next_review_at && plan.next_review_at <= todayIso()); const readyPlan = plan.checklist.length > 0 && completeCount === plan.checklist.length && !reviewDue; return <article className="hp-panel plan-card" key={plan.id}><div className="entity-card-head"><div><h3>{plan.name}</h3><p>{plan.description}</p></div><StatusChip status={readyPlan ? "ready" : "attention"}>{readyPlan ? "Ready" : "Needs attention"}</StatusChip></div><div className="metadata-line"><span>{plan.last_reviewed_at ? `Last reviewed: ${dateOnly(plan.last_reviewed_at)}` : "Never reviewed"}</span><span>{plan.next_review_at ? `Next review: ${plan.next_review_at}` : "No review schedule"}</span></div><div className="check-progress"><strong>{completeCount} / {plan.checklist.length}</strong><span>Checklist</span></div><div className="plan-checklist">{plan.checklist.length ? plan.checklist.map((item) => <button type="button" className={item.completed ? "complete" : ""} key={item.id} disabled={!canWrite} onClick={() => void togglePlanCheck(plan, item)}><span>{item.completed ? "✓" : "○"}</span>{item.label}</button>) : <EmptyState>No checklist items yet.</EmptyState>}</div>{canWrite && <div className="row-actions"><button className="compact" onClick={() => void markReviewed(plan)}>▣ Mark reviewed</button><button className="compact" onClick={() => setPlanEditor({ mode: "edit", value: plan })}>Edit</button><button className="danger compact" onClick={() => void remove("plans", plan.id, plan.revision)}>Delete</button></div>}</article>; })}</div></section>}

    {page === "targets" && <section className="content-width"><PageHeader title="Personal targets" subtitle="Targets tell you what ‘ready’ means. Quantities are measured automatically; capabilities use clear confirmations instead of abstract 0/1 values." action={canWrite && <button onClick={() => setTargetEditor({ mode: "new", value: null })}>＋ Add target</button>} /><div className="card-grid">{data.targets.map((target) => { const evaluation = readiness?.target_evaluations.find((item) => item.target_id === target.id); const ui = targetUiStatus(evaluation?.status ?? "unknown"); const requirements = evaluation?.requirements?.length ? evaluation.requirements : target.requirements.map((item) => ({ ...item, complete: target.completed_requirement_ids.includes(item.id) })); return <article className="hp-panel target-card" key={target.id}><div className="entity-card-head"><div><h3>{target.name}</h3><p>{pretty(target.category)} · {target.origin === "recommendation" ? "from guidance" : "personal target"}</p></div><StatusChip status={ui.tone}>{ui.label}</StatusChip></div>{["quantity", "count", "coverage"].includes(target.target_type) && <div className="target-metrics"><div><span>Current</span><strong>{evaluation?.current_value ?? target.current_value ?? "Not assessed"} {target.unit ?? ""}</strong></div><div><span>Minimum</span><strong>{target.minimum_value ?? "—"} {target.unit ?? ""}</strong></div><div><span>Your target</span><strong>{target.target_value ?? "—"} {target.unit ?? ""}</strong></div></div>}{target.target_type === "coverage" && evaluation?.status === "unknown" && <p className="hint">Coverage is deliberately assessed by you; HomePrep will not guess days of coverage from arbitrary inventory.</p>}{requirements.length > 0 && <><strong className="ready-label">{ui.label}</strong><p className="hint">Complete the items below when they are genuinely ready.</p><div className="requirement-list">{requirements.map((requirement) => <label className={requirement.complete ? "complete" : ""} key={requirement.id}><input type="checkbox" disabled={!canWrite} checked={Boolean(requirement.complete)} onChange={() => void toggleRequirement(target, requirement.id)} /><span><strong>{requirement.label}</strong>{requirement.description && <small>{requirement.description}</small>}</span></label>)}</div></>}{canWrite && <div className="row-actions"><button className="compact" onClick={() => setTargetEditor({ mode: "edit", value: target })}>Edit</button><button className="danger compact" onClick={() => void remove("targets", target.id, target.revision)}>Delete</button></div>}</article>; })}</div></section>}

    {page === "guidance" && <section className="content-width"><PageHeader title="Official guidance" subtitle={guidance ? `${guidance.profile.authority} · profile ${guidance.profile.version ?? guidance.profile.id}` : "Configure Household to load official guidance."} />{guidance?.profile.disclaimer && <div className="info-strip">{guidance.profile.disclaimer}</div>}<div className="card-grid guidance-grid">{guidance?.recommendations.filter((recommendation) => recommendation.applicable !== false).map((recommendation) => { const adopted = data.targets.some((target) => target.origin === "recommendation" && target.source_profile_id === guidance.profile.id && target.source_recommendation_id === recommendation.id); const requirements = recommendation.calculated?.requirements ?? recommendation.requirements ?? []; const calculated = recommendation.calculated; return <article className="hp-panel guidance-card" key={recommendation.id}><div className="guidance-title"><div className="entity-icon">{recommendation.category === "water" ? "●" : recommendation.category === "food" ? "▣" : "✓"}</div><div><h3>{recommendation.title}</h3><p>{pretty(recommendation.category)}</p></div></div>{calculated?.minimum_value !== undefined && <div className="calculated"><span>Calculated guidance</span><strong>{calculated.minimum_value} {calculated.unit}</strong></div>}{requirements.length > 0 && <div className="ready-definition"><span>What ‘ready’ means</span>{requirements.map((requirement) => <div key={requirement.id}>✓ {requirement.label}</div>)}</div>}{recommendation.advisory_note && <p className="body-copy">{recommendation.advisory_note}</p>}{adopted ? <div className="adopted">✓ Adopted</div> : canWrite && <button onClick={() => void adoptRecommendation(recommendation.id)}>Add as personal target</button>}</article>; })}</div></section>}

    {page === "household" && <section className="content-width"><PageHeader title="Household" subtitle="Changes recalculate guidance. Existing personal targets remain yours until you choose to change them." />{profile ? <form className="hp-panel edit-form household-form" onSubmit={saveHousehold}><div className="form-grid two"><Field label="Country / guidance profile"><select name="country_code" defaultValue={profile.country_code ?? "OTHER"}><option value="SE">Sweden · MSB</option><option value="NO">Norway · DSB</option><option value="OTHER">Other · HomePrep general</option></select></Field><Field label="Preparedness horizon"><input type="number" name="preparedness_days" min={1} defaultValue={profile.preparedness_days} /></Field><Field label="Adults"><input type="number" name="adults" min={0} defaultValue={profile.adults} /></Field><Field label="Children"><input type="number" name="children" min={0} defaultValue={profile.children} /></Field><Field label="Pets"><input type="number" name="pets" min={0} defaultValue={profile.pets} /></Field></div><p className="hint">HomePrep never silently overwrites adopted personal targets when household data or guidance changes.</p>{canWrite && <button type="submit">Save household</button>}</form> : <section className="hp-panel"><EmptyState>Household profile is not configured.</EmptyState></section>}</section>}

    {page === "access" && isOwner && <section className="content-width"><PageHeader title="Access Control" subtitle="Manage people who can use this HomePrep Server. Home Assistant uses separate revocable client credentials." /><div className="role-cards"><article className="hp-panel"><h3>Owner</h3><p>Full preparedness data and Server/security administration.</p></article><article className="hp-panel"><h3>Editor</h3><p>Read and write normal preparedness data.</p></article><article className="hp-panel"><h3>Viewer</h3><p>Read-only access to preparedness data.</p></article></div><section className="hp-panel access-panel"><h3>Users</h3><div className="user-list">{users.map((user) => <div className="user-row" key={user.id}><div><strong>{user.username}</strong><span>{user.disabled_at ? "Disabled" : "Active"}</span></div><select value={user.role} disabled={Boolean(user.disabled_at)} onChange={(event) => void updateUser(user, { role: event.currentTarget.value })}><option value="owner">Owner</option><option value="editor">Editor</option><option value="viewer">Viewer</option></select><button className="secondary compact" onClick={() => void updateUser(user, { disabled: !user.disabled_at })}>{user.disabled_at ? "Enable" : "Disable"}</button></div>)}</div><form className="create-user" onSubmit={createUser}><input name="username" placeholder="Username" required minLength={3} /><input name="password" type="password" placeholder="Password (12+ characters)" required minLength={12} /><select name="role" defaultValue="viewer"><option value="viewer">Viewer</option><option value="editor">Editor</option><option value="owner">Owner</option></select><button>Add user</button></form></section></section>}

    <footer><span>HomePrep Server {system?.version ?? "—"} · {auth?.user?.username} ({role})</span><span>Your preparedness. Your server. Your data.</span></footer>

    {inventoryEditor && <Modal title={inventoryEditor.mode === "new" ? "Add item" : "Edit item"} onClose={() => setInventoryEditor(null)}><InventoryForm editor={inventoryEditor} taxonomy={taxonomy} containers={data.containers} tasks={data.tasks} preferredUnits={preferredUnits} save={saveInventory} close={() => setInventoryEditor(null)} /></Modal>}
    {containerEditor && <Modal title={containerEditor.mode === "new" ? "Add container" : "Edit container"} onClose={() => setContainerEditor(null)}><ContainerForm editor={containerEditor} tasks={data.tasks} save={saveContainer} close={() => setContainerEditor(null)} /></Modal>}
    {assetEditor && <Modal title={assetEditor.mode === "new" ? "Add asset" : "Edit asset"} onClose={() => setAssetEditor(null)}><AssetForm editor={assetEditor} tasks={data.tasks} save={saveAsset} close={() => setAssetEditor(null)} /></Modal>}
    {taskEditor && <Modal title={taskEditor.mode === "new" ? "Add task" : "Edit task"} onClose={() => setTaskEditor(null)}><TaskForm editor={taskEditor} save={saveTask} close={() => setTaskEditor(null)} /></Modal>}
    {planEditor && <Modal title={planEditor.mode === "new" ? "Add plan" : "Edit plan"} onClose={() => setPlanEditor(null)}><PlanForm editor={planEditor} save={savePlan} close={() => setPlanEditor(null)} /></Modal>}
    {targetEditor && <Modal title={targetEditor.mode === "new" ? "Add target" : "Edit target"} onClose={() => setTargetEditor(null)}><TargetForm editor={targetEditor} taxonomy={taxonomy} save={saveTarget} close={() => setTargetEditor(null)} /></Modal>}
    {shoppingEditor && <Modal title={shoppingEditor.mode === "new" ? "Add shopping item" : "Edit shopping item"} onClose={() => setShoppingEditor(null)}><ShoppingForm editor={shoppingEditor} taxonomy={taxonomy} containers={data.containers} preferredUnits={preferredUnits} save={saveShopping} close={() => setShoppingEditor(null)} /></Modal>}
  </main>;
}

function InventoryForm({ editor, taxonomy, containers, tasks, preferredUnits, save, close }: { editor: NonNullable<Editor<InventoryItem>>; taxonomy: InventoryTaxonomy | null; containers: Container[]; tasks: Task[]; preferredUnits: (category: string) => string[]; save: (event: FormEvent<HTMLFormElement>, editor: NonNullable<Editor<InventoryItem>>) => Promise<void>; close: () => void }) {
  const item = editor.mode === "edit" ? editor.value : null;
  const [category, setCategory] = useState(item?.category ?? "other");
  const linked = item ? recurringTaskFor(tasks, "inventory", item.id) : undefined;
  return <form className="edit-form" onSubmit={(event) => void save(event, editor)}><div className="form-grid two"><Field label="Name"><input name="name" required defaultValue={item?.name ?? ""} /></Field><Field label="Category"><select name="category" value={category} onChange={(event) => setCategory(event.currentTarget.value)}>{Object.entries(taxonomy?.categories ?? { other: "Other" }).map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select></Field><Field label="Item type"><select name="item_type" defaultValue={item?.item_type ?? "consumable"}>{Object.entries(taxonomy?.item_types ?? { consumable: "Consumable" }).map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select></Field><Field label="Quantity"><input name="quantity" type="number" step="any" min={0} defaultValue={item?.quantity ?? 1} /></Field><Field label="Unit"><select name="unit" defaultValue={item?.unit ?? taxonomy?.category_meta[category]?.default_unit ?? "piece"}>{preferredUnits(category).map((value) => <option key={value} value={value}>{unitLabel(value, taxonomy)}</option>)}</select></Field><Field label="Container"><select name="container_id" defaultValue={item?.container_id ?? ""}><option value="">No container</option>{containers.map((container) => <option key={container.id} value={container.id}>{container.name}{container.location ? ` · ${container.location}` : ""}</option>)}</select></Field><Field label="Expires / best before"><input name="expires_at" type="date" defaultValue={item?.expires_at ?? ""} /></Field><Field label="Last checked"><input name="last_checked" type="date" defaultValue={item?.last_checked ?? ""} /></Field><Field label="First due / next check"><input name="next_check_at" type="date" defaultValue={item?.next_check_at ?? linked?.next_due_at ?? ""} /></Field></div><RecurrenceEditor prefix="recurring" initial={recurrenceFromTask(linked)} /><Field label="Notes"><textarea name="notes" defaultValue={item?.notes ?? ""} /></Field><div className="image-field"><div><strong>Item image</strong><small>Images should help you find, identify or act — not decorate.</small></div>{item?.image_id && <img src={`/api/v1/media/images/${item.image_id}`} alt="Current item" />}<input type="file" name="image" accept="image/png,image/jpeg,image/webp,image/gif" />{item?.image_id && <label className="check-row"><input type="checkbox" name="remove_image" />Remove current image</label>}</div><FormActions submitLabel="Save item" onCancel={close} /></form>;
}

function ContainerForm({ editor, tasks, save, close }: { editor: NonNullable<Editor<Container>>; tasks: Task[]; save: (event: FormEvent<HTMLFormElement>, editor: NonNullable<Editor<Container>>) => Promise<void>; close: () => void }) {
  const item = editor.mode === "edit" ? editor.value : null;
  const linked = item ? recurringTaskFor(tasks, "container", item.id) : undefined;
  return <form className="edit-form" onSubmit={(event) => void save(event, editor)}><div className="form-grid two"><Field label="Name"><input name="name" required defaultValue={item?.name ?? ""} /></Field><Field label="Container type"><select name="container_type" defaultValue={item?.container_type ?? "other"}>{Object.entries(CONTAINER_TYPES).map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select></Field><Field label="Location"><input name="location" defaultValue={item?.location ?? ""} placeholder="Hallway cabinet, basement, car…" /></Field><Field label="Last checked"><input type="date" name="last_checked_at" defaultValue={dateOnly(item?.last_checked_at)} /></Field><Field label="First due / next check"><input type="date" name="next_check_at" defaultValue={dateOnly(item?.next_check_at) || linked?.next_due_at || ""} /></Field></div><RecurrenceEditor prefix="recurring" initial={recurrenceFromTask(linked)} /><Field label="Description"><textarea name="description" defaultValue={item?.description ?? ""} /></Field><Field label="Notes"><textarea name="notes" defaultValue={item?.notes ?? ""} /></Field><FormActions submitLabel="Save container" onCancel={close} /></form>;
}

function AssetForm({ editor, tasks, save, close }: { editor: NonNullable<Editor<Asset>>; tasks: Task[]; save: (event: FormEvent<HTMLFormElement>, editor: NonNullable<Editor<Asset>>) => Promise<void>; close: () => void }) {
  const item = editor.mode === "edit" ? editor.value : null;
  const linked = item ? recurringTaskFor(tasks, "asset", item.id) : undefined;
  return <form className="edit-form" onSubmit={(event) => void save(event, editor)}><div className="form-grid two"><Field label="Name"><input name="name" required defaultValue={item?.name ?? ""} /></Field><Field label="Asset type"><select name="asset_type" defaultValue={item?.asset_type ?? "other"}>{Object.entries(ASSET_TYPES).map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select></Field><Field label="Location"><input name="location" defaultValue={item?.location ?? ""} placeholder="Basement utility room, kitchen…" /></Field><Field label="Last checked"><input type="date" name="last_checked_at" defaultValue={dateOnly(item?.last_checked_at)} /></Field><Field label="First due / next check"><input type="date" name="next_check_at" defaultValue={dateOnly(item?.next_check_at) || linked?.next_due_at || ""} /></Field></div><RecurrenceEditor prefix="recurring" initial={recurrenceFromTask(linked)} /><Field label="Description"><textarea name="description" defaultValue={item?.description ?? ""} /></Field><Field label="Instructions"><textarea name="instructions" defaultValue={item?.instructions ?? ""} placeholder="How to find, operate or check this point" /></Field><div className="image-field"><div><strong>Asset image</strong><small>Use an image to identify an important point quickly.</small></div>{item?.image_id && <img src={`/api/v1/media/images/${item.image_id}`} alt="Current asset" />}<input type="file" name="image" accept="image/png,image/jpeg,image/webp,image/gif" />{item?.image_id && <label className="check-row"><input type="checkbox" name="remove_image" />Remove current image</label>}</div><Field label="Notes"><textarea name="notes" defaultValue={item?.notes ?? ""} /></Field><FormActions submitLabel="Save asset" onCancel={close} /></form>;
}

function TaskForm({ editor, save, close }: { editor: NonNullable<Editor<Task>>; save: (event: FormEvent<HTMLFormElement>, editor: NonNullable<Editor<Task>>) => Promise<void>; close: () => void }) {
  const item = editor.mode === "edit" ? editor.value : null;
  return <form className="edit-form" onSubmit={(event) => void save(event, editor)}><Field label="Name"><input name="name" required defaultValue={item?.name ?? ""} /></Field><div className="form-grid two"><Field label="Category"><select name="category" defaultValue={item?.category ?? "general"}>{TASK_CATEGORIES.map((value) => <option key={value} value={value}>{pretty(value)}</option>)}</select></Field><Field label="Next due"><input type="date" name="next_due_at" defaultValue={item?.next_due_at ?? ""} /></Field><Field label="Repeat every"><input type="number" name="recurrence_interval" min={1} defaultValue={item?.recurrence_interval ?? 1} /></Field><Field label="Period"><select name="recurrence_type" defaultValue={item?.recurrence_type ?? "months"}><option value="days">Days</option><option value="weeks">Weeks</option><option value="months">Months</option><option value="years">Years</option></select></Field><Field label="After completion"><select name="reschedule_mode" defaultValue={item?.reschedule_mode ?? "completion"}><option value="completion">Schedule from completion</option><option value="scheduled">Keep planned cadence</option></select></Field><Field label="Reminder before due"><input type="number" name="reminder_before_days" min={0} defaultValue={item?.reminder_before_days ?? 0} /></Field></div><label className="check-row"><input type="checkbox" name="enabled" defaultChecked={item?.enabled ?? true} />Enabled</label><Field label="Notes"><textarea name="notes" defaultValue={item?.notes ?? ""} /></Field><FormActions submitLabel="Save task" onCancel={close} /></form>;
}

function PlanForm({ editor, save, close }: { editor: NonNullable<Editor<Plan>>; save: (event: FormEvent<HTMLFormElement>, editor: NonNullable<Editor<Plan>>) => Promise<void>; close: () => void }) {
  const item = editor.mode === "edit" ? editor.value : null;
  return <form className="edit-form" onSubmit={(event) => void save(event, editor)}><Field label="Name"><input name="name" required defaultValue={item?.name ?? ""} /></Field><div className="form-grid two"><Field label="Plan type"><select name="plan_type" defaultValue={item?.plan_type ?? "other"}>{Object.entries(PLAN_TYPES).map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select></Field><Field label="Meeting point (optional)"><input name="meeting_point" defaultValue={item?.meeting_point ?? ""} /></Field><Field label="Review every (months)"><input type="number" name="review_interval_months" min={0} defaultValue={item?.review_interval_months ?? 6} /></Field><Field label="Next review"><input value={item?.next_review_at ?? "Not scheduled"} readOnly /></Field></div><Field label="Description"><textarea name="description" defaultValue={item?.description ?? ""} /></Field><label className="check-row"><input type="checkbox" name="enabled" defaultChecked={item?.enabled ?? true} />Enabled</label><Field label="Checklist items (one per line)"><textarea name="checklist" rows={8} defaultValue={item?.checklist.map((check) => check.label).join("\n") ?? ""} /></Field><Field label="Notes"><textarea name="notes" defaultValue={item?.notes ?? ""} /></Field><FormActions submitLabel="Save plan" onCancel={close} /></form>;
}

function TargetForm({ editor, taxonomy, save, close }: { editor: NonNullable<Editor<Target>>; taxonomy: InventoryTaxonomy | null; save: (event: FormEvent<HTMLFormElement>, editor: NonNullable<Editor<Target>>) => Promise<void>; close: () => void }) {
  const item = editor.mode === "edit" ? editor.value : null;
  return <form className="edit-form" onSubmit={(event) => void save(event, editor)}><Field label="Name"><input name="name" required defaultValue={item?.name ?? ""} /></Field>{editor.mode === "new" && <Field label="Target type"><select name="target_type" defaultValue="quantity"><option value="quantity">Quantity</option><option value="count">Count</option><option value="coverage">Coverage</option><option value="capability">Capability</option></select></Field>}<div className="form-grid two"><Field label="Category"><select name="category" defaultValue={item?.category ?? "other"}>{Object.entries(taxonomy?.categories ?? { other: "Other" }).map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select></Field><Field label="Unit"><select name="unit" defaultValue={item?.unit ?? "piece"}>{Object.keys(taxonomy?.units ?? { piece: {} }).map((value) => <option key={value} value={value}>{unitLabel(value, taxonomy)}</option>)}</select></Field><Field label="Current coverage / value"><input type="number" step="any" min={0} name="current_value" defaultValue={item?.current_value ?? ""} /></Field><Field label="Minimum"><input type="number" step="any" min={0} name="minimum_value" defaultValue={item?.minimum_value ?? ""} /></Field><Field label="Your target"><input type="number" step="any" min={0} name="target_value" defaultValue={item?.target_value ?? ""} /></Field><Field label="Priority"><select name="priority" defaultValue={item?.priority ?? "normal"}><option value="critical">Critical</option><option value="high">High</option><option value="normal">Normal</option></select></Field></div><label className="check-row"><input type="checkbox" name="enabled" defaultChecked={item?.enabled ?? true} />Enabled</label><Field label="Notes"><textarea name="notes" defaultValue={item?.notes ?? ""} /></Field><FormActions submitLabel="Save target" onCancel={close} /></form>;
}

function ShoppingForm({ editor, taxonomy, containers, preferredUnits, save, close }: { editor: NonNullable<Editor<ShoppingItem>>; taxonomy: InventoryTaxonomy | null; containers: Container[]; preferredUnits: (category: string) => string[]; save: (event: FormEvent<HTMLFormElement>, editor: NonNullable<Editor<ShoppingItem>>) => Promise<void>; close: () => void }) {
  const item = editor.mode === "edit" ? editor.value : null;
  const [category, setCategory] = useState(item?.category ?? "other");
  return <form className="edit-form" onSubmit={(event) => void save(event, editor)}><Field label="Name"><input name="name" required defaultValue={item?.name ?? ""} /></Field><div className="form-grid two"><Field label="Quantity"><input type="number" step="any" min={0} name="quantity" defaultValue={item?.quantity ?? 1} /></Field><Field label="Unit"><select name="unit" defaultValue={item?.unit ?? taxonomy?.category_meta[category]?.default_unit ?? "piece"}>{preferredUnits(category).map((value) => <option key={value} value={value}>{unitLabel(value, taxonomy)}</option>)}</select></Field><Field label="Category"><select name="category" value={category} onChange={(event) => setCategory(event.currentTarget.value)}>{Object.entries(taxonomy?.categories ?? { other: "Other" }).map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select></Field><Field label="Container (optional)"><select name="container_id" defaultValue={item?.container_id ?? ""}><option value="">No container</option>{containers.map((container) => <option key={container.id} value={container.id}>{container.name}</option>)}</select></Field></div><Field label="Notes"><textarea name="notes" defaultValue={item?.notes ?? ""} /></Field><FormActions submitLabel="Save" onCancel={close} /></form>;
}

export default App;

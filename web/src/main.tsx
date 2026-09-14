import React, { FormEvent, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type SystemInfo = {
  name: string;
  version: string;
  environment: string;
  api_version: string;
  server_id?: string;
};

type UserRole = "owner" | "editor" | "viewer";

type User = {
  id: string;
  username: string;
  role: UserRole;
  created_at: string;
  disabled_at: string | null;
};

type AuthStatus = {
  setup_required: boolean;
  authenticated: boolean;
  user: User | null;
};

type Household = {
  id: string;
  name: string;
  revision: number;
};

type InventoryItem = {
  id: string;
  household_id: string;
  name: string;
  category: string;
  item_type: string;
  quantity: number;
  unit: string;
  expires_at: string | null;
  revision: number;
};

type ApiErrorBody = {
  error?: {
    code?: string;
    message?: string;
  };
};

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiErrorBody;
    throw new Error(body.error?.message ?? `${response.status} ${response.statusText}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function AuthCard({
  setupRequired,
  onAuthenticated,
}: {
  setupRequired: boolean;
  onAuthenticated: () => Promise<void>;
}) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    const form = new FormData(event.currentTarget);
    const username = String(form.get("username") ?? "").trim();
    const password = String(form.get("password") ?? "");
    const confirmPassword = String(form.get("confirmPassword") ?? "");

    if (setupRequired && password !== confirmPassword) {
      setError("Passwords do not match.");
      setBusy(false);
      return;
    }

    try {
      await request<User>(setupRequired ? "/api/v1/auth/setup" : "/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      await onAuthenticated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="auth-wrap">
      <div className="card auth-card">
        <div className="auth-logo">HP</div>
        <span className="eyebrow">HOME PREP SERVER</span>
        <h2>{setupRequired ? "Create your owner account" : "Welcome back"}</h2>
        <p>
          {setupRequired
            ? "This owner account stays on your own HomePrep Server and controls local access to your preparedness data."
            : "Sign in to access your HomePrep household."}
        </p>
        {error && <div className="error">{error}</div>}
        <form className="form" onSubmit={submit}>
          <label className="field">
            <span>Username</span>
            <input name="username" autoComplete="username" minLength={3} maxLength={64} required autoFocus />
          </label>
          <label className="field">
            <span>Password</span>
            <input
              name="password"
              type="password"
              autoComplete={setupRequired ? "new-password" : "current-password"}
              minLength={setupRequired ? 12 : 1}
              required
            />
          </label>
          {setupRequired && (
            <label className="field">
              <span>Confirm password</span>
              <input name="confirmPassword" type="password" autoComplete="new-password" minLength={12} required />
            </label>
          )}
          <button type="submit" disabled={busy}>
            {busy ? "Please wait…" : setupRequired ? "Create owner" : "Sign in"}
          </button>
        </form>
        {setupRequired && <small>Use at least 12 characters for the password.</small>}
      </div>
    </section>
  );
}

function App() {
  const [system, setSystem] = useState<SystemInfo | null>(null);
  const [ready, setReady] = useState(false);
  const [auth, setAuth] = useState<AuthStatus | null>(null);
  const [households, setHouseholds] = useState<Household[]>([]);
  const [householdId, setHouseholdId] = useState("");
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const role = auth?.user?.role ?? "viewer";
  const canWrite = role === "owner" || role === "editor";
  const isOwner = role === "owner";
  const activeHousehold = useMemo(
    () => households.find((household) => household.id === householdId) ?? null,
    [households, householdId],
  );

  async function loadInventory(id: string) {
    const items = await request<InventoryItem[]>(`/api/v1/inventory?household_id=${id}`);
    setInventory(items);
  }

  async function loadUsers() {
    if (!isOwner) {
      setUsers([]);
      return;
    }
    setUsers(await request<User[]>("/api/v1/users"));
  }

  async function loadProtectedData(currentRole: UserRole) {
    const householdList = await request<Household[]>("/api/v1/households");
    setHouseholds(householdList);
    const selected = householdList[0]?.id ?? "";
    setHouseholdId(selected);
    if (selected) await loadInventory(selected);
    else setInventory([]);
    if (currentRole === "owner") setUsers(await request<User[]>("/api/v1/users"));
    else setUsers([]);
  }

  async function bootstrap() {
    setLoading(true);
    setError("");
    try {
      const [info, readiness, authStatus] = await Promise.all([
        request<SystemInfo>("/api/v1/system/info"),
        request<{ status: string }>("/readyz"),
        request<AuthStatus>("/api/v1/auth/status"),
      ]);
      setSystem(info);
      setReady(readiness.status === "ready");
      setAuth(authStatus);
      if (authStatus.authenticated && authStatus.user) {
        await loadProtectedData(authStatus.user.role);
      } else {
        setHouseholds([]);
        setHouseholdId("");
        setInventory([]);
        setUsers([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to connect to HomePrep Server");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void bootstrap();
  }, []);

  async function createHousehold(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const name = String(form.get("name") ?? "").trim();
    if (!name) return;
    try {
      const household = await request<Household>("/api/v1/households", {
        method: "POST",
        body: JSON.stringify({ name }),
      });
      setHouseholds([household]);
      setHouseholdId(household.id);
      formElement.reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create household");
    }
  }

  async function createItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!householdId || !canWrite) return;
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    try {
      await request<InventoryItem>("/api/v1/inventory", {
        method: "POST",
        body: JSON.stringify({
          household_id: householdId,
          name: String(form.get("name") ?? "").trim(),
          category: String(form.get("category") ?? "other"),
          item_type: "consumable",
          quantity: Number(form.get("quantity") ?? 1),
          unit: String(form.get("unit") ?? "pcs"),
        }),
      });
      await loadInventory(householdId);
      formElement.reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to add inventory item");
    }
  }

  async function updateItem(event: FormEvent<HTMLFormElement>, item: InventoryItem) {
    event.preventDefault();
    if (!canWrite) return;
    const form = new FormData(event.currentTarget);
    try {
      await request<InventoryItem>(`/api/v1/inventory/${item.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: String(form.get("name") ?? "").trim(),
          quantity: Number(form.get("quantity") ?? 0),
          unit: String(form.get("unit") ?? "pcs"),
          category: String(form.get("category") ?? "other"),
          expected_revision: item.revision,
        }),
      });
      setEditingId(null);
      await loadInventory(householdId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update inventory item");
      await loadInventory(householdId).catch(() => undefined);
    }
  }

  async function removeItem(item: InventoryItem) {
    if (!canWrite) return;
    try {
      await request<InventoryItem>(
        `/api/v1/inventory/${item.id}?expected_revision=${item.revision}`,
        { method: "DELETE" },
      );
      if (editingId === item.id) setEditingId(null);
      await loadInventory(householdId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to remove inventory item");
      await loadInventory(householdId).catch(() => undefined);
    }
  }

  async function createUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    try {
      await request<User>("/api/v1/users", {
        method: "POST",
        body: JSON.stringify({
          username: String(form.get("username") ?? "").trim(),
          password: String(form.get("password") ?? ""),
          role: String(form.get("role") ?? "viewer"),
        }),
      });
      formElement.reset();
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create user");
    }
  }

  async function setUserRole(user: User, nextRole: UserRole) {
    try {
      await request<User>(`/api/v1/users/${user.id}`, {
        method: "PATCH",
        body: JSON.stringify({ role: nextRole }),
      });
      await loadUsers();
      if (auth?.user?.id === user.id) await bootstrap();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to change role");
    }
  }

  async function setUserDisabled(user: User, disabled: boolean) {
    try {
      await request<User>(`/api/v1/users/${user.id}`, {
        method: "PATCH",
        body: JSON.stringify({ disabled }),
      });
      if (auth?.user?.id === user.id && disabled) {
        await bootstrap();
        return;
      }
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to change user status");
    }
  }

  async function logout() {
    await request<void>("/api/v1/auth/logout", { method: "POST" });
    await bootstrap();
  }

  if (loading && auth === null) return <div className="boot">Starting HomePrep…</div>;

  if (auth && !auth.authenticated) {
    return (
      <main className="shell">
        <header className="topbar">
          <div className="brandmark">HP</div>
          <div><h1>HomePrep</h1><p>Your preparedness. Your server. Your data.</p></div>
          <div className={`status ${ready ? "online" : "offline"}`}>
            <span /> {ready ? "Server online" : "Server unavailable"}
          </div>
        </header>
        {error && <div className="error">{error}</div>}
        <AuthCard setupRequired={auth.setup_required} onAuthenticated={bootstrap} />
      </main>
    );
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brandmark">HP</div>
        <div><h1>HomePrep</h1><p>Your preparedness. Your server. Your data.</p></div>
        <div className={`status ${ready ? "online" : "offline"}`}>
          <span /> {ready ? "Server online" : "Server unavailable"}
        </div>
        <button className="secondary compact" onClick={() => void logout()}>Sign out</button>
      </header>

      {error && <div className="error">{error}</div>}

      <section className="hero card">
        <div>
          <span className="eyebrow">SELF-HOSTED HOME PREPAREDNESS</span>
          <h2>{activeHousehold ? activeHousehold.name : "Set up your household"}</h2>
          <p>
            HomePrep runs against your own server and SQLite database. Your signed-in account is
            <strong> {auth?.user?.username}</strong> with the <strong>{role}</strong> role.
          </p>
        </div>
        <div className="server-meta">
          <div><span>Version</span><strong>{system?.version ?? "—"}</strong></div>
          <div><span>API</span><strong>{system?.api_version ?? "—"}</strong></div>
          <div><span>Inventory</span><strong>{inventory.length}</strong></div>
        </div>
      </section>

      <div className="grid">
        <section className="card">
          <div className="section-title">
            <div><span className="eyebrow">HOUSEHOLD</span><h3>{activeHousehold ? "Your household" : "Create your household"}</h3></div>
          </div>
          {activeHousehold ? (
            <div className="empty"><strong>{activeHousehold.name}</strong><br />This server is dedicated to one HomePrep household.</div>
          ) : isOwner ? (
            <form className="form" onSubmit={createHousehold}>
              <label className="field"><span>Household name</span><input name="name" placeholder="My household" required maxLength={120} /></label>
              <button type="submit">Create household</button>
            </form>
          ) : (
            <div className="empty">An owner must create the household before this account can use HomePrep.</div>
          )}
        </section>

        <section className="card inventory-card">
          <div className="section-title">
            <div><span className="eyebrow">INVENTORY</span><h3>Preparedness supplies</h3></div>
            <button className="secondary" onClick={() => void bootstrap()} disabled={loading}>Refresh</button>
          </div>

          {!householdId ? (
            <div className="empty">No household is configured yet.</div>
          ) : inventory.length === 0 ? (
            <div className="empty">No inventory yet.{canWrite ? " Add the first item below." : ""}</div>
          ) : (
            <div className="inventory-list">
              {inventory.map((item) =>
                editingId === item.id && canWrite ? (
                  <form className="inventory-edit" key={item.id} onSubmit={(event) => void updateItem(event, item)}>
                    <input name="name" defaultValue={item.name} required maxLength={120} />
                    <input name="quantity" type="number" min="0" step="0.1" defaultValue={item.quantity} required />
                    <select name="unit" defaultValue={item.unit}><option value="pcs">pcs</option><option value="l">L</option><option value="kg">kg</option></select>
                    <select name="category" defaultValue={item.category}>
                      <option value="food">Food</option><option value="water">Water</option><option value="medicine">Medicine</option>
                      <option value="power">Power</option><option value="lighting">Lighting</option><option value="other">Other</option>
                    </select>
                    <div className="edit-actions"><button type="submit">Save</button><button type="button" className="secondary" onClick={() => setEditingId(null)}>Cancel</button></div>
                  </form>
                ) : (
                  <article className="inventory-row" key={item.id}>
                    <div><strong>{item.name}</strong><span>{item.category.replaceAll("_", " ")} · revision {item.revision}</span></div>
                    <div className="quantity">{item.quantity} {item.unit}</div>
                    {canWrite && (
                      <div className="row-actions">
                        <button className="secondary compact" onClick={() => setEditingId(item.id)}>Edit</button>
                        <button className="icon-button" onClick={() => void removeItem(item)} aria-label={`Remove ${item.name}`}>×</button>
                      </div>
                    )}
                  </article>
                ),
              )}
            </div>
          )}

          {householdId && canWrite && (
            <form className="item-form" onSubmit={createItem}>
              <input name="name" placeholder="Item name" required maxLength={120} />
              <input name="quantity" type="number" min="0" step="0.1" defaultValue="1" required />
              <select name="unit" defaultValue="pcs"><option value="pcs">pcs</option><option value="l">L</option><option value="kg">kg</option></select>
              <select name="category" defaultValue="other">
                <option value="food">Food</option><option value="water">Water</option><option value="medicine">Medicine</option>
                <option value="power">Power</option><option value="lighting">Lighting</option><option value="other">Other</option>
              </select>
              <button type="submit">Add item</button>
            </form>
          )}
          {!canWrite && householdId && <div className="permission-note">Viewer access: Inventory is read-only.</div>}
        </section>
      </div>

      {isOwner && (
        <section className="card user-admin">
          <div className="section-title">
            <div><span className="eyebrow">ACCESS CONTROL</span><h3>Users and roles</h3></div>
            <button className="secondary" onClick={() => void loadUsers()}>Refresh users</button>
          </div>
          <p className="section-copy">Owners administer server access. Editors can change preparedness data. Viewers are read-only. Home Assistant pairing is managed separately from these user roles.</p>
          <div className="user-list">
            {users.map((user) => (
              <article className="user-row" key={user.id}>
                <div><strong>{user.username}</strong><span>{user.disabled_at ? "Disabled" : "Active"}</span></div>
                <select value={user.role} disabled={Boolean(user.disabled_at)} onChange={(event) => void setUserRole(user, event.target.value as UserRole)}>
                  <option value="owner">Owner</option><option value="editor">Editor</option><option value="viewer">Viewer</option>
                </select>
                <button className="secondary compact" onClick={() => void setUserDisabled(user, !user.disabled_at)}>
                  {user.disabled_at ? "Enable" : "Disable"}
                </button>
              </article>
            ))}
          </div>
          <form className="user-create" onSubmit={createUser}>
            <input name="username" placeholder="Username" minLength={3} maxLength={64} required />
            <input name="password" type="password" placeholder="Password (12+ chars)" minLength={12} required />
            <select name="role" defaultValue="viewer"><option value="viewer">Viewer</option><option value="editor">Editor</option><option value="owner">Owner</option></select>
            <button type="submit">Add user</button>
          </form>
        </section>
      )}

      <footer>
        <span>HomePrep Server {system?.version ?? ""} · signed in as {auth?.user?.username ?? ""} ({role})</span>
        <span>Local-first · self-hosted · no central HomePrep account</span>
      </footer>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode><App /></React.StrictMode>,
);

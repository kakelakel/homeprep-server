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

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

function App() {
  const [system, setSystem] = useState<SystemInfo | null>(null);
  const [ready, setReady] = useState(false);
  const [households, setHouseholds] = useState<Household[]>([]);
  const [householdId, setHouseholdId] = useState("");
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const activeHousehold = useMemo(
    () => households.find((household) => household.id === householdId) ?? null,
    [households, householdId],
  );

  async function loadInventory(id: string) {
    const items = await request<InventoryItem[]>(`/api/v1/inventory?household_id=${id}`);
    setInventory(items);
  }

  async function bootstrap() {
    setLoading(true);
    setError("");
    try {
      const [info, readiness, householdList] = await Promise.all([
        request<SystemInfo>("/api/v1/system/info"),
        request<{ status: string }>("/readyz"),
        request<Household[]>("/api/v1/households"),
      ]);
      setSystem(info);
      setReady(readiness.status === "ready");
      setHouseholds(householdList);
      const stored = localStorage.getItem("homeprep.household_id");
      const selected =
        householdList.find((item) => item.id === stored)?.id ?? householdList[0]?.id ?? "";
      setHouseholdId(selected);
      if (selected) await loadInventory(selected);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to connect to HomePrep Server");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void bootstrap();
  }, []);

  useEffect(() => {
    if (!householdId) return;
    localStorage.setItem("homeprep.household_id", householdId);
    void loadInventory(householdId).catch((err) => {
      setError(err instanceof Error ? err.message : "Unable to load inventory");
    });
  }, [householdId]);

  async function createHousehold(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const form = new FormData(event.currentTarget);
    const name = String(form.get("name") ?? "").trim();
    if (!name) return;
    try {
      const household = await request<Household>("/api/v1/households", {
        method: "POST",
        body: JSON.stringify({ name }),
      });
      setHouseholds((current) => [...current, household]);
      setHouseholdId(household.id);
      event.currentTarget.reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create household");
    }
  }

  async function createItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!householdId) return;
    setError("");
    const form = new FormData(event.currentTarget);
    const quantity = Number(form.get("quantity") ?? 1);
    try {
      await request<InventoryItem>("/api/v1/inventory", {
        method: "POST",
        body: JSON.stringify({
          household_id: householdId,
          name: String(form.get("name") ?? "").trim(),
          category: String(form.get("category") ?? "other"),
          item_type: "consumable",
          quantity,
          unit: String(form.get("unit") ?? "pcs"),
        }),
      });
      await loadInventory(householdId);
      event.currentTarget.reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to add inventory item");
    }
  }

  async function removeItem(item: InventoryItem) {
    setError("");
    try {
      await request<InventoryItem>(
        `/api/v1/inventory/${item.id}?expected_revision=${item.revision}`,
        { method: "DELETE" },
      );
      await loadInventory(householdId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to remove inventory item");
    }
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brandmark">HP</div>
        <div>
          <h1>HomePrep</h1>
          <p>Your preparedness. Your server. Your data.</p>
        </div>
        <div className={`status ${ready ? "online" : "offline"}`}>
          <span /> {ready ? "Server online" : "Server unavailable"}
        </div>
      </header>

      {error && <div className="error">{error}</div>}

      <section className="hero card">
        <div>
          <span className="eyebrow">SELF-HOSTED HOME PREPAREDNESS</span>
          <h2>{activeHousehold ? activeHousehold.name : "Set up your household"}</h2>
          <p>
            This is the first HomePrep Web client running against your own HomePrep Server.
            Everything shown here comes from your server API and SQLite database.
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
            <div>
              <span className="eyebrow">HOUSEHOLD</span>
              <h3>Data owner</h3>
            </div>
          </div>

          {households.length > 0 && (
            <label className="field">
              <span>Active household</span>
              <select value={householdId} onChange={(event) => setHouseholdId(event.target.value)}>
                {households.map((household) => (
                  <option key={household.id} value={household.id}>{household.name}</option>
                ))}
              </select>
            </label>
          )}

          <form className="form" onSubmit={createHousehold}>
            <label className="field">
              <span>{households.length ? "Add another household" : "Household name"}</span>
              <input name="name" placeholder="My household" required maxLength={120} />
            </label>
            <button type="submit">Create household</button>
          </form>
        </section>

        <section className="card inventory-card">
          <div className="section-title">
            <div>
              <span className="eyebrow">INVENTORY</span>
              <h3>Preparedness supplies</h3>
            </div>
            <button className="secondary" onClick={() => void bootstrap()} disabled={loading}>Refresh</button>
          </div>

          {!householdId ? (
            <div className="empty">Create a household to start adding preparedness supplies.</div>
          ) : inventory.length === 0 ? (
            <div className="empty">No inventory yet. Add the first item below.</div>
          ) : (
            <div className="inventory-list">
              {inventory.map((item) => (
                <article className="inventory-row" key={item.id}>
                  <div>
                    <strong>{item.name}</strong>
                    <span>{item.category.replaceAll("_", " ")} · revision {item.revision}</span>
                  </div>
                  <div className="quantity">{item.quantity} {item.unit}</div>
                  <button
                    className="icon-button"
                    onClick={() => void removeItem(item)}
                    aria-label={`Remove ${item.name}`}
                  >
                    ×
                  </button>
                </article>
              ))}
            </div>
          )}

          {householdId && (
            <form className="item-form" onSubmit={createItem}>
              <input name="name" placeholder="Item name" required maxLength={120} />
              <input name="quantity" type="number" min="0" step="0.1" defaultValue="1" required />
              <select name="unit" defaultValue="pcs">
                <option value="pcs">pcs</option>
                <option value="l">L</option>
                <option value="kg">kg</option>
              </select>
              <select name="category" defaultValue="other">
                <option value="food">Food</option>
                <option value="water">Water</option>
                <option value="medicine">Medicine</option>
                <option value="power">Power</option>
                <option value="lighting">Lighting</option>
                <option value="other">Other</option>
              </select>
              <button type="submit">Add item</button>
            </form>
          )}
        </section>
      </div>

      <footer>
        <span>HomePrep Server {system?.version ?? ""}</span>
        <span>Local-first · self-hosted · no central HomePrep account</span>
      </footer>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

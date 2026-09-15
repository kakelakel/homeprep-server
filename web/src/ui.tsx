import React, { ReactNode } from "react";
import type { Page } from "./types";

export function PageHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return <div className="page-heading"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{action}</div>;
}

export function StatusChip({ status, children }: { status: string; children?: ReactNode }) {
  const normalized = status.toLowerCase().replaceAll(" ", "-");
  return <span className={`hp-chip hp-${normalized}`}>{children ?? status}</span>;
}

export function Modal({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="modal-card" role="dialog" aria-modal="true" aria-label={title}>
      <div className="modal-head"><h2>{title}</h2><button type="button" className="icon-button" onClick={onClose} aria-label="Close">×</button></div>
      {children}
    </section>
  </div>;
}

export type NavGroup = { label: string; pages: Array<{ page: Page; label: string }>; icon: string };

export function GroupedNav({ page, groups, navigate }: { page: Page; groups: NavGroup[]; navigate: (page: Page) => void }) {
  return <nav className="group-nav" aria-label="HomePrep navigation">
    <button className={page === "overview" ? "active" : ""} onClick={() => navigate("overview")}><span className="nav-icon">▦</span>Overview</button>
    {groups.map((group) => <details className="nav-group" key={group.label} open={group.pages.some((item) => item.page === page)}>
      <summary className={group.pages.some((item) => item.page === page) ? "active-parent" : ""}><span className="nav-icon">{group.icon}</span>{group.label}<span className="chevron">⌄</span></summary>
      <div className="nav-menu">{group.pages.map((item) => <button key={item.page} className={page === item.page ? "active" : ""} onClick={() => navigate(item.page)}>{item.label}</button>)}</div>
    </details>)}
  </nav>;
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <div className="empty-state">{children}</div>;
}

export function Field({ label, children, className = "" }: { label: string; children: ReactNode; className?: string }) {
  return <label className={`field ${className}`}><span>{label}</span>{children}</label>;
}

export function FormActions({ submitLabel = "Save", onCancel, danger }: { submitLabel?: string; onCancel: () => void; danger?: ReactNode }) {
  return <div className="form-actions"><button type="submit">{submitLabel}</button><button type="button" className="secondary" onClick={onCancel}>Cancel</button>{danger}</div>;
}

import React, { ReactNode, useEffect, useRef, useState } from "react";
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

function supportsHover(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(hover: hover) and (pointer: fine)").matches;
}

export function GroupedNav({ page, groups, navigate }: { page: Page; groups: NavGroup[]; navigate: (page: Page) => void }) {
  const [openGroup, setOpenGroup] = useState<string | null>(null);
  const navRef = useRef<HTMLElement | null>(null);
  const closeTimer = useRef<number | null>(null);

  useEffect(() => {
    function outside(event: PointerEvent) {
      if (navRef.current && !navRef.current.contains(event.target as Node)) setOpenGroup(null);
    }
    function keyboard(event: KeyboardEvent) {
      if (event.key === "Escape") setOpenGroup(null);
    }
    document.addEventListener("pointerdown", outside);
    document.addEventListener("keydown", keyboard);
    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("keydown", keyboard);
      if (closeTimer.current !== null) window.clearTimeout(closeTimer.current);
    };
  }, []);

  function cancelClose() {
    if (closeTimer.current !== null) {
      window.clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
  }

  function hoverOpen(label: string) {
    if (!supportsHover()) return;
    cancelClose();
    setOpenGroup(label);
  }

  function hoverClose() {
    if (!supportsHover()) return;
    cancelClose();
    closeTimer.current = window.setTimeout(() => setOpenGroup(null), 140);
  }

  function go(next: Page) {
    setOpenGroup(null);
    navigate(next);
  }

  return <nav ref={navRef} className="group-nav" aria-label="HomePrep navigation">
    <button type="button" className={page === "overview" ? "active" : ""} onClick={() => go("overview")}><span className="nav-icon">▦</span>Overview</button>
    {groups.map((group) => {
      const active = group.pages.some((item) => item.page === page);
      const open = openGroup === group.label;
      return <div className={`nav-group${open ? " open" : ""}`} key={group.label} onMouseEnter={() => hoverOpen(group.label)} onMouseLeave={hoverClose}>
        <button
          type="button"
          className={`nav-group-trigger${active ? " active-parent" : ""}`}
          aria-expanded={open}
          aria-haspopup="menu"
          onClick={(event) => {
            event.stopPropagation();
            cancelClose();
            setOpenGroup(open ? null : group.label);
          }}
        >
          <span className="nav-icon">{group.icon}</span>{group.label}<span className="chevron" aria-hidden="true">⌄</span>
        </button>
        <div className="nav-menu" role="menu" aria-hidden={!open}>
          {group.pages.map((item) => <button type="button" role="menuitem" key={item.page} className={page === item.page ? "active" : ""} onClick={() => go(item.page)}>{item.label}<span className="menu-arrow" aria-hidden="true">›</span></button>)}
        </div>
      </div>;
    })}
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

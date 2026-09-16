const AREA_ROUTES: Record<string, string> = {
  Inventory: "inventory",
  Containers: "containers",
  Tasks: "tasks",
  Assets: "assets",
  Plans: "plans",
  Targets: "targets",
};

function navigate(page: string) {
  window.location.hash = `/${page}`;
}

function enhanceReadinessCards(root: ParentNode = document) {
  root.querySelectorAll<HTMLElement>(".area-card").forEach((card) => {
    if (card.dataset.route) return;
    const label = card.querySelector<HTMLElement>(".area-head strong")?.textContent?.trim();
    if (!label) return;
    const route = AREA_ROUTES[label];
    if (!route) return;
    card.dataset.route = route;
    card.setAttribute("role", "button");
    card.setAttribute("tabindex", "0");
    card.setAttribute("aria-label", `Open ${label}`);
  });
}

export function initializeEnhancements() {
  const root = document.getElementById("root");
  if (!root) return;

  enhanceReadinessCards(root);

  const observer = new MutationObserver(() => enhanceReadinessCards(root));
  observer.observe(root, { childList: true, subtree: true });

  root.addEventListener("click", (event) => {
    const target = event.target as HTMLElement | null;
    const card = target?.closest<HTMLElement>(".area-card[data-route]");
    if (card?.dataset.route) navigate(card.dataset.route);
  });

  root.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const target = event.target as HTMLElement | null;
    const card = target?.closest<HTMLElement>(".area-card[data-route]");
    if (!card?.dataset.route) return;
    event.preventDefault();
    navigate(card.dataset.route);
  });
}

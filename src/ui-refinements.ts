import { getOpenCodeEmailByLabel, moveOpenCodeEmailLabel } from "./opencode-account-email";

const TRASH_ICON = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6M10 11v5M14 11v5" /></svg>`;

type CardProvider = "openai" | "anthropic" | "antigravity" | "opencode_go";

function cardProvider(card: HTMLElement): CardProvider | null {
  const icon = card.querySelector<HTMLElement>(".account-card-provider-icon");
  if (icon?.classList.contains("provider-openai")) return "openai";
  if (icon?.classList.contains("provider-anthropic")) return "anthropic";
  if (icon?.classList.contains("provider-antigravity")) return "antigravity";
  if (icon?.classList.contains("provider-opencode_go")) return "opencode_go";
  return null;
}

function refineHeader(card: HTMLElement): void {
  const nameRow = card.querySelector<HTMLElement>(".account-card-name-row");
  const actions = card.querySelector<HTMLElement>(".account-card-header-actions");
  const plan = actions?.querySelector<HTMLElement>(".account-plan-badge") ?? null;
  const status = nameRow?.querySelector<HTMLElement>(".account-status-badge") ?? null;

  if (nameRow && plan && plan.parentElement !== nameRow) {
    status?.insertAdjacentElement("afterend", plan);
  }

  if (!actions) return;
  const notification = Array.from(actions.querySelectorAll<HTMLButtonElement>("button"))
    .find((button) => button.title === "Usage notifications");
  const remove = Array.from(actions.querySelectorAll<HTMLButtonElement>("button"))
    .find((button) => button.title === "Remove this account");
  const refresh = Array.from(actions.querySelectorAll<HTMLButtonElement>("button"))
    .find((button) => button.title === "Refresh this account");

  if (remove && !remove.querySelector(".mini-spinner")) {
    const existingPath = remove.querySelector("path")?.getAttribute("d");
    if (existingPath !== "M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6M10 11v5M14 11v5") {
      remove.innerHTML = TRASH_ICON;
    }
  }

  const desired = [notification, remove, refresh].filter((button): button is HTMLButtonElement => Boolean(button));
  const current = Array.from(actions.querySelectorAll<HTMLButtonElement>(":scope > button"));
  if (desired.some((button, index) => current[index] !== button)) {
    for (const button of desired) actions.append(button);
  }
}

function refineMetric(metric: HTMLElement, provider: CardProvider): void {
  const label = metric.querySelector<HTMLElement>(".metric-label");
  if (!label) return;

  if (provider === "openai" && label.textContent?.trim().toLowerCase() === "session") {
    metric.remove();
    return;
  }

  if (provider === "antigravity") {
    const current = label.textContent ?? "";
    const cleaned = current.replace(/\s*·\s*(?:five hour|5 hour|weekly) limit\s*$/i, "").trim();
    if (cleaned && cleaned !== current) label.textContent = cleaned;
  }

  const pill = metric.querySelector<HTMLElement>(".metric-window-pill");
  const track = metric.querySelector<HTMLElement>(".account-metric-track");
  if (pill && track && pill.nextElementSibling !== track) {
    track.insertAdjacentElement("beforebegin", pill);
  }
}

function refineCredits(card: HTMLElement, provider: CardProvider): void {
  const credits = card.querySelector<HTMLElement>(".account-credit-metric");
  if (!credits) return;

  if (provider === "antigravity" || provider === "opencode_go") {
    credits.remove();
    return;
  }

  if (provider === "openai") {
    for (const child of Array.from(credits.children)) {
      if (child.textContent?.trim() === "Provider-reported remaining credit balance") child.remove();
    }
  }
}

function refineOpenCodeEmail(card: HTMLElement): void {
  const name = card.querySelector<HTMLElement>(".account-card-name-row h2")?.textContent?.trim();
  const subtitle = card.querySelector<HTMLElement>(".account-card-identity > p");
  if (!name || !subtitle) return;

  const previousLabel = card.dataset.emailLabel;
  const email = previousLabel && previousLabel !== name
    ? moveOpenCodeEmailLabel(previousLabel, name)
    : getOpenCodeEmailByLabel(name);

  card.dataset.emailLabel = name;
  if (email && subtitle.textContent !== email) subtitle.textContent = email;
}

function refineAccountCard(card: HTMLElement): void {
  const provider = cardProvider(card);
  if (!provider) return;
  card.dataset.provider = provider;
  refineHeader(card);
  for (const metric of Array.from(card.querySelectorAll<HTMLElement>(".account-usage-metric"))) {
    refineMetric(metric, provider);
  }
  refineCredits(card, provider);
  if (provider === "opencode_go") refineOpenCodeEmail(card);
}

function refineUpdateControl(): void {
  for (const duplicate of Array.from(document.querySelectorAll<HTMLElement>(".sidebar-footer > span"))) {
    duplicate.remove();
  }
}

function applyRefinements(): void {
  for (const card of Array.from(document.querySelectorAll<HTMLElement>(".provider-account-card"))) {
    refineAccountCard(card);
  }
  refineUpdateControl();
}

export function installUiRefinements(): void {
  applyRefinements();
  const observer = new MutationObserver(() => applyRefinements());
  observer.observe(document.body, { childList: true, subtree: true });
}

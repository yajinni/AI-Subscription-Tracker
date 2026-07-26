import { getOpenCodeEmailByLabel, moveOpenCodeEmailLabel } from "./opencode-account-email";

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
  const plan = card.querySelector<HTMLElement>(".account-plan-badge");
  if (nameRow && plan?.textContent?.trim()) {
    nameRow.dataset.plan = plan.textContent.trim();
  } else {
    delete nameRow?.dataset.plan;
  }
}

function refineMetric(metric: HTMLElement, provider: CardProvider): void {
  const label = metric.querySelector<HTMLElement>(".metric-label");
  if (!label) return;

  const labelText = label.textContent?.trim() ?? "";
  metric.classList.toggle(
    "ui-hidden-metric",
    provider === "openai" && labelText.toLowerCase() === "session",
  );

  if (provider === "antigravity") {
    const cleaned = labelText.replace(/\s*·\s*(?:five hour|5 hour|weekly) limit\s*$/i, "").trim();
    if (cleaned && cleaned !== labelText) label.textContent = cleaned;
  }
}

function refineCredits(card: HTMLElement, provider: CardProvider): void {
  const credits = card.querySelector<HTMLElement>(".account-credit-metric");
  if (!credits) return;

  credits.classList.toggle("ui-hidden-credit", provider === "antigravity" || provider === "opencode_go");

  if (provider === "openai") {
    for (const child of Array.from(credits.children)) {
      child.classList.toggle(
        "ui-hidden-credit-helper",
        child.textContent?.trim() === "Provider-reported remaining credit balance",
      );
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

function applyRefinements(): void {
  for (const card of Array.from(document.querySelectorAll<HTMLElement>(".provider-account-card"))) {
    refineAccountCard(card);
  }
}

export function installUiRefinements(): void {
  applyRefinements();
  const observer = new MutationObserver(() => applyRefinements());
  observer.observe(document.body, { childList: true, subtree: true, characterData: true });
}

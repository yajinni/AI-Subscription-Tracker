import { bridgeApi } from "./api";
import type { BridgeInfo } from "./types";

let attachFrame: number | null = null;

function buildIntegrationView(view: HTMLElement): void {
  if (view.dataset.paseoIntegrationControl === "true") return;
  view.dataset.paseoIntegrationControl = "true";
  view.replaceChildren();

  const header = document.createElement("header");
  header.className = "page-header";
  const headingCopy = document.createElement("div");
  const eyebrow = document.createElement("span");
  eyebrow.className = "eyebrow";
  eyebrow.textContent = "Optional integration";
  const heading = document.createElement("h1");
  heading.textContent = "Integrations";
  const intro = document.createElement("p");
  intro.textContent = "Connect AI Subscription Tracker to other local tools only when you need them.";
  headingCopy.append(eyebrow, heading, intro);
  header.append(headingCopy);

  const card = document.createElement("section");
  card.className = "settings-card paseo-integration-card";
  const row = document.createElement("div");
  row.className = "settings-row paseo-integration-row";

  const description = document.createElement("div");
  const title = document.createElement("strong");
  title.textContent = "Paseo Bridge";
  const helper = document.createElement("small");
  helper.textContent = "Expose sanitized usage data to Paseo over an authenticated localhost endpoint. Disabled by default.";
  const status = document.createElement("span");
  status.className = "paseo-bridge-inline-status";
  description.append(title, helper, status);

  const actions = document.createElement("div");
  actions.className = "paseo-integration-actions";
  const viewButton = document.createElement("button");
  viewButton.type = "button";
  viewButton.className = "paseo-view-link";
  viewButton.textContent = "View";
  viewButton.hidden = true;

  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "toggle";
  toggle.setAttribute("aria-label", "Enable Paseo Bridge");
  toggle.setAttribute("aria-pressed", "false");
  toggle.append(document.createElement("span"));
  actions.append(viewButton, toggle);
  row.append(description, actions);
  card.append(row);

  const errorPanel = document.createElement("div");
  errorPanel.className = "error-panel paseo-integration-error";
  errorPanel.hidden = true;

  view.append(header, card, errorPanel);

  let bridge: BridgeInfo | null = null;
  let busy = false;

  const render = (next: BridgeInfo) => {
    bridge = next;
    toggle.classList.toggle("on", next.enabled);
    toggle.setAttribute("aria-pressed", String(next.enabled));
    toggle.setAttribute("aria-label", next.enabled ? "Disable Paseo Bridge" : "Enable Paseo Bridge");
    viewButton.hidden = !next.enabled;

    if (!next.enabled) {
      status.textContent = "Off";
      status.className = "paseo-bridge-inline-status off";
    } else if (next.running) {
      status.textContent = "On · Running locally";
      status.className = "paseo-bridge-inline-status running";
    } else if (next.error) {
      status.textContent = "On · Needs attention";
      status.className = "paseo-bridge-inline-status error";
    } else {
      status.textContent = "On · Starting";
      status.className = "paseo-bridge-inline-status starting";
    }

    errorPanel.hidden = !next.error;
    errorPanel.textContent = next.error ?? "";
  };

  const setBusy = (next: boolean) => {
    busy = next;
    toggle.disabled = next;
    viewButton.disabled = next;
    row.classList.toggle("busy", next);
  };

  const load = async () => {
    try {
      const snapshot = await bridgeApi.snapshot();
      render(snapshot.bridge);
    } catch (cause) {
      errorPanel.hidden = false;
      errorPanel.textContent = String(cause);
    }
  };

  toggle.addEventListener("click", () => {
    if (busy) return;
    setBusy(true);
    void bridgeApi.setPaseoBridgeEnabled(!bridge?.enabled)
      .then(render)
      .catch((cause) => {
        errorPanel.hidden = false;
        errorPanel.textContent = String(cause);
      })
      .finally(() => setBusy(false));
  });

  viewButton.addEventListener("click", () => {
    if (busy || !bridge?.enabled) return;
    setBusy(true);
    void bridgeApi.openPaseoBridgeWindow()
      .catch((cause) => {
        errorPanel.hidden = false;
        errorPanel.textContent = String(cause);
      })
      .finally(() => setBusy(false));
  });

  void load();
}

function attach(): void {
  const oldHeading = Array.from(document.querySelectorAll<HTMLElement>(".page-header h1"))
    .find((heading) => heading.textContent?.trim() === "Paseo bridge API");
  const view = oldHeading?.closest<HTMLElement>(".content-scroll.narrow-content");
  if (view) buildIntegrationView(view);
}

function scheduleAttach(): void {
  if (attachFrame != null) return;
  attachFrame = window.requestAnimationFrame(() => {
    attachFrame = null;
    attach();
  });
}

export function installPaseoIntegrationControl(): void {
  scheduleAttach();
  const observer = new MutationObserver(scheduleAttach);
  observer.observe(document.body, { childList: true, subtree: true });
}

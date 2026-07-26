import { setCustomAccountEmail } from "./account-metadata";

const LABEL_EMAIL_PREFIX = "ai-subscription-tracker:opencode-email-by-label:";

function labelKey(label: string): string {
  return `${LABEL_EMAIL_PREFIX}${label.trim().toLocaleLowerCase()}`;
}

export function saveOpenCodeAccountEmail(accountId: string, label: string, email: string): void {
  const normalized = email.trim();
  setCustomAccountEmail(accountId, normalized);
  try {
    if (normalized) window.localStorage.setItem(labelKey(label), normalized);
  } catch {
    // The account remains usable if WebView storage is unavailable.
  }
}

export function getOpenCodeEmailByLabel(label: string): string | null {
  try {
    const value = window.localStorage.getItem(labelKey(label))?.trim();
    return value || null;
  } catch {
    return null;
  }
}

export function moveOpenCodeEmailLabel(previousLabel: string, nextLabel: string): string | null {
  const email = getOpenCodeEmailByLabel(previousLabel);
  if (!email) return getOpenCodeEmailByLabel(nextLabel);
  try {
    window.localStorage.setItem(labelKey(nextLabel), email);
    if (previousLabel.trim().toLocaleLowerCase() !== nextLabel.trim().toLocaleLowerCase()) {
      window.localStorage.removeItem(labelKey(previousLabel));
    }
  } catch {
    // Keep displaying the email from the current render even if storage is unavailable.
  }
  return email;
}

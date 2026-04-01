import { chromium } from "playwright";
import readline from "node:readline/promises";
import { stdin as input, stdout as output } from "node:process";
import { access, mkdir } from "node:fs/promises";
import path from "node:path";

const TARGET_APP_NAME = process.env.AUTH0_APP_NAME || "Vermanaut AI";
const APPS_URL =
  process.env.AUTH0_APPS_URL ||
  "https://manage.auth0.com/dashboard/us/dev-brfamxqos30shlb5/applications";

const VALUES = {
  callbacks:
    process.env.AUTH0_ALLOWED_CALLBACKS ||
    "http://localhost:3000/auth/callback, https://vermanaut.com/auth/callback",
  logouts:
    process.env.AUTH0_ALLOWED_LOGOUTS ||
    "http://localhost:3000, https://vermanaut.com",
  origins:
    process.env.AUTH0_ALLOWED_ORIGINS ||
    "http://localhost:3000, https://vermanaut.com",
};

const AUTH0_USERNAME = process.env.AUTH0_USERNAME || "";
const AUTH0_PASSWORD = process.env.AUTH0_PASSWORD || "";
const AUTH0_START_DELAY_MS = Number(process.env.AUTH0_START_DELAY_MS || "15000");
const AUTH0_FORCE_FRESH_LOGIN = process.env.AUTH0_FORCE_FRESH_LOGIN === "true";
const AUTH0_STORAGE_STATE_PATH =
  process.env.AUTH0_STORAGE_STATE_PATH ||
  path.resolve(process.cwd(), ".playwright-auth0-profile", "storage-state.json");
const AUTH0_BROWSER_CHANNEL = process.env.AUTH0_BROWSER_CHANNEL || undefined;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function hasStoredSession(filePath) {
  try {
    await access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function ensureParentDir(filePath) {
  await mkdir(path.dirname(filePath), { recursive: true });
}

async function isLoginScreen(page) {
  const emailField = page
    .locator('input[type="email"], input[name="email"], input[id*="email" i]')
    .first();
  const passwordField = page
    .locator('input[type="password"], input[name="password"], input[id*="password" i]')
    .first();

  const hasEmail = await emailField.isVisible().catch(() => false);
  const hasPassword = await passwordField.isVisible().catch(() => false);
  return hasEmail || hasPassword;
}

async function attemptCredentialLogin(page) {
  if (!AUTH0_USERNAME || !AUTH0_PASSWORD) {
    console.log("No AUTH0_USERNAME/AUTH0_PASSWORD provided. Manual login will be used.");
    return false;
  }

  const emailField = page
    .locator('input[type="email"], input[name="email"], input[id*="email" i]')
    .first();
  const passwordField = page
    .locator('input[type="password"], input[name="password"], input[id*="password" i]')
    .first();

  if (!(await emailField.isVisible().catch(() => false))) {
    return false;
  }

  await emailField.fill(AUTH0_USERNAME);
  if (await passwordField.isVisible().catch(() => false)) {
    await passwordField.fill(AUTH0_PASSWORD);
  }

  const submitted = await clickIfVisible(page.locator('button:has-text("Continue")')) ||
    await clickIfVisible(page.locator('button:has-text("Log In")')) ||
    await clickIfVisible(page.locator('button:has-text("Sign In")')) ||
    await clickIfVisible(page.locator('button[type="submit"]'));

  if (submitted) {
    console.log("Auth0 credentials submitted. Complete MFA on your phone if prompted.");
  }

  return submitted;
}

async function clickIfVisible(locator, timeout = 1500) {
  try {
    await locator.first().waitFor({ state: "visible", timeout });
    await locator.first().click({ timeout });
    return true;
  } catch {
    return false;
  }
}

async function openAppSettings(page) {
  await page.goto(APPS_URL, { waitUntil: "domcontentloaded" });

  if (AUTH0_START_DELAY_MS > 0) {
    await page.waitForTimeout(AUTH0_START_DELAY_MS);
  }

  if (await isLoginScreen(page)) {
    await attemptCredentialLogin(page);
  }

  // Give user time to complete any interactive login/MFA.
  console.log("If Auth0 asks you to log in or do MFA, complete that in the browser now.");

  for (let i = 0; i < 90; i++) {
    const appCard = page.getByRole("link", { name: new RegExp(TARGET_APP_NAME, "i") });
    const appText = page.getByText(new RegExp(TARGET_APP_NAME, "i"));
    if ((await appCard.count()) > 0) {
      await appCard.first().click();
      return;
    }
    if ((await appText.count()) > 0) {
      await appText.first().click();
      return;
    }
    await sleep(1000);
  }

  throw new Error("Could not find the Vermanaut AI application card. Open it manually, then rerun.");
}

async function goToSettingsTab(page) {
  const tabCandidates = [
    page.getByRole("tab", { name: /^Settings$/i }),
    page.getByRole("link", { name: /^Settings$/i }),
    page.locator("a").filter({ hasText: /^Settings$/i }),
  ];

  for (const tab of tabCandidates) {
    if (await clickIfVisible(tab)) {
      return;
    }
  }

  throw new Error("Could not open the Settings tab.");
}

async function fillFieldByLabel(page, labelText, value) {
  const label = page.locator("label", { hasText: labelText }).first();
  await label.waitFor({ state: "visible", timeout: 15000 });

  const id = await label.getAttribute("for");
  if (id) {
    const byId = page.locator(`#${id}`);
    if ((await byId.count()) > 0) {
      await byId.fill(value);
      return;
    }
  }

  const container = label.locator("xpath=ancestor::*[self::div or self::section][1]");
  const field = container.locator("textarea, input").first();
  await field.fill(value);
}

async function fillAllowedUrls(page) {
  // These fields are lower in the page.
  await page.mouse.wheel(0, 2500);
  await sleep(600);

  await fillFieldByLabel(page, "Allowed Callback URLs", VALUES.callbacks);
  await fillFieldByLabel(page, "Allowed Logout URLs", VALUES.logouts);
  await fillFieldByLabel(page, "Allowed Web Origins", VALUES.origins);
}

async function main() {
  const hasSession =
    !AUTH0_FORCE_FRESH_LOGIN && (await hasStoredSession(AUTH0_STORAGE_STATE_PATH));
  const browser = await chromium.launch({
    channel: AUTH0_BROWSER_CHANNEL,
    headless: false,
    slowMo: 80,
  });
  const context = await browser.newContext({
    viewport: { width: 1400, height: 950 },
    storageState: hasSession ? AUTH0_STORAGE_STATE_PATH : undefined,
  });
  const page = await context.newPage();

  try {
    await openAppSettings(page);
    await page.waitForLoadState("domcontentloaded");
    await goToSettingsTab(page);
    await page.waitForLoadState("domcontentloaded");
    await fillAllowedUrls(page);

    console.log("\nFilled these fields:");
    console.log(`- Allowed Callback URLs: ${VALUES.callbacks}`);
    console.log(`- Allowed Logout URLs:   ${VALUES.logouts}`);
    console.log(`- Allowed Web Origins:   ${VALUES.origins}`);
    console.log("\nPlease review in the browser and click Save manually.");

    const rl = readline.createInterface({ input, output });
    await rl.question("Press Enter here after you clicked Save to close browser...");
    rl.close();

    await ensureParentDir(AUTH0_STORAGE_STATE_PATH);
    await context.storageState({ path: AUTH0_STORAGE_STATE_PATH });
    console.log(`Saved Auth0 session: ${AUTH0_STORAGE_STATE_PATH}`);
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error("Auth0 assist failed:", err.message);
  process.exit(1);
});

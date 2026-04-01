import { chromium } from "playwright";
import readline from "node:readline/promises";
import { stdin as input, stdout as output } from "node:process";
import { access, mkdir } from "node:fs/promises";
import path from "node:path";

const TARGET = {
  appUrl:
    process.env.AUTH0_APP_URL ||
    "https://manage.auth0.com/dashboard/us/dev-brfamxqos30shlb5/applications/j8Jh9McUP44KuYmmDL2LJYq6Toqdf5EF/settings",
  callbacks:
    process.env.AUTH0_ALLOWED_CALLBACKS ||
    "http://localhost:3000/auth/callback, https://vermanaut.com/auth/callback",
  logouts:
    process.env.AUTH0_ALLOWED_LOGOUTS ||
    "http://localhost:3000, https://vermanaut.com",
  origins:
    process.env.AUTH0_ALLOWED_ORIGINS ||
    "http://localhost:3000, https://vermanaut.com",
  username: process.env.AUTH0_USERNAME || "",
  password: process.env.AUTH0_PASSWORD || "",
  startDelayMs: Number(process.env.AUTH0_START_DELAY_MS || "15000"),
  forceFreshLogin: process.env.AUTH0_FORCE_FRESH_LOGIN === "true",
  storageStatePath:
    process.env.AUTH0_STORAGE_STATE_PATH ||
    path.resolve(process.cwd(), ".playwright-auth0-profile", "storage-state.json"),
  browserChannel: process.env.AUTH0_BROWSER_CHANNEL || undefined,
};

const rl = readline.createInterface({ input, output });

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function pause(message) {
  await rl.question(`\n${message}\nPress Enter to continue...`);
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

async function clickIfVisible(page, selectors) {
  for (const selector of selectors) {
    const node = page.locator(selector).first();
    if (await node.isVisible().catch(() => false)) {
      await node.click({ timeout: 4000 });
      return true;
    }
  }
  return false;
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
  if (!TARGET.username || !TARGET.password) {
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

  await emailField.fill(TARGET.username);
  if (await passwordField.isVisible().catch(() => false)) {
    await passwordField.fill(TARGET.password);
  }

  const submitted = await clickIfVisible(page, [
    'button:has-text("Continue")',
    'button:has-text("Log In")',
    'button:has-text("Sign In")',
    'button[type="submit"]',
  ]);

  if (submitted) {
    console.log("Auth0 credentials submitted. Complete MFA on your phone if prompted.");
  }

  return submitted;
}

async function fillByLabel(page, text, value) {
  const label = page.locator("label", { hasText: text }).first();
  await label.waitFor({ state: "visible", timeout: 20000 });

  const id = await label.getAttribute("for");
  if (id) {
    const input = page.locator(`#${id}`);
    if ((await input.count()) > 0) {
      await input.fill(value);
      return;
    }
  }

  const container = label.locator("xpath=ancestor::*[self::div or self::section][1]");
  await container.locator("textarea, input").first().fill(value);
}

async function clickSave(page) {
  const saveCandidates = [
    page.getByRole("button", { name: /^Save Changes$/i }),
    page.getByRole("button", { name: /^Save$/i }),
    page.locator("button").filter({ hasText: /^Save$/i }),
  ];

  for (const btn of saveCandidates) {
    if ((await btn.count()) > 0) {
      const first = btn.first();
      await first.scrollIntoViewIfNeeded();
      await first.click({ timeout: 10000 });
      return true;
    }
  }
  return false;
}

async function main() {
  const hasSession =
    !TARGET.forceFreshLogin && (await hasStoredSession(TARGET.storageStatePath));
  const browser = await chromium.launch({
    channel: TARGET.browserChannel,
    headless: false,
    slowMo: 70,
  });
  const context = await browser.newContext({
    viewport: { width: 1500, height: 980 },
    storageState: hasSession ? TARGET.storageStatePath : undefined,
  });
  const page = await context.newPage();

  try {
    await page.goto(TARGET.appUrl, { waitUntil: "domcontentloaded" });

    if (TARGET.startDelayMs > 0) {
      await page.waitForTimeout(TARGET.startDelayMs);
    }

    if (await isLoginScreen(page)) {
      await attemptCredentialLogin(page);
      await pause("Approve Auth0 login/MFA in browser if prompted.");
    }

    console.log("Waiting for Auth0 settings form...");

    for (let i = 0; i < 120; i++) {
      if ((await page.locator("label", { hasText: "Allowed Callback URLs" }).count()) > 0) {
        break;
      }
      await wait(1000);
    }

    await page.mouse.wheel(0, 2200);
    await wait(500);

    await fillByLabel(page, "Allowed Callback URLs", TARGET.callbacks);
    await fillByLabel(page, "Allowed Logout URLs", TARGET.logouts);
    await fillByLabel(page, "Allowed Web Origins", TARGET.origins);

    const saved = await clickSave(page);
    if (!saved) {
      throw new Error("Could not find Save button. Please verify page state.");
    }

    await wait(2000);
    console.log("Auth0 application settings updated and save action triggered.");
    await ensureParentDir(TARGET.storageStatePath);
    await context.storageState({ path: TARGET.storageStatePath });
    console.log(`Saved Auth0 session: ${TARGET.storageStatePath}`);
    await wait(1500);
  } finally {
    rl.close();
    await browser.close();
  }
}

main().catch((err) => {
  console.error("Apply script failed:", err.message);
  process.exit(1);
});

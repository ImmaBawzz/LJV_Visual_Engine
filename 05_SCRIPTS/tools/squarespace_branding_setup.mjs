import { chromium } from "playwright";
import readline from "node:readline/promises";
import { stdin as input, stdout as output } from "node:process";
import { access, mkdir } from "node:fs/promises";
import path from "node:path";

const config = {
  editorUrl:
    process.env.SQ_EDITOR_URL ||
    "https://cricket-sunflower-yps8.squarespace.com/config/website",
  siteTitle: "Vermanaut AI",
  heroTitle: "Music Visuals. Creative Tools. AI-Engineered Releases.",
  heroSubtitle: "Built by Vermanaut AI - home of the LJV Visual Engine.",
  heroButtonOld: "Learn more",
  heroButtonNew: "See the Work",
  heroButtonLink: "/projects",
  removeSectionTitle: "Choose your plan",
  basicDescription:
    "Music visuals, creative tools, and AI-powered release engineering.",
  autoContinue: process.env.SQ_AUTO_CONTINUE === "true",
  startDelayMs: Number(process.env.SQ_START_DELAY_MS || "30000"),
  username: process.env.SQ_USERNAME || "",
  password: process.env.SQ_PASSWORD || "",
  storageStatePath:
    process.env.SQ_STORAGE_STATE_PATH ||
    path.resolve(process.cwd(), ".playwright-squarespace-profile", "storage-state.json"),
  forceFreshLogin: process.env.SQ_FORCE_FRESH_LOGIN === "true",
};

const rl = readline.createInterface({ input, output });

async function pause(message) {
  if (config.autoContinue) {
    console.log(`\n${message} (auto-continue enabled)`);
    return;
  }
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
  if (!config.username || !config.password) {
    console.log("No SQ_USERNAME/SQ_PASSWORD provided. Manual login will be used.");
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

  await emailField.fill(config.username);
  if (await passwordField.isVisible().catch(() => false)) {
    await passwordField.fill(config.password);
  }

  const submitted = await clickIfVisible(page, [
    'button:has-text("Log In")',
    'button:has-text("Sign In")',
    'button[type="submit"]',
    '[role="button"]:has-text("Log In")',
  ]);

  if (submitted) {
    console.log("Credentials submitted. Complete phone approval if prompted.");
  }

  return submitted;
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

function allScopes(page) {
  return [page, ...page.frames()];
}

async function domReplaceText(page, oldText, newText) {
  for (const scope of allScopes(page)) {
    const changed = await scope
      .evaluate(
        ({ oldText, newText }) => {
          const walker = document.createTreeWalker(document.body || document.documentElement, NodeFilter.SHOW_TEXT);
          let node;
          while ((node = walker.nextNode())) {
            if (!node.nodeValue || !node.nodeValue.includes(oldText)) continue;
            node.nodeValue = node.nodeValue.replace(oldText, newText);
            return true;
          }
          return false;
        },
        { oldText, newText },
      )
      .catch(() => false);

    if (changed) return true;
  }

  return false;
}

async function editTextNodeByVisibleText(page, oldText, newText) {
  for (const scope of allScopes(page)) {
    const node = scope.getByText(oldText, { exact: false }).first();
    if (!(await node.isVisible().catch(() => false))) continue;

    await node.click({ timeout: 10000 });
    await page.keyboard.press("Control+A");
    await page.keyboard.type(newText, { delay: 10 });
    return true;
  }

  return false;
}

async function tryFillFieldNearLabel(page, labelPattern, value) {
  const label = page.getByText(labelPattern, { exact: false }).first();
  if (!(await label.isVisible().catch(() => false))) return false;

  const group = label.locator("xpath=ancestor::*[self::div or self::label][1]");
  const inputField = group.locator("xpath=.//input|.//textarea").first();

  if (await inputField.isVisible().catch(() => false)) {
    await inputField.fill(value);
    return true;
  }

  const siblingField = label.locator("xpath=following::input[1] | following::textarea[1]").first();
  if (await siblingField.isVisible().catch(() => false)) {
    await siblingField.fill(value);
    return true;
  }

  return false;
}

async function replaceTextOnPage(page, oldText, newText) {
  try {
    let replaced = await editTextNodeByVisibleText(page, oldText, newText);
    if (!replaced) {
      replaced = await domReplaceText(page, oldText, newText);
    }
    if (!replaced) {
      throw new Error("text not found");
    }
    console.log(`Updated text: \"${oldText}\" -> \"${newText}\"`);
  } catch {
    console.log(`Skipped (not found): \"${oldText}\"`);
  }
}

async function removeSectionByHeading(page, sectionHeading) {
  for (const scope of allScopes(page)) {
    const removed = await scope
      .evaluate((headingText) => {
        const nodes = Array.from(document.querySelectorAll("h1,h2,h3,h4,h5,h6,p,span,div"));
        const hit = nodes.find((n) => (n.textContent || "").trim().includes(headingText));
        if (!hit) return false;

        const removable =
          hit.closest("section") || hit.closest("article") || hit.closest("div[data-section-id]") || hit.parentElement;
        if (!removable) return false;
        removable.remove();
        return true;
      }, sectionHeading)
      .catch(() => false);

    if (removed) {
      console.log(`Attempted delete section: \"${sectionHeading}\"`);
      return;
    }
  }

  console.log(`Skipped delete (section not found): \"${sectionHeading}\"`);
}

async function setHeaderTitle(page) {
  const headerTarget = page.getByText(/Vermanaut AI|Chimera AI|Site title/i).first();
  if (!(await headerTarget.isVisible().catch(() => false))) {
    console.log("Header target not visible. Skipping header title update.");
    return;
  }

  await headerTarget.click();
  await clickIfVisible(page, [
    'text="Content"',
    'button:has-text("Content")',
    '[aria-label*="Content"]',
  ]);

  const updated = await tryFillFieldNearLabel(page, /SITE TITLE|Site title/i, config.siteTitle);
  if (updated) {
    console.log(`Header site title set to: ${config.siteTitle}`);
  } else {
    console.log("Could not reliably find header Site title field. Skipping.");
  }
}

async function setBasicInfo(page) {
  const openedSettings = await clickIfVisible(page, [
    'nav >> text="Settings"',
    '[role="navigation"] >> text="Settings"',
    'text="Settings"',
  ]);

  if (!openedSettings) {
    console.log("Could not open Settings. Skipping Basic Information step.");
    return;
  }

  const openedBasic = await clickIfVisible(page, [
    'text="Basic Information"',
    'text="Business Information"',
  ]);

  if (!openedBasic) {
    console.log("Could not open Basic Information panel. Skipping.");
    return;
  }

  const setSiteTitle = await tryFillFieldNearLabel(page, /Site title|Website title/i, config.siteTitle);
  const setDesc = await tryFillFieldNearLabel(
    page,
    /Site description|Description|SEO description/i,
    config.basicDescription,
  );

  console.log(`Basic Information updated: title=${setSiteTitle}, description=${setDesc}`);
}

async function setHeroButton(page) {
  for (const scope of allScopes(page)) {
    const changed = await scope
      .evaluate(({ oldText, newText }) => {
        const candidates = Array.from(document.querySelectorAll("button,a,[role='button']"));
        const hit = candidates.find((el) => (el.textContent || "").trim().toLowerCase().includes(oldText.toLowerCase()));
        if (!hit) return false;

        hit.textContent = newText;
        return true;
      }, { oldText: config.heroButtonOld, newText: config.heroButtonNew })
      .catch(() => false);

    if (changed) {
      const linkUpdated = await tryFillFieldNearLabel(page, /Link|URL|Web address/i, config.heroButtonLink);
      console.log(`Hero button updated. Link updated: ${linkUpdated}`);
      return;
    }
  }

  console.log("Hero button not found. Skipping button update.");
}

async function savePage(page) {
  const saved = await clickIfVisible(page, [
    'button:has-text("Save")',
    '[aria-label="Save"]',
    'text="SAVE"',
  ]);

  if (saved) {
    console.log("Save clicked.");
  } else {
    console.log("Could not find Save button. Please click Save manually.");
  }
}

async function main() {
  const browserChannel = process.env.SQ_BROWSER_CHANNEL || undefined;
  const browser = await chromium.launch({
    channel: browserChannel,
    headless: false,
  });

  const hasSession = !config.forceFreshLogin && (await hasStoredSession(config.storageStatePath));
  if (hasSession) {
    console.log(`Using saved session: ${config.storageStatePath}`);
  } else if (config.forceFreshLogin) {
    console.log("Fresh login forced (SQ_FORCE_FRESH_LOGIN=true).");
  } else {
    console.log("No saved session found. Login + MFA approval will be required.");
  }

  const context = await browser.newContext({
    viewport: { width: 1600, height: 900 },
    storageState: hasSession ? config.storageStatePath : undefined,
  });

  const page = await context.newPage();
  await page.goto(config.editorUrl, { waitUntil: "domcontentloaded" });

  if (config.startDelayMs > 0) {
    console.log(`Waiting ${config.startDelayMs}ms for login/editor readiness...`);
    await page.waitForTimeout(config.startDelayMs);
  }

  if (await isLoginScreen(page)) {
    await attemptCredentialLogin(page);
    await pause(
      "If prompted, approve login on your phone, then wait for the Squarespace editor to fully load.",
    );
  }

  await pause(
    "Log into Squarespace if prompted, then open the page editor where hero content is visible.",
  );

  await setHeaderTitle(page);
  await replaceTextOnPage(page, "Time to let your brand shine", config.heroTitle);
  await replaceTextOnPage(
    page,
    "Welcome people to your site with an introduction that's short, sweet, and sounds like you.",
    config.heroSubtitle,
  );
  await setHeroButton(page);
  await removeSectionByHeading(page, config.removeSectionTitle);

  await setBasicInfo(page);
  await savePage(page);

  await ensureParentDir(config.storageStatePath);
  await context.storageState({ path: config.storageStatePath });
  console.log(`Saved authenticated session: ${config.storageStatePath}`);

  console.log("\nBranding automation pass complete.");
  await pause("Review the page, make any visual adjustments, then close the browser.");

  await context.close();
  rl.close();
}

main().catch(async (err) => {
  console.error("Automation failed:", err);
  rl.close();
  process.exit(1);
});

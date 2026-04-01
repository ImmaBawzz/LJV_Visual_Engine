import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..", "..");
const manifestPath = path.resolve(repoRoot, "01_CONFIG", "source_integrity_manifest.json");

function toPosix(p) {
  return p.replaceAll("\\", "/");
}

async function sha256ForFile(absPath) {
  const data = await readFile(absPath);
  return createHash("sha256").update(data).digest("hex");
}

async function main() {
  const manifestRaw = await readFile(manifestPath, "utf8");
  const manifest = JSON.parse(manifestRaw);

  if (manifest.algorithm !== "sha256" || typeof manifest.files !== "object" || !manifest.files) {
    throw new Error("01_CONFIG/source_integrity_manifest.json is invalid.");
  }

  const mismatches = [];
  for (const [relPath, expectedHash] of Object.entries(manifest.files)) {
    const normalized = toPosix(relPath);
    const absPath = path.resolve(repoRoot, normalized);

    let actualHash;
    try {
      actualHash = await sha256ForFile(absPath);
    } catch (error) {
      mismatches.push({ file: normalized, reason: `missing/unreadable: ${error.message}` });
      continue;
    }

    if (actualHash !== expectedHash) {
      mismatches.push({ file: normalized, reason: "hash mismatch" });
    }
  }

  if (mismatches.length > 0) {
    console.error("Source integrity verification failed:");
    for (const item of mismatches) {
      console.error(`- ${item.file}: ${item.reason}`);
    }
    process.exit(1);
  }

  console.log("Source integrity verification passed.");
}

main().catch((error) => {
  console.error("Failed to verify source integrity:", error.message);
  process.exit(1);
});

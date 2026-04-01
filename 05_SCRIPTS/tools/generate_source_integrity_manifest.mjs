import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..", "..");

const targetsPath = path.resolve(repoRoot, "01_CONFIG", "source_integrity_targets.json");
const manifestPath = path.resolve(repoRoot, "01_CONFIG", "source_integrity_manifest.json");

function toPosix(p) {
  return p.replaceAll("\\", "/");
}

async function sha256ForFile(absPath) {
  const data = await readFile(absPath);
  return createHash("sha256").update(data).digest("hex");
}

async function main() {
  const targetsRaw = await readFile(targetsPath, "utf8");
  const targets = JSON.parse(targetsRaw);

  if (!Array.isArray(targets.files) || targets.files.length === 0) {
    throw new Error("01_CONFIG/source_integrity_targets.json must contain a non-empty files array.");
  }

  const files = {};
  for (const relPath of targets.files) {
    const normalized = toPosix(relPath);
    const absPath = path.resolve(repoRoot, normalized);
    files[normalized] = await sha256ForFile(absPath);
  }

  const manifest = {
    schemaVersion: 1,
    generatedAtUtc: new Date().toISOString(),
    algorithm: "sha256",
    files,
  };

  await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  console.log(`Wrote integrity manifest: ${toPosix(path.relative(repoRoot, manifestPath))}`);
}

main().catch((error) => {
  console.error("Failed to generate source integrity manifest:", error.message);
  process.exit(1);
});

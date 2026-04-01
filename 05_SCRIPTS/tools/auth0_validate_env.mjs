const REQUIRED = [
  "AUTH0_DOMAIN",
  "AUTH0_MGMT_CLIENT_ID",
  "AUTH0_MGMT_CLIENT_SECRET",
  "AUTH0_APP_CLIENT_ID",
];

const APPLY_RECOMMENDED = [
  "AUTH0_ALLOWED_CALLBACKS",
  "AUTH0_ALLOWED_LOGOUTS",
  "AUTH0_ALLOWED_ORIGINS",
];

function isBlank(value) {
  return value === undefined || value === null || String(value).trim() === "";
}

function printList(header, keys, valuePrefix = "") {
  console.log(header);
  for (const key of keys) {
    if (valuePrefix) {
      console.log(`- ${key}: ${valuePrefix}`);
    } else {
      console.log(`- ${key}`);
    }
  }
}

function main() {
  const missingRequired = REQUIRED.filter((key) => isBlank(process.env[key]));

  const configuredApplyValues = APPLY_RECOMMENDED.filter(
    (key) => !isBlank(process.env[key]),
  );

  if (missingRequired.length > 0) {
    printList("Missing required Auth0 API environment variables:", missingRequired);
    console.log("\nSet these in your .env before running auth0:check:api or auth0:apply:api.");
    process.exit(1);
  }

  console.log("Auth0 API required environment variables are configured.");

  if (configuredApplyValues.length === 0) {
    printList(
      "No apply target variables are currently set (optional for check, recommended for apply):",
      APPLY_RECOMMENDED,
      "(not set)",
    );
    console.log("\nYou can still run auth0:check:api. For auth0:apply:api, set at least one of the values above.");
    process.exit(0);
  }

  printList("Apply target variables detected:", configuredApplyValues);
  console.log("\nEnvironment validation passed.");
}

main();

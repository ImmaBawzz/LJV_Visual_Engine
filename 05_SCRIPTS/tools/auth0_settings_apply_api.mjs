const required = [
  "AUTH0_DOMAIN",
  "AUTH0_MGMT_CLIENT_ID",
  "AUTH0_MGMT_CLIENT_SECRET",
  "AUTH0_APP_CLIENT_ID",
];

for (const key of required) {
  if (!process.env[key]) {
    console.error(`Missing required environment variable: ${key}`);
    process.exit(1);
  }
}

const domain = process.env.AUTH0_DOMAIN;
const mgmtClientId = process.env.AUTH0_MGMT_CLIENT_ID;
const mgmtClientSecret = process.env.AUTH0_MGMT_CLIENT_SECRET;
const appClientId = process.env.AUTH0_APP_CLIENT_ID;

const allowedCallbacks = (process.env.AUTH0_ALLOWED_CALLBACKS || "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);
const allowedLogouts = (process.env.AUTH0_ALLOWED_LOGOUTS || "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);
const allowedOrigins = (process.env.AUTH0_ALLOWED_ORIGINS || "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);

async function getManagementToken() {
  const res = await fetch(`https://${domain}/oauth/token`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      client_id: mgmtClientId,
      client_secret: mgmtClientSecret,
      audience: `https://${domain}/api/v2/`,
      grant_type: "client_credentials",
    }),
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Token request failed (${res.status}): ${body}`);
  }

  const data = await res.json();
  return data.access_token;
}

async function patchApplication(accessToken) {
  const payload = {};

  if (allowedCallbacks.length > 0) payload.callbacks = allowedCallbacks;
  if (allowedLogouts.length > 0) payload.allowed_logout_urls = allowedLogouts;
  if (allowedOrigins.length > 0) {
    payload.web_origins = allowedOrigins;
    payload.allowed_origins = allowedOrigins;
  }

  if (Object.keys(payload).length === 0) {
    throw new Error(
      "No settings to update. Set AUTH0_ALLOWED_CALLBACKS, AUTH0_ALLOWED_LOGOUTS, and/or AUTH0_ALLOWED_ORIGINS.",
    );
  }

  const res = await fetch(`https://${domain}/api/v2/clients/${appClientId}`, {
    method: "PATCH",
    headers: {
      authorization: `Bearer ${accessToken}`,
      "content-type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Client patch failed (${res.status}): ${body}`);
  }

  return res.json();
}

async function main() {
  const token = await getManagementToken();
  const updated = await patchApplication(token);

  const summary = {
    client_id: updated.client_id,
    name: updated.name,
    callbacks: updated.callbacks || [],
    allowed_logout_urls: updated.allowed_logout_urls || [],
    web_origins: updated.web_origins || [],
    allowed_origins: updated.allowed_origins || [],
  };

  console.log("Auth0 application settings updated via Management API:");
  console.log(JSON.stringify(summary, null, 2));
}

main().catch((err) => {
  console.error("Auth0 API apply failed:", err.message);
  process.exit(1);
});

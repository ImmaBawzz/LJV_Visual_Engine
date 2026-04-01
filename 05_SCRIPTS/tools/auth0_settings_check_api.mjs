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

async function fetchApplication(accessToken) {
  const res = await fetch(`https://${domain}/api/v2/clients/${appClientId}`, {
    method: "GET",
    headers: {
      authorization: `Bearer ${accessToken}`,
      "content-type": "application/json",
    },
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Client read failed (${res.status}): ${body}`);
  }

  return res.json();
}

async function main() {
  const token = await getManagementToken();
  const app = await fetchApplication(token);

  const summary = {
    client_id: app.client_id,
    name: app.name,
    callbacks: app.callbacks || [],
    allowed_logout_urls: app.allowed_logout_urls || [],
    web_origins: app.web_origins || [],
    allowed_origins: app.allowed_origins || [],
  };

  console.log("Current Auth0 application settings:");
  console.log(JSON.stringify(summary, null, 2));
}

main().catch((err) => {
  console.error("Auth0 API check failed:", err.message);
  process.exit(1);
});

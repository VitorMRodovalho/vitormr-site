// Thin Worker wrapping the static-asset bundle in dist/.
//
// Responsibilities:
//   1. 301-redirect www.vitormr.dev to the apex (Google flagged the dual
//      hostname as duplicate content).
//   2. Serve curated Cloudflare Web Analytics aggregates as JSON on
//      /admin/api/metrics. /admin/* is gated by CF Access at the edge,
//      so this endpoint inherits the gate — no auth logic in Worker.
//   3. Add easter-egg HTTP header X-Engineering-Note on every non-redirect
//      response (v26).
//
// All other requests fall through to env.ASSETS, which serves dist/.
// Sibling subdomains (orenu, panorama, meridianiq, nucleoia) bind to
// different Workers and never reach this script.

export default {
  async fetch(req, env, ctx) {
    const url = new URL(req.url);

    if (url.hostname === "www.vitormr.dev") {
      url.hostname = "vitormr.dev";
      return Response.redirect(url.toString(), 301);
    }

    if (url.pathname === "/admin/api/metrics") {
      return handleAdminMetrics(env, ctx);
    }

    const response = await env.ASSETS.fetch(req);
    // Easter egg — visible to anyone who inspects HTTP response headers.
    // ASCII-only per RFC 7230; some intermediaries mangle non-ASCII bytes.
    const newResponse = new Response(response.body, response);
    newResponse.headers.set(
      "X-Engineering-Note",
      '"It is what it is until it isn\'t." -- Bobby Axelrod, Billions',
    );
    return newResponse;
  },
};

// ---------------------------------------------------------------------------
// /admin/api/metrics — Cloudflare Web Analytics aggregates via GraphQL.
//
// Cached 5 min in the Worker Cache API to avoid burning rate budget on
// back-to-back refreshes. Pattern mirrors sarah-rodovalho-site
// (commit 342e555).
// ---------------------------------------------------------------------------

const CACHE_TTL_SECONDS = 300;
const CACHE_KEY = "https://internal-cache/admin-metrics/v1";

async function handleAdminMetrics(env, ctx) {
  const cache = caches.default;
  const cacheKey = new Request(CACHE_KEY, { method: "GET" });
  const cached = await cache.match(cacheKey);
  if (cached) return cached;

  let payload;
  try {
    const raw = await fetchAnalytics(env);
    payload = transformAnalytics(raw, env);
  } catch (err) {
    return jsonResponse({ error: String(err.message || err) }, 502);
  }

  const response = jsonResponse(payload, 200, {
    "cache-control": `private, max-age=${CACHE_TTL_SECONDS}`,
  });
  ctx.waitUntil(cache.put(cacheKey, response.clone()));
  return response;
}

function jsonResponse(body, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "x-content-type-options": "nosniff",
      ...extraHeaders,
    },
  });
}

const GRAPHQL_QUERY = `
query SiteMetrics(
  $accountTag: string!,
  $siteTag: string!,
  $now: Time!,
  $minus7d: Time!,
  $minus14d: Time!,
  $minus30d: Time!,
  $minus60d: Time!,
  $launch: Date!
) {
  viewer {
    accounts(filter: { accountTag: $accountTag }) {
      last7d: rumPageloadEventsAdaptiveGroups(
        limit: 1
        filter: { siteTag: $siteTag, datetime_geq: $minus7d, datetime_lt: $now }
      ) { count sum { visits } }

      prior7d: rumPageloadEventsAdaptiveGroups(
        limit: 1
        filter: { siteTag: $siteTag, datetime_geq: $minus14d, datetime_lt: $minus7d }
      ) { count sum { visits } }

      last30d: rumPageloadEventsAdaptiveGroups(
        limit: 1
        filter: { siteTag: $siteTag, datetime_geq: $minus30d, datetime_lt: $now }
      ) { count sum { visits } }

      prior30d: rumPageloadEventsAdaptiveGroups(
        limit: 1
        filter: { siteTag: $siteTag, datetime_geq: $minus60d, datetime_lt: $minus30d }
      ) { count sum { visits } }

      allTime: rumPageloadEventsAdaptiveGroups(
        limit: 1
        filter: { siteTag: $siteTag, date_geq: $launch }
      ) { count sum { visits } }

      daily: rumPageloadEventsAdaptiveGroups(
        limit: 60
        filter: { siteTag: $siteTag, datetime_geq: $minus30d }
        orderBy: [date_ASC]
      ) {
        count
        sum { visits }
        dimensions { date }
      }

      topPages: rumPageloadEventsAdaptiveGroups(
        limit: 15
        filter: { siteTag: $siteTag, datetime_geq: $minus30d }
        orderBy: [count_DESC]
      ) {
        count
        sum { visits }
        dimensions { requestPath }
      }

      topCountries: rumPageloadEventsAdaptiveGroups(
        limit: 10
        filter: { siteTag: $siteTag, datetime_geq: $minus30d }
        orderBy: [count_DESC]
      ) {
        count
        sum { visits }
        dimensions { countryName }
      }

      topReferrers: rumPageloadEventsAdaptiveGroups(
        limit: 10
        filter: { siteTag: $siteTag, datetime_geq: $minus30d }
        orderBy: [count_DESC]
      ) {
        count
        sum { visits }
        dimensions { refererHost }
      }
    }
  }
}
`;

async function fetchAnalytics(env) {
  if (!env.CF_ANALYTICS_TOKEN) {
    throw new Error("CF_ANALYTICS_TOKEN is not set");
  }
  if (!env.CF_ACCOUNT_ID || !env.CF_WEB_ANALYTICS_SITE_TAG) {
    throw new Error("CF_ACCOUNT_ID or CF_WEB_ANALYTICS_SITE_TAG is missing");
  }

  const now = new Date();
  const variables = {
    accountTag: env.CF_ACCOUNT_ID,
    siteTag: env.CF_WEB_ANALYTICS_SITE_TAG,
    now: now.toISOString(),
    minus7d: offsetISO(now, -7),
    minus14d: offsetISO(now, -14),
    minus30d: offsetISO(now, -30),
    minus60d: offsetISO(now, -60),
    launch: env.CF_SITE_LAUNCH_DATE || "2026-03-19",
  };

  const resp = await fetch("https://api.cloudflare.com/client/v4/graphql", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      authorization: `Bearer ${env.CF_ANALYTICS_TOKEN}`,
    },
    body: JSON.stringify({ query: GRAPHQL_QUERY, variables }),
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`CF GraphQL HTTP ${resp.status}: ${text.slice(0, 240)}`);
  }
  const json = await resp.json();
  if (json.errors && json.errors.length > 0) {
    const messages = json.errors.map((e) => e.message).join("; ");
    throw new Error(`CF GraphQL errors: ${messages.slice(0, 240)}`);
  }
  return json;
}

function offsetISO(base, days) {
  const d = new Date(base);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString();
}

function transformAnalytics(raw, env) {
  const account = raw?.data?.viewer?.accounts?.[0] ?? {};

  const totalsBlock = (groups) => {
    const row = groups?.[0];
    return {
      views: row?.count ?? 0,
      visits: row?.sum?.visits ?? 0,
    };
  };

  const last7d = totalsBlock(account.last7d);
  const prior7d = totalsBlock(account.prior7d);
  const last30d = totalsBlock(account.last30d);
  const prior30d = totalsBlock(account.prior30d);
  const allTime = totalsBlock(account.allTime);

  const daily = (account.daily ?? []).map((row) => ({
    date: row?.dimensions?.date ?? null,
    views: row?.count ?? 0,
    visits: row?.sum?.visits ?? 0,
  }));

  const groupedList = (groups, dimKey) =>
    (groups ?? []).map((row) => ({
      label: row?.dimensions?.[dimKey] ?? "(unknown)",
      views: row?.count ?? 0,
      visits: row?.sum?.visits ?? 0,
    }));

  return {
    siteTag: env.CF_WEB_ANALYTICS_SITE_TAG,
    launch: env.CF_SITE_LAUNCH_DATE || "2026-03-19",
    generatedAt: new Date().toISOString(),
    totals: {
      last7d,
      prior7d,
      last30d,
      prior30d,
      allTime,
      delta7d: percentDelta(last7d.visits, prior7d.visits),
      delta30d: percentDelta(last30d.visits, prior30d.visits),
    },
    daily,
    topPages: groupedList(account.topPages, "requestPath"),
    topCountries: groupedList(account.topCountries, "countryName"),
    topReferrers: groupedList(account.topReferrers, "refererHost"),
  };
}

function percentDelta(current, prior) {
  if (!prior || prior === 0) return null;
  return Math.round(((current - prior) / prior) * 100);
}

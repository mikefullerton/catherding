interface Env {
  DB: D1Database;
  ASSETS: Fetcher;
  API_BACKEND_URL: string;
  MAIN_SITE_URL: string;
  ADMIN_SITE_URL: string;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    // Dashboard API routes
    if (url.pathname.startsWith("/api/dashboard/")) {
      return handleDashboardApi(url, env);
    }

    // Serve SPA
    const response = await env.ASSETS.fetch(request);
    if (response.status === 404) {
      return env.ASSETS.fetch(new URL("/index.html", request.url));
    }
    return response;
  },

  async scheduled(event: ScheduledEvent, env: Env, ctx: ExecutionContext): Promise<void> {
    const cron = event.cron;

    if (cron === "*/1 * * * *") {
      ctx.waitUntil(runHealthChecks(env));
    }

    if (cron === "*/5 * * * *") {
      ctx.waitUntil(syncDeployments(env));
    }

    if (cron === "0 * * * *") {
      ctx.waitUntil(rollupMetrics(env));
    }
  },
};

async function handleDashboardApi(url: URL, env: Env): Promise<Response> {
  const path = url.pathname.replace("/api/dashboard", "");

  if (path === "/health-checks") {
    const results = await env.DB.prepare(
      "SELECT * FROM health_checks ORDER BY checked_at DESC LIMIT 100",
    ).all();
    return Response.json({ checks: results.results });
  }

  if (path === "/incidents") {
    const results = await env.DB.prepare(
      "SELECT * FROM incidents ORDER BY started_at DESC LIMIT 50",
    ).all();
    return Response.json({ incidents: results.results });
  }

  if (path === "/deployments") {
    const results = await env.DB.prepare(
      "SELECT * FROM deployments ORDER BY deployed_at DESC LIMIT 50",
    ).all();
    return Response.json({ deployments: results.results });
  }

  if (path === "/uptime") {
    const results = await env.DB.prepare(`
      SELECT service,
             COUNT(*) as total,
             SUM(CASE WHEN status = 'up' THEN 1 ELSE 0 END) as up_count,
             ROUND(SUM(CASE WHEN status = 'up' THEN 1.0 ELSE 0.0 END) / COUNT(*) * 100, 2) as uptime_pct
      FROM health_checks
      WHERE checked_at > datetime('now', '-24 hours')
      GROUP BY service
    `).all();
    return Response.json({ uptime: results.results });
  }

  return Response.json({ error: "Not found" }, { status: 404 });
}

async function runHealthChecks(env: Env): Promise<void> {
  const services = [
    { name: "backend", url: `${env.API_BACKEND_URL}/api/health` },
    { name: "main", url: env.MAIN_SITE_URL },
    { name: "admin", url: env.ADMIN_SITE_URL },
  ];

  for (const service of services) {
    let status = "down";
    let responseTime = 0;

    try {
      const start = Date.now();
      const res = await fetch(service.url, { signal: AbortSignal.timeout(10_000) });
      responseTime = Date.now() - start;
      status = res.ok ? "up" : "degraded";
    } catch {
      status = "down";
    }

    await env.DB.prepare(
      "INSERT INTO health_checks (service, status, response_time_ms, checked_at) VALUES (?, ?, ?, datetime('now'))",
    )
      .bind(service.name, status, responseTime)
      .run();

    // Check for incident creation/resolution
    if (status === "down") {
      const openIncident = await env.DB.prepare(
        "SELECT id FROM incidents WHERE service = ? AND resolved_at IS NULL LIMIT 1",
      )
        .bind(service.name)
        .first();

      if (!openIncident) {
        await env.DB.prepare(
          "INSERT INTO incidents (service, status, started_at) VALUES (?, 'investigating', datetime('now'))",
        )
          .bind(service.name)
          .run();
      }
    } else if (status === "up") {
      await env.DB.prepare(
        "UPDATE incidents SET resolved_at = datetime('now'), status = 'resolved' WHERE service = ? AND resolved_at IS NULL",
      )
        .bind(service.name)
        .run();
    }
  }
}

async function syncDeployments(env: Env): Promise<void> {
  // Placeholder: in production, query Railway and Cloudflare APIs for deployment status
  // For now, no-op — deployments are recorded by the deploy command
}

async function rollupMetrics(env: Env): Promise<void> {
  // Roll up hourly metrics from health checks
  const hour = new Date();
  hour.setMinutes(0, 0, 0);

  const services = ["backend", "main", "admin", "dashboard"];

  for (const service of services) {
    const stats = await env.DB.prepare(`
      SELECT
        COUNT(*) as check_count,
        SUM(CASE WHEN status = 'up' THEN 1 ELSE 0 END) as up_count,
        AVG(response_time_ms) as avg_response_time,
        MAX(response_time_ms) as max_response_time
      FROM health_checks
      WHERE service = ? AND checked_at >= datetime(?, '-1 hour') AND checked_at < datetime(?)
    `)
      .bind(service, hour.toISOString(), hour.toISOString())
      .first();

    if (stats && (stats.check_count as number) > 0) {
      await env.DB.prepare(`
        INSERT INTO metrics (service, period, check_count, up_count, avg_response_time, max_response_time, recorded_at)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
      `)
        .bind(
          service,
          "hourly",
          stats.check_count,
          stats.up_count,
          stats.avg_response_time,
          stats.max_response_time,
        )
        .run();
    }
  }
}

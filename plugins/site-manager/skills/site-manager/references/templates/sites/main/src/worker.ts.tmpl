interface Env {
  API_BACKEND_URL: string;
  ASSETS: Fetcher;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    // Proxy API and auth requests to backend
    if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/auth/")) {
      const backendUrl = new URL(url.pathname + url.search, env.API_BACKEND_URL);
      const headers = new Headers(request.headers);
      headers.set("X-Forwarded-For", request.headers.get("cf-connecting-ip") ?? "");
      headers.set("X-Forwarded-Proto", "https");

      return fetch(backendUrl.toString(), {
        method: request.method,
        headers,
        body: request.body,
      });
    }

    // Serve static assets, fall back to index.html for SPA routing
    const response = await env.ASSETS.fetch(request);
    if (response.status === 404) {
      return env.ASSETS.fetch(new URL("/index.html", request.url));
    }
    return response;
  },
};

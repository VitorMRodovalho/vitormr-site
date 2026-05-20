// Thin Worker wrapping the static-asset bundle in dist/.
//
// Sole responsibility: 301-redirect www.vitormr.dev to the apex. Both
// hostnames are bound to this Worker via Custom Domains, so without an
// explicit redirect they serve identical content under different URLs —
// Google flagged this pattern as duplicate content. All other requests
// fall through to env.ASSETS, which serves dist/ exactly as the prior
// static-only deployment did. Sibling subdomains (orenu, panorama,
// meridianiq, nucleoia) are bound to different Workers and never reach
// this script.

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (url.hostname === "www.vitormr.dev") {
      url.hostname = "vitormr.dev";
      return Response.redirect(url.toString(), 301);
    }
    const response = await env.ASSETS.fetch(req);
    // Easter egg — visible to anyone who inspects HTTP response headers.
    // ASCII-only per RFC 7230; some intermediaries mangle non-ASCII bytes.
    const newResponse = new Response(response.body, response);
    newResponse.headers.set(
      "X-Engineering-Note",
      "\"It is what it is until it isn't.\" -- Bobby Axelrod, Billions",
    );
    return newResponse;
  },
};

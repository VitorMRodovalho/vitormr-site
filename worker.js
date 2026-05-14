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
    return env.ASSETS.fetch(req);
  },
};

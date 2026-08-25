"""Cache control middleware for ComfyUI server"""

import re

from aiohttp import web
from typing import Callable, Awaitable

# Time in seconds
ONE_HOUR: int = 3600
ONE_DAY: int = 86400
ONE_YEAR: int = 31536000

# Frontend build assets carry an 8-char content hash in the filename (e.g.
# /assets/index-vtow2bzT.js), so they can be cached forever. The hash must
# contain an uppercase letter or digit so plain words like the "node-map" in
# sorted-custom-node-map.json don't count as a hash.
HASHED_ASSET_RE = re.compile(r"^/assets/[^/]+-(?=[a-z_-]{0,7}[A-Z0-9])[A-Za-z0-9_-]{8}\.[a-z0-9]+$")
IMG_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".ppm",
    ".bmp",
    ".pgm",
    ".tif",
    ".tiff",
    ".webp",
)


@web.middleware
async def cache_control(
    request: web.Request, handler: Callable[[web.Request], Awaitable[web.Response]]
) -> web.Response:
    """Cache control middleware that sets appropriate cache headers based on file type and response status"""
    response: web.Response = await handler(request)

    if response.status == 200 and HASHED_ASSET_RE.match(request.path):
        response.headers.setdefault(
            "Cache-Control", f"public, max-age={ONE_YEAR}, immutable"
        )
        return response

    path_filename = request.path.rsplit("/", 1)[-1]
    is_entry_point = path_filename.startswith("index") and path_filename.endswith(
        ".json"
    )

    if request.path.endswith(".js") or request.path.endswith(".css") or is_entry_point:
        response.headers.setdefault("Cache-Control", "no-store")
        return response

    if request.path.endswith((".woff2", ".woff", ".ttf")):
        response.headers.setdefault("Cache-Control", f"public, max-age={ONE_DAY}")
        return response

    # Early return for non-image files - no cache headers needed
    if not request.path.lower().endswith(IMG_EXTENSIONS):
        return response

    # Handle image files
    if response.status == 404:
        response.headers.setdefault("Cache-Control", f"public, max-age={ONE_HOUR}")
    elif response.status in (200, 201, 202, 203, 204, 205, 206, 301, 308):
        # Success responses and permanent redirects - cache for 1 day
        response.headers.setdefault("Cache-Control", f"public, max-age={ONE_DAY}")
    elif response.status in (302, 303, 307):
        # Temporary redirects - no cache
        response.headers.setdefault("Cache-Control", "no-cache")
    # Note: 304 Not Modified falls through - no cache headers set

    return response

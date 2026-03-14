import os

from werkzeug.wrappers import Response

import frappe
from frappe.website.page_renderers.base_renderer import BaseRenderer


class ServiceWorkerRenderer(BaseRenderer):
    """
    /sw.js ni to'g'ri application/javascript MIME type va
    Service-Worker-Allowed: / header bilan serve qiluvchi renderer.
    """

    def can_render(self):
        return self.path == "sw.js"

    def render(self):
        sw_file = os.path.join(frappe.get_app_path("ury"), "..", "public", "pos", "sw.js")
        sw_file = os.path.normpath(sw_file)

        try:
            with open(sw_file, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            return Response("/* sw.js not found */", status=404, mimetype="application/javascript")

        response = Response(content, status=200, mimetype="application/javascript")
        response.headers["Service-Worker-Allowed"] = "/"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response

"""
CDP-based Perception Plugin — uses Chrome DevTools Protocol accessibility tree
to extract real interactive elements from the page (ported from V1.py).
"""

from typing import Annotated, List, Dict
from semantic_kernel.functions import kernel_function
from app.plugins.browser_plugin import BrowserPlugin

INTERACTIVE_ROLES = {
    "button", "textbox", "link", "checkbox", "radio", "combobox",
    "menuitem", "tab", "searchbox", "slider", "spinbutton",
}


def _collect(node, node_map, results, idx_counter=None):
    if idx_counter is None:
        idx_counter = [1]

    role_obj = node.get("role", {})
    role = role_obj.get("value") if isinstance(role_obj, dict) else role_obj

    if role in INTERACTIVE_ROLES:
        name_obj = node.get("name", {})
        name = name_obj.get("value") if isinstance(name_obj, dict) else name_obj
        results.append({
            "id": idx_counter[0],
            "role": role,
            "label": name or "",
        })
        idx_counter[0] += 1

    for child_id in node.get("childIds", []):
        if child_id in node_map:
            _collect(node_map[child_id], node_map, results, idx_counter)


class CDPPerceptionPlugin:
    """Extracts interactive elements via CDP accessibility tree."""

    def __init__(self, browser_plugin: BrowserPlugin):
        self.browser_plugin = browser_plugin
        self._last_elements: List[Dict] = []

    @kernel_function(
        description="Observes the current page using the CDP accessibility tree and returns interactive elements with IDs."
    )
    async def observe(self) -> str:
        bp = self.browser_plugin
        await bp.ensure_initialized()
        page = bp.page

        try:
            cdp = await page.context.new_cdp_session(page)
            response = await cdp.send("Accessibility.getFullAXTree")
            await cdp.detach()
        except Exception as e:
            return f"[CDP Error] {e}"

        nodes = response.get("nodes", [])
        if not nodes:
            return "[No accessibility nodes found]"

        node_map = {n["nodeId"]: n for n in nodes}
        all_child_ids = set()
        for n in nodes:
            all_child_ids.update(n.get("childIds", []))
        root_nodes = [n for n in nodes if n["nodeId"] not in all_child_ids]
        root = root_nodes[0] if root_nodes else nodes[0]

        elements = []
        _collect(root, node_map, elements)
        self._last_elements = elements

        if not elements:
            return "[No interactive elements found on page]"

        lines = [f"[{el['id']}] {el['role']} — {el['label']}" for el in elements]
        header = f"Found {len(elements)} interactive elements:\n"
        return header + "\n".join(lines)

    @property
    def last_elements(self) -> List[Dict]:
        return list(self._last_elements)

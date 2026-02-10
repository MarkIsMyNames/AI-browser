"""
AI Browser - DOM Distillation & Set-of-Marks

Features:
- Extracts interactive elements from accessibility tree via CDP
- Strips non-essential HTML (scripts, styles, SVG) for cleaner parsing
- Captures screenshot with numbered bounding boxes on elements
"""

import re
import json
from io import BytesIO
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont

# Accessibility roles that represent interactive elements
INTERACTIVE_ROLES = {
    "button", "textbox", "link", "checkbox",
    "radio", "combobox", "menuitem", "tab",
    "searchbox", "slider", "switch"  # noqa: spelling
}

# Regex patterns for DOM distillation
STRIP_PATTERN = re.compile(
    r"<(script|style|noscript|head|meta|link|svg|path)[\s\S]*?</\1>"
    r"|<(script|style|meta|link|br|hr|img)[^>]*/?>|<!--[\s\S]*?-->",
    re.IGNORECASE
)

WHITESPACE_PATTERN = re.compile(r"\s{2,}")

INTERACTIVE_TAG_PATTERN = re.compile(
    r"<(a|button|input|select|textarea)\b([^>]*)>",
    re.IGNORECASE
)

ATTR_PATTERN = re.compile(
    r'\b(aria-label|placeholder|title|alt|name|id|type|href|value)\s*=\s*["\']([^"\']*)["\']',
    re.IGNORECASE
)


def get_node_value(ax_node, key, default=""):
    """Extract value from CDP node property."""
    obj = ax_node.get(key, {})
    if isinstance(obj, dict):
        return obj.get("value", default)
    return obj if obj else default


def collect_elements(ax_node, nodes_map, cdp_session, results):
    """Recursively collect interactive elements with bounding boxes."""
    role = get_node_value(ax_node, "role")

    if role in INTERACTIVE_ROLES:
        name = get_node_value(ax_node, "name")

        if name and name.strip():
            backend_node_id = ax_node.get("backendDOMNodeId")
            bbox = None

            if backend_node_id:
                try:
                    box_resp = cdp_session.send("DOM.getBoxModel", {"backendNodeId": backend_node_id})
                    content = box_resp.get("model", {}).get("content", [])

                    if len(content) >= 8:
                        # Content is quad corners: [x1,y1, x2,y2, x3,y3, x4,y4]
                        xs = [content[idx] for idx in range(0, 8, 2)]
                        ys = [content[idx] for idx in range(1, 8, 2)]
                        x, y = min(xs), min(ys)
                        w, h = max(xs) - x, max(ys) - y

                        if w >= 5 and h >= 5 and x >= 0 and y >= 0:
                            bbox = {"x": int(x), "y": int(y), "w": int(w), "h": int(h)}
                except (KeyError, TypeError):
                    pass

            results.append({
                "role": role,
                "label": name.strip()[:60],
                "bbox": bbox
            })

    for child_id in ax_node.get("childIds", []):
        if child_id in nodes_map:
            collect_elements(nodes_map[child_id], nodes_map, cdp_session, results)


def distill_dom(raw_html):
    """Strip non-essential HTML and extract interactive elements."""
    cleaned = STRIP_PATTERN.sub("", raw_html)
    cleaned = WHITESPACE_PATTERN.sub(" ", cleaned)

    tags_found = []
    for match in INTERACTIVE_TAG_PATTERN.finditer(cleaned):
        tag = match.group(1).lower()
        attrs_str = match.group(2)
        attrs = dict(ATTR_PATTERN.findall(attrs_str))

        if attrs:
            tags_found.append({"tag": tag, "attrs": attrs})

    return cleaned, tags_found


def create_set_of_marks(browser_page, elem_list, output_path="marked_screenshot.png"):
    """Overlay numbered bounding boxes on screenshot."""
    screenshot_bytes = browser_page.screenshot(full_page=False)
    img = Image.open(BytesIO(screenshot_bytes))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
    except OSError:
        font = ImageFont.load_default()

    marked_count = 0
    for idx, elem in enumerate(elem_list):
        bbox = elem.get("bbox")
        if not bbox:
            continue

        x, y, w, h = bbox["x"], bbox["y"], bbox["w"], bbox["h"]

        if x > img.width or y > img.height:
            continue

        num = idx + 1
        marked_count += 1

        draw.rectangle([x, y, x + w, y + h], outline="#E53935", width=2)

        label = str(num)
        text_bbox = draw.textbbox((0, 0), label, font=font)
        text_w = text_bbox[2] - text_bbox[0] + 4
        text_h = text_bbox[3] - text_bbox[1] + 2

        label_x = max(0, x)
        label_y = max(0, y - text_h - 2)

        draw.rectangle([label_x, label_y, label_x + text_w, label_y + text_h], fill="#E53935")
        draw.text((label_x + 2, label_y), label, fill="#FFFFFF", font=font)

    img.save(output_path)
    return output_path, marked_count


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://youtube.com/", wait_until="domcontentloaded")  # noqa: spelling
    page.wait_for_timeout(2000)

    # Get accessibility tree via Chrome DevTools Protocol
    cdp = page.context.new_cdp_session(page)
    response = cdp.send("Accessibility.getFullAXTree")
    
    # Build a map of nodeId -> node for easy lookup
    nodes = response.get("nodes", [])
    if not nodes:
        print("No accessibility nodes found")
        browser.close()
        exit()

    node_map = {node["nodeId"]: node for node in nodes}

    # Find root node (node that isn't a child of any other node)
    all_child_ids = set()
    for node in nodes:
        all_child_ids.update(node.get("childIds", []))
    
    root_nodes = [node for node in nodes if node["nodeId"] not in all_child_ids]
    root_node = root_nodes[0] if root_nodes else nodes[0]

    elements = []
    collect_elements(root_node, node_map, cdp, elements)

    for i, el in enumerate(elements):
        bbox_str = ""
        if el["bbox"]:
            b = el["bbox"]
            bbox_str = f" @ ({b['x']},{b['y']} {b['w']}x{b['h']})"
        print(f"[{i+1}] {el['role']} → {el['label']}{bbox_str}")

    # DOM Distillation - strip non-essential HTML
    html = page.content()
    cleaned_html, extracted = distill_dom(html)

    print(f"\nDOM Distillation: {len(html):,} → {len(cleaned_html):,} chars")
    print(f"Extracted {len(extracted)} interactive tags via regex")

    distilled_data = {
        "url": page.url,
        "title": page.title(),
        "elements": elements,
        "regex_extracted": extracted[:30]
    }

    with open("distilled.json", "w") as f:
        json.dump(distilled_data, f, indent=2)

    # Set-of-Marks - screenshot with numbered bounding boxes
    output_file, marked = create_set_of_marks(page, elements)
    print(f"Set-of-Marks: {marked} elements marked → {output_file}")

    input("\nPress Enter to exit")
    browser.close()

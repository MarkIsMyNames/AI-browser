from playwright.sync_api import sync_playwright

INTERACTIVE_ROLES = {
    "button",
    "textbox",
    "link",
    "checkbox",
    "radio",
    "combobox"
}

def collect(node, node_map, results):
    # CDP returns role as an object with a "value" property
    role_obj = node.get("role", {})
    role = role_obj.get("value") if isinstance(role_obj, dict) else role_obj
    
    if role in INTERACTIVE_ROLES:
        # CDP returns name as an object with a "value" property
        name_obj = node.get("name", {})
        name = name_obj.get("value") if isinstance(name_obj, dict) else name_obj
        
        results.append({
            "role": role,
            "label": name
        })

    # CDP returns childIds, not actual child nodes
    for child_id in node.get("childIds", []):
        if child_id in node_map:
            collect(node_map[child_id], node_map, results)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://youtube.com/")

    # Get accessibility tree using CDP (Chrome DevTools Protocol)
    cdp = page.context.new_cdp_session(page)
    response = cdp.send("Accessibility.getFullAXTree")
    
    # Build a map of nodeId -> node for easy lookup
    nodes = response.get("nodes", [])
    if not nodes:
        print("No accessibility nodes found")
        browser.close()
        exit()
    
    node_map = {node["nodeId"]: node for node in nodes}
    
    # Find root node(s) - nodes that aren't children of any other node
    all_child_ids = set()
    for node in nodes:
        all_child_ids.update(node.get("childIds", []))
    
    root_nodes = [node for node in nodes if node["nodeId"] not in all_child_ids]
    root_node = root_nodes[0] if root_nodes else nodes[0]
    
    elements = []
    collect(root_node, node_map, elements)

    for i, el in enumerate(elements):
        print(f"[{i+1}] {el['role']} → {el['label']}")

    input("Press Enter to exit")
    browser.close()

from playwright.sync_api import sync_playwright
from browser_interaction import BrowserInteractionAgent
from browser_types import BrowserCommand, ActionType, DistilledElement
import time

def mock_perception():
    # Returns a list of elements "perceived" on the page
    return [
        DistilledElement(
            element_id="search_box",
            tag_name="input",
            role="searchbox",
            attributes={"name": "search", "title": "Search", "placeholder": "Search Wikipedia"}
        ),
        DistilledElement(
            element_id="search_button",
            tag_name="button",
            text="Search"
        )
    ]

def test_wikipedia_interaction():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://www.wikipedia.org")

        # Initialize our agent
        agent = BrowserInteractionAgent(page, mock_perception)
        
        # Initial perception load
        agent.update_map(mock_perception())

        print("Testing Type Action...")
        # Test 1: Type into search box
        cmd_type = BrowserCommand(
            action_type=ActionType.TYPE,
            element_id="search_box",
            text_content="Python (programming language)"
        )
        result = agent.execute_command(cmd_type)
        print(f"Type Result: {result.success}, {result.failure_reason}")

        print("Testing Click Action...")
        # Test 2: Click search button
        # Note: Wikipedia search button might be an input[type=submit] or button. 
        # On wikipedia.org main page, it is <button class="pure-button pure-button-primary-progressive">...</button>
        # Our mock perception said "search_button" is tag="button", text="Search".
        # Let's see if the logic finds it.
        cmd_click = BrowserCommand(
            action_type=ActionType.CLICK,
            element_id="search_button"
        )
        result = agent.execute_command(cmd_click)
        print(f"Click Result: {result.success}, {result.failure_reason}")
        
        # Wait to see result
        time.sleep(2)
        
        print("Final URL:", page.url)
        browser.close()

if __name__ == "__main__":
    test_wikipedia_interaction()

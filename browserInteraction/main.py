from playwright.sync_api import sync_playwright
import time

def run_browser_interaction():
    """
    A simple example of how to use Playwright to:
    1. Launch a browser
    2. Navigate to a URL
    3. Interact with the page (type, click)
    4. Extract information
    """
    print("Starting Playwright...")
    
    # Use sync_playwright context manager
    with sync_playwright() as p:
        # Launch Chromium browser
        # headless=False lets you see the browser interaction. Set to True for background execution.
        browser = p.chromium.launch(headless=False) 
        
        # Create a new browser context (like a separate session)
        context = browser.new_context()
        
        # Open a new page/tab
        page = context.new_page()
        
        # 1. Navigate
        url = "https://www.wikipedia.org"
        print(f"Navigating to {url}...")
        page.goto(url)
        
        # 2. Interact - Search for "Playwright"
        # We use a CSS selector to find the input. 'input[name="search"]' is common on Wiki.
        search_term = "Software testing"
        print(f"Typing '{search_term}' into search bar...")
        page.fill('input[name="search"]', search_term)
        
        # Press Enter to search (or you could click the search button with page.click())
        page.press('input[name="search"]', 'Enter')
        
        # Wait for the page to load the results. 
        # Playwright auto-waits for many things, but waiting for a specific element is robust.
        print("Waiting for results...")
        page.wait_for_selector('#firstHeading')
        
        # 3. Extract Info
        title = page.title()
        heading = page.inner_text('#firstHeading')
        print(f"Page Title: {title}")
        print(f"Heading: {heading}")
        
        # Take a screenshot to verify
        page.screenshot(path="search_result.png")
        print("Screenshot saved to 'search_result.png'")
        
        # Optional: Sleep briefly to let you see the result before closing
        time.sleep(2)
        
        # 4. cleanup
        print("Closing browser.")
        browser.close()

if __name__ == "__main__":
    run_browser_interaction()

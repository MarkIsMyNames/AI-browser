from playwright.sync_api import sync_playwright

def run_advanced_features():
    with sync_playwright() as p:
        print("--- Feature 1: Mobile Emulation & Video Recording ---")
        # Playwright has a registry of device descriptors
        iphone_13 = p.devices['iPhone 13']
        
        # Launch browser (chromium)
        browser = p.chromium.launch(headless=False)
        
        # Create a context with iPhone 13 characteristics (viewport, user agent, etc.)
        # Also enable video recording for this context
        context = browser.new_context(
            **iphone_13,
            record_video_dir="videos/",  # Where to save videos
            record_video_size={"width": 640, "height": 480}
        )
        
        # Start tracing (records everything: screenshots, DOM snapshots, network)
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        page = context.new_page()
        
        print("--- Feature 2: Network Interception (Blocking Images) ---")
        # Define a route handler to block images for faster loading
        def block_images(route):
            if route.request.resource_type == "image":
                return route.abort()
            return route.continue_()

        # Apply the interception to all URLs (wildcard **)
        page.route("**/*", block_images)

        print("Navigating to a heavy site (The Verge) as iPhone 13 with no images...")
        page.goto("https://www.theverge.com")
        
        print(f"Page title: {page.title()}")
        
        # Take a screenshot of the mobile view
        page.screenshot(path="iphone_view_no_images.png")
        print("Saved 'iphone_view_no_images.png'")
        
        # Stop tracing and save it
        context.tracing.stop(path="trace.zip")
        print("Saved trace execution to 'trace.zip' (View with: playwright show-trace trace.zip)")

        context.close() # valid video is saved on close
        browser.close()
        print("Video saved to 'videos/' folder")

        print("\n--- Feature 3: PDF Generation (Headless Only) ---")
        # PDF generation acts like "Print to PDF" and usually requires headless mode
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://en.wikipedia.org/wiki/Python_(programming_language)")
        
        # Generate PDF
        page.pdf(path="article.pdf", format="A4")
        print("Saved 'article.pdf'")
        
        browser.close()

if __name__ == "__main__":
    run_advanced_features()

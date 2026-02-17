# AI-browser

A browser interaction tool using [Playwright](https://playwright.dev/).

## Setup

1. **Activate the Virtual Environment:**
   ```bash
   source .venv/bin/activate
   ```
   *(Note: This project is already configured with a virtual environment in `.venv/`)*

2. **Install Dependencies (if needed):**
   ```bash
   pip install -r requirements.txt
   playwright install
   ```
   *(These are already installed, but useful if you move the project)*

## Usage

To run the example interaction script:

```bash
python main.py
```

This script will:
1. Launch a browser (with UI visible).
2. Go to Wikipedia.
3. Search for "Software testing".
4. Print the resulting page title and heading.
5. Save a screenshot to `search_result.png`.

## Code Walkthrough

See `main.py` for detailed comments on how the Playwright API works.


you want to store references to different elements on screen and possiblibly pass them to this module and then dictate the interation 
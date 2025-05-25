# site_news_scrapper 🕵️‍♂️📄📰

[![Python Version](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)

**A robust Python web scraper using Selenium & undetected-chromedriver to fetch full HTML content from websites, featuring anti-detection capabilities. Intended for educational and non-commercial use.**

This tool is designed to powerfully extract complete HTML from dynamic web pages, including those that load content via JavaScript or employ various anti-scraping measures. While named `site_news_scrapper`, its core is a versatile HTML fetching engine suitable for a wide range of sites, primarily for learning and research.

---

## 📖 Overview

In an era of dynamic web content, `site_news_scrapper` provides a reliable solution to access the full HTML structure of web pages for educational exploration. By leveraging `Selenium` with `undetected-chromedriver`, it bypasses many common bot-detection systems and accurately renders pages before extraction. This makes it an excellent tool for understanding advanced scraping techniques on complex sites, such as news portals or any data-rich platform, within a non-commercial framework.

**This project is for educational and non-commercial purposes only.**

---

## ✨ Key Features

* 🤫 **Advanced Bot Evasion:** Utilizes `undetected-chromedriver` and specialized browser configurations to minimize detection.
* 👤 **Human-like Behavior Simulation:** Incorporates page scrolling, random mouse movements, and human-like delays.
* 🍪 **Cookie Consent Handling:** Attempts to automatically accept common cookie banners to access content smoothly.
* 📄 **Full HTML Extraction:** Captures the complete HTML source after all JavaScript rendering and dynamic content updates.
* 🌐 **Proxy Integration:** Supports proxy configurations for specific learning scenarios or bypassing regional restrictions for research.
* 🕵️ **Randomized User-Agents:** Employs `fake-useragent` for varied and legitimate browser identification.
* ⚙️ **Configurable & Easy to Use:** Straightforward setup for target URLs and operational parameters.
* 📝 **Comprehensive Logging:** Detailed logs for monitoring progress and easier troubleshooting.
* 🎓 **Educational & Non-Commercial Use Only:** Licensed under CC BY-NC 4.0 to encourage learning and research while preventing commercial exploitation.

---

---

## ⚙️ Tech Stack

* **Python 3.11+**
* **Selenium:** For automating web browser interaction.
* **undetected-chromedriver:** A modified ChromeDriver to help avoid detection.
* **Fake-UserAgent:** For generating random User-Agent strings.
* **Logging:** Python's built-in logging module.

---

## ⚠️ Important Note on Python Version

The underlying `undetected-chromedriver` library can be sensitive to Python and Chrome version mismatches. Using development versions of Python (e.g., Python 3.13 as noted in the original code comments from which this tool is derived) may lead to instability or "invalid handle" errors.

**It is strongly recommended to use a stable Python version (e.g., 3.11 or 3.12) within a virtual environment.**

---

## 📋 Prerequisites

* **Python** (version 3.11 or 3.12 recommended).
* **Google Chrome** browser installed.
* `pip` (Python package installer) and `venv` (for virtual environments).

---

## 🚀 Getting Started

1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/arshia8430/site_news_scrapper.git](https://github.com/arshia8430/site_news_scrapper.git)
    cd site_news_scrapper
    ```

2.  **Set Up Virtual Environment:**
    ```bash
    python -m venv venv
    ```
    * **Windows:**
        ```bash
        venv\Scripts\activate
        ```
    * **macOS/Linux:**
        ```bash
        source venv/bin/activate
        ```

3.  **Install Dependencies:**
    Ensure you have a `requirements.txt` file in your project root with the following (or your specific versions):
    ```txt
    selenium
    undetected-chromedriver
    fake-useragent
    ```
    Then, install them:
    ```bash
    pip install -r requirements.txt
    ```

---

## 🛠️ Configuration

Key operational parameters are set within the main execution block (e.g., in `scraper.py` or your primary script file) typically found in the `if __name__ == "__main__":` section.

* `url`: The target website URL.
* `USE_PROXY`: `True` or `False` to enable/disable proxy.
* `PROXY_ADDRESS`: Proxy server details if enabled (e.g., `http://user:pass@host:port`).
* `CHROME_DRIVER_MANUAL_PATH`: (Optional) Path to a specific `chromedriver` executable.

**Example (in your Python script, e.g., `scraper.py`):**
```python
if __name__ == "__main__":
    # === CONFIGURATION START ===
    url = "[https://news.example.com](https://news.example.com)"  # <<--- Set your target URL here
    USE_PROXY = False
    PROXY_ADDRESS = None  # e.g., "http://your_proxy_address:port"
    CHROME_DRIVER_MANUAL_PATH = None # e.g., "/path/to/your/chromedriver"
    # === CONFIGURATION END ===

    logging.info(f"Starting scraping operation for {url} (HTML only)...")
    # Assuming your scraper class is named NPRScraperHTMLOnly or similar
    scraper = NPRScraperHTMLOnly( # Or your adapted class name
        url,
        use_proxy=USE_PROXY,
        proxy_address=PROXY_ADDRESS,
        chromedriver_path=CHROME_DRIVER_MANUAL_PATH
    )
    # ... rest of the execution logic ...

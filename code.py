import random
import time
import re # For using regular expressions
import logging
import os
from enum import Enum
from urllib.parse import urljoin, urlparse
import hashlib # For creating a hash from the URL for file naming (optional)

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from fake_useragent import UserAgent
# For automatic chromedriver management (optional but very useful)
from webdriver_manager.chrome import ChromeDriverManager
import json
from goose3 import Goose

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log", mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('webdriver_manager').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# --- Constants ---
DEFAULT_OUTPUT_BASE_DIR = "scraped_pages"
DEFAULT_MAX_RETRIES = 3
DEFAULT_WINDOW_SIZES = ['1920,1080', '1600,900', '1366,768']
PAGE_LOAD_TIMEOUT_DEFAULT = 10
PAGE_LOAD_TIMEOUT_SECOND_ATTEMPT = 5


json_dict={}

def make_json(html_content):
    g = Goose()
    try:
        # استخراج محتوا با Goose
        article = g.extract(raw_html=html_content)
        return {
            'title': article.title,
            'cleaned_text': article.cleaned_text
        }
    except Exception as e:
        logging.info("WHAT THE FUCK")
        return None


class ContentType(Enum):
    HOMEPAGE = "homepage"
    ARTICLE = "article"

# --- Target News Websites and their Link Patterns ---
# !!! Important: The regex patterns below are examples and must be carefully adjusted for each site !!!
# "article_url_regex_patterns": A LIST of regular expression (regex) patterns.
#                                 All <a> tags on the homepage will be checked against these patterns
#                                 to identify news article URLs.
# "article_page_content_selector": (Optional) CSS selector for the main content section of an article.
#                                  This selector is NOT used for link extraction. It can be used for
#                                  post-processing the saved HTML content with other tools (e.g., BeautifulSoup).
NEWS_LINK_PATTERNS = {
    "https://www.aljazeera.com/": {
        "article_url_regex_patterns": [
            r"^https://www\.aljazeera\.com/(news|features|opinion)/"

        ]
    }
    # Example for another hypothetical site:
    # "https://www.example-news.com/": {
    #     "article_url_regex_patterns": [
    #        r"https://www.example-news.com/news/article-\d+/",
    #        r"https://www.example-news.com/story/\d+/.+"
    #      ],
    #     "article_page_content_selector": "div.main-article-body" # For optional post-processing
    # },
}

# --- Proxy List (Optional) ---
PROXIES = []

class StealthChromeDriver:
    def __init__(self, proxies=None, use_headless=True, max_retries=DEFAULT_MAX_RETRIES, chromedriver_path=None):
        self.ua_rotator = UserAgent()
        self.driver = None
        self.actions = None
        self.proxies = proxies if proxies else []
        self.current_proxy_index = 0
        self.use_headless = use_headless
        self.max_retries = max_retries
        self.chromedriver_path = chromedriver_path

    def get_random_ua(self):
        return self.ua_rotator.random

    def _configure_chrome_options(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument(f"--window-size={random.choice(DEFAULT_WINDOW_SIZES)}")
        options.add_argument(f"--user-agent={self.get_random_ua()}")
        options.add_argument("--lang=en-US,en;q=0.9")
        options.add_argument("--accept-lang=en-US,en;q=0.9")

        if self.use_headless:
            options.add_argument("--headless=new")
            options.add_argument("--disable-extensions")
            logger.info("Headless mode enabled.")

        if self.proxies:
            proxy = self.proxies[self.current_proxy_index % len(self.proxies)]
            options.add_argument(f"--proxy-server={proxy}")
            logger.info(f"Using proxy: {proxy}")
        return options

    def init_driver(self):
        options = self._configure_chrome_options()
        try:
            if self.chromedriver_path:
                service = Service(executable_path=self.chromedriver_path)
                logger.info(f"Using chromedriver from specified path: {self.chromedriver_path}")
            else:
                logger.info("Attempting to use WebDriverManager for ChromeDriver.")
                try:
                    service = Service(ChromeDriverManager().install())
                except Exception as e_manager:
                    logger.error(f"WebDriverManager failed to install/find ChromeDriver: {e_manager}")
                    logger.info("Falling back to default ChromeDriver path (ensure it's in PATH).")
                    service = Service()

            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_page_load_timeout(10)  
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": """
                        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5].map(i => ({name: `Plugin ${i}`, description: `Description ${i}`, filename: `plugin${i}.dll`, length: 1}))});
                        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en', 'es-ES']});
                        if (Math.random() < 0.5) {
                            window.screenX = Math.floor(Math.random() * 100);
                            window.screenY = Math.floor(Math.random() * 50);
                        }
                        window.chrome = window.chrome || {};
                        window.chrome.runtime = window.chrome.runtime || {};
                    """
                }
            )
            self.actions = ActionChains(self.driver)
            logger.info("WebDriver initialized successfully.")
            return True
        except WebDriverException as e:
            logger.error(f"WebDriver initialization failed: {e}")
            if "net::ERR_PROXY_CONNECTION_FAILED" in str(e) and self.proxies:
                failed_proxy = self.proxies[self.current_proxy_index % len(self.proxies)]
                logger.error(f"Proxy {failed_proxy} might be down or invalid.")
                self.current_proxy_index += 1
            self.driver = None
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred during driver initialization: {e}", exc_info=True)
            self.driver = None
            return False

    def human_like_delay(self, min_sec=0.5, max_sec=1.5):
        time.sleep(random.uniform(min_sec, max_sec))

    def human_interaction(self):
        if not self.driver: return
        try:
            body_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )
            for _ in range(random.randint(0, 1)):
                try:
                    page_width = self.driver.execute_script("return document.body.scrollWidth")
                    page_height = self.driver.execute_script("return document.body.scrollHeight")
                    random_x = random.randint(0, page_width // 2)
                    random_y = random.randint(0, page_height // 2)
                    self.actions.move_to_element_with_offset(body_element, random_x, random_y).perform()
                    self.human_like_delay(0.1, 0.3)
                except Exception:
                    if body_element: self.actions.move_to_element(body_element).perform()
            if random.random() < 0.2:
                scroll_depth_factor = random.uniform(0.1, 0.25)
                self.driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {scroll_depth_factor});")
                self.human_like_delay(0.3, 0.8)
            self.human_like_delay(0.2, 0.5)
        except Exception as e:
            logger.warning(f"Human interaction simulation failed: {e}")

    def advanced_cookie_handler(self):
        if not self.driver: return False
        common_selectors = [
            "button#onetrust-accept-btn-handler", "button[data-testid='accept-button']", "button[data-gdpr-accept]",
            "button[aria-label*='Accept Cookies']", "button[aria-label*='Agree']", "button[aria-label*='Allow all']",
            "button[id*='cookie'][id*='accept']", "button[class*='cookie'][class*='accept']",
            "button[id*='consent'][id*='accept']", "button[class*='consent'][class*='accept']",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept all')]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'allow all')]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree')]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'got it')]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ok')]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'i understand')]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continue')]",
            "div[id*='cookie-banner'] button.accept", "div[class*='cookie-consent'] button.primary"
        ]
        for i, selector in enumerate(common_selectors):
            try:
                wait_time = 1.5 if i < 5 else 0.75 
                by_type = By.XPATH if selector.startswith("//") else By.CSS_SELECTOR
                elements = WebDriverWait(self.driver, wait_time).until(
                    EC.presence_of_all_elements_located((by_type, selector))
                )
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].click();", element)
                            logger.info(f"Clicked cookie/consent button using selector: {selector}")
                            self.human_like_delay(0.8, 1.5)
                            return True
                        except Exception as e_click:
                            logger.debug(f"Could not click element for selector {selector}: {e_click}")
            except TimeoutException:
                logger.debug(f"Cookie selector not found or not ready: {selector}")
            except Exception as e_general:
                logger.warning(f"Error processing cookie selector {selector}: {e_general}")
        logger.info("No common cookie banners found or handled.")
        return False

    def clear_browser_data(self):
        if not self.driver: return
        try:
            self.driver.delete_all_cookies()
            self.driver.execute_script("window.localStorage.clear();")
            self.driver.execute_script("window.sessionStorage.clear();")
        except Exception as e:
            logger.warning(f"Error clearing browser data: {e}")

    def stealth_scrape(self, url):
        if not self.driver and not self.init_driver_if_needed():
            logger.error(f"Driver not available for {url}. Aborting.")
            return None

        for attempt in range(self.max_retries):
            current_page_load_timeout = PAGE_LOAD_TIMEOUT_DEFAULT
            if attempt == 1:
                current_page_load_timeout = PAGE_LOAD_TIMEOUT_SECOND_ATTEMPT

            try:
                logger.info(f"Navigating to {url} (Attempt {attempt + 1}/{self.max_retries}, Timeout: {current_page_load_timeout}s)")
                if self.driver:
                    try:
                        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": self.get_random_ua()})
                    except Exception as e_ua_req:
                        logger.warning(f"Could not change UA for request {url}: {e_ua_req}")

                self.driver.get(url)
                WebDriverWait(self.driver, current_page_load_timeout).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
                self.human_like_delay(1.5, 2.5)
                self.advanced_cookie_handler()
                self.human_like_delay(0.5, 1.0)
                self.human_interaction()
                
                page_title = (self.driver.title or "").lower()
                block_keywords = ["access denied", "blocked", "captcha", "are you a robot", "pardon our interruption", "verify your identity", "challenge", "not available", "error"]
                if any(keyword in page_title for keyword in block_keywords):
                    logger.warning(f"Potential block keyword in title on {url}. Title: {self.driver.title}")

                page_source_lower = self.driver.page_source.lower() 
                if any(keyword in page_source_lower for keyword in block_keywords):
                    logger.warning(f"Potential block keyword in page source on {url}. Title: {self.driver.title}")
                    if self.proxies and self.rotate_proxy_and_reinit_driver():
                        logger.info(f"Rotated proxy. Retrying {url}.")
                        continue
                    else:
                        logger.warning(f"Cannot bypass block for {url}. Will retry or fail.")

                content = self.driver.page_source
                if len(content) < 2000 and ("captcha" in content.lower() or "blocked" in content.lower()):
                    logger.warning(f"BLOCKED or CAPTCHA suspected (small content: {len(content)} bytes) on {url}")
                    if self.proxies and self.rotate_proxy_and_reinit_driver():
                        logger.info(f"Rotated proxy due to small content. Retrying {url}.")
                        continue
                
                logger.info(f"Successfully scraped content from {url} ({len(content)} bytes)")
                return content
            
            except TimeoutException:
                logger.warning(f"Timeout loading page {url} on attempt {attempt + 1} after {current_page_load_timeout}s.")
                if attempt == 1:
                    logger.info(f"Attempting to stop page load and get partial content for {url} (2nd attempt timeout).")
                    try:
                        self.driver.execute_script("window.stop();")
                        self.human_like_delay(0.5, 1.0)
                    except Exception as e_stop:
                        logger.warning(f"Could not execute window.stop() on {url}: {e_stop}")
                    try:
                        partial_content_on_stop = self.driver.page_source
                        if partial_content_on_stop and len(partial_content_on_stop) > 1000:
                            logger.info(f"Returning partial content for {url} after stopping load on 2nd attempt ({len(partial_content_on_stop)} bytes).")
                            return partial_content_on_stop
                        else:
                            logger.warning(f"Partial content after stop on 2nd attempt too short or unavailable for {url}.")
                    except Exception as e_partial_stop:
                        logger.warning(f"Error getting partial content after stop on 2nd attempt for {url}: {e_partial_stop}")

                elif attempt == self.max_retries - 1:
                    logger.info(f"Final attempt for {url} timed out. Trying for partial content.")
                    try:
                        partial_content_final = self.driver.page_source
                        if partial_content_final and len(partial_content_final) > 1000:
                             logger.info(f"Scraped partial content from {url} after final timeout ({len(partial_content_final)} bytes)")
                             return partial_content_final
                    except Exception as e_partial_final:
                         logger.warning(f"Could not get partial content on final timeout for {url}: {e_partial_final}")

            except WebDriverException as e:
                logger.error(f"WebDriverException on {url} (Attempt {attempt + 1}): {e}")
                if any(err_msg in str(e).lower() for err_msg in ["net::err_proxy_connection_failed", "timed out", "target crashed", "disconnected", "unable to connect"]):
                    if self.proxies and self.rotate_proxy_and_reinit_driver():
                        logger.info("Proxy/Connection error or target crash. Rotated proxy. Retrying.")
                        continue
                    else:
                        logger.warning("No proxies or rotation failed. Re-initializing driver for next attempt.")
                        self.cleanup_driver_quietly()
                        if not self.init_driver_if_needed():
                             logger.error(f"Failed to re-initialize driver for {url} after WebDriverException. Failing URL.")
                             return None
                elif any(err_msg in str(e) for err_msg in ["ERR_NAME_NOT_RESOLVED", "ERR_CONNECTION_REFUSED"]):
                    logger.error(f"Site {url} might be down or unreachable. No more retries for this URL.")
                    break
            except Exception as e:
                content = self.driver.page_source
                if attempt ==1 and len(content)>20000:
                    logger.error(f"Scraping failed for {url} (Attempt {attempt + 1}): {e}", exc_info=True)
                    return content
                logger.error(f"Scraping failed for {url} (Attempt {attempt + 1}): {e}", exc_info=True)

            if attempt < self.max_retries - 1:
                backoff_time = random.uniform(5.0 * (attempt + 1), 10.0 * (attempt + 1))
                logger.info(f"Waiting for {backoff_time:.2f} seconds before next attempt for {url}.")
                time.sleep(backoff_time)
            else:
                logger.error(f"All {self.max_retries} retries failed for {url}.")
        return None

    def extract_news_links(self, homepage_url, article_url_regex_patterns_list=None):
        if not self.driver:
            logger.error("Driver not initialized. Cannot extract links.")
            return []
        
        logger.info(f"Extracting all 'href' attributes from <a> tags on {homepage_url} and filtering by regex.")
        
        compiled_regex_filters = []
        if article_url_regex_patterns_list:
            if not isinstance(article_url_regex_patterns_list, list):
                logger.warning(f"article_url_regex_patterns_list for {homepage_url} is not a list. Wrapping it.")
                article_url_regex_patterns_list = [article_url_regex_patterns_list]

            for idx, pattern_str in enumerate(article_url_regex_patterns_list):
                if not pattern_str or not isinstance(pattern_str, str):
                    logger.warning(f"Empty or invalid regex pattern string at index {idx} for {homepage_url}. Skipping.")
                    continue
                try:
                    compiled_regex_filters.append(re.compile(pattern_str))
                    logger.debug(f"Compiled regex pattern: '{pattern_str}' for {homepage_url}")
                except re.error as e_re:
                    logger.error(f"Invalid regex pattern '{pattern_str}' for {homepage_url}: {e_re}. Skipping.")
        
        if not compiled_regex_filters: # If no valid patterns provided or compiled
            logger.warning(f"No valid regex patterns provided or compiled for {homepage_url}. No article links will be extracted.")
            return []

        extracted_links = set()
        try:
            # Page is assumed to be fully loaded by stealth_scrape before this method is called.
            all_anchor_elements = self.driver.find_elements(By.TAG_NAME, 'a')

            if not all_anchor_elements:
                logger.warning(f"No <a> tags found on {homepage_url}")
                return []

            logger.info(f"Found {len(all_anchor_elements)} <a> tags on {homepage_url}.")
            parsed_homepage_url = urlparse(homepage_url)

            for element in all_anchor_elements:
                try:
                    href = element.get_attribute('href')
                    if href and href.strip() and not href.lower().startswith(("javascript:", "#", "mailto:", "tel:")):
                        absolute_url = urljoin(homepage_url, href.strip())
                        
                        parsed_absolute_url = urlparse(absolute_url)
                        if parsed_absolute_url.netloc != parsed_homepage_url.netloc and \
                           not parsed_absolute_url.netloc.endswith("." + parsed_homepage_url.netloc):
                            logger.debug(f"Skipping external link: {absolute_url}")
                            continue

                        # Filter with compiled Regex patterns
                        for regex_filter in compiled_regex_filters:
                            if regex_filter.match(absolute_url):
                                extracted_links.add(absolute_url)
                                logger.debug(f"Added link matched by regex '{regex_filter.pattern}': {absolute_url}")
                                break # Matched one pattern, no need to check others for this link
                            
                except Exception as e_attr:
                    logger.debug(f"Could not get href or process an <a> element: {e_attr}")
            
            logger.info(f"Found {len(extracted_links)} unique news links matching regex patterns from {homepage_url}.")
            return list(extracted_links)
            
        except Exception as e:
            logger.error(f"Error extracting news links from {homepage_url}: {e}", exc_info=True)
            return []

    def multi_site_scraper(self, sites_with_patterns: dict):
        all_successful_articles = []
        all_failed_items = []
        
        for base_url, patterns_dict in sites_with_patterns.items():
            logger.info(f"--- Starting process for site: {base_url} ---")
            
            if not self.init_driver_if_needed():
                logger.error(f"Failed to initialize driver for {base_url}. Skipping site.")
                all_failed_items.append(f"Site_Init_Fail: {base_url}")
                continue
            
            self.clear_browser_data()
            try:
                if self.driver:
                    self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": self.get_random_ua()})
                    logger.info(f"User-Agent set for {base_url}")
            except Exception as e_ua_main:
                logger.warning(f"Could not set new User-Agent for {base_url}: {e_ua_main}. Driver might be unstable.")
                self.cleanup_driver_quietly() 
                all_failed_items.append(f"Site_UA_Set_Fail: {base_url}")
                continue 

            homepage_html = self.stealth_scrape(base_url)
            if not homepage_html:
                logger.warning(f"Failed to scrape homepage {base_url}. Skipping link extraction.")
                all_failed_items.append(f"Homepage_Scrape_Fail: {base_url}")
                self.prepare_for_next_site()
                continue
            
            article_regex_patterns = patterns_dict.get("article_url_regex_patterns")

            if not article_regex_patterns: # Check if regex patterns are defined
                logger.warning(f"No 'article_url_regex_patterns' defined for {base_url}. Skipping link extraction for this site.")
                self.prepare_for_next_site()
                continue
            
            article_urls = self.extract_news_links(base_url, article_regex_patterns) # Modified call
            article_urls=list(set(article_urls))
            if not article_urls:
                logger.info(f"No matching news article links found on {base_url} using provided regex patterns.")
            else:
                logger.info(f"Found {len(article_urls)} articles to scrape from {base_url}.")
                # article_urls = article_urls[:2] # For testing
                # logger.info(f"Processing first {len(article_urls)} articles for testing from {base_url}.")

            for i, article_url in enumerate(article_urls):
                logger.info(f"Scraping article {i+1}/{len(article_urls)} from {base_url}: {article_url}")
                self.human_like_delay(1.0, 2.5)
                article_html_content = self.stealth_scrape(article_url)
                
                if article_html_content and len(article_html_content) > 3000:
                    if self.save_content(article_html_content, article_url, content_type=ContentType.ARTICLE):
                        all_successful_articles.append(article_url)
                    else:
                        all_failed_items.append(f"Article_Save_Fail: {article_url}")
                else:
                    logger.warning(f"No content or insufficient content (length: {len(article_html_content or '')}) for article: {article_url}")
                    all_failed_items.append(f"Article_Content_Fail: {article_url}")
                self.human_like_delay(min_sec=2.0, max_sec=5.0)
            self.prepare_for_next_site()
        return all_successful_articles, all_failed_items

    def prepare_for_next_site(self):
        delay = random.uniform(10.0, 25.0)
        logger.info(f"Waiting for {delay:.2f} seconds before next site or finishing...")
        time.sleep(delay)
        if self.proxies and len(self.proxies) > 1:
            logger.info("Attempting to rotate proxy and re-initialize driver for the next site.")
            self.cleanup_driver_quietly() 
            if not self.init_driver():
                logger.critical("Failed to re-initialize driver with new proxy. This might affect subsequent sites.")
    
    def init_driver_if_needed(self):
        if self.driver:
            try:
                _ = self.driver.current_url
                return True
            except WebDriverException:
                logger.warning("Driver seems closed or unresponsive. Re-initializing.")
                self.cleanup_driver_quietly()
        logger.info("Driver not found or previously closed. Initializing new one.")
        return self.init_driver()

    def rotate_proxy_and_reinit_driver(self):
        if not self.proxies:
            logger.warning("No proxies available to rotate.")
            self.cleanup_driver_quietly()
            logger.info("Attempting to re-initialize driver without proxy rotation.")
            return self.init_driver()
        logger.info("Rotating proxy and re-initializing driver.")
        self.cleanup_driver_quietly()
        return self.init_driver()

    def save_content(self, content: str, url: str, content_type: ContentType, base_dir: str = DEFAULT_OUTPUT_BASE_DIR):
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.replace('.', '_').replace('www_', '')
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            path_segments = [seg for seg in parsed_url.path.split('/') if seg and seg.lower() not in ['index.html', 'index.htm']]
            
            if not path_segments or (len(path_segments) == 1 and not path_segments[0]):
                safe_url_path = "index"
            else:
                raw_path_name = "_".join(path_segments)
                safe_url_path = re.sub(r'[^\w\-\.]', '_', raw_path_name)
                safe_url_path = safe_url_path[:100].strip('_.- ')
            
            if not safe_url_path:
                safe_url_path = f"{content_type.value}_content"

            specific_output_dir = os.path.join(base_dir, domain, content_type.value + "s")
            os.makedirs(specific_output_dir, exist_ok=True)
            filename = os.path.join(specific_output_dir, f"{safe_url_path}_{timestamp}.html")
            if domain not in json_dict.keys():
                json_dict[domain]=[]
            json_dict[domain].append(make_json(content))
            logger.info(f"Content from {url} saved to {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to save content for {url} to file: {e}", exc_info=True)
            return False

    def cleanup_driver_quietly(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception: 
                pass
            finally:
                self.driver = None

    def cleanup(self):
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver quit successfully during final cleanup.")
            except Exception as e:
                logger.error(f"Error during final WebDriver cleanup: {e}")
            finally:
                self.driver = None

if __name__ == "__main__":
    use_gui = False
    chromedriver_executable_path = None 

    scraper = StealthChromeDriver(
        proxies=PROXIES if PROXIES else None,
        use_headless=(not use_gui),
        max_retries=2,
        chromedriver_path=chromedriver_executable_path
    )
    
    try:
        successful_articles, failed_items = scraper.multi_site_scraper(NEWS_LINK_PATTERNS)
        logger.info("-" * 50)
        logger.info("***** FINAL SCRAPING SUMMARY *****")
        logger.info(f"Successfully scraped articles: {len(successful_articles)}")
        if failed_items:
            logger.warning(f"Failed to scrape items (sites/articles): {len(failed_items)}")
        logger.info("-" * 50)
        for key in json_dict.keys():
            json_data = json.dumps(json_dict[key], ensure_ascii=False, indent=4)
            with open(f'scraped_pages/{key}.json', 'w', encoding='utf-8') as f:
                f.write(json_data)
    except SystemExit as se:
        logger.critical(f"SystemExit occurred: {se}")
    except KeyboardInterrupt:
        logger.info("Scraping process interrupted by user (KeyboardInterrupt).")
    except Exception as e:
        logger.critical(f"An uncaught critical exception in main execution: {e}", exc_info=True)
    finally:
        logger.info("Initiating final cleanup...")
        scraper.cleanup()
        logger.info("Scraping process finished.")

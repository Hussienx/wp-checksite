import requests
from bs4 import BeautifulSoup
from queue import Queue
from urllib.parse import urljoin, urlparse
from threading import Thread
from colorama import Fore, init
import concurrent.futures

# Initialize colorama
init()

# Function to check if a website uses WordPress and return its base URL
def is_wordpress(url, proxies=None):
    try:
        response = requests.get(url if url.startswith('http') else 'http://' + url, proxies=proxies, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        base_url = None

        for script in soup.find_all('script'):
            if 'wp-content' in script.get('src', ''):
                base_url = urljoin(url, script['src']).split('wp-content')[0]
                return True, base_url
        for link in soup.find_all('link'):
            if 'wp-content' in link.get('href', ''):
                base_url = urljoin(url, link['href']).split('wp-content')[0]
                return True, base_url
        return False, None
    except requests.exceptions.RequestException:
        return None, None  # Return None if a request fails

# Read the list of proxies from the file
with open('proxies.txt', 'r') as f:
    proxies_list = [f"http://{line.strip()}" for line in f]

# Put proxies in a thread-safe queue
proxies_queue = Queue()
for proxy in proxies_list:
    proxies_queue.put(proxy)

# Read the list of sites from the file
with open('sites.txt', 'r') as f:
    urls = f.read().splitlines()

# Function to check each URL
def check_url(url):
    # First, try without a proxy
    result, base_url = is_wordpress(url)
    if result is True:  # It's a WordPress site
        print(f"{Fore.GREEN}{url} is a WordPress site.{Fore.RESET}")
        with open('wordpress_sites.txt', 'a') as f:
            f.write(f"{base_url}\n")
    elif result is None:  # The request failed, try again with a proxy
        while not proxies_queue.empty():
            proxy = proxies_queue.get()
            proxies = {
                'http': proxy,
                'https': proxy,
            }
            print(f"Checking {url} using proxy {proxy}")
            result, base_url = is_wordpress(url, proxies)
            if result is True:  # It's a WordPress site
                print(f"{Fore.GREEN}{url} is a WordPress site.{Fore.RESET}")
                with open('wordpress_sites.txt', 'a') as f:
                    f.write(f"{base_url}\n")
                proxies_queue.put(proxy)  # Put the proxy back into the queue for later use
                break
            elif result is False:  # The site is not a WordPress site
                break  # No need to try other proxies
            else:  # The request failed, remove this proxy and try the next one
                print(f"Removing non-working proxy {proxy}.")
        if proxies_queue.empty():
            print("No working proxies left.")

# Use a ThreadPoolExecutor to check URLs concurrently
with concurrent.futures.ThreadPoolExecutor() as executor:
    executor.map(check_url, urls)

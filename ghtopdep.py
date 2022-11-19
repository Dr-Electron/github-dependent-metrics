# This code is based on the work of 
# https://github.com/github-tooling/ghtopdep/blob/master/ghtopdep/ghtopdep.py
# and its license

import calendar
import datetime
from email.utils import formatdate, parsedate
from urllib.parse import urlparse

import appdirs
import requests

from urllib3.util.retry import Retry
from cachecontrol.caches import FileCache
from cachecontrol.heuristics import BaseHeuristic
from cachecontrol import CacheControlAdapter
from halo import Halo
from selectolax.parser import HTMLParser

PACKAGE_NAME = "ghtopdep"
CACHE_DIR = appdirs.user_cache_dir(PACKAGE_NAME)
NEXT_BUTTON_SELECTOR = "#dependents > div.paginate-container > div > a"
ITEM_SELECTOR = "#dependents > div.Box > div.flex-items-center"
REPO_SELECTOR = "span > a.text-bold"
STARS_SELECTOR = "div > span:nth-child(1)"
GITHUB_URL = "https://github.com"

class OneDayHeuristic(BaseHeuristic):
    cacheable_by_default_statuses = {
        200, 203, 204, 206, 300, 301, 404, 405, 410, 414, 501
    }

    def update_headers(self, response):
        if response.status not in self.cacheable_by_default_statuses:
            return {}

        date = parsedate(response.headers["date"])
        expires = datetime.datetime(*date[:6]) + datetime.timedelta(days=1)
        return {"expires": formatdate(calendar.timegm(expires.timetuple())), "cache-control": "public"}

    def warning(self, response):
        msg = "Automatically cached! Response is Stale."
        return "110 - {0}".format(msg)

def already_added(repo_url, repos):
    for repo in repos:
        if repo['url'] == repo_url:
            return True

def sort_repos(repos):
    return sorted(repos, key=lambda i: i["stars"], reverse=True)

def get_dependents_packages(sess, url, destination):
    page_urls = []
    page_url = "{0}/network/dependents?dependent_type={1}".format(url, destination.upper())
    main_response = sess.get(page_url)
    parsed_node = HTMLParser(main_response.text)
    link = parsed_node.css('.select-menu-item')
    for i in link:
        package_name = i.text().strip()
        package_id = urlparse(i.attributes["href"]).query.split("=")[1]
        page_url = "{0}/network/dependents?dependent_type={1}&package_id={2}".format(
            url, 
            destination.upper(),
            package_id
        )
        page_urls.append({"name": package_name, "id": package_id, "url": page_url})

    return page_urls

def get_dependents(url, repositories, package_filter, minstar): 
    destination = "repository"
    destinations = "repositories"
    if not repositories:
        destination = "package"
        destinations = "packages"
    
    repos = []
    more_than_zero_count = 0
    total_repos_count = 0
    spinner = Halo(text="Fetching information about {0}".format(destinations), spinner="dots")
    spinner.start()

    sess = requests.session()
    retries = Retry(
        total=15,
        backoff_factor=15,
        status_forcelist=[429])
    adapter = CacheControlAdapter(max_retries=retries,
                                    cache=FileCache(CACHE_DIR),
                                    heuristic=OneDayHeuristic())
    sess.mount("http://", adapter)
    sess.mount("https://", adapter)

    packages = get_dependents_packages(sess, url, destination)

    for package in list(packages):
        if package_filter and (not package["name"] in package_filter):
            packages.remove(package)
            continue
        page_url = package["url"]
        while True:
            response = sess.get(page_url)
            parsed_node = HTMLParser(response.text)
            dependents = parsed_node.css(ITEM_SELECTOR)
            total_repos_count += len(dependents)
            for dep in dependents:
                repo_stars_list = dep.css(STARS_SELECTOR)
                # only for ghost or private? packages
                if repo_stars_list:
                    repo_stars = repo_stars_list[0].text().strip()
                    repo_stars_num = int(repo_stars.replace(",", ""))
                else:
                    continue

                if repo_stars_num != 0:
                    more_than_zero_count += 1
                if repo_stars_num >= minstar:
                    relative_repo_url = dep.css(REPO_SELECTOR)[0].attributes["href"]
                    repo_url = "{0}{1}".format(GITHUB_URL, relative_repo_url)

                    # can be listed same package
                    is_already_added = already_added(repo_url, repos)
                    if not is_already_added and repo_url != url:
                        repos.append({
                            "url": repo_url,
                            "stars": repo_stars_num
                        })

            node = parsed_node.css(NEXT_BUTTON_SELECTOR)
            if len(node) == 2:
                page_url = node[1].attributes["href"]
            elif len(node) == 0 or node[0].text() == "Previous":
                spinner.stop()
                break
            elif node[0].text() == "Next":
                page_url = node[0].attributes["href"]

        sorted_repos = sort_repos(repos)

        package["dependents"] = sorted_repos

    return packages

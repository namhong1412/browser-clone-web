# -*- coding: utf-8 -*-
# __author__ = "Hong Nguyen Nam (Jeremy Nguyen)"
# __copyright__ = "Copyright 2022, The Browser Clone"
# __license__ = "GPL"
# __version__ = "2.1.0"
# __email__ = "a2FpdG9raWQxNDEyLmNvbmFuQGdtYWlsLmNvbQ=="
__black_list_type__ = [".php"]
__status_code__ = [200, 404]
__clone_all__ = False
__zip__ = False
__headless__ = False
__clone_url__ = "https://themesbrand.com/velzon/html/default/index.html"

import os
import os.path
import re
import shutil
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from seleniumwire import webdriver
from tqdm import tqdm
from webdriver_manager.chrome import ChromeDriverManager
from zipfile36 import ZipFile


def extract_info_url(url, main=False):
    data_url = urlparse(url)
    domain = data_url.netloc
    path_file = domain.replace(".", "") + os.path.split(data_url.path)[0] + "/"
    file_name = os.path.split(data_url.path)[1]
    scheme = data_url.scheme
    url_ori = url.replace(file_name, "")
    black_list = ["", "/"]
    if main == True and file_name in black_list:
        file_name = "index.html"
    return {
        "domain": domain,
        "path": path_file,
        "file_name": file_name,
        "scheme": scheme,
        "url": url_ori,
    }


def get_all_file_paths(directory):
    file_paths = []
    for root, directories, files in os.walk(directory):
        for filename in files:
            filepath = os.path.join(root, filename)
            file_paths.append(filepath)
    return file_paths


def compress(path_folder):
    print(f"Compression files... {str(path_folder)}.zip")
    directory = path_folder
    file_paths = get_all_file_paths(directory)
    with ZipFile(f"{path_folder}.zip", "w") as zip:
        for file in file_paths:
            zip.write(file)
    print("All files zipped successfully!")


def check_invalid(file_name):
    regex = r"[a-z-0-9]+.html"
    matches = re.finditer(regex, file_name, re.MULTILINE)
    for match in matches:
        return match.group()


class File:
    info_url = ""

    def __init__(self, url):
        self.url = url
        self.info_url = extract_info_url(url, True)
        self.check_exists(url)

    def download_file(self, url, headers):
        info_url = extract_info_url(url)
        if url == self.url:
            info_url = extract_info_url(url, True)

        if info_url["file_name"][-4:] not in __black_list_type__:
            file_name = info_url["file_name"]
            black_list = ["", "/"]
            if file_name in black_list:
                file_name = "index.html"
            path_file = info_url["path"] + file_name
            if not os.path.exists(path_file):
                r = requests.get(url, headers=headers)
                os.makedirs(os.path.dirname(path_file), exist_ok=True)
                with open(path_file, "wb") as f:
                    f.write(r.content)

    def check_exists(self, url):
        info_url = extract_info_url(url)
        if info_url["domain"] != self.info_url["domain"]:
            return False
        path_file = info_url["path"] + info_url["file_name"]
        return os.path.exists(path_file) == False

    def get_all_urls_in_page(self, page_source):
        result = []
        source = BeautifulSoup(page_source, "html.parser")
        try:
            data_a = source.find_all("a")
        except Exception:
            data_a = None
        a_tag = []
        for a in data_a:
            if (
                a.get("href") != ""
                and a.get("href") != "#"
                and str(a.get("href")) not in a_tag
                and check_invalid(str(a.get("href"))) is not None
            ):
                a_tag.append(a.get("href"))

        for href in a_tag:
            domain = urlparse(href).netloc
            if domain == "":
                if len(href.split("../")) > 1:
                    cut = self.info_url["url"].split(
                        "/")[-(len(href.split("../"))):]
                    link = self.info_url["url"]
                    for text in cut:
                        if text != "":
                            link = link.replace(f"{str(text)}/", "")
                    result.append(link + href.replace("../", ""))
                elif href[:1] == "/":
                    link = re.split("[\/]+", self.info_url["url"])[:2]
                    link = f"{str(link[0])}//{str(link[1])}"
                    result.append(link + href)
                else:
                    result.append(self.info_url["url"] + href)
            if domain == self.info_url["domain"]:
                result.append(href)
        return result


class BrowserClone(File):
    driver = ""
    page_source = ""
    all_url = []
    url_down = []
    headers = {}

    def __init__(self, url):
        super().__init__(url)
        self.url = url
        self.open_browser()

    def open_browser(self):
        print("============================== Begin ==============================")
        options = webdriver.ChromeOptions()
        if __headless__:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_experimental_option("useAutomationExtension", False)
        options.add_experimental_option(
            "excludeSwitches", ["enable-automation"])
        options.page_load_strategy = "none"

        self.driver = webdriver.Chrome(
            chrome_options=options, executable_path=ChromeDriverManager().install()
        )
        self.driver.get(self.url)
        print("Waiting 30s to make sure the page has finished loading...")
        time.sleep(30)
        self.set_page_source()
        self.extract_file()

        print("Getting all the links to crawl...")
        all_urls_in_page = super().get_all_urls_in_page(self.page_source)
        for url_in_page in all_urls_in_page:
            self.all_url.append(url_in_page)
            self.extract_html(url_in_page)

        # clone options
        if __clone_all__:
            all_url = list(set(self.all_url))
            for url in all_url:
                self.driver.get(url)
                self.extract_file()

        print("Get all the links done!")
        self.extract_file(True)

        if __zip__:
            url_info = extract_info_url(self.url, True)
            folder = "./" + url_info["domain"].replace(".", "")
            compress(folder)
            try:
                shutil.rmtree(folder, ignore_errors=True)
            except OSError as e:
                print(f"Error: {folder} : {e.strerror}")
        print("============================== End Game ==============================")

    def extract_html(self, url):
        super().__init__(url)
        self.driver.get(url)
        self.set_page_source()
        all_urls_in_page = super().get_all_urls_in_page(self.page_source)
        for url_in_page in all_urls_in_page:
            self.all_url.append(url_in_page)
            self.headers = self.driver.requests[0].headers

    def extract_file(self, down=False):
        for request in self.driver.requests:
            if (
                request.response
                and request.response.status_code in __status_code__
                and request.url not in self.url_down
            ):
                self.url_down.append(request.url)
        if down:
            print("Save files...")
            super().__init__(self.url)
            data = list(set(self.url_down))
            with tqdm(total=len(data)) as pbar:
                for file in data:
                    if super().check_exists(file):
                        super().download_file(file, self.headers)
                    pbar.update(1)
            print("Save files Done!")

    def set_page_source(self):
        for _ in range(5):
            try:
                self.driver.switch_to.alert.accept()
            except Exception:
                continue
        self.page_source = self.driver.page_source


BrowserClone(__clone_url__)

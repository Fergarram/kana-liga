#!/usr/bin/env python3
# Downloads the pinned Noto Sans JP Regular (static CFF, CID-keyed) and its
# OFL license from the noto-cjk release tag into source/.
#
# usage: fetch-source.py

import os
import urllib.request

#
# Constants
#

ROOT = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.join(ROOT, "source")

TAG = "Sans2.004"
BASE_URL = f"https://github.com/notofonts/noto-cjk/raw/{TAG}"

FILES = [
    (f"{BASE_URL}/Sans/SubsetOTF/JP/NotoSansJP-Regular.otf", "NotoSansJP-Regular.otf"),
    (f"{BASE_URL}/LICENSE", "OFL.txt"),
]

#
# Functions
#

def main():
    os.makedirs(SOURCE_DIR, exist_ok=True)
    for url, name in FILES:
        path = os.path.join(SOURCE_DIR, name)
        if os.path.exists(path):
            print(f"have {name}")
            continue
        print(f"get  {url}")
        urllib.request.urlretrieve(url, path)


#
# Code execution
#

if __name__ == "__main__":
    main()

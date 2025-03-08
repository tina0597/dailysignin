import json
import os
import re

import requests
import urllib3

from dailysignin import CheckIn

urllib3.disable_warnings()


class FnOS(CheckIn):
    name = "飞牛社区论坛"

    def __init__(self, check_item: dict):
        self.check_item = check_item
        self.contentid = "27259341"
        self.st = None

    def main(self):

        msg = self.contentid
        return msg

if __name__ == "__main__":
    with open(
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json"),
        encoding="utf-8",
    ) as f:
        datas = json.loads(f.read())
    _check_item = datas.get("FnOS", [])[0]
    print(FnOS(check_item=_check_item).main())

import json
import os
import re

import requests
import urllib3
from bs4 import BeautifulSoup
from dailysignin import CheckIn

urllib3.disable_warnings()


class FnOS(CheckIn):
    name = "飞牛社区论坛"

    def __init__(self, check_item: dict):
        self.fn_sign = None
        self.required_cookies = None

        self.parse_cookie(check_item)

    # 解析Cookie获取关键参数
    def parse_cookie(self,cookie):
        fn_cookie = {
            item.split("=")[0]: item.split("=")[1]
            for item in cookie.get("fn_cookie").split(";")
        }


        self.fn_sign = cookie.get("fn_sign")
        self.required_cookies = {
            'pvRK_2132_saltkey': fn_cookie.get("pvRK_2132_saltkey"),
            'pvRK_2132_auth': fn_cookie.get("pvRK_2132_auth")
        }

    def main(self):
        return self.sign_in()

    def sign_in(self):
        """
        执行签到操作，处理三种状态：
        1. 签到成功 2. 已签到 3. 签到失败
        """
        try:
            # 构建签到请求URL（需要签名参数）
            sign_url = f'https://club.fnnas.com/plugin.php?id=zqlj_sign&sign={self.fn_sign}'
            response = requests.get(sign_url, cookies=self.required_cookies)

            if '恭喜您，打卡成功！' in response.text:
                print('✅ 签到成功')
                msg = self.get_sign_in_info()
            elif '您今天已经打过卡了' in response.text:
                print('⏰ 今日已签到')
                msg = self.get_sign_in_info()
            else:
                error_msg = '❌ 失败：Cookie可能失效或网站改版'
                print(error_msg)
                # push_message('飞牛签到失败', error_msg)
                msg = [
                    {
                        "name": "飞牛签到失败",
                        "value": error_msg,
                    }
                ]

        except Exception as e:
            error_msg = f'🚨 请求异常：{str(e)}'
            print(error_msg)
            # push_message('飞牛签到异常', error_msg)
            msg = [
                {
                    "name": "飞牛签到异常",
                    "value": error_msg,
                }
            ]
        return msg

    def get_sign_in_info(self):
        """
        获取签到详情数据并推送
        使用CSS选择器定位关键数据
        """
        try:
            response = requests.get('https://club.fnnas.com/plugin.php?id=zqlj_sign',
                                    cookies=self.required_cookies)
            soup = BeautifulSoup(response.text, 'html.parser')

            # 定义需要抓取的数据项和对应CSS选择器
            target_data = {
                '最近打卡': 'li:-soup-contains("最近打卡")',
                '本月打卡': 'li:-soup-contains("本月打卡")',
                '连续打卡': 'li:-soup-contains("连续打卡")',
                '累计打卡': 'li:-soup-contains("累计打卡")',
                '累计奖励': 'li:-soup-contains("累计奖励")',
                '最近奖励': 'li:-soup-contains("最近奖励")',
                '当前等级': 'li:-soup-contains("当前打卡等级")',
            }

            # 提取并格式化数据
            result = []
            for name, selector in target_data.items():
                element = soup.select_one(selector)
                if element:
                    # 提取文本并分割出数值部分
                    text = element.get_text().split('：')[-1].strip()
                    result.append(f'{name}: {text}')

            # 推送格式化后的消息
            if result:
                msg_content = '\n'.join(result)
                print('📊 签到详情：\n' + msg_content)
                msg = [
                    {
                        "name": '飞牛签到成功',
                        "value": msg_content,
                    }
                ]
                # push_message('飞牛签到成功', msg_content)  # PUSH消息推送
            else:
                raise Exception('未找到签到数据，页面结构可能已变更')

        except Exception as e:
            error_msg = f'抓取详情失败：{str(e)}'
            print(error_msg)
            msg = [
                {
                    "name": '飞牛签到详情异常',
                    "value": error_msg,
                }
            ]

            # push_message('飞牛签到详情异常', error_msg)
        return msg

if __name__ == "__main__":
    with open(
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json"),
        encoding="utf-8",
    ) as f:
        datas = json.loads(f.read())
    _check_item = datas.get("FnOS", [])[0]
    print(FnOS(check_item=_check_item).main())

import argparse
import json
import os
import time
from datetime import datetime, timedelta
import threading
import requests

from dailysignin.__version__ import __version__
from dailysignin.configs import checkin_map, get_checkin_info, get_notice_info
from dailysignin.utils.message import push_message


# 解析命令行参数
def parse_arguments():
    # 创建 ArgumentParser 对象，用于解析命令行参数
    parser = argparse.ArgumentParser()
    # 添加 --include 参数，用于指定要执行的任务列表
    parser.add_argument("--include", nargs="+", help="任务执行包含的任务列表")
    # 添加 --exclude 参数，用于指定要排除的任务列表
    parser.add_argument("--exclude", nargs="+", help="任务执行排除的任务列表")
    # 解析命令行参数并返回结果
    return parser.parse_args()


# 检查配置文件并获取任务信息
def check_config(task_list):
    config_path = None
    config_path_list = []
    # 遍历可能的配置文件路径
    for one_path in [
        "/ql/scripts/config.json",
        "config.json",
        "../config.json",
        "./config/config.json",
        "../config/config.json",
        "/config.json",
    ]:
        # 拼接当前工作目录和配置文件路径
        _config_path = os.path.join(os.getcwd(), one_path)
        # 如果配置文件存在，则设置 config_path 并退出循环
        if os.path.exists(_config_path):
            config_path = os.path.normpath(_config_path)
            break
        # 将配置文件所在目录添加到 config_path_list 中
        config_path_list.append(os.path.normpath(os.path.dirname(_config_path)))
    # 如果找到了配置文件
    if config_path:
        print("使用配置文件路径:", config_path)
        # 打开配置文件并读取内容
        with open(config_path, encoding="utf-8") as f:
            try:
                # 解析 JSON 格式的配置文件
                data = json.load(f)
            except Exception:
                # 如果 JSON 格式错误，打印错误信息并返回
                print("Json 格式错误，请检查 config.json 文件格式是否正确！")
                return False, False
        try:
            # 从配置文件中获取通知信息
            notice_info = get_notice_info(data=data)
            # 从配置文件中获取签到信息
            _check_info = get_checkin_info(data=data)
            check_info = {}
            # 遍历任务列表，过滤出有效的签到信息
            for one_check, _ in checkin_map.items():
                if one_check in task_list:
                    if _check_info.get(one_check.lower()):
                        for _, check_item in enumerate(
                            _check_info.get(one_check.lower(), [])
                        ):
                            # 过滤掉无效的签到信息（如 "xxxxxx" 或 "多账号"）
                            if "xxxxxx" not in str(check_item) and "多账号" not in str(
                                check_item
                            ):
                                if one_check.lower() not in check_info.keys():
                                    check_info[one_check.lower()] = []
                                check_info[one_check.lower()].append(check_item)
            # 返回通知信息和签到信息
            return notice_info, check_info
        except Exception as e:
            # 如果发生异常，打印错误信息并返回
            print(e)
            return False, False
    else:
        # 如果未找到配置文件，打印提示信息并返回
        print(
            "未找到 config.json 配置文件\n请在下方任意目录中添加「config.json」文件:\n"
            + "\n".join(config_path_list)
        )
        return False, False

def perform_checkin(check_name, check_func, check_item, index, notice_info):
    try:
        # 执行签到函数并获取结果
        msg = check_func(check_item).main()
        # 推送签到结果
        push_message(content_list=[f"「{check_name}」\n{msg}"], notice_info=notice_info)
        print(f"第 {index + 1} 个账号: ✅✅✅✅✅ msg-->", msg)
    except Exception as e:
        # 如果签到失败，推送错误信息
        push_message(content_list=[f"「{check_name}」\n{e}"], notice_info=notice_info)
        print(f"第 {index + 1} 个账号: ❌❌❌❌❌\n{e}")

# 主函数，执行签到任务
def checkin():
    # 记录开始时间
    start_time = time.time()
    # 获取当前时间（UTC+8）
    utc_time = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    # 打印当前时间和版本信息
    print(f"当前时间: {utc_time}\n当前版本: {__version__}")
    # 解析命令行参数
    args = parse_arguments()
    include = args.include
    exclude = args.exclude

    # 如果没有指定 --include 参数，则默认执行所有任务
    if not include:
        include = list(checkin_map.keys())
    else:
        # 过滤掉不在 checkin_map 中的任务
        include = [one for one in include if one in checkin_map.keys()]
    # 如果没有指定 --exclude 参数，则默认不排除任何任务
    if not exclude:
        exclude = []
    else:
        # 过滤掉不在 checkin_map 中的任务
        exclude = [one for one in exclude if one in checkin_map.keys()]
    # 计算最终要执行的任务列表
    task_list = list(set(include) - set(exclude))
    # 检查配置文件并获取通知信息和签到信息
    notice_info, check_info = check_config(task_list)
    # 如果有有效的签到信息
    if check_info:
        # 格式化任务名称和账号数量
        task_name_str = "\n".join(
            [
                f"「{checkin_map.get(one.upper())[0]}」账号数 : {len(value)}"
                for one, value in check_info.items()
            ]
        )
        # 打印本次执行的签到任务
        print(f"\n---------- 本次执行签到任务如下 ----------\n\n{task_name_str}")

        # 创建一个线程列表
        threads = []
        content_list = []
        # 遍历每个任务和对应的签到信息
        for one_check, check_list in check_info.items():
            # 获取任务名称和对应的签到函数
            check_name, check_func = checkin_map.get(one_check.upper())
            print(f"\n\n----------开始执行「{check_name}」签到----------")
            # 遍历每个账号的签到信息
            for index, check_item in enumerate(check_list):
                # 创建线程并启动
                thread = threading.Thread(target=perform_checkin,
                                          args=(check_name, check_func, check_item, index, notice_info))
                thread.start()
                threads.append(thread)
            # 等待所有线程完成
            for thread in threads:
                thread.join()

        print("\n\n")
        try:
            # 获取最新版本信息
            url = "https://pypi.org/pypi/dailysignin/json"
            latest_version = requests.get(url=url, timeout=30).json()["info"]["version"]
        except:
            # 如果获取最新版本失败，则使用默认版本
            print("获取最新版本失败")
            latest_version = "0.0.0"
        # 将任务执行的时间、用时、版本信息等添加到内容列表中
        content_list.append(
            f"开始时间: {utc_time}\n"
            f"任务用时: {int(time.time() - start_time)} 秒\n"
            f"当前版本: {__version__}\n"
            f"最新版本: {latest_version}\n"
            f"项目地址: https://github.com/tina0597/dailysignin"
        )

        # print(1111,content_list[0])
        # print(22222,content_list[1])
        # 推送消息
        # push_message(content_list=content_list, notice_info=notice_info)
        return


# 主程序入口
if __name__ == "__main__":
    checkin()
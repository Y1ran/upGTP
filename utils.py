import datetime
import random
import sys
import time


def cal_timediff(t1, t2):
    dt1 = datetime.datetime.utcfromtimestamp(t1)
    dt2 = datetime.datetime.utcfromtimestamp(t2)
    return (dt2 - dt1).days


def timestamp_format(timestamp: int):
    timeArray = time.localtime(timestamp)
    return time.strftime("%Y年%m月%d日", timeArray)


def immediate_print(text):
    for i in text:
        print(i, end="")
        sys.stdout.flush()
        time.sleep(random.random() / 20)
    print("\n")


def floor(number):
    return round(number, 1)

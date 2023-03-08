import datetime
import json
import logging
import os
import random
import sys
import time
from utils import floor

from lxml import etree
import openai
import requests
from jsonlines import jsonlines
from anti_useragent import UserAgent  # pip install -U anti-useragent
# from fake_useragent import UserAgent
from utils import cal_timediff, timestamp_format, immediate_print

TEST_RESULT = "./testLog/test"
uuid = 371846699

os.environ["OPENAI_API_KEY"] = "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"
import argparse

parser = argparse.ArgumentParser(description='inputs args batch')
parser.add_argument('--batch', nargs='?', const=10000, default=10000, type=int, help='input batch number')
parser.add_argument('--time', nargs='?', const=20, default=10, type=int, help='input api wait time')
parser.add_argument('--prompt', nargs='?', const="", default="", type=str, help='input your prompt')

# args = parser.parse_args()
args = []
os.environ['CUDA_VISIBLE_DEVICES'] = '0'
os.environ["http_proxy"] = "127.0.0.1:7890"
os.environ["https_proxy"] = "127.0.0.1:7890"


class BilibiliUpGPT(object):
    """
    generate dataset pair and finetuned GPT model for HootGPT web-side
        - fetch raw data from bilibili scrawler and open-source repo
        - union all dataset for prompt inputs
        - generate related QA pair from ChatGPT API
        - save those QA pair into GPT tables for
    """

    def __init__(self, uuid):
        self.suffix = None
        self.raw_text = []
        self.dataset = {}
        self.querydict = {}
        self.data_size = 0
        self.raw_data = {}
        self.agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36"
        self.uuid = uuid
        self.learning_rate = 0.1
        self.prompt = """please raise some related question-answer pairs according to the following content: """
        # self.con = DBConnector(ssh_tunnel=True)
        self.all_ip_list = []  # 用于存放从网站上抓取到的ip
        self.usable_ip_list = []  # 用于存放通过检测ip后是否可以使用
        self.result = ""

    def __repr__(self):
        f"""generate dataset pair and finetuned GPT model for HootGPT web-side"""

    """
        Part I - generate qa dataset based on ChatGPT
    """

    def _proxies_request(self, url, parameters):
        response = ""
        proxies = {
            "http": "https://" + random.choice(self.usable_ip_list),
            # "https": "http://" + proxy,
            # "http": proxy,
            # "https": proxy,
        }
        try:
            response = requests.get(url, params=parameters, headers=self.set_headers(), proxies=proxies, verify=True)
        except Exception as e:
            logging.error(e)
            print(f"dict get value error: {e}.")

        return response

    def get_video_response(self):

        response = ""
        # curl -G 'https://api.bilibili.com/x/space/top/arc' \
        #         --data-urlencode 'vmid=23215368'
        # url = 'https://api.bilibili.com/x/space/top/arc'

        url = f"https://api.bilibili.com/x/space/wbi/arc/search?mid={self.uuid}"
        headers = {
            'user-agent': self.agent}

        # submit GET curl request
        parameters = {'ps': "30",
                      'tid': "0",
                      'keyword': "",
                      'order': "pubdate",
                      'order_avoided': "true"
                      }

        return self._proxies_request(url, parameters)

    def get_user_response(self):

        url = f"https://api.bilibili.com/x/web-interface/card?mid={self.uuid}"
        try:
            # submit GET curl request
            parameters = {
                "photo": 'false'
            }

        except Exception as e:
            logging.error(e)
            print(f"dict get value error: {e}.")

        return self._proxies_request(url, parameters)

    def get_acc_response(self, mid):

        if mid != "":
            url = f"https://api.bilibili.com/x/space/acc/info?mid={mid}"
        else:
            url = f"https://api.bilibili.com/x/space/acc/info?mid={self.uuid}"

        parameters = {
            "photo": 'false'
        }

        return self._proxies_request(url, parameters)

    def get_relation_response(self):

        url = f"https://api.bilibili.com/x/relation/followings"

        # submit GET curl request
        parameters = {
            "order_type": 'attention',
            "vmid": self.uuid
        }

        return self._proxies_request(url, parameters)

    def get_follower_response(self):

        url = f"https://api.bilibili.com/x/relation/followers"

        # submit GET curl request
        parameters = {
            # "order_type": 'attention',
            "vmid": self.uuid,
            "ps": 250,
            "pn": 1
        }

        return self._proxies_request(url, parameters)

    def get_vstat_response(self, avid):

        url = f"https://api.bilibili.com/archive_stat/stat"

        # submit GET curl request
        parameters = {
            "aid": avid
        }

        return self._proxies_request(url, parameters)


    @staticmethod
    def eval_chat(knowledge, inputs: str) -> str:
        """
        测试finetuned模型的生成结果质量
        :param: self.image_dict
        :return:
        """
        # result = HootGPTTrainingProcessor.topsim_questions(filename, inputs)
        openai.api_key = "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"
        os.environ["http_proxy"] = "127.0.0.1:7890"
        os.environ["https_proxy"] = "127.0.0.1:7890"

        if "。" not in inputs:
            prompt = inputs + "。"
        else:
            prompt = inputs

        # HootGPTTrainingProcessor.eval_ask(prompt)
        # Make a request to the ChatGPT API
        messages = [dict(role="system",
                         content=f"You are Bilibili assistant, answer user's question in Chinese based on following"
                                 f"knowledge: {knowledge} If you don't know the answer,please say '非常抱歉，我还没有学习这些信息哦~"),
                    {"role": 'user', "content": prompt}]

        # for pair in result:
        #     messages.append({"role": 'user', "content": pair[0].split("###")[0]})
        #     messages.append({"role": 'assistant', "content": pair[0].split("###")[1]})

        # print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Load {len(messages[0]['content'])} tokens.")
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.75,
            max_tokens=1949,
            top_p=1,
            frequency_penalty=1,
            presence_penalty=0,
        )

        # save to log
        with jsonlines.open(TEST_RESULT + f"{datetime.datetime.now().strftime('%Y-%m-%d-%H')}" + ".jsonl",
                            mode='a') as writer:
            answer = response["choices"][0]["message"]['content'].strip()
            immediate_print(f"{answer}")
            writer.write({"Q": inputs, "A": answer})
            return answer

    def generate_prompt(self):
        # s = json.dumps({'key1': 'value1', 'key2': 'value2'})
        # r = requests.post(url, data=s)
        video_response = self.get_video_response()
        user_response = self.get_user_response()
        acc_response = self.get_acc_response("")
        relation_response = self.get_relation_response()

        # 获取用户粉丝数/关注数
        json_data = json.loads(user_response.text)
        follower_count = json_data['data']['follower']
        uploader = json_data['data']['card']['name']
        article_count = json_data['data']['archive_count']
        result = f"""UP主{uploader}目前拥有{follower_count}关注者。"""

        # 获取UP主详细信息
        json_data = json.loads(acc_response.text)
        try:
            sexual = json_data['data']['sex']
            sign = json_data['data']['sign']
            if json_data['data']['official'] is not None:
                official = json_data['data']['official']['title']
            birthday = json_data['data']['birthday']
            school = json_data['data']['school']['name']
            if sexual is not None:
                result += f"""UP主{uploader}性别为{sexual}。"""
            if sign is not None:
                result += f"""UP主{uploader}的简介为{sign}。"""
            if official is not None:
                result += f"""UP主{uploader}的认证信息为{official}。"""
            if birthday is not None:
                result += f"""UP主{uploader}的生日为{birthday}。"""
            if school is not None:
                result += f"""UP主{uploader}的学校为{school}。"""
        except Exception as e:
            logging.warning(f"occurs data miss due to {e}")
        result += f"""今年是2023年，UP主{uploader}一共在"""

        json_data = json.loads(video_response.text)
        tid_list = [(x['name'], x['count']) for x in json_data['data']['list']['tlist'].values()]

        for tid in tid_list:
            channel = tid[0]
            count = int(tid[1])
            result += f"{channel}区投稿了{count}个视频，"
        # print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 累计投稿{article_count}个视频。")

        result += f"累计投稿{article_count}个视频。"

        # 获取视频基本信息
        video_list = json_data['data']['list']['vlist']
        result += f"UP最近投稿的10个视频分别为:"
        count = 1
        for video in video_list[:10]:
            title = video['title']  # 标题
            view = video['play']  # 播放量
            comments = video['comment']  # 评论数
            video_length = video['length']  # 视频时长 mm:ss
            video_desc = video['description']  # 视频简介
            created_at = timestamp_format(video['created'])  # 发布时间
            result += f"{count}.{title}，投稿于{created_at}，视频长度{video_length}，截止{datetime.datetime.now().hour}点" \
                      f"{datetime.datetime.now().minute}分播放量为{view}，评论数为{comments},"
            count += 1

            vid = video['aid']
            tmp = json.loads(self.get_vstat_response(avid=vid).text)

            try:
                danmaku = tmp['data']['danmaku']
                favorite = tmp['data']['favorite']
                coin = tmp['data']['coin']
                share = tmp['data']['share']
                like = tmp['data']['like']
                his_rank = tmp['data']['his_rank']
            except Exception as e:
                continue
            result += f"弹幕数为{danmaku}，收藏数为{favorite}，收藏率{floor(favorite / view * 100)}%；投币数为{coin}，投币率{floor(coin / view * 100)}%；" \
                      f"分享数为{share}，分享率{floor(share / view * 100)}%；点赞数为{like}，点赞率{floor(like / view * 100)}%；全站最高历史排名{his_rank}。 "

        # 获取UP主关注列表
        json_data = json.loads(relation_response.text)
        rel_list = json_data['data']['list']
        result += f"UP最近关注的B站用户分别为:"
        for friend in rel_list[:3]:
            mtime = cal_timediff(friend['mtime'], datetime.datetime.now().timestamp())
            if friend['special'] == 0:
                spec = "不是UP的特别关注"
            else:
                spec = "是UP的特别关注"
            uname = friend['uname']
            if friend['attribute'] == 6:
                attribute = "已经互粉"
            else:
                attribute = "并没有互粉"
            result += f"{uname}，已经关注了{mtime}天，{spec}，他们{attribute}。"

        # 获取UP主粉丝采样
        level_list = []
        sign_list = []
        follower_list = json.loads(self.get_follower_response().text)['data']['list']
        for follower in follower_list[:100]:
            mid = follower['mid']
            tmp = json.loads(self.get_acc_response(mid=mid).text)
            try:
                level_list.append(tmp['data']['level'])
                sign_list.append(tmp['data']['sign'])
            except Exception as e:
                continue

        a = [x for x in level_list if x == 0]
        b = [x for x in level_list if x == 1]
        c = [x for x in level_list if x >= 2]
        result += f"最近的新增关注中，有{floor(len(a) / len(level_list) * 100)}%是0级用户," \
                  f"{floor(len(b) / len(level_list) * 100)}%是1级用户,{floor(len(c) / len(level_list) * 100)}%是2级以上用户。"

        self.result = result

    def request_header(self):
        headers = {
            'User-Agent': UserAgent().random #常见浏览器的请求头伪装（如：火狐,谷歌）
            # 'User-Agent': UserAgent().Chrome  # 谷歌浏览器
        }
        return headers

    def set_headers(self, platform='windows', browser_type='chrome', min_version=80, max_version=100):
        headers = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,"
                             "*/*;q=0.8,application/signed-exchange;v=b3;q=0.9", "Accept-Language": "zh-CN,zh;q=0.9",
                   "Cache-Control": "no-cache", "Connection": "keep-alive", "Pragma": "no-cache",
                   "sec-ch-ua-platform": "\"Windows\"",
                   'User-Agent': UserAgent(platform=platform, min_version=min_version, max_version=max_version)[
                       browser_type]}
        return headers

    '''
    创建两个列表用来存放代理ip
    '''
    def send_request(self):
        for i in range(1, 100):
            print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 正在抓取第{i}页……")
            response = requests.get(url=f'http://www.ip3366.net/free/?page={i}', headers=self.set_headers())
            text = response.text.encode('ISO-8859-1')
            # print(text.decode('gbk'))
            html = etree.HTML(text)
            tr_list = html.xpath('/html/body/div[2]/div/div[2]/table/tbody/tr')
            for td in tr_list:
                ip_ = td.xpath('./td[1]/text()')[0]  # ip
                port_ = td.xpath('./td[2]/text()')[0]  # 端口
                proxy = ip_ + ':' + port_  # 115.218.5.5:9000
                self.all_ip_list.append(proxy)
                self.test_ip(proxy)  # 开始检测获取到的ip是否可以使用
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 抓取完成")
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 抓取到的ip个数为：{len(self.all_ip_list)}")
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 可以使用的ip个数为：{len(self.usable_ip_list)}")

    def test_ip(self, proxy):
        # 构建代理ip
        proxies = {
            "http": "https://" + proxy,
            # "https": "http://" + proxy,
            # "http": proxy,
            # "https": proxy,
        }
        try:
            response = requests.get(url='https://www.baidu.com/', headers=self.set_headers(), proxies=proxies,
                                    timeout=1)  # 设置timeout，使响应等待1s
            response.close()
            if response.status_code == 200:
                self.usable_ip_list.append(proxy)
                print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {proxy} \033[31m可用\033[0m.")
            else:
                print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {proxy} 不可用.")
        except Exception as e:
            print(proxy, f'请求异常{e}')


def test():
    upgpt = BilibiliUpGPT(uuid)
    upgpt.send_request()
    upgpt.generate_prompt()

    while True:
        inputs = input("请输入你的问题：")
        upgpt.eval_chat(inputs)


if __name__ == "__main__":
    test()

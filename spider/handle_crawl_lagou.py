#模拟请求

import requests,re,time,json
import multiprocessing
from spider.handle_insert_data import  lagou_mysql

class HandleLaGou(object):
    def __init__(self):
        #使用session保存cookies信息
        self.lagou_session = requests.session()
        self.header = {
            'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36'
        }
        self.city_list = ""

    #获取全国城市列表
    def handle_city(self):
        city_search = re.compile(r'www\.lagou\.com\/.*\/">(.*?)</a>') #www\.lagou\.com\/.*\/">(.*?)</a>     zhaopin/">(.*?)</a>
        city_url = "https://www.lagou.com/jobs/allCity.html"
        city_result = self.handle_request(method="GET", url=city_url)
        #使用正则表达式获取城市列表
        self.city_list = city_search.findall(city_result)
        #手动清除所有session信息
        self.lagou_session.cookies.clear()

    def handle_city_job(self,city):
        first_request_url="https://www.lagou.com/jobs/list_python/p-city_%d?&cl=false&fromSearch=true&labelWords=&suginput="%city
        #发送get请求
        first_response = self.handle_request(method="GET",url=first_request_url)
        total_page_search = re.compile(r'class="span\stotalNum">(\d+)</span>')
        try:
            total_page = total_page_search.search(first_response).group(1)
        #由于没有岗位信息造成的exception
        except:
            return "无"
        else:
            for i in range(1,int(total_page)+1):
                data={
                    "pn":i,
                    "kd":"python"
                }
                page_url="https://www.lagou.com/jobs/positionAjax.json?px=default&city=%s&needAddtionalResult=false"%self.city_list[city]
                #必须携带referer信息，否则会被发现,还需要encode
                referer_url="https://www.lagou.com/jobs/list_python/p-city_%d?&cl=false&fromSearch=true&labelWords=&suginput="%city
                self.header["Referer"]=referer_url.encode()
                #发送post请求
                response = self.handle_request(method="POST",url=page_url,data=data,info=city)
                lagou_data=json.loads(response)
                job_list=lagou_data['content']['positionResult']['result']
                for job in job_list:
                    #print(job)
                    lagou_mysql.insert_item(job)
                #print(response)

    def handle_request(self,method,url,data=None,info=None):
        while True:
            '''
            #加入阿布云的动态代理 这里可以自己注册一个
            proxyinfo = "http://%s:%s@%s:%s" % ('H1V32R6470A7G90D', 'CD217C660A9143C3', 'http-dyn.abuyun.com', '9020')
            proxy = {
                "http":proxyinfo,
                "https":proxyinfo
            }
            try:
                if method == "GET":
                    response = self.lagou_session.get(url=url,headers=self.header,proxies=proxy,timeout=6)
                    # response = self.lagou_session.get(url=url,headers=self.header,timeout=6)
                elif method == "POST":
                    response = self.lagou_session.post(url=url,headers=self.header,data=data,proxies=proxy,timeout=6)
                    # response = self.lagou_session.post(url=url,headers=self.header,data=data,timeout=6)
            except:
                # 需要先清除cookies信息
                self.lagou_session.cookies.clear()
                # 重新获取cookies信息
                first_request_url = "https://www.lagou.com/jobs/list_python?city=%s&cl=false&fromSearch=true&labelWords=&suginput=" % info
                self.handle_request(method="GET", url=first_request_url)
                time.sleep(10)
                continue
            response.encoding = 'utf-8'
            '''
            if method == "GET":
                response = self.lagou_session.get(url=url, headers=self.header)
            elif method == "POST":
                response = self.lagou_session.post(url=url, headers=self.header, data=data)
            
            response.encoding = 'utf-8'

            if '频繁' in response.text:
                #需要先清除cookies信息
                self.lagou_session.cookies.clear()
                #重新获取cookies信息
                first_request_url = "https://www.lagou.com/jobs/list_python/p-city_%d?&cl=false&fromSearch=true&labelWords=&suginput=" % info
                self.handle_request(method="GET", url=first_request_url)
                #休眠10s后，继续请求
                time.sleep(2)
                continue

            return response.text

if __name__ == '__main__':
    lagou = HandleLaGou()
    lagou.handle_city()#所有城市的方法
    #创建一个进程池 4代表一个进程池里面有4个进程;引入多进程加速抓取
    pool= multiprocessing.Pool(4)
    for city in range(1,len(lagou.city_list)):
        #把数据提交到进程池;使用非阻塞方法
        pool.apply_async(lagou.handle_city_job, args=(city,))
        #print(city)
    #print(lagou.city_list)
    pool.close()
    pool.join()


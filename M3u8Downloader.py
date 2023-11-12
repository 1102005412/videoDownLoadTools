import requests
import re
import math
import time
import os

class M3U8Downloader:

    def __download_ts_list(self,tsList,outputPath):
        allNum = len(tsList)
        print("allNum = %d" % (allNum))
        finished = 0
        for ts in tsList:
            fileName = ts.split('?')[0];
            if(os.path.exists(outputPath + "/" + fileName)):
                finished = finished + 1
                print("%s已存在，跳过 (%d / %d)" % (fileName,finished,allNum))
                continue

            ret = self.__try_get_url(self.__downUrl + ts)
            if(ret.status_code != 200):
                print("%s下载失败%d，跳过 (%d/%d)" % (fileName,ret.status_code,finished,allNum))

            with open(outputPath + "/" + fileName, "ab") as code:
                code.write(ret.content)
                finished = finished + 1
                print("%s下载成功 (%d/%d)" % (fileName,finished,allNum))
        
        print("%s下载完成" % (outputPath))
        


    def __get_ts_list(self,m3u8Data):
        m3u8Data = m3u8Data.replace('\r','')
        lines = m3u8Data.split('\n')
        ts = []
        for i in lines:
            if ".ts" in i:
                ts.append(i)
        return ts

    def __try_get_url(self,url):
        count = 0
        while True:
            try:
                count += 1
                print("第%d次尝试..." % (count))
                res = requests.get(url)
                return res
            except Exception as e:
                print("we catch an exception,wait 500 ms again!")
                print(e)
                time.sleep(0.5)
    
    def __download_m3u8_file(self,m3u8Url,outputPath):
        m3u8UrlSplit = m3u8Url.split('/')
        m3u8FileName = m3u8UrlSplit.pop().split('?')[0]

        if os.path.exists(outputPath):
            pass
        else:
            os.mkdir(outputPath)

        ret = self.__try_get_url(m3u8Url)
        if(ret.status_code != 200):
            print("%s下载失败" % (m3u8FileName))
            return None

        lines = ret.text.split('\n')
        u3m8file = open(outputPath + "/" + m3u8FileName, "wt")
        if u3m8file == None:
            print("%s 创建失败" % (m3u8FileName))
            return None
        for line in lines:
            if ".ts" in line:
                u3m8file.write(line.split('?')[0] + "\n")
            else:
                u3m8file.write(line + "\n")
        u3m8file.close()
        
        print("%s下载成功" % (m3u8FileName))

        self.__downUrl = ""
        for i in m3u8UrlSplit:
            self.__downUrl += i + "/"

        return ret.text

    def down(self,m3u8Url,outputPath):
        m3u8Data = self.__download_m3u8_file(m3u8Url,outputPath)
        if(None == m3u8Data):
            return
        
        tsList = self.__get_ts_list(m3u8Data)
        self.__download_ts_list(tsList,outputPath)

        # if(!self)
        # ts_list = get_ts_list(m3_path)
        # combine_url_and_download(ts_list,urlpath,outputPath)


if __name__ == '__main__':
    a = M3U8Downloader()
    #a.down("https://dv-h.phncdn.com/hls/videos/202212/21/421792331/,1080P_4000K,720P_4000K,480P_2000K,240P_1000K,_421792331.mp4.urlset/index-f1-v1-a1.m3u8?ttl=1698768235&l=0&ipa=149.104.96.17&hash=c816c1801755de8bb3ca89d84184560e","./123")
    #a.down("https://ev-h.phncdn.com/hls/videos/202303/07/426913121/,1080P_4000K,720P_4000K,480P_2000K,240P_1000K,_426913121.mp4.urlset/index-f1-v1-a1.m3u8?validfrom=1698766967&validto=1698774167&ipa=149.104.96.17&hdl=-1&hash=XLoMap%2BiGb6zVAvGTuQkILUMAZU%3D","./123")
    a.down("https://qq.iqiyi2.b555b.com:7777/7f/7f49dcd0c6b118a6e026742774e04bb28100d3ed/hd.m3u8","./pacopacomama_110222_730")

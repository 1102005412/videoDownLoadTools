import requests
import re
import math
import time
import os
import threading
import subprocess
import msvcrt
#import ffmpeg    #这个库还是需要依赖ffmpeg，不如直接调ffmpeg命令行

class M3U8Downloader:

    def __init__(self):
        self._downTaskLock = threading.Lock()
        self._timeout = 30      #超时时间 单位：秒
        self._retry = 5         #重试次数
        self._threadCount = 12  #线程数

    def __get_next_task(self):
        task = []
        self._downTaskLock.acquire()
        hasFind = False
        for i in range(self._currentIndex,self._allNum):
            ts = self._tsList[i]
            fileName = ts.split('?')[0]
            if(os.path.exists(self._outputPath + "/" + fileName)):
                self._finished = self._finished + 1
                print("%s已存在，跳过 (%d / %d)" % (fileName,self._finished,self._allNum))
                continue
            
            task = [self.__downUrl + ts, fileName]
            hasFind = True
            self._currentIndex = i + 1
            break
        if not hasFind:
            self._currentIndex = self._allNum
        self._downTaskLock.release()
        return task

    def __download_task(self):

        while(True):
            task = self.__get_next_task()
            if not task:
                return

            ret = self.__try_get_url(task[0])
            if( ret == None or ret.status_code != 200):
                self._downTaskLock.acquire()
                print("%s下载失败，跳过 (%d/%d)" % (task[1],self._finished,self._allNum))
                self._downTaskLock.release()
                continue

            with open(self._outputPath + "/" + task[1], "ab") as code:
                code.write(ret.content)
                self._downTaskLock.acquire()
                self._finished = self._finished + 1
                print("%s下载成功 (%d/%d)" % (task[1],self._finished,self._allNum))
                self._downTaskLock.release()


    def __download_ts_list(self,tsList,outputPath):
        self._allNum = len(tsList)
        self._currentIndex = 0
        self._tsList = tsList
        self._finished = 0
        self._outputPath = outputPath
        print("allNum = %d" % (self._allNum))

        threadList = []
        for i in range(self._threadCount):
            t = threading.Thread(target=self.__download_task)
            t.start()
            threadList.append(t)
        
        for t in threadList:
            t.join()

        print("%s下载完成 %d/%d" % (outputPath,self._finished,self._allNum))
        


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
                if count > self._retry:
                    break

                print("第%d次尝试..." % (count))
                res = requests.get(url,timeout=(self._timeout,self._timeout))
                if res == None or res.status_code != 200:
                    continue
                
                lengthStr = res.headers.get('Content-Length')
                if lengthStr:
                    length = int(lengthStr)
                    if length != len(res.content):
                        print("check data error,retry!")
                        continue
                else:
                    print("%s:%d why come here?" % (__file__,__line__))
                
                return res
            except Exception as e:
                print("we catch an exception,wait 500 ms again!")
                print(e)
                time.sleep(0.5)
        return None
    
    def __download_m3u8_file(self,m3u8Url,outputPath):
        m3u8UrlSplit = m3u8Url.split('/')
        m3u8FileName = m3u8UrlSplit.pop().split('?')[0]

        if os.path.exists(outputPath):
            pass
        else:
            os.mkdir(outputPath)

        ret = self.__try_get_url(m3u8Url)
        if ret == None or ret.status_code != 200 :
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

    def __clear_ts_list(self):
        for ts in self._tsList:
            fileName = self._outputPath + "/" + ts.split('?')[0]
            if(os.path.exists(fileName)):
                os.remove(fileName)
            else:
                print("%s 不存在" % (fileName))

    def __combine_ts_list(self,m3u8Url):
        print("开始合并ts片段...")
        if self._finished != self._allNum:
            print("文件数量不全，取消合并，请尝试重新下载!")
            return

        m3u8UrlSplit = m3u8Url.split('/')
        m3u8FileName = m3u8UrlSplit.pop().split('?')[0]
        
        outputFile = self._outputPath.replace("\\","/")
        if outputFile[len(outputFile) - 1] == '/':
            outputFile = outputFile[:len(outputFile) - 1]
        
        if "/" in outputFile:
            last_point = outputFile.rfind("/") + 1
            outputFile = outputFile[last_point:]

        inputPath = self._outputPath + "/" + m3u8FileName
        outputPatn = self._outputPath + "/" + outputFile + ".mp4"

        #stream = ffmpeg.input(self._outputPath + "/" + m3u8FileName)
        #stream = ffmpeg.output(stream,self._outputPath + "/" + outputFile + ".mp4",c="copy")
        #ffmpeg.run(stream)

        command = ['ffmpeg','-i',inputPath,
            '-c','copy',outputPatn]
        subprocess.run(command)

        print("合并完成，开始清理ts片段...")
        os.remove(inputPath)
        self.__clear_ts_list()
        print("清理完成!")


    def down(self,m3u8Url,outputPath):
        m3u8Data = self.__download_m3u8_file(m3u8Url,outputPath)
        if(None == m3u8Data):
            return
        
        tsList = self.__get_ts_list(m3u8Data)
        self.__download_ts_list(tsList,outputPath)
        self.__combine_ts_list(m3u8Url)
        # if(!self)
        # ts_list = get_ts_list(m3_path)
        # combine_url_and_download(ts_list,urlpath,outputPath)


if __name__ == '__main__':
    a = M3U8Downloader()
    #a.down("https://dv-h.phncdn.com/hls/videos/202212/21/421792331/,1080P_4000K,720P_4000K,480P_2000K,240P_1000K,_421792331.mp4.urlset/index-f1-v1-a1.m3u8?ttl=1698768235&l=0&ipa=149.104.96.17&hash=c816c1801755de8bb3ca89d84184560e","./123")
    #a.down("https://ev-h.phncdn.com/hls/videos/202303/07/426913121/,1080P_4000K,720P_4000K,480P_2000K,240P_1000K,_426913121.mp4.urlset/index-f1-v1-a1.m3u8?validfrom=1698766967&validto=1698774167&ipa=149.104.96.17&hdl=-1&hash=XLoMap%2BiGb6zVAvGTuQkILUMAZU%3D","./123")
    start = time.time()
    a.down("https://qq.iqiyi2.b555b.com:7777/7f/7f49dcd0c6b118a6e026742774e04bb28100d3ed/hd.m3u8","./test")
    end = time.time()
    print("一共耗时：%.2f秒,按任意键退出" % (end - start))
    msvcrt.getch()

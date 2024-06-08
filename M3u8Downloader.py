import requests
import re
import math
import time
import os
import threading
import subprocess
import msvcrt
import shutil
#import ffmpeg    #这个库还是需要依赖ffmpeg，不如直接调ffmpeg命令行

class M3u8Downloader:

    def __init__(self,threadCount = 10,timeout = 30,retry = 5):
        self._downTaskLock = threading.Lock()
        self._timeout = timeout      #超时时间 单位：秒
        self._retry = retry         #重试次数
        self._threadCount = threadCount  #线程数

    def __get_next_task(self):
        task = []
        self._downTaskLock.acquire()
        hasFind = False
        for i in range(self._currentIndex,self._allNum):
            ts = self._tsList[i]
            fileName = ts.split('?')[0]
            if(os.path.exists(self._taskPath + "/" + fileName)):
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

            with open(self._taskPath + "/" + task[1], "wb") as code:
                code.write(ret.content)
                code.close()
                self._downTaskLock.acquire()
                self._finished = self._finished + 1
                print("%s下载成功 (%d/%d)" % (task[1],self._finished,self._allNum))
                self._downTaskLock.release()


    def __download_ts_list(self,tsList):
        self._allNum = len(tsList)
        self._currentIndex = 0
        self._tsList = tsList
        self._finished = 0
        outputPath = self._taskPath
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
                    time.sleep(0.5)
                    continue
                
                lengthStr = res.headers.get('Content-Length')
                if lengthStr:
                    length = int(lengthStr)
                    if length != len(res.content):
                        print("check data error,retry!")
                        time.sleep(0.5)
                        continue
                else:
                    print("can't find Content-Length.res.headers=",res.headers)
                
                return res
            except Exception as e:
                print("we catch an exception,wait 500 ms again!")
                print(e)
                time.sleep(0.5)
        return None
    
    def __download_m3u8_file(self,m3u8Url,outputPath,taskName):
        m3u8UrlSplit = m3u8Url.split('/')
        m3u8FileName = m3u8UrlSplit.pop().split('?')[0]

        taskPath = outputPath + "/" + taskName
        if os.path.exists(taskPath):
            pass
        else:
            os.mkdir(taskPath)

        M3u8Downloader.saveTask(m3u8Url,outputPath,taskName)

        ret = self.__try_get_url(m3u8Url)
        if ret == None or ret.status_code != 200 :
            print("%s下载失败" % (m3u8FileName))
            return None

        lines = ret.text.split('\n')
        u3m8file = open(taskPath + "/" + m3u8FileName, "wt")
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

        self._taskPath = taskPath
        return ret.text

    def __clear_ts_list(self):
        fileName = self._taskPath
        if(os.path.exists(fileName)):
            shutil.rmtree(fileName)
        else:
            print("%s 不存在" % (fileName))

    def __combine_ts_list(self,m3u8Url):
        print("开始合并ts片段...")
        if self._finished != self._allNum:
            print("文件数量不全，取消合并，请尝试重新下载!")
            return False

        m3u8UrlSplit = m3u8Url.split('/')
        m3u8FileName = m3u8UrlSplit.pop().split('?')[0]

        inputPath = self._taskPath + "/" + m3u8FileName
        outputPatn = self._taskPath + ".mp4"

        i = 1
        while(os.path.exists(outputPatn)):
            print("%s 已存在!" % (outputPatn))
            outputPatn = self._taskPath + "(%d).mp4" % (i)
            print("重新生成命名为:%s" % (outputPatn))
            i = i + 1

        #stream = ffmpeg.input(self._outputPath + "/" + m3u8FileName)
        #stream = ffmpeg.output(stream,self._outputPath + "/" + outputFile + ".mp4",c="copy")
        #ffmpeg.run(stream)

        command = ['ffmpeg','-i',inputPath,
            '-c','copy',outputPatn]
        subprocess.run(command)

        if(os.path.exists(outputPatn) == False):
            print("合并失败，请确认...")
            return False
        print("合并完成，输出文件为:%s" % (outputPatn))
        print("开始清理ts片段...")
        os.remove(inputPath)
        self.__clear_ts_list()
        print("清理完成!")
        return True


    def down(self,m3u8Url,outputPath,taskName):
        m3u8Data = self.__download_m3u8_file(m3u8Url,outputPath,taskName)
        if(None == m3u8Data):
            return False
        
        tsList = self.__get_ts_list(m3u8Data)
        self.__download_ts_list(tsList)
        return self.__combine_ts_list(m3u8Url)
        # if(!self)
        # ts_list = get_ts_list(m3_path)
        # combine_url_and_download(ts_list,urlpath,outputPath)
    
    @staticmethod
    def saveTask(m3u8Url,outputPath,taskName):
        #保存任务信息，如果失败可以重新下载
        taskfile = outputPath + "/" + taskName + "/" + taskName + ".m3u8task"
        with open(taskfile, "wt") as urlFile:
            urlFile.write(m3u8Url + '\n')
            urlFile.write(outputPath + '\n')
            urlFile.write(taskName + '\n')
            urlFile.close()
    @staticmethod
    def loadTask(taskfile):
        with open(taskfile, "rt") as urlFile:
            m3u8Url = urlFile.readline()
            outputPath = urlFile.readline()
            taskName = urlFile.readline()
            urlFile.close()
            return [m3u8Url[:-1],outputPath[:-1],taskName[:-1]]
        return None

def startTask(m3u8Url,downloadPath,taskName,threadCount=10,timeout=30,retry=5):
    a = M3u8Downloader(threadCount,timeout,retry)
    start = time.time()

    downloadPath = downloadPath.replace("\\","/")
    if downloadPath[len(downloadPath) - 1] == '/':
        downloadPath = downloadPath[:-1]

    ret = a.down(m3u8Url,downloadPath,taskName)
    end = time.time()
    print("一共耗时：%.2f秒" % (end - start))
    #msvcrt.getch()
    return ret

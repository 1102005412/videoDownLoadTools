import requests
import re
import math
import time
import os
import threading
import subprocess
import msvcrt
import shutil
import DownTask
#import ffmpeg    #这个库还是需要依赖ffmpeg，不如直接调ffmpeg命令行

class M3u8Downloader:
    onlySaveTask = False

    def __init__(self,threadCount = 10,timeout = 30,retry = 5):
        self._downTaskLock = threading.Lock()
        self._timeout = timeout      #超时时间 单位：秒
        self._retry = retry         #重试次数
        self._threadCount = threadCount  #线程数
        # self._headers={
        #     'User-Agent': 'python',
        #     'Accept': 'application/json',
        #     'Accept-Encoding': 'gzip, deflate'
        # }
        self._m3u8EnableTypes = [".ts",".jpg",".jpeg"]
        self._totalDownloadSize = 0  # 总下载数据量（字节）
        self._downloadSpeed = 0  # 实时下载速度（字节/秒）
        self._lastDownloadSize = 0  # 上次计算速度时的下载量
        self._lastSpeedTime = time.time()  # 上次计算速度的时间
        self._speedThread = None  # 网速显示线程
        self._isDownloading = False  # 下载状态标志
        self._maxFilesPerFolder = 200  # 每个文件夹存放的文件数量

    def __get_sub_folder_path(self, index, files_per_folder=200):
        """根据文件索引计算存储文件夹路径
        Args:
            index: 文件在列表中的索引
            files_per_folder: 每个文件夹存放的文件数量
            
        Returns:
            文件夹路径（相对于taskPath）
        """
        folder_index = index // files_per_folder + 1
        return f"part{folder_index:d}"

    def __get_next_task(self):
        task = []
        self._downTaskLock.acquire()
        hasFind = False
        for i in range(self._currentIndex,self._allNum):
            ts = self._tsList[i]
            fileName = ts.split('?')[0]
            if fileName.endswith(".ts") is False:
                fileName += ".ts"

            if(os.path.exists(self._taskPath + "/" + fileName)):
                self._finished = self._finished + 1
                print("%s已存在，跳过 (%d / %d)" % (fileName,self._finished,self._allNum))
                continue
            
            subFolderPath = self.__get_sub_folder_path(i,self._maxFilesPerFolder)
            if ts.startswith("http://") or ts.startswith("https://"):
                task = [ts, fileName.split("/")[-1],subFolderPath]
            elif ts.startswith("/"):
                task = [self.__downUrl + ts[1:], fileName.split("/")[-1],subFolderPath]
            else:
                task = [self.__downUrl + ts, fileName,subFolderPath]
            hasFind = True
            self._currentIndex = i + 1
            break
        if not hasFind:
            self._currentIndex = self._allNum
        self._downTaskLock.release()
        return task

    def __download_task(self):
        ret = None
        while(M3u8Downloader.onlySaveTask == False):
            task = self.__get_next_task()
            if not task:
                return
            if ret != None:
                ret.close()
            ret = self.__try_get_url(task[0])
            if( ret == None or ret.status_code != 200):
                self._downTaskLock.acquire()
                print("%s下载失败，跳过 (%d/%d)" % (task[1],self._finished,self._allNum))
                print("Url=%s" % task[0])
                self._downTaskLock.release()
                continue

            # 确保子文件夹存在
            os.makedirs(self._taskPath + "/" + task[2], exist_ok=True)
            with open(self._taskPath + "/" + task[2] + "/" + task[1], "wb") as code:
                code.write(ret.content)
                code.flush()  # 刷新 Python 缓冲区
                os.fsync(code.fileno())  # 强制操作系统将数据写入磁盘
                self._downTaskLock.acquire()
                self._finished = self._finished + 1
                # 累加下载数据量
                self._totalDownloadSize += len(ret.content)

                speed = self._downloadSpeed
                total_size = self._totalDownloadSize

                #格式化速度显示
                if speed < 1024:
                    speed_str = "%.2f B/s" % speed
                elif speed < 1024 * 1024:
                    speed_str = "%.2f KB/s" % (speed / 1024)
                else:
                    speed_str = "%.2f MB/s" % (speed / (1024 * 1024))
            
                # 格式化总下载量
                if total_size < 1024:
                    total_str = "%.2f B" % total_size
                elif total_size < 1024 * 1024:
                    total_str = "%.2f KB" % (total_size / 1024)
                else:
                    total_str = "%.2f MB" % (total_size / (1024 * 1024))

                print("%s下载成功 (%d/%d) 实时网速: %s | 总下载量: %s" % (task[1], self._finished, self._allNum,speed_str, total_str))
                self._downTaskLock.release()


    def __download_ts_list(self,tsList):
        self._allNum = len(tsList)
        self._currentIndex = 0
        self._tsList = tsList
        self._finished = 0
        self._totalDownloadSize = 0  # 重置下载数据量
        self._lastDownloadSize = 0
        self._lastSpeedTime = time.time()
        outputPath = self._taskPath
        print("allNum = %d" % (self._allNum))

        # 启动网速显示线程
        self.__start_speed_thread()

        threadList = []
        for i in range(self._threadCount):
            t = threading.Thread(target=self.__download_task)
            t.start()
            threadList.append(t)
        
        for t in threadList:
            t.join()

        # 停止网速显示线程
        self.__stop_speed_thread()
        print("\n%s下载完成 %d/%d" % (outputPath,self._finished,self._allNum))
        


    def __get_ts_list(self,m3u8Data):
        m3u8Data = m3u8Data.replace('\r','')
        lines = m3u8Data.split('\n')
        ts = []
        for i in lines:
            if any(var in i for var in self._m3u8EnableTypes):
                ts.append(i)
        return ts

    def __try_get_url(self,url):
        count = 0
        while M3u8Downloader.onlySaveTask == False:
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

        ret = self.__try_get_url(m3u8Url)
        if ret == None or ret.status_code != 200 :
            print("%s下载失败" % (m3u8FileName))
            return None

        lines = ret.text.split('\n')
        u3m8file = open(taskPath + "/" + m3u8FileName, "wt",encoding='utf-8')
        if u3m8file == None:
            print("%s 创建失败" % (m3u8FileName))
            return None
        currentIndex = 0
        for line in lines:
            if any(var in line for var in self._m3u8EnableTypes):
                fileName = line.split('?')[0]
                if line.startswith("http:") or line.startswith("https:") or "/" in line:
                    fileName = fileName.split("/")[-1]
                if fileName.endswith(".ts") is False:
                    fileName += ".ts"
                subFolderPath = self.__get_sub_folder_path(currentIndex,self._maxFilesPerFolder)
                currentIndex += 1
                fileName = subFolderPath + "/" + fileName

                u3m8file.write(fileName + "\n")
            else:
                u3m8file.write(line + "\n")
        ret.close()
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

    def __show_download_speed(self):
        """显示实时下载速度"""
        while self._isDownloading:
            current_time = time.time()
            time_diff = current_time - self._lastSpeedTime
            
            with self._downTaskLock:
                current_size = self._totalDownloadSize
                size_diff = current_size - self._lastDownloadSize
                # 只有当时间差达到10秒或有新数据下载时才更新速度和时间
                if time_diff >= 5 and size_diff > 0:
                    speed = size_diff / max(time_diff, 0.1)  # 避免除以0
                    self._downloadSpeed = speed
                    self._lastDownloadSize = current_size
                    self._lastSpeedTime = current_time
                # else:
                #     speed = self._downloadSpeed
                # total_size = self._totalDownloadSize
                # finished = self._finished
                # all_num = self._allNum
            
            # 格式化速度显示
            # if speed < 1024:
            #     speed_str = "%.2f B/s" % speed
            # elif speed < 1024 * 1024:
            #     speed_str = "%.2f KB/s" % (speed / 1024)
            # else:
            #     speed_str = "%.2f MB/s" % (speed / (1024 * 1024))
            
            # # 格式化总下载量
            # if total_size < 1024:
            #     total_str = "%.2f B" % total_size
            # elif total_size < 1024 * 1024:
            #     total_str = "%.2f KB" % (total_size / 1024)
            # else:
            #     total_str = "%.2f MB" % (total_size / (1024 * 1024))
            
            # 使用回车符覆盖当前行，实现实时更新效果
            #print("\r实时网速: %s | 总下载量: %s | 完成: %d/%d" % (speed_str, total_str, finished, all_num), end="", flush=True)
            
            time.sleep(1)  # 减少CPU占用

    def __start_speed_thread(self):
        """启动网速显示线程"""
        self._isDownloading = True
        self._speedThread = threading.Thread(target=self.__show_download_speed)
        self._speedThread.daemon = True  # 设为守护线程，主线程结束时自动退出
        self._speedThread.start()

    def __stop_speed_thread(self):
        """停止网速显示线程"""
        self._isDownloading = False
        if self._speedThread:
            self._speedThread.join(timeout=1)  # 等待线程结束，最多等待1秒

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

        ffmpeg_cmd_path = os.path.dirname(os.path.abspath(__file__)) + "\\ffmpeg\\bin\\ffmpeg"
        command = [ffmpeg_cmd_path, '-i', inputPath,
                   '-c', 'copy', outputPatn]
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
        try:
            M3u8Downloader.saveTask(m3u8Url,outputPath,taskName)
            if M3u8Downloader.onlySaveTask:
                return True
 
            m3u8Data = self.__download_m3u8_file(m3u8Url,outputPath,taskName)
            if(None == m3u8Data):
                return False
        except Exception as e:
            print("we catch an exception,wait 500 ms again!")
            print(e)
            time.sleep(0.5)
            return False
            
        tsList = self.__get_ts_list(m3u8Data)
        self.__download_ts_list(tsList)

        if M3u8Downloader.onlySaveTask:
                return True
        
        return self.__combine_ts_list(m3u8Url)
        # if(!self)
        # ts_list = get_ts_list(m3_path)
        # combine_url_and_download(ts_list,urlpath,outputPath)
    
    @staticmethod
    def saveTask(m3u8Url,outputPath,taskName):
        taskPath = outputPath + "/" + taskName
        if os.path.exists(taskPath) == False:
            os.mkdir(taskPath)

        #保存任务信息，如果失败可以重新下载
        taskfile = taskPath + "/" + taskName + ".m3u8task"
        if len(taskfile) > 255:
            taskfile = taskPath + "/task.m3u8task"
        with open(taskfile, "wt",encoding='utf-8') as urlFile:
            urlFile.write(m3u8Url + '\n')
            urlFile.write(outputPath + '\n')
            urlFile.write(taskName + '\n')
            urlFile.close()
    @staticmethod
    def loadTask(taskfile):
        with open(taskfile, "rt",encoding='utf-8') as urlFile:
            m3u8Url = urlFile.readline()
            outputPath = urlFile.readline()
            taskName = urlFile.readline()
            urlFile.close()
            return DownTask.DownTask(m3u8Url[:-1],outputPath[:-1],taskName[:-1])
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

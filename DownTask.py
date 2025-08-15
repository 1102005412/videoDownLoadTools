import time
import threading
import M3u8Downloader
from tkinter import *
from tkinter import messagebox
import base
import pygame

class DownTask:
    def __init__(self,m3u8Url,downloadPath,taskName,threadCount = 10,timeout = 30,retry = 5):
        self.m3u8Url = m3u8Url
        self.downloadPath = downloadPath
        self.taskName = taskName
        self.threadCount = threadCount
        self.timeout = timeout
        self.retry = retry
    
    def start(self):
        print("m3u8Url:" + self.m3u8Url)
        print("downloadPath:"+self.downloadPath)
        print("taskName:"+self.taskName)
        return M3u8Downloader.startTask(self.m3u8Url,self.downloadPath,self.taskName,\
                                        self.threadCount,self.timeout,self.retry)

class DownTaskThread:
    def __init__(self):
        self.downThread = None
        self.downThreadRun = False
        self.taskList = []
        self.taskListLock = threading.Lock()

        pygame.init()
        pygame.mixer.init()

        soundPath =  "res/sound/"
        self.finishSound = pygame.mixer.Sound(soundPath + "download-complete.wav")
        self.finishSound.set_volume(1)
        self.errorSound = pygame.mixer.Sound(soundPath + "download-error.wav")
        self.errorSound.set_volume(1)
        self.allFinishSound = pygame.mixer.Sound(soundPath + "all-finished.wav")
        self.allFinishSound.set_volume(1)
    
    def add_task(self,task):
        taskInList = False
        self.taskListLock.acquire()
        for t in self.taskList:
            if task.m3u8Url == t.m3u8Url:
                taskInList = True
                break
        if taskInList == False:
            self.taskList.append(task)
        num = len(self.taskList)
        self.taskListLock.release()
        
        t = Tk()
        t.geometry('%dx%d' % (0,0))
        base.set_window_center_display(t)

        if taskInList == False:
            title = 'add Succeed!'
            answer = messagebox.showinfo(title, 'current download queue len is %d' % num,parent=t)
        else:
            title = 'add Fail!'
            answer = messagebox.showinfo(title, 'The url already exists in the download queue,current download queue len is %d' % num,parent=t)
        t.protocol("WM_DELETE_WINDOW", t.quit)
        t.destroy()
        return taskInList == False

    def start_download(self):
        if self.downThread is None:
            self.downThread = threading.Thread(target=self.download_thread)
            self.downThreadRun = True
            self.downThread.start()
        elif self.downThreadRun == False:
            self.downThread.join()
            self.downThread = threading.Thread(target=self.download_thread)
            self.downThreadRun = True
            self.downThread.start()

    def stop_download(self):
        self.downThreadRun = False
        if self.downThread:
            self.downThread.join()
            self.downThread = None
 
    def download_thread(self):
        allFinished = False
        while self.downThreadRun:
            task = None
            self.taskListLock.acquire()
            if len(self.taskList) > 0:
                task = self.taskList.pop(0)
                allFinished = True
            self.taskListLock.release()

            if task:
                ret = task.start()
                if ret == False:
                    self.taskListLock.acquire()
                    self.taskList.append(task)
                    self.taskListLock.release()
                    self.errorSound.play()
                    if self.isContinue(ret) == False:
                        self.downThreadRun = False
                else:
                    self.finishSound.play()
            else:
                if allFinished:
                    print("All tasks have been downloaded!!!")
                    self.allFinishSound.play()
                    allFinished = False
                time.sleep(1)

    def isContinue(self,ret):
        t = Tk()
        t.geometry('%dx%d' % (0,0))
        base.set_window_center_display(t)
        t.after(1000 * 30, t.destroy)  # 超时强制关闭‌:ml-citation{ref="6" data="citationList"}
        title = 'Download Succeed!' if ret else 'Download Fail!'
        answer = messagebox.askquestion(title, 'Do you want to download continue?',parent = t)
        try:
            t.protocol("WM_DELETE_WINDOW", t.quit)
            t.destroy()
        except TclError:
            pass

        if answer == 'yes':
            print("User selected yes.")
            return True
        elif answer == 'no':
            print("User selected no.")
            return False
        else:
            print("User selected timeout,default yes!")
            return True

    def save_task_list(self):
        if len(self.taskList) > 0 :
            with open("downloadTaskList.txt", "wt",encoding='utf-8') as taskF:
                for task in self.taskList:
                    taskF.write(task.m3u8Url + "\n")
                    taskF.write(task.downloadPath + "\n")
                    taskF.write(task.taskName + "\n")
                    taskF.write("\n")
                taskF.close()
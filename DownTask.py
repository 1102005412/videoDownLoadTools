import time
import threading
import M3u8Downloader
from tkinter import *
from tkinter import messagebox
import base
import pygame
from abc import ABC, abstractmethod

# 观察者接口
class TaskChangedObserver(ABC):
    @abstractmethod
    def on_task_start(self, task):
        pass
    @abstractmethod
    def on_task_finished(self, task):
        pass
    @abstractmethod
    def on_task_append(self, task):
        pass

class TaskChangedObservable:
    def __init__(self):
        self.observers = []  # 存储观察者

    def add_observer(self, observer):
        if observer not in self.observers:
            self.observers.append(observer)
    
    def remove_observer(self, observer):
        if observer in self.observers:
            self.observers.remove(observer)
    
    def notify_task_start(self, task):
        for observer in self.observers:
            observer.on_task_start(task)
    
    def notify_task_finished(self, task):
        for observer in self.observers:
            observer.on_task_finished(task)

    def notify_task_error(self, task):
        for observer in self.observers:
            observer.on_task_error(task)

    def notify_task_append(self, task):
        for observer in self.observers:
            observer.on_task_append(task)

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

class DownTaskThread(TaskChangedObservable):
    def __init__(self):
        super().__init__()
        self.downThread = None
        self.downThreadRun = False
        self.taskList = []
        self.taskListLock = threading.Lock()
        self.exit = False

        pygame.init()
        pygame.mixer.init()

        soundPath =  base.resource_path("res/sound/")
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
            self.notify_task_append(task)
        num = len(self.taskList)
        self.taskListLock.release()
        return [taskInList == False,num]

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
        M3u8Downloader.M3u8Downloader.onlySaveTask = True
        self.exit = True
        if self.downThread:
            self.downThread.join()
            self.downThread = None
 
    def download_thread(self):
        allFinished = False
        task = None
        while self.downThreadRun:
            task = None
            self.taskListLock.acquire()
            if len(self.taskList) > 0:
                task = self.taskList.pop(0)
                allFinished = True
            self.taskListLock.release()

            if task:
                self.notify_task_start(task)
                ret = task.start()
                if ret == False:
                    self.taskListLock.acquire()
                    self.taskList.append(task)
                    self.notify_task_append(task)
                    self.taskListLock.release()
                    self.notify_task_error(task)
                    self.errorSound.play()
                    if self.isContinue(ret) == False:
                        self.downThreadRun = False
                else:
                    self.notify_task_finished(task)
                    self.finishSound.play()
            else:
                if allFinished:
                    print("All tasks have been downloaded!!!")
                    self.allFinishSound.play()
                    allFinished = False
                if self.exit:
                    break
                time.sleep(1)

    def isContinue(self,ret):
        t = Tk()
        t.geometry('%dx%d' % (0,0))
        base.set_window_center_display(t)
        t.after(1000 * 30, t.destroy)  # 超时强制关闭‌:ml-citation{ref="6" data="citationList"}
        title = 'Download Succeed!' if ret else 'Download Fail!'
        answer = messagebox.askquestion(title, 'Do you want to download continue?',parent = t)
        try:
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
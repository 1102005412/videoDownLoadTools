from tkinter import *
import tkinter.filedialog as filedialog
from tkinter import messagebox
from M3u8Downloader import startTask
import datetime
import configparser
import os
import re

def set_window_center_display(window):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    #获取窗口大小前需要更新一下才能得到实际值
    window.update()
    window_width = window.winfo_width()
    window_height = window.winfo_height()

    # 计算窗口左上角的坐标
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2

    # 设置窗口左上角的坐标
    window.geometry('{}x{}+{}+{}'.format(window_width,window_height,x, y))
    window.mainloop()

def is_valid_filename(filename):
    """
    判断文件名是否合法
    """
    pattern = "[\\/:*?\"<>|]"
    res = re.match(pattern,filename)
    return res is None

class NewTaskWindow:
    def __init__(self):
        self.hasTask = False
        self.__configFileName = "taskConfig.ini"
        self.downloadPath = ""
        self.__read_config()
        self.__init_window(1080,720)

    def __read_config(self):
        configFileName = self.__configFileName
        config = configparser.ConfigParser()
        if os.path.exists(configFileName) == False:
            return

        conf_file = open(configFileName)
        config.read_file(conf_file)
        self.downloadPath = config.get("MainWindow","downloadPath")

    def __save_config(self):
        configFileName = self.__configFileName
        config = configparser.ConfigParser()
        config["MainWindow"] = {"downloadPath" : self.downloadPath}
        file_write = open(configFileName,"w")
        config.write(file_write)

    def __select_path(self):
        path = filedialog.askdirectory(initialdir=".",mustexist=False)
        if len(path) != 0: 
            self.__downloadPath.set(path)

    def __start_download(self):
        url = self.__uriText.get("1.0",END)
        path = self.__downloadPath.get()
        taskName = self.__taskName.get()
        #Text 获取的文本末尾自带'\n'
        if len(url) <= 1 or len(path) == 0 or len(taskName) == 0:
            messagebox.showerror("错误","请输入正确的url、任务名称和下载路径")
        elif is_valid_filename(taskName) == False:
            messagebox.showerror("错误","请输入符合文件系统命名规则的任务名称")
        elif os.path.exists(path) == False:
            messagebox.showerror("错误","下载路径不存在，请输入有效的下载路径")
        else: 
            self._window.protocol("WM_DELETE_WINDOW", self._window.quit)
            self._window.destroy()
            self.downloadPath = path
            self.m3u8Url = url
            self.taskName = taskName
            if url[len(url) - 1] == '\n':
                self.m3u8Url = url[:-1]
            self.hasTask = True
            self.__save_config()

    def __get_timestamp(self):
        now_time = datetime.datetime.now()
        self.__taskName.set(now_time.strftime('%Y%m%d_%H%M%S_%f')[:-3])

    def __init_window(self,width,height):
        newTaskWindow = Tk()
        self._window = newTaskWindow
        self.__downloadPath = StringVar()
        self.__downloadPath.set(self.downloadPath)
        self.__taskName = StringVar()

        newTaskWindow.title("new task")
        newTaskWindow.geometry('%dx%d' % (width,height))
        #newTaskWindow.resizable(0, 0)

        urlLable = Label(newTaskWindow,text="m3u8 url:")
        uriText = Text(newTaskWindow,width=1,height=1)
        downloadPathLable = Label(newTaskWindow,text="下载路径:")
        downloadPathEntry = Entry(newTaskWindow,textvariable = self.__downloadPath)
        self.__uriText = uriText

        selectPathBtn = Button(newTaskWindow,text = "选择下载文件夹",
        fg = "black",height = 1,
        font = ('楷体',10,'bold'),
        command = self.__select_path)

        startTaskBtn = Button(newTaskWindow,text = "开始下载",
        fg = "red",height = 1,
        font = ('楷体',10,'bold'),
        command = self.__start_download)

        useTimestamp = Button(newTaskWindow,text = "使用时间戳命名",
        fg = "black",height = 1,
        font = ('楷体',10,'bold'),
        command = self.__get_timestamp)

        taskNameLable = Label(newTaskWindow,text="任务名称:")
        taskNameEntry = Entry(newTaskWindow,textvariable = self.__taskName)

        row = 1
        urlLable.grid(row=row,column=0,pady=5,sticky=E+N)
        uriText.grid(row=row,column=1,pady=5,sticky=W+E+S+N)

        row = row + 1
        taskNameLable.grid(row=row,column=0,pady=5,sticky=E+N)
        taskNameEntry.grid(row=row,column=1,pady=5,sticky=W+E)
        useTimestamp.grid(row=row,column=2,pady=5,sticky=W+N)

        row = row + 1
        downloadPathLable.grid(row=row,column=0,sticky=E+N)
        downloadPathEntry.grid(row=row,column=1,sticky=W+E+N)
        selectPathBtn.grid(row=row,column=2,sticky=W+N)

        row = row + 1
        startTaskBtn.grid(row=row,column=1,sticky=N,pady=5,ipadx=10,ipady=10)

        newTaskWindow.grid_columnconfigure(0,weight=1)
        newTaskWindow.grid_columnconfigure(1,weight=5)
        newTaskWindow.grid_columnconfigure(2,weight=1)
        newTaskWindow.grid_rowconfigure(0,weight=2)
        newTaskWindow.grid_rowconfigure(1,weight=3)
        newTaskWindow.grid_rowconfigure(4,weight=3)

        set_window_center_display(newTaskWindow)

    def dispaly(self):
        self._window.mainloop()


if __name__ == '__main__':
    task = NewTaskWindow()
    task.dispaly()
    
    if task.hasTask:
        print("m3u8Url:" + task.m3u8Url)
        print("downloadPath:"+task.downloadPath)
        print("taskName:"+task.taskName)
        startTask(task.m3u8Url,task.downloadPath,task.taskName)

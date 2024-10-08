from tkinter import *
import tkinter.filedialog as filedialog
from tkinter import messagebox
import datetime
import configparser
import os
import re
from ToolTip import *
from M3u8Downloader import M3u8Downloader
import DownTask
import base

def is_valid_filename(filename):
    """
    判断文件名是否合法
    """
    pattern = "[\\/:*?\"<>|]"
    res = re.match(pattern,filename)
    return res is None

def try_read_config(config,selection,name):
    try:
        return config.get(selection,name)
    except:
        return None

class NewTaskWindow:
    def __init__(self):
        self.__configFileName = "taskConfig.ini"
        self.downloadPath = ""
        self.threadCount = 10
        self.timeout = 30
        self.retry = 5

        self.__read_config()

    def __read_config(self):
        configFileName = self.__configFileName
        config = configparser.ConfigParser()
        if os.path.exists(configFileName) == False:
            return

        conf_file = open(configFileName)
        config.read_file(conf_file)
        temp = try_read_config(config,"MainWindow","downloadPath")
        if temp:
            self.downloadPath = temp
        temp = try_read_config(config,"MainWindow","threadCount")
        if temp:
            self.threadCount = temp
        temp = try_read_config(config,"MainWindow","timeout")
        if temp:
            self.timeout = temp
        temp = try_read_config(config,"MainWindow","retry")
        if temp:
            self.retry = temp

    def save_config(self):
        configFileName = self.__configFileName
        config = configparser.ConfigParser()
        config["MainWindow"] = {
            "downloadPath" : self.downloadPath,
            "threadCount"  : self.threadCount,
            "timeout"      : self.timeout,
            "retry"        : self.retry
        }
        file_write = open(configFileName,"w")
        config.write(file_write)

    def __select_path(self):
        path = self.__downloadPath.get()
        if len(path) == 0:
            path = "."
        path = filedialog.askdirectory(initialdir=path,mustexist=False)
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
            self.threadCount = int(self.__threadCount.get())
            self.timeout = int(self.__timeout.get())
            self.retry = int(self.__retry.get())

    def __load_task(self):
        path = filedialog.askopenfilename(initialdir=self.downloadPath,filetypes=[('Text Files','.m3u8task')])
        if path == None or len(path) == 0:
            return
        task = M3u8Downloader.loadTask(path)
        if task == None:
            return
        self.__uriText.insert("1.0",task[0])
        self.__downloadPath.set(task[1])
        self.__taskName.set(task[2])

    def __continue_task(self):
        path = filedialog.askopenfilename(initialdir=self.downloadPath,filetypes=[('Text Files','.m3u8task')])
        if path == None or len(path) == 0:
            return
        task = M3u8Downloader.loadTask(path)
        if task == None:
            return
        self.m3u8Url = task[0]
        self.downloadPath = task[1]
        self.taskName = task[2]
        self.hasTask = True
        self.threadCount = int(self.__threadCount.get())
        self.timeout = int(self.__timeout.get())
        self.retry = int(self.__retry.get())
        self._window.protocol("WM_DELETE_WINDOW", self._window.quit)
        self._window.destroy()

    def __get_timestamp(self):
        now_time = datetime.datetime.now()
        self.__taskName.set(now_time.strftime('%Y%m%d_%H%M%S_%f')[:-3])

    def __do_paste(self,event):
        widget = event.widget
        clipboard_content = self._window.clipboard_get()

        index = INSERT
        if (type(widget) is Entry and widget.selection_present()) or \
        (type(widget) is Text  and len(widget.tag_ranges("sel")) != 0 ):
            index = widget.index(SEL_FIRST)
            widget.delete(SEL_FIRST,SEL_LAST)
        
        widget.insert(index,clipboard_content)

    def __init_window(self,width,height):
        newTaskWindow = Tk()
        self._window = newTaskWindow
        self.__downloadPath = StringVar(value = self.downloadPath)
        self.__taskName = StringVar()
        self.__threadCount = StringVar(value = self.threadCount)
        self.__timeout = StringVar(value = self.timeout)
        self.__retry = StringVar(value = self.retry)

        newTaskWindow.title("new task")
        newTaskWindow.geometry('%dx%d' % (width,height))
        #newTaskWindow.resizable(0, 0)

        urlLable = Label(newTaskWindow,text="m3u8 url:")
        uriText = Text(newTaskWindow,width=1,height=1)
        uriText.bind('<ButtonRelease-3>',self.__do_paste)

        downloadPathLable = Label(newTaskWindow,text="下载路径:")
        downloadPathEntry = Entry(newTaskWindow,textvariable = self.__downloadPath)
        self.__uriText = uriText

        buttonframe = Frame(newTaskWindow)

        selectPathBtn = Button(newTaskWindow,text = "选择文件夹",
        fg = "black",height = 1,
        font = ('楷体',10,'bold'),
        command = self.__select_path)

        startTaskBtn = Button(buttonframe,text = "开始下载",
        fg = "red",height = 1,
        font = ('楷体',10,'bold'),
        command = self.__start_download)
        ToolTip(startTaskBtn,"开始新任务")

        useTimestamp = Button(newTaskWindow,text = "使用时间戳",
        fg = "black",height = 1,
        font = ('楷体',10,'bold'),
        command = self.__get_timestamp)
        ToolTip(useTimestamp,"以当前系统时间命名")

        loadTaskBtn = Button(buttonframe,text = "导入任务",
        fg = "red",height = 1,
        font = ('楷体',10,'bold'),
        command = self.__load_task)
        ToolTip(loadTaskBtn,"导入之前未下载完的任务")

        continueTaskBtn = Button(buttonframe,text = "继续下载",
        fg = "red",height = 1,
        font = ('楷体',10,'bold'),
        command = self.__continue_task)
        ToolTip(continueTaskBtn,"继续之前未下载完的任务")

        taskNameLable = Label(newTaskWindow,text="任务名称:")
        taskNameEntry = Entry(newTaskWindow,textvariable = self.__taskName)
        taskNameEntry.bind('<ButtonRelease-3>',self.__do_paste)

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
        frame = Frame(newTaskWindow)
        frame.grid(row=row,column=1,sticky=W+E+N+S)
        label_timeout = Label(frame,text="超时时间:")
        label_timeout.grid(row=0,column=0)
        startValue = 5
        endValue = 60
        timeout_spin = Spinbox(frame,from_=startValue,to=endValue,increment=1,validate='key',
            width=5,textvariable=self.__timeout,
            validatecommand = (frame.register(lambda str:len(str) == 0 or 
                (str.isdigit() 
                and int(str) >= startValue 
                and int(str) <= endValue)),'%P'), wrap=True)
        timeout_spin.grid(row=0,column=1,sticky=W)
        Label(frame,text="秒").grid(row=0,column=2)

        label_retry = Label(frame,text="重试次数:")
        label_retry.grid(row=0,column=3,sticky=E)
        startValue = 0
        endValue = 20
        retry_spin = Spinbox(frame,from_=startValue,to=endValue,increment=1,validate='key',
            width=5,textvariable=self.__retry,
            validatecommand = (frame.register(lambda str:len(str) == 0 or 
                (str.isdigit() 
                and int(str) >= startValue 
                and int(str) <= endValue)),'%P'), wrap=True)
        retry_spin.grid(row=0,column=4)
        
        label_threadCount = Label(frame,text="线程数:")
        label_threadCount.grid(row=0,column=5,sticky=E)
        startValue = 1
        threadCount_spin = Spinbox(frame,from_=startValue,to=endValue,increment=1,validate='key',
            width=5,textvariable=self.__threadCount,
            validatecommand = (frame.register(lambda str:
                (str.isdigit() 
                and int(str) >= startValue 
                and int(str) <= endValue)),'%P'), wrap=True)
        threadCount_spin.grid(row=0,column=6)
        frame.grid_columnconfigure(3,weight=1)
        frame.grid_columnconfigure(5,weight=1)

        row = row + 1
        buttonframe.grid(row=row,column=1,sticky=N+S+W+E)
        loadTaskBtn.grid(row=1,column=1,sticky=N+S+E+W,padx=5)
        continueTaskBtn.grid(row=1,column=2,sticky=N+S+E+W,padx=5)
        startTaskBtn.grid(row=1,column=3,sticky=N+S+W+E,padx=5)
        buttonframe.grid_rowconfigure(0,weight=2)
        buttonframe.grid_rowconfigure(1,weight=1)
        buttonframe.grid_rowconfigure(2,weight=3)
        
        buttonframe.grid_columnconfigure(0,weight=2)
        buttonframe.grid_columnconfigure(1,weight=1)
        buttonframe.grid_columnconfigure(2,weight=1)
        buttonframe.grid_columnconfigure(3,weight=1)
        buttonframe.grid_columnconfigure(4,weight=2)

        #startTaskBtn.grid(row=row,column=1,sticky=N,pady=5,ipadx=10,ipady=10)
        #continueTaskBtn.grid(row=row,column=2,sticky=N,pady=5,ipadx=10,ipady=10)

        newTaskWindow.grid_columnconfigure(0,weight=1)
        newTaskWindow.grid_columnconfigure(1,weight=5)
        newTaskWindow.grid_columnconfigure(2,weight=1)
        newTaskWindow.grid_rowconfigure(0,weight=2)
        newTaskWindow.grid_rowconfigure(1,weight=3)
        newTaskWindow.grid_rowconfigure(row,weight=3)

        base.set_window_center_display(newTaskWindow)

    def dispaly(self):
        self.hasTask = False
        self.__init_window(1080,720)
        self._window.mainloop()
    
    def get_downtask(self):
        return DownTask.DownTask(self.m3u8Url,self.downloadPath,self.taskName,self.threadCount,self.timeout,self.retry)

def isContinue(ret):
    t = Tk()
    t.geometry('%dx%d' % (0,0))
    base.set_window_center_display(t)

    title = 'Download Succeed!' if ret else 'Download Fail!'
    answer = messagebox.askquestion(title, 'Do you want to download continue?',parent=t)
    t.protocol("WM_DELETE_WINDOW", t.quit)
    t.destroy()

    if answer == 'yes':
        print("User selected yes.")
        return True
    else:
        print("User selected no.")
        return False


if __name__ == '__main__':
    iscontinue = True
    window = NewTaskWindow()
    downthread = DownTask.DownTaskThread()
    while(iscontinue):
        iscontinue = False
        window.dispaly()

        if window.hasTask:
            downthread.add_task(window.get_downtask())
            downthread.start_download()
            iscontinue = True

    downthread.stop_download()
    downthread.save_task_list()
    window.save_config()
    

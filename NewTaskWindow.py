from tkinter import *
import tkinter.filedialog as filedialog
from tkinter import messagebox,ttk
import datetime
import configparser
import os
import re
from ToolTip import *
from M3u8Downloader import M3u8Downloader
import DownTask
import base
import sys
import time
import threading

def is_valid_filename(filename: str, allow_dots: bool = False) -> bool:
    """
    校验文件名合法性
    :param filename: 待校验的文件名（不含路径）
    :param allow_dots: 是否允许以点开头或结尾（用于处理隐藏文件）
    :return: 是否合法
    """
    # ------------------- 基础校验 -------------------
    # 空值检查
    if not filename or filename.strip() == "":
        print("filename is None!")
        return False
    
    # 长度检查（1-255字符）
    if len(filename) > 255 or len(filename) < 1:
        return False

    # ------------------- 非法字符检查 -------------------
    # 正则表达式：排除 \ / : * ? " < > | 和控制字符
    illegal_pattern = r'[\\/:*?"<>|\x00-\x1F]'
    if re.search(illegal_pattern, filename):
        print("文件名不能包含以下字符：",illegal_pattern)
        return False

    # ------------------- 特殊格式检查 -------------------
    # 禁止全空格文件名
    if filename.strip() == "":
        print("禁止全空格文件名!")
        return False

    # 可选：禁止以点开头/结尾（默认关闭）
    if not allow_dots:
        if filename.startswith('.') or filename.endswith('.'):
            print("文件名禁止以点开头/结尾!")
            return False

    # ------------------- 系统保留名称检查 -------------------
    # Windows 保留名称列表（不区分大小写）
    windows_reserved = [
        "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4",
        "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", 
        "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    ]
    if sys.platform.startswith('win'):
        if filename.split('.')[0].upper() in windows_reserved:
            print("禁止使用下列名称做文件名（不区分大小写）：",windows_reserved)
            return False

    return True


def try_read_config(config,selection,name):
    try:
        return config.get(selection,name)
    except:
        return None

class NewTaskWindow(DownTask.TaskChangedObserver):
    def __init__(self):
        self.__configFileName = "taskConfig.ini"
        self.downloadPath = ""
        self.threadCount = 10
        self.timeout = 30
        self.retry = 5
        self.exit = False

        self.__waiting_frame = None
        self.__active_frame = None
        self.__completed_frame = None
        self.__notebook = None
        self.__waiting_queue = []
        self.__active_queue = []
        self.__completed_queue = []

        self.__waiting_add = []
        self.__waiting_remove = []
        self.__active_add = []
        self.__active_remove = []
        self.__completed_add = []

        self.__queue_lock = threading.Lock()

        self.__read_config()
        self.__downthread = DownTask.DownTaskThread()

    def on_task_start(self,task):
        self.__queue_lock.acquire()
        self.__active_add.append(task.taskName)
        self.__waiting_remove.append(task.taskName)
        self.__active_queue.append(task.taskName)
        self.__waiting_queue.remove(task.taskName)
        self.__queue_lock.release()
    
    def on_task_finished(self,task):
        self.__queue_lock.acquire()
        self.__active_remove.append(task.taskName)
        self.__completed_add.append(task.taskName)
        self.__active_queue.remove(task.taskName)
        self.__completed_queue.append(task.taskName)
        self.__queue_lock.release()

    def on_task_append(self, task):
        self.__queue_lock.acquire()
        self.__waiting_add.append(task.taskName)
        self.__waiting_queue.append(task.taskName)
        self.__queue_lock.release()

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
            self.downloadPath = path
            self.m3u8Url = url
            self.taskName = taskName
            if url[len(url) - 1] == '\n':
                self.m3u8Url = url[:-1]
            self.hasTask = True
            self.threadCount = int(self.__threadCount.get())
            self.timeout = int(self.__timeout.get())
            self.retry = int(self.__retry.get())
            ret = self.__downthread.add_task(self.get_downtask())
            num = ret[1]
            if ret[0]:
                title = 'add Succeed!'
                messagebox.showinfo(title, 'current download queue len is %d' % num,parent=self._window)
            else:
                title = 'add Fail!'
                messagebox.showinfo(title, 'The url already exists in the download queue,current download queue len is %d' % num,parent=self._window)
            
            self.__uriText.delete("1.0", "end")  # 从第一行第一个字符删除到末尾
            self.__taskName.set('')
            self._window.focus_set()

    def __load_task(self):
        path = filedialog.askopenfilename(initialdir=self.downloadPath,filetypes=[('Text Files','.m3u8task')])
        if path == None or len(path) == 0:
            return
        task = M3u8Downloader.loadTask(path)
        if task == None:
            return
        self.__display_task(task)
    
    def __display_task(self,task):
        if task:
            self.__uriText.insert("1.0",task.m3u8Url)
            self.__downloadPath.set(task.downloadPath)
            self.__taskName.set(task.taskName)

    def __safe_exit(self):
        self.exit = True
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

    def __find_task_view(self,parent):
        tree = None
        for widget in parent.winfo_children():
            if type(widget) is ttk.Treeview:
                tree = widget
                break
        return tree

    def __create_task_view(self,parent):
        for widget in parent.winfo_children():
            widget.destroy()
        # 创建树形视图
        # columns = ('name')#, 'url', 'status', 'progress', 'speed', 'size')
        tree = ttk.Treeview(parent, show='tree headings', height=10)#, columns=columns)
        # # 定义列
        tree.heading("#0", text="任务名称")  # 树列 (#0) 的表头
        # tree.heading('name', text='任务名称')
        tree.column("#0",anchor=tk.W)
        # 添加滚动条
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        return tree

    def __del_task_view(self,parent,tasks):
        view = self.__find_task_view(parent)
        if view == None:
            return 0
        if not tasks:
            return len(view.get_children())
        del_list = []
        items = view.get_children()
        for t in tasks:
            for it in items:
                if t == view.item(it,'text'):
                    del_list.append(it)
        for it in del_list:
            view.delete(it)

        num = len(view.get_children())
        if num == 0:
            for widget in parent.winfo_children():
                widget.destroy()
            ttk.Label(parent, text="没有任务", font=('Arial', 14)).pack(expand=True)
            return 0
        return num

    def __append_task_view(self,parent,tasks,append = True):
        view = self.__find_task_view(parent)
        if not tasks:
            if view == None:
                return 0
            else:
                return len(view.get_children())

        if view == None:
            view = self.__create_task_view(parent)
        for task in tasks:
            view.insert('', 'end' if append else 0, text = task)
        return len(view.get_children())     

    def __update_task_frame(self,queue_window):
        num = 0
        self.__queue_lock.acquire()
        if self.__waiting_frame:
            self.__append_task_view(self.__waiting_frame,self.__waiting_add)
            num = self.__del_task_view(self.__waiting_frame,self.__waiting_remove)
        self.__notebook.tab(0, text=f"等待中 ({num})")

        if self.__active_frame:
            self.__append_task_view(self.__active_frame,self.__active_add)
            num = self.__del_task_view(self.__active_frame,self.__active_remove)
        self.__notebook.tab(1, text=f"下载中 ({num})")

        if self.__completed_frame:
            num = self.__append_task_view(self.__completed_frame,self.__completed_add,False)
        self.__notebook.tab(2, text=f"已完成 ({num})")
        self.__waiting_add.clear()
        self.__waiting_remove.clear()
        self.__active_add.clear()
        self.__active_remove.clear()
        self.__completed_add.clear()
        self.__update_task_id = queue_window.after(1000,self.__update_task_frame,queue_window)
        self.__queue_lock.release()

    def __view_task_queue(self):
        """查看任务队列详情"""
        # 创建新窗口显示任务队列详情
        queue_window = tk.Toplevel(self._window)
        queue_window.title("任务队列详情")
        window_width = self._window.winfo_width()
        window_height = self._window.winfo_height()
        width = window_width * 3 // 4
        height = window_height * 3 // 4
        window_x = self._window.winfo_x()
        window_y = self._window.winfo_y()
        pos_x = window_x + (window_width - width) // 2
        pos_y = window_y + (window_height - height) // 2
        
        queue_window.geometry('%dx%d+%d+%d' % (width, height, pos_x, pos_y))
        queue_window.transient(self._window)  # 设置为主窗口的临时窗口
        queue_window.grab_set()       # 捕获焦点，防止主窗口被操作
        
        # 创建笔记本控件显示不同状态的任务
        notebook = ttk.Notebook(queue_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 等待中任务标签页
        waiting_frame = ttk.Frame(notebook, padding=10)
        notebook.add(waiting_frame)

        # 下载中任务标签页
        active_frame = ttk.Frame(notebook, padding=10)
        notebook.add(active_frame)

        # 已完成任务标签页
        completed_frame = ttk.Frame(notebook, padding=10)
        notebook.add(completed_frame)

        self.__queue_lock.acquire()
        self.__waiting_frame = waiting_frame
        self.__active_frame = active_frame
        self.__completed_frame = completed_frame
        self.__notebook = notebook
        num = 0
        num = self.__append_task_view(self.__waiting_frame,self.__waiting_queue)
        self.__notebook.tab(0, text=f"等待中 ({num})")
        if num == 0:
            ttk.Label(self.__waiting_frame, text="没有任务", font=('Arial', 14)).pack(expand=True)

        num = self.__append_task_view(self.__active_frame,self.__active_queue)
        self.__notebook.tab(1, text=f"下载中 ({num})")
        if num == 0:
            ttk.Label(self.__active_frame, text="没有任务", font=('Arial', 14)).pack(expand=True)

        num = self.__append_task_view(self.__completed_frame,self.__completed_queue,False)
        self.__notebook.tab(2, text=f"已完成 ({num})")
        if num == 0:
            ttk.Label(self.__completed_frame, text="没有任务", font=('Arial', 14)).pack(expand=True)

        self.__waiting_add.clear()
        self.__waiting_remove.clear()
        self.__active_add.clear()
        self.__active_remove.clear()
        self.__completed_add.clear()
        self.__queue_lock.release()

        self.__update_task_id = queue_window.after(1000,self.__update_task_frame,queue_window)
        # self._window.attributes('-disabled', 1)  # 禁用主窗口
        self._window.wait_window(queue_window)  # 等待窗口关闭
        # self._window.attributes('-disabled', 0)  # 重新启用主窗口
        self.__queue_lock.acquire()
        queue_window.after_cancel(self.__update_task_id)
        self.__waiting_frame = None
        self.__active_frame = None
        self.__completed_frame = None
        self.__notebook = None
        self.__queue_lock.release()
        self._window.lift()

    def __set_window_center_display(self,event):
        base.set_window_center_display(self._window)

    def __init_window(self,width,height):
        newTaskWindow = Tk()
        self._window = newTaskWindow
        self.__downloadPath = StringVar(value = self.downloadPath)
        self.__taskName = StringVar()
        self.__threadCount = StringVar(value = self.threadCount)
        self.__timeout = StringVar(value = self.timeout)
        self.__retry = StringVar(value = self.retry)

        newTaskWindow.title("MyVideoDownloader")
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

        safeExitBtn = Button(buttonframe,text = "安全退出",
        fg = "red",height = 1,
        font = ('楷体',10,'bold'),
        command = self.__safe_exit)
        ToolTip(safeExitBtn,"停止所有任务安全退出")

        taskNameLable = Label(newTaskWindow,text="任务名称:")
        taskNameEntry = Entry(newTaskWindow,textvariable = self.__taskName)
        taskNameEntry.bind('<ButtonRelease-3>',self.__do_paste)

        viewQueueBtn = Button(newTaskWindow, text="查看任务队列", command=self.__view_task_queue)

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
        safeExitBtn.grid(row=1,column=2,sticky=N+S+E+W,padx=5)
        startTaskBtn.grid(row=1,column=3,sticky=N+S+W+E,padx=5)
        viewQueueBtn.grid(row=row,column=2,sticky=S+E,padx=5,pady=5)
        buttonframe.grid_rowconfigure(0,weight=2)
        buttonframe.grid_rowconfigure(1,weight=1)
        buttonframe.grid_rowconfigure(2,weight=3)
        
        buttonframe.grid_columnconfigure(0,weight=2)
        buttonframe.grid_columnconfigure(1,weight=1)
        buttonframe.grid_columnconfigure(2,weight=1)
        buttonframe.grid_columnconfigure(3,weight=1)
        buttonframe.grid_columnconfigure(4,weight=2)

        #startTaskBtn.grid(row=row,column=1,sticky=N,pady=5,ipadx=10,ipady=10)
        #safeExitBtn.grid(row=row,column=2,sticky=N,pady=5,ipadx=10,ipady=10)

        newTaskWindow.grid_columnconfigure(0,weight=1)
        newTaskWindow.grid_columnconfigure(1,weight=5)
        newTaskWindow.grid_columnconfigure(2,weight=1)
        newTaskWindow.grid_rowconfigure(0,weight=2)
        newTaskWindow.grid_rowconfigure(1,weight=3)
        newTaskWindow.grid_rowconfigure(row,weight=3)

        #base.set_window_center_display(newTaskWindow)
        newTaskWindow.bind("<Map>", self.__set_window_center_display)
        newTaskWindow.lift()

    def dispaly(self):
        self.hasTask = False
        self.__init_window(1080,720)
        self.__downthread.add_observer(self)
        self.__downthread.start_download()
        self._window.mainloop()

        print("Saving and exiting...")
        self.__downthread.remove_observer(self)
        self.__downthread.stop_download()
        #downthread.save_task_list()
        self.save_config()
    
    def get_downtask(self):
        return DownTask.DownTask(self.m3u8Url,self.downloadPath,self.taskName,self.threadCount,self.timeout,self.retry)

def isContinue(ret):
    t = Tk()
    t.geometry('%dx%d' % (0,0))
    base.set_window_center_display(t)

    title = 'Download Succeed!' if ret else 'Download Fail!'
    answer = messagebox.askquestion(title, 'Do you want to download continue?',parent=t)
    t.destroy()

    if answer == 'yes':
        print("User selected yes.")
        return True
    else:
        print("User selected no.")
        return False


if __name__ == '__main__':
    window = NewTaskWindow()
    window.dispaly()
    print("Exiting in 3 seconds...")
    time.sleep(3)
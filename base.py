import sys
import os

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

def resource_path(relative_path):
    """获取资源绝对路径"""
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)
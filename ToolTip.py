import tkinter as tk
from tkinter import StringVar

class ToolTipImp:
    def __init__(self, widget, text):
        self.tooltip = None
        self.text = StringVar(value = text)
        widget.tooltip = self
        widget.bind('<Enter>', self.show_tooltip)
        widget.bind('<Leave>', self.hide_tooltip)
        # widget 销毁时解除绑定
        widget.bind('<Destroy>', self.unbind)

    # def __del__(self):
    #     print("delete " + str(self))

    def show_tooltip(self, event):
        widget = event.widget
        x, y, cx, cy = widget.bbox('insert')
        x = x + widget.winfo_rootx() + 25
        y = y + cy + widget.winfo_rooty() + 25

        if self.tooltip is None:
            self.tooltip = tk.Toplevel(widget)
            label = tk.Label(self.tooltip, textvariable=self.text, justify='left', background='#ffffe0', relief='solid', borderwidth=1, font=('楷体', '10', 'normal'))
            label.pack(ipadx=1)

        self.tooltip.overrideredirect(True) 
        self.tooltip.deiconify()
        self.tooltip.geometry('+{}+{}'.format(x, y))

    def hide_tooltip(self, event):
        if self.tooltip:
            self.tooltip.withdraw()
            
    def unbind(self,event):
        widget = event.widget
        widget.unbind('<Enter>')
        widget.unbind('<Leave>')
        widget.unbind('<Destroy>')
        self.tooltip.destroy()
        self.tooltip = None
        widget.tooltip = None

def ToolTip(widget, text):
    #防止重复绑定
    if hasattr(widget,"tooltip"):
        widget.tooltip.text.set(text)
        return
    widget.tooltip = ToolTipImp(widget, text)
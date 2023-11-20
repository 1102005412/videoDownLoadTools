import tkinter as tk
from tkinter import ttk

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.tooltip = None
        self.text = text

        self.widget.bind('<Enter>', self.show_tooltip)
        self.widget.bind('<Leave>', self.hide_tooltip)

    def show_tooltip(self, event):
        x, y, cx, cy = self.widget.bbox('insert')
        x = x + self.widget.winfo_rootx() + 25
        y = y + cy + self.widget.winfo_rooty() + 25

        if self.tooltip is None:
            self.tooltip = tk.Toplevel(self.widget)
            label = tk.Label(self.tooltip, text=self.text, justify='left', background='#ffffe0', relief='solid', borderwidth=1, font=('楷体', '10', 'normal'))
            label.pack(ipadx=1)

        self.tooltip.overrideredirect(True) 
        self.tooltip.deiconify()
        self.tooltip.geometry('+{}+{}'.format(x, y))

    def hide_tooltip(self, event):
        if self.tooltip:
            self.tooltip.withdraw()
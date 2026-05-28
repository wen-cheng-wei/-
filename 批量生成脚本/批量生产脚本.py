# -*- coding: utf-8 -*-
import os
import uuid
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ====================== 工具1：批量生成 Lua 检测脚本 ======================
def generate_lua_scripts(class_list, save_path, template_text):
    try:
        os.makedirs(save_path, exist_ok=True)
        for idx, class_name in enumerate(class_list, start=1):
            tool_name = f"DLObjDetect{idx}"
            script_id = str(uuid.uuid4()).replace("-", "_")
            content = template_text.format(
                tool_name=tool_name,
                class_name=class_name.strip(),
                script_id=script_id
            )
            filename = os.path.join(save_path, f"{class_name}.lua")
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
        messagebox.showinfo("完成", "Lua 脚本批量生成成功！\n\n共生成 {} 个脚本文件".format(len(class_list)))
    except Exception as e:
        messagebox.showerror("错误", str(e))

# ====================== 主界面 ======================
class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("批量生成 Lua 检测脚本")
        self.root.geometry("550x450")
        self.root.resizable(True, True)
        
        # 设置全局样式
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # 自定义样式
        self.style.configure('Title.TLabel', font=('微软雅黑', 13, 'bold'), foreground='#2c3e50')
        self.style.configure('Subtitle.TLabel', font=('微软雅黑', 10), foreground='#7f8c8d')
        self.style.configure('Button.TButton', font=('微软雅黑', 10), padding=6)
        
        # 变量
        self.lua_template_path = tk.StringVar(value="add.txt")
        self.lua_save_dir = tk.StringVar()
        
        # 主滚动容器
        self.main_canvas = tk.Canvas(root, bg="#ffffff", bd=0, highlightthickness=0)
        self.main_scrollbar = ttk.Scrollbar(root, orient=tk.VERTICAL, command=self.main_canvas.yview)
        self.main_canvas.configure(yscrollcommand=self.main_scrollbar.set)
        
        # 布局滚动组件
        self.main_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 创建内容框架
        self.content_frame = ttk.Frame(self.main_canvas, padding=15)
        self.content_frame_id = self.main_canvas.create_window((0, 0), window=self.content_frame, anchor=tk.NW)
        
        # 绑定滚动事件
        self.content_frame.bind("<Configure>", self.on_content_configure)
        self.main_canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        
        # === 标题区域 ===
        title_frame = ttk.Frame(self.content_frame)
        title_frame.pack(fill=tk.X, pady=(0, 12))
        
        title_label = ttk.Label(title_frame, text="批量生成 Lua 检测脚本", style='Title.TLabel')
        title_label.pack(anchor=tk.W)
        
        subtitle_label = ttk.Label(title_frame, text="根据模板文件批量生成检测脚本", style='Subtitle.TLabel')
        subtitle_label.pack(anchor=tk.W, pady=(2, 0))
        
        # === 分隔线 ===
        ttk.Separator(self.content_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        
        # === 模板文件选择 ===
        template_frame = ttk.LabelFrame(self.content_frame, text="模板文件", padding=10)
        template_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(template_frame, text="模板文件路径：", font=('微软雅黑', 10)).pack(anchor=tk.W, pady=(0, 5))
        
        template_entry_frame = ttk.Frame(template_frame)
        template_entry_frame.pack(fill=tk.X)
        
        ttk.Entry(template_entry_frame, textvariable=self.lua_template_path, font=('微软雅黑', 10), width=40).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        ttk.Button(template_entry_frame, text="浏览", command=self.choose_lua_template, style='Button.TButton').pack(side=tk.RIGHT)
        
        # === 保存目录选择 ===
        save_frame = ttk.LabelFrame(self.content_frame, text="保存目录", padding=10)
        save_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(save_frame, text="脚本保存位置：", font=('微软雅黑', 10)).pack(anchor=tk.W, pady=(0, 5))
        
        save_entry_frame = ttk.Frame(save_frame)
        save_entry_frame.pack(fill=tk.X)
        
        ttk.Entry(save_entry_frame, textvariable=self.lua_save_dir, font=('微软雅黑', 10), width=40).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        ttk.Button(save_entry_frame, text="浏览", command=self.choose_lua_save_dir, style='Button.TButton').pack(side=tk.RIGHT)
        
        # === 类别列表输入 ===
        class_frame = ttk.LabelFrame(self.content_frame, text="类别列表", padding=10)
        class_frame.pack(fill=tk.X, pady=(0, 12))
        
        ttk.Label(class_frame, text="输入类别名称（每行一个）：", font=('微软雅黑', 10)).pack(anchor=tk.W, pady=(0, 5))
        
        # 类别列表滚动区域
        class_scroll_frame = ttk.Frame(class_frame)
        class_scroll_frame.pack(fill=tk.X)
        
        class_scrollbar = ttk.Scrollbar(class_scroll_frame, orient=tk.VERTICAL)
        class_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.class_editor = tk.Text(class_scroll_frame, width=50, height=8, font=('微软雅黑', 10), 
                                   wrap=tk.WORD, bd=1, relief=tk.SUNKEN, padx=5, pady=5,
                                   yscrollcommand=class_scrollbar.set)
        self.class_editor.pack(side=tk.LEFT, fill=tk.X)
        
        class_scrollbar.config(command=self.class_editor.yview)
        
        # 预置示例数据
        self.class_editor.insert("end", "1-6_auxiliary_patch\nknife\n1-1_auxiliary_patch")
        
        # 统计信息
        stat_frame = ttk.Frame(class_frame)
        stat_frame.pack(fill=tk.X)
        
        self.stat_label = ttk.Label(stat_frame, text="当前已输入 3 个类别", font=('微软雅黑', 9), foreground='#7f8c8d')
        self.stat_label.pack(anchor=tk.E)
        
        # 绑定文本变化事件
        self.class_editor.bind('<KeyRelease>', self.update_stat)
        
        # === 生成按钮 ===
        button_frame = ttk.Frame(self.content_frame)
        button_frame.pack(fill=tk.X)
        
        self.generate_btn = ttk.Button(button_frame, text="开始生成", command=self.do_gen_lua, 
                                      style='Button.TButton', width=16)
        self.generate_btn.pack(side=tk.RIGHT)
        
        # 底部留白
        ttk.Frame(self.content_frame, height=10).pack(fill=tk.X)

    def on_content_configure(self, event):
        """更新滚动区域"""
        self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
        
    def on_mouse_wheel(self, event):
        """鼠标滚轮事件"""
        self.main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def update_stat(self, event):
        """更新类别数量统计"""
        content = self.class_editor.get("1.0", "end").strip()
        if content:
            count = len([c for c in content.splitlines() if c.strip()])
        else:
            count = 0
        self.stat_label.config(text=f"当前已输入 {count} 个类别")

    def choose_lua_template(self):
        f = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if f: 
            self.lua_template_path.set(f)

    def choose_lua_save_dir(self):
        d = filedialog.askdirectory()
        if d: 
            self.lua_save_dir.set(d)

    # 执行生成Lua
    def do_gen_lua(self):
        temp_path = self.lua_template_path.get()
        save_dir = self.lua_save_dir.get()
        class_txt = self.class_editor.get("1.0", "end").strip()

        if not os.path.exists(temp_path):
            messagebox.showerror("错误", "模板文件不存在")
            return
        if not save_dir:
            messagebox.showerror("错误", "请选择保存目录")
            return
        if not class_txt:
            messagebox.showerror("错误", "请输入类别列表")
            return

        with open(temp_path, "r", encoding="utf-8") as f:
            template = f.read()
        class_list = [c.strip() for c in class_txt.splitlines() if c.strip()]
        generate_lua_scripts(class_list, save_dir, template)

if __name__ == "__main__":
    root = tk.Tk()
    MainWindow(root)
    root.mainloop()
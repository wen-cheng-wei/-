import os
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import glob
from collections import defaultdict
import copy

class AnnotationManager:
    """标注数据管理 - 适配指定COCO格式"""
    def __init__(self):
        self.annotations = {}      # 内部仍用 {filename: list of box dicts} 方便操作
        self.labels = []           # 标签列表（保持顺序）
        self.label_to_id = {}      # name -> category_id 映射
        self.inherit_labels = []   # 用于继承的标签列表（持久化）
    
    def load_existing(self, json_path, image_dir):
        """加载指定COCO格式的标注"""
        if not os.path.exists(json_path):
            self.annotations = {}
            self.labels = []
            self.label_to_id = {}
            self.inherit_labels = []
            return
        
        try:
            with open(json_path, 'r', encoding='gbk') as f:
                data = json.load(f)
            
            # 新格式加载
            if "images" in data and "annotations" in data and "categories" in data:
                # 提取 categories
                self.labels = [cat["name"] for cat in data.get("categories", [])]
                self.label_to_id = {cat["name"]: cat["id"] for cat in data.get("categories", [])}
                # 加载继承标签配置
                self.inherit_labels = data.get("inherit_labels", [])
                
                # 按图片重建内部结构（关键修复）
                self.annotations = {}
                img_id_to_fname = {img["id"]: img["file_name"] 
                                 for img in data.get("images", [])}
                
                for ann in data.get("annotations", []):
                    ck = ann.get("ckvision", {})
                    image_id = ann.get("image_id")
                    fname = img_id_to_fname.get(image_id)
                    
                    if not fname:
                        continue
                    
                    if fname not in self.annotations:
                        self.annotations[fname] = []
                    
                    # 关键：确保每个 box 都有 'label' 字段
                    cat_id = ann.get("category_id", 1)
                    label_name = "object"
                    for cat in data.get("categories", []):
                        if cat["id"] == cat_id:
                            label_name = cat["name"]
                            break
                    
                    self.annotations[fname].append({
                        'x': ck.get('x', 0),
                        'y': ck.get('y', 0),
                        'width': ck.get('width', 0),
                        'height': ck.get('height', 0),
                        'label': label_name   # 必须存在
                    })
            
            # 去重并重建映射
            self.labels = list(dict.fromkeys([lb.strip() for lb in self.labels if lb.strip()]))
            self.label_to_id = {name: idx + 1 for idx, name in enumerate(self.labels)}
            
        except Exception as e:
            print(f"加载标注文件出错: {e}")
            self.annotations = {}
            self.labels = []
            self.label_to_id = {}
    
    def save(self, json_path, image_dir, image_files, current_labels):
        """保存为指定COCO格式"""
        if not image_files:
            return 0
        
        self.labels = current_labels  # 同步最新标签
        self.label_to_id = {name: idx + 1 for idx, name in enumerate(self.labels)}
        
        images = []
        annotations = []
        categories = []
        ann_id = 0
        img_id_map = {}  # filename -> image_id
        
        # 构建 categories
        for idx, name in enumerate(self.labels):
            # 简单颜色映射（可根据需要调整）
            color = 16733695 if name == "main" else (idx * 12345678) % 16777216
            categories.append({
                "id": idx + 1,
                "name": name,
                "color": color
            })
        
        # 只处理有标注的图片
        for idx, path in enumerate(image_files):
            fname = os.path.basename(path)
            boxes = self.annotations.get(fname, [])
            if not boxes:
                continue  # 无框则跳过
            
            # 加载图片尺寸
            try:
                with Image.open(path) as img:
                    w, h = img.size
            except:
                w, h = 1920, 1080  # 兜底尺寸
            
            img_id = len(images)
            img_id_map[fname] = img_id
            
            images.append({
                "id": img_id,
                "width": w,
                "height": h,
                "format": 4,
                "file_name": fname
            })
            
            # 标注框
            for box in boxes:
                annotations.append({
                    "id": ann_id,
                    "image_id": img_id,
                    "category_id": self.label_to_id.get(box.get('label'), 1),
                    "ckvision": {
                        "type": 4,
                        "x": box.get('x', 0),
                        "y": box.get('y', 0),
                        "width": box.get('width', 0),
                        "height": box.get('height', 0),
                        "hollow_list": []
                    }
                })
                ann_id += 1
        
        data = {
            "images": images,
            "annotations": annotations,
            "categories": categories,
            "inherit_labels": self.inherit_labels  # 保存继承标签配置
        }
        
        try:
            with open(json_path, 'w', encoding='gbk') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return len(annotations)  # 返回总框数
        except Exception:
            return 0

class ImageLoader:
    """图片加载与显示"""
    def __init__(self, canvas):
        self.canvas = canvas
        self.current_img = None
        self.display_img = None
        self.tk_img = None
        
        self.image_cache = {}      # 新增：内存缓存 (文件名 -> PhotoImage)
        self.cache_max_size = 50   # 限制缓存数量，避免内存爆炸
    
    def load_and_display(self, path):
        self.current_img = Image.open(path)
        canvas_w = self.canvas.winfo_width() or 800
        canvas_h = self.canvas.winfo_height() or 600
        self.display_img = self.current_img.copy()
        self.display_img.thumbnail((canvas_w, canvas_h))
        self.tk_img = ImageTk.PhotoImage(self.display_img)
        
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)
        return self.current_img, self.display_img

class BoxDrawer:
    """框绘制管理"""
    def __init__(self, canvas, image_loader):
        self.canvas = canvas
        self.image_loader = image_loader
        self.box_rects = []      # 存储矩形ID
        self.box_labels = []     # 存储标签文本ID（新增/确保存在）
        self.selected_box = None  # 当前选中的框索引
    
    def redraw(self, boxes):
        """完全重绘所有框和标签"""
        # 清除旧的绘制元素
        for rect_id in self.box_rects:
            self.canvas.delete(rect_id)
        for label_id in self.box_labels:
            self.canvas.delete(label_id)
        # 新增：清除旧手柄
        self.canvas.delete("handle")
        
        self.box_rects = []
        self.box_labels = []
        
        if not boxes:
            return
        
        # 获取缩放比例
        scale_x = self.image_loader.current_img.width / self.image_loader.display_img.width
        scale_y = self.image_loader.current_img.height / self.image_loader.display_img.height
        
        for idx, box in enumerate(boxes):

            # 边界保护
            box['x'] = max(0, box['x'])
            box['y'] = max(0, box['y'])
            box['width'] = min(self.image_loader.current_img.width - box['x'], box['width'])
            box['height'] = min(self.image_loader.current_img.height - box['y'], box['height'])
            
            # 计算显示坐标
            disp_x = box['x'] / scale_x
            disp_y = box['y'] / scale_y
            disp_w = box['width'] / scale_x
            disp_h = box['height'] / scale_y
            
            # 1. 绘制矩形框（选中时高亮）
            color = "lime" if idx == getattr(self, 'selected_box', None) else "red"
            width = 3 if idx == getattr(self, 'selected_box', None) else 2
            
            rect_id = self.canvas.create_rectangle(
                disp_x, disp_y, disp_x + disp_w, disp_y + disp_h,
                outline=color, width=width
            )
            self.box_rects.append(rect_id)
            
            # 2. 绘制标签文本
            label_text = box.get('label', 'object')
            label_id = self.canvas.create_text(
                disp_x + 5, disp_y + 5,
                text=label_text,
                fill="yellow",
                font=("Arial", 10, "bold"),
                anchor="nw"
            )
            self.box_labels.append(label_id)
            
            # 3. **关键修复**：为选中框绘制缩放手柄
            if idx == getattr(self, 'selected_box', None):
                self._draw_handles(disp_x, disp_y, disp_x + disp_w, disp_y + disp_h, idx)
    
    def _draw_handles(self, x1, y1, x2, y2, box_idx):
        """绘制四个角的手柄，并附加角的索引"""
        size = 8
        handles = [
            (x1, y1, 0),  # 左上
            (x2, y1, 1),  # 右上
            (x1, y2, 2),  # 左下
            (x2, y2, 3)   # 右下
        ]
        for hx, hy, h_idx in handles:
            self.canvas.create_rectangle(
                hx - size/2, hy - size/2, 
                hx + size/2, hy + size/2,
                fill="blue", 
                outline="white", 
                width=1,
                tags=("handle", f"handle_{box_idx}_{h_idx}")
            )

class InteractionHandler:
    """鼠标与键盘交互（新增实时新建框预览）"""
    def __init__(self, canvas, drawer, current_boxes_ref, label_var):
        self.canvas = canvas
        self.drawer = drawer
        self.current_boxes = current_boxes_ref
        self.label_var = label_var
        
        # 状态变量
        self.drag_start = None
        self.resize_handle = False
        self.selected_box = None
        self.active_handle = None
        
        # 预览相关
        self.preview_rect = None
        self.preview_label = None
        
        # 绑定事件
        canvas.bind("<ButtonPress-1>", self.on_press)
        canvas.bind("<B1-Motion>", self.on_drag)
        canvas.bind("<ButtonRelease-1>", self.on_release)
        canvas.bind("<Button-3>", self.on_right_click)
    
    def on_press(self, event):
        """按下鼠标 - 优先检测手柄/已有框，否则准备新建"""
        self._clear_preview()
        self.drag_start = (event.x, event.y)
        self.resize_handle = False
        self.active_handle = None
        
        # === 1. 优先检测手柄 ===
        items = self.canvas.find_overlapping(event.x-8, event.y-8, event.x+8, event.y+8)
        for item in items:
            tags = self.canvas.gettags(item)
            for t in tags:
                if t.startswith("handle_"):
                    handle_info = t.split("_")
                    self.selected_box = int(handle_info[1])
                    self.drawer.selected_box = self.selected_box
                    self.resize_handle = True
                    self.active_handle = int(handle_info[2]) if len(handle_info) > 2 else None
                    self.drawer.redraw(self.current_boxes)
                    return
        
        # === 2. 检测是否点击在已有框内部（用于拖动整个框）===
        # 优化：当多个框重叠时，选择面积最小的框（最里面的框）
        scale_x = self.drawer.image_loader.display_img.width / self.drawer.image_loader.current_img.width
        scale_y = self.drawer.image_loader.display_img.height / self.drawer.image_loader.current_img.height
        
        clicked_box = None
        min_area = float('inf')  # 记录最小面积
        
        for i, box in enumerate(self.current_boxes):
            x1 = box['x'] * scale_x
            y1 = box['y'] * scale_y
            x2 = (box['x'] + box['width']) * scale_x
            y2 = (box['y'] + box['height']) * scale_y
            
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                # 计算当前框的面积
                area = box['width'] * box['height']
                # 选择面积最小的框（最里面的框）
                if area < min_area:
                    min_area = area
                    clicked_box = i
        
        if clicked_box is not None:
            self.selected_box = clicked_box
            self.drawer.selected_box = clicked_box
            self.resize_handle = False
            self.drawer.redraw(self.current_boxes)
            return
        
        # === 3. 准备新建框 ===
        # 只有当有选中状态需要清除时才重绘，避免不必要的重绘导致闪烁或消失
        if self.drawer.selected_box is not None:
            self.drawer.selected_box = None
            self.selected_box = None
            self.drawer.redraw(self.current_boxes)  # 清除选中高亮
        else:
            self.selected_box = None
    
    def on_drag(self, event):
        """拖拽处理"""
        if not self.drag_start:
            return
        
        # 已选中框的移动或缩放
        if self.selected_box is not None:
            dx = event.x - self.drag_start[0]
            dy = event.y - self.drag_start[1]
            box = self.current_boxes[self.selected_box]
            
            scale_x = self.drawer.image_loader.current_img.width / self.drawer.image_loader.display_img.width
            scale_y = self.drawer.image_loader.current_img.height / self.drawer.image_loader.display_img.height
            
            if self.resize_handle and self.active_handle is not None:
                # 角点缩放
                dx_real = dx * scale_x
                dy_real = dy * scale_y
                
                if self.active_handle == 0:   # 左上
                    box['x'] += int(dx_real)
                    box['y'] += int(dy_real)
                    box['width'] = max(10, int(box['width'] - dx_real))
                    box['height'] = max(10, int(box['height'] - dy_real))
                elif self.active_handle == 1: # 右上
                    box['y'] += int(dy_real)
                    box['width'] = max(10, int(box['width'] + dx_real))
                    box['height'] = max(10, int(box['height'] - dy_real))
                elif self.active_handle == 2: # 左下
                    box['x'] += int(dx_real)
                    box['width'] = max(10, int(box['width'] - dx_real))
                    box['height'] = max(10, int(box['height'] + dy_real))
                elif self.active_handle == 3: # 右下
                    box['width'] = max(10, int(box['width'] + dx_real))
                    box['height'] = max(10, int(box['height'] + dy_real))
            else:
                # 移动整个框
                box['x'] = int(box['x'] + dx * scale_x)
                box['y'] = int(box['y'] + dy * scale_y)
            
            self.drag_start = (event.x, event.y)
            self.drawer.redraw(self.current_boxes)
            return
        
        # 新建框的实时预览
        self._update_preview(event.x, event.y)
    
    def _update_preview(self, curr_x, curr_y):
        """实时更新新建框预览"""
        x1, y1 = self.drag_start
        x2, y2 = curr_x, curr_y
        
        self._clear_preview()
        
        if abs(x2 - x1) < 5 or abs(y2 - y1) < 5:
            return
        
        # 预览矩形（绿色虚线）
        self.preview_rect = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            outline="#00ff88",
            width=2,
            dash=(4, 4)
        )
        
        # 预览标签文字
        label = self.label_var.get().strip() or "object"
        self.preview_label = self.canvas.create_text(
            min(x1, x2) + 5, min(y1, y2) + 5,
            text=label,
            fill="#ffff00",
            font=("Arial", 10, "bold"),
            anchor="nw"
        )
    
    def _clear_preview(self):
        """清除预览元素"""
        if self.preview_rect:
            self.canvas.delete(self.preview_rect)
            self.preview_rect = None
        if self.preview_label:
            self.canvas.delete(self.preview_label)
            self.preview_label = None
    
    def on_release(self, event):
        """松开鼠标"""
        if not self.drag_start:
            self._clear_preview()
            return
        
        # 已选中框的操作结束
        if self.selected_box is not None:
            self._clear_preview()
            self.drag_start = None
            self.resize_handle = False
            self.active_handle = None
            self.drawer.redraw(self.current_boxes)
            return
        
        # 新建框逻辑
        x1, y1 = self.drag_start
        x2, y2 = event.x, event.y
        
        self._clear_preview()
        
        if abs(x2 - x1) < 10 or abs(y2 - y1) < 10:
            self.drag_start = None
            return
        
        # 计算真实坐标
        scale_x = self.drawer.image_loader.current_img.width / self.drawer.image_loader.display_img.width
        scale_y = self.drawer.image_loader.current_img.height / self.drawer.image_loader.display_img.height
        
        bx = int(min(x1, x2) * scale_x)
        by = int(min(y1, y2) * scale_y)
        bw = int(abs(x2 - x1) * scale_x)
        bh = int(abs(y2 - y1) * scale_y)
        
        label = self.label_var.get().strip() or "object"
        
        self.current_boxes.append({
            'x': bx, 'y': by, 'width': bw, 'height': bh, 'label': label
        })
        
        self.drag_start = None
        self.drawer.redraw(self.current_boxes)
    
    def on_right_click(self, event):
        """右键操作：选中框时直接删除，未选中时修改标签"""
        # 优先处理已选中的框：右键直接删除（符合你的需求）
        if self.drawer.selected_box is not None:
            # 确保索引有效
            if 0 <= self.drawer.selected_box < len(self.current_boxes):
                del self.current_boxes[self.drawer.selected_box]
            self.drawer.selected_box = None
            self.selected_box = None  # 同步清除InteractionHandler的选中状态
            self.drawer.redraw(self.current_boxes)
            return
        
        # 如果没有选中框，则执行原来的修改标签逻辑
        scale_x = self.drawer.image_loader.display_img.width / self.drawer.image_loader.current_img.width
        scale_y = self.drawer.image_loader.display_img.height / self.drawer.image_loader.current_img.height
        
        for i, box in enumerate(self.current_boxes):
            x1 = box['x'] * scale_x
            y1 = box['y'] * scale_y
            x2 = (box['x'] + box['width']) * scale_x
            y2 = (box['y'] + box['height']) * scale_y
            
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                new_label = simpledialog.askstring("修改标签", "输入新标签：", initialvalue=box['label'])
                if new_label and new_label.strip():
                    box['label'] = new_label.strip()
                    self.drawer.redraw(self.current_boxes)
                return

class FrameAnnotator:
    """主控制器 - 协调 UI 与各功能模块"""
    def __init__(self, root):
        self.root = root
        self.root.title("视频帧接力标注工具")
        
        # 核心状态
        self.image_dir = None
        self.image_files = []
        self.current_idx = 0
        self.inherit_mode = True
        self.delete_mode = False   # 删除模式：开启时按A键会删除当前图片的指定标签框
        self.current_boxes = []   # 当前帧的标注框列表（引用传递给其他模块）
        self.inherit_tolerance = 1000
        self.inherit_labels = set()  # 用于继承的标签集合
        
        # 模块初始化
        self.manager = AnnotationManager()
        self.json_path = None
        
        self.image_loader = None
        self.drawer = None
        self.interaction = None
        
        self.setup_ui()

            # === 新增：退出时自动保存 ===
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_ui(self):
        """重构后的左右布局 UI"""
        # 主容器 - 使用 PanedWindow 支持拖拽调整宽度
        self.main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=6)
        self.main_paned.pack(fill=tk.BOTH, expand=True)
    
        # ==================== 左侧控制面板（带滚动条）====================
        left_container = tk.Frame(self.main_paned, width=280, relief=tk.GROOVE, bd=1)
        self.main_paned.add(left_container, stretch="never")
        
        # 添加滚动条
        self.left_scrollbar = tk.Scrollbar(left_container, orient=tk.VERTICAL)
        self.left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 可滚动的内部面板
        self.left_panel = tk.Canvas(left_container, width=280, yscrollcommand=self.left_scrollbar.set)
        self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.left_scrollbar.config(command=self.left_panel.yview)
        
        # 实际的内容框架
        self.left_content = tk.Frame(self.left_panel)
        self.left_content_id = self.left_panel.create_window((0, 0), window=self.left_content, anchor=tk.NW)
        
        # 绑定滚动事件
        self.left_content.bind("<Configure>", lambda e: self.left_panel.configure(scrollregion=self.left_panel.bbox("all")))
        self.left_panel.bind("<MouseWheel>", self.on_left_scroll)
        self.left_panel.bind("<Button-1>", lambda e: self.left_panel.focus_set())  # 点击Canvas获得焦点
    
        # 文件操作区
        file_frame = tk.LabelFrame(self.left_content, text="文件操作", padx=8, pady=8)
        file_frame.pack(fill=tk.X, padx=8, pady=6)
        
        tk.Button(file_frame, text="📁 选择图片文件夹", 
                  command=self.load_folder, height=2).pack(fill=tk.X, pady=4)
    
        # 导航区
        nav_frame = tk.LabelFrame(self.left_content, text="导航控制", padx=8, pady=8)
        nav_frame.pack(fill=tk.X, padx=8, pady=6)
    
        nav_btns = tk.Frame(nav_frame)
        nav_btns.pack(fill=tk.X)
        
        tk.Button(nav_btns, text="← 上一张 (A)", command=self.prev_image, width=12).pack(side=tk.LEFT, padx=4)
        tk.Button(nav_btns, text="下一张 (D) →", command=self.next_image, width=12).pack(side=tk.RIGHT, padx=4)
        
        self.status_label = tk.Label(nav_frame, text="第 0 / 0 张", 
                                    font=("微软雅黑", 10, "bold"), fg="#0066cc")
        self.status_label.pack(pady=8)
    
        # 继承模式
        mode_frame = tk.Frame(nav_frame)
        mode_frame.pack(fill=tk.X, pady=4)
        tk.Label(mode_frame, text="继承模式：").pack(side=tk.LEFT)
        
        self.mode_var = tk.StringVar(value="ON")
        self.mode_label = tk.Label(mode_frame, textvariable=self.mode_var, 
                                  font=("微软雅黑", 10, "bold"), fg="green")
        self.mode_label.pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Button(mode_frame, text="切换 (G)", command=self.toggle_inherit, 
                  width=10).pack(side=tk.RIGHT)
        
        # 新增：当前框数量显示（放在继承模式下方）
        self.box_count_var = tk.StringVar(value="当前框: 0")
        self.box_count_label = tk.Label(nav_frame, textvariable=self.box_count_var,
                                       font=("微软雅黑", 10, "bold"), fg="#0066cc")
        self.box_count_label.pack(anchor=tk.W, padx=8, pady=(4, 0))

        # 继承模式下方新增
        tolerance_frame = tk.Frame(nav_frame)
        tolerance_frame.pack(fill=tk.X, pady=4)
        
        tk.Label(tolerance_frame, text="继承容差(px)：").pack(side=tk.LEFT)
        self.tolerance_var = tk.StringVar(value=str(self.inherit_tolerance))
        self.tolerance_entry = tk.Entry(tolerance_frame, textvariable=self.tolerance_var, width=6)
        self.tolerance_entry.pack(side=tk.LEFT, padx=4)
        tk.Button(tolerance_frame, text="应用", command=self.update_tolerance, width=6).pack(side=tk.RIGHT)
        
        # 继承标签选择
        inherit_label_frame = tk.Frame(nav_frame)
        inherit_label_frame.pack(fill=tk.X, pady=4)
        self.inherit_label_btn = tk.Button(inherit_label_frame, text="选择继承标签", 
                                          command=self.select_inherit_labels, width=16)
        self.inherit_label_btn.pack(side=tk.LEFT)
        self.inherit_label_status = tk.Label(inherit_label_frame, text="全部", fg="#0066cc")
        self.inherit_label_status.pack(side=tk.RIGHT)
    
        # 删除模式（类似于继承模式的开关）
        delete_frame = tk.Frame(nav_frame)
        delete_frame.pack(fill=tk.X, pady=4)
        tk.Label(delete_frame, text="删除模式：").pack(side=tk.LEFT)
        
        self.delete_var = tk.StringVar(value="OFF")
        self.delete_label = tk.Label(delete_frame, textvariable=self.delete_var, 
                                  font=("微软雅黑", 10, "bold"), fg="#ff6666")
        self.delete_label.pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Button(delete_frame, text="切换 (H)", command=self.toggle_delete_mode, 
                  width=10).pack(side=tk.RIGHT)
    
        # 标签管理区
        label_frame = tk.LabelFrame(self.left_content, text="标签管理", padx=8, pady=8)
        label_frame.pack(fill=tk.X, padx=8, pady=6)
    
        # 当前标签选择
        tk.Label(label_frame, text="当前标签：").pack(anchor=tk.W)
        self.label_var = tk.StringVar(value="")
        self.label_combo = ttk.Combobox(label_frame, textvariable=self.label_var, 
                                      state="readonly", width=25)
        self.label_combo.pack(fill=tk.X, pady=4)
    
        # 标签操作按钮
        btn_frame1 = tk.Frame(label_frame)
        btn_frame1.pack(fill=tk.X, pady=6)
        tk.Button(btn_frame1, text="添加标签", command=self.add_label).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame1, text="修改标签", command=self.modify_label).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame1, text="删除标签", command=self.delete_label).pack(side=tk.LEFT, padx=4)
    
        # 快捷操作区
        quick_frame = tk.LabelFrame(self.left_content, text="快捷操作", padx=8, pady=8)
        quick_frame.pack(fill=tk.X, padx=8, pady=6)
        
        tk.Button(quick_frame, text="💾 保存全部标注 (Ctrl+S)", 
                  command=self.manual_save, bg="#e6f0ff").pack(fill=tk.X, pady=4)
        
        tk.Button(quick_frame, text="🗑️ 删除选中框 (Delete)", 
                  command=self.delete_selected_box).pack(fill=tk.X, pady=4)
        
        # 新增：按标签删除
        tk.Button(quick_frame, text="🗑️ 按标签删除框 (Ctrl+Shift+Delete)", 
                  command=self.delete_boxes_by_label, bg="#ffe6e6").pack(fill=tk.X, pady=4)
    
        # 跳转区
        # 跳转控制区
        jump_frame = tk.LabelFrame(self.left_content, text="快速跳转", padx=8, pady=8)
        jump_frame.pack(fill=tk.X, padx=8, pady=6)
        
        # 快速导航按钮
        nav_quick = tk.Frame(jump_frame)
        nav_quick.pack(fill=tk.X, pady=4)
        tk.Button(nav_quick, text="首页", command=self.go_first, width=8).pack(side=tk.LEFT)
        tk.Button(nav_quick, text="上10张", command=self.prev_ten, width=8).pack(side=tk.LEFT)
        tk.Button(nav_quick, text="下10张", command=self.next_ten, width=8).pack(side=tk.LEFT)
        tk.Button(nav_quick, text="末页", command=self.go_last, width=8).pack(side=tk.RIGHT)
        
        # 输入跳转
        sub_jump = tk.Frame(jump_frame)
        sub_jump.pack(fill=tk.X, pady=4)
        tk.Label(sub_jump, text="跳转到第").pack(side=tk.LEFT)
        self.jump_entry = tk.Entry(sub_jump, width=8)
        self.jump_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(sub_jump, text="张").pack(side=tk.LEFT)
        tk.Button(sub_jump, text="Go", command=self.jump_to, width=8).pack(side=tk.RIGHT)
        
        # 图片列表（支持点击跳转）
        list_frame = tk.LabelFrame(self.left_content, text="图片列表", padx=8, pady=8)
        list_frame.pack(fill=tk.X, padx=8, pady=6)
        
        # 创建滚动条和列表框
        list_scroll = tk.Scrollbar(list_frame)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.image_listbox = tk.Listbox(list_frame, yscrollcommand=list_scroll.set, 
                                        width=30, height=8, font=("微软雅黑", 9))
        self.image_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_scroll.config(command=self.image_listbox.yview)
        
        # 绑定点击事件
        self.image_listbox.bind("<Double-1>", self.on_list_double_click)
        self.image_listbox.bind("<Button-1>", self.on_list_click)
    
        # ==================== 右侧图片显示区 ====================
        self.right_panel = tk.Frame(self.main_paned)
        self.main_paned.add(self.right_panel, stretch="always")  # 右侧可伸缩
    
        self.canvas = tk.Canvas(self.right_panel, bg="#2f2f2f", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
        # 绑定全局快捷键
        # self.root.bind("<KeyPress>", self.on_key)

            # ==================== 全局快捷键增强 ====================
        self.canvas.bind("<KeyPress>", self.on_key)   # 让画布也能接收按键
        self.canvas.focus_set()                       # 默认让画布获得焦点
        
        # 确保点击画布后仍能响应快捷键
        self.canvas.bind("<Button-1>", lambda e: self.canvas.focus_set(), add="+")

    def update_tolerance(self):
        """更新继承容差"""
        try:
            val = int(self.tolerance_var.get())
            if val < 1:
                val = 1
            self.inherit_tolerance = val
            self.tolerance_var.set(str(val))
            # 可选：立即重新加载当前图片以应用新容差
            self.load_current_image()
        except:
            messagebox.showwarning("输入错误", "请输入有效的正整数")
    
    def load_folder(self):
        """加载图片文件夹"""
        self.image_dir = filedialog.askdirectory()
        if not self.image_dir:
            return
        
        self.image_files = sorted(glob.glob(os.path.join(self.image_dir, "*.jpg")) + 
                                 glob.glob(os.path.join(self.image_dir, "*.png")))
        if not self.image_files:
            messagebox.showwarning("警告", "文件夹中没有图片")
            return
        
        self.json_path = os.path.join(self.image_dir, "annotations.json")
        self.manager.load_existing(self.json_path, self.image_dir)
    
        # 清理已不存在图片的标注记录
        valid_fnames = {os.path.basename(p) for p in self.image_files}
        to_delete = [k for k in list(self.manager.annotations.keys()) if k not in valid_fnames]
        for k in to_delete:
            del self.manager.annotations[k]
        
        # === 新增：更新标签下拉框 ===
        self.label_combo['values'] = self.manager.labels
        if self.manager.labels:
            self.label_var.set(self.manager.labels[0])  # 默认选中第一个标签
        else:
            self.label_var.set("")
        
        # 恢复继承标签状态
        self.inherit_labels = set(self.manager.inherit_labels)
        # 更新继承标签状态显示
        if hasattr(self, 'inherit_label_status'):
            if not self.inherit_labels:
                self.inherit_label_status.config(text="全部", fg="#0066cc")
            else:
                self.inherit_label_status.config(text=f"{len(self.inherit_labels)}个标签", fg="#00cc66")
        
        # 初始化图片与绘制模块
        self.image_loader = ImageLoader(self.canvas)
        self.drawer = BoxDrawer(self.canvas, self.image_loader)
        self.interaction = InteractionHandler(self.canvas, self.drawer, 
                                            self.current_boxes, self.label_var)
        
        self.current_idx = 0
        self.load_current_image()
        self.update_image_list()  # 初始化图片列表
        self.setup_left_scroll_bindings()  # 绑定滚轮事件
        self.main_paned.update()
    
    def load_current_image(self):
        """加载当前图片并刷新标注（支持可配置继承容差）"""
        if not self.image_files:
            return
        
        path = self.image_files[self.current_idx]
        fname = os.path.basename(path)
        
        # 加载图片
        self.image_loader.load_and_display(path)
        
        # === 修复后的继承逻辑：先继承上一帧，再补充当前帧独有的框 ===
        saved_ann = self.manager.annotations.get(fname)
        
        def filter_by_inherit_labels(boxes):
            """根据选中的继承标签过滤框"""
            if not self.inherit_labels:
                return boxes  # 如果没有选择任何标签，继承全部
            return [box for box in boxes if box.get('label', 'object') in self.inherit_labels]
        
        if self.inherit_mode and self.current_idx > 0:
            # 继承模式开启且不是第一张图片 → 先继承上一帧的框（最新的）
            prev_fname = os.path.basename(self.image_files[self.current_idx - 1])
            prev_ann = self.manager.annotations.get(prev_fname, [])
            
            # 按继承标签过滤
            filtered_prev_ann = filter_by_inherit_labels(prev_ann)
            
            # 先清空当前框，继承上一帧的框（保证最新的继承优先）
            self.current_boxes.clear()
            self.current_boxes.extend(copy.deepcopy(filtered_prev_ann))
            
            if saved_ann is not None and len(saved_ann) > 0:
                # 当前帧已有保存的标注 → 补充当前帧独有的框（用户之前手动添加的）
                existing = set()
                tolerance = self.inherit_tolerance
                
                for box in self.current_boxes:
                    key = (
                        round(box['x'] / tolerance),
                        round(box['y'] / tolerance),
                        round(box['width'] / tolerance),
                        round(box['height'] / tolerance),
                        box.get('label', 'object')
                    )
                    existing.add(key)
                
                # 添加当前帧保存的、但不在继承框中的框（用户手动添加的）
                for sbox in saved_ann:
                    skey = (
                        round(sbox['x'] / tolerance),
                        round(sbox['y'] / tolerance),
                        round(sbox['width'] / tolerance),
                        round(sbox['height'] / tolerance),
                        sbox.get('label', 'object')
                    )
                    if skey not in existing:
                        self.current_boxes.append(copy.deepcopy(sbox))
        
        elif saved_ann is not None and len(saved_ann) > 0:
            # 没有开启继承模式，但有保存的标注 → 加载已保存的标注
            self.current_boxes.clear()
            self.current_boxes.extend(copy.deepcopy(saved_ann))
        
        else:
            # 无继承模式且无保存的标注，或第一张图片
            self.current_boxes.clear()
        
        # 保留选中状态（允许跨图片拖动）
        # 如果当前有选中的框，尝试在新图片中找到对应的框
        if self.drawer.selected_box is not None and 0 <= self.drawer.selected_box < len(self.current_boxes):
            # 保持选中状态
            pass
        elif len(self.current_boxes) > 0:
            # 默认选中第一个框（方便继续拖动）
            self.drawer.selected_box = 0
            if hasattr(self.interaction, 'selected_box'):
                self.interaction.selected_box = 0
        else:
            # 没有框，清除选中状态
            self.drawer.selected_box = None
            if hasattr(self.interaction, 'selected_box'):
                self.interaction.selected_box = None
        
        self.drawer.redraw(self.current_boxes)
        self.update_status()
        
        # 更新图片列表选中状态
        if hasattr(self, 'image_listbox'):
            self.image_listbox.selection_clear(0, tk.END)
            self.image_listbox.selection_set(self.current_idx)
            self.image_listbox.see(self.current_idx)
        self.canvas.focus_set()  # 每次切换图片都确保焦点在画布
    
    def save_current(self):
        """保存当前帧标注"""
        if not self.image_files:
            return
        fname = os.path.basename(self.image_files[self.current_idx])
        self.manager.annotations[fname] = copy.deepcopy(self.current_boxes)
        # 可选：如果为空，也可以考虑不保存，让下次继续继承
        # 但目前保留保存行为更安全
    
    def next_image(self):
        """下一张"""
        if not self.image_files:
            return
        self.save_current()        # 只更新内存
        
        if self.current_idx < len(self.image_files) - 1:
            self.current_idx += 1
            self.load_current_image()

    def toggle_inherit(self):
        """切换继承模式"""
        self.inherit_mode = not self.inherit_mode
        self.mode_var.set('ON' if self.inherit_mode else 'OFF')
        self.mode_label.config(fg="green" if self.inherit_mode else "#ff6666")
        self.update_status()   # 同步刷新当前框计数
    
    def toggle_delete_mode(self):
        """切换删除模式"""
        # 切换前先保存当前状态，确保状态一致
        if self.image_files:
            self.save_current()
        
        self.delete_mode = not self.delete_mode
        self.delete_var.set('ON' if self.delete_mode else 'OFF')
        self.delete_label.config(fg="#ff6666" if self.delete_mode else "#888888")
        self.update_status()   # 同步刷新状态显示
    
    def prev_image(self):
        """上一张（删除模式下会先删除当前图片的指定标签框）"""
        if self.current_idx > 0:
            # 如果删除模式开启，先删除当前图片的指定标签框
            if self.delete_mode:
                current_label = self.label_var.get().strip()
                if current_label:
                    # 删除当前图片中指定标签的框
                    # 使用原地修改方式，保持引用不变
                    original_count = len(self.current_boxes)
                    filtered_boxes = [box for box in self.current_boxes 
                                      if box.get('label') != current_label]
                    deleted_count = original_count - len(filtered_boxes)
                    if deleted_count > 0:
                        # 关键修复：使用 clear + extend 保持引用不变
                        self.current_boxes.clear()
                        self.current_boxes.extend(filtered_boxes)
                        self.drawer.selected_box = None
                        self.drawer.redraw(self.current_boxes)
            
            self.save_current()    # 保存当前状态到 manager.annotations
            self.current_idx -= 1
            self.load_current_image()
    
    def on_key(self, event):
        """键盘快捷键 - 增强版"""
        # 统一处理大小写
        key = event.keysym.lower()
        
        if key in ['d', 'right']:
            self.next_image()
        elif key in ['a', 'left']:
            self.prev_image()
        elif key in ['g', 'i']:
            self.toggle_inherit()
        elif key == 'h':
            self.toggle_delete_mode()
        elif event.keysym == 'Delete':
            # 只有真正按下Delete键才处理（防止误触）
            if self.drawer and self.drawer.selected_box is not None:
                # 确保索引有效
                if 0 <= self.drawer.selected_box < len(self.current_boxes):
                    del self.current_boxes[self.drawer.selected_box]
                self.drawer.selected_box = None
                if hasattr(self.interaction, 'selected_box'):
                    self.interaction.selected_box = None  # 同步清除状态
                self.drawer.redraw(self.current_boxes)
                self.update_status()
        elif event.state & 0x4 and key == 's':            # Ctrl + S
            self.manual_save()
    
    def update_status(self):
        """更新状态显示"""
        total = len(self.image_files)
        fname = os.path.basename(self.image_files[self.current_idx]) if self.image_files else ""
        
        # 添加删除模式提示
        delete_hint = "[删除模式] " if self.delete_mode else ""
        self.status_label.config(text=f"{delete_hint}第 {self.current_idx + 1} / {total} 张 - {fname}")
        
        # 更新左侧当前框计数
        if hasattr(self, 'box_count_var'):
            self.box_count_var.set(f"当前框: {len(self.current_boxes)}")
    
    def add_label(self):
        """添加新标签"""
        new = simpledialog.askstring("添加标签", "新标签名称:")
        if not new:
            return
        new = new.strip()
        if not new:
            return
        if new in self.manager.labels:
            messagebox.showwarning("提示", "该标签已存在")
            return
        
        self.manager.labels.append(new)
        self.label_combo['values'] = self.manager.labels
        self.label_var.set(new)
        self.update_status()
    
    def jump_to(self):
        """跳转到指定序号"""
        try:
            idx = int(self.jump_entry.get()) - 1
            if 0 <= idx < len(self.image_files):
                self.save_current()
                self.current_idx = idx
                self.load_current_image()
        except:
            pass
    
    def on_left_scroll(self, event):
        """左侧面板滚动事件"""
        self.left_panel.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
    def setup_left_scroll_bindings(self):
        """为左侧面板的所有子控件绑定滚轮事件"""
        def scroll_handler(event):
            if hasattr(self, 'left_panel'):
                self.left_panel.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        # 为所有子控件绑定滚轮事件
        for widget in self.left_content.winfo_children():
            widget.bind("<MouseWheel>", scroll_handler)
            # 递归绑定子控件的子控件
            for child in widget.winfo_children():
                child.bind("<MouseWheel>", scroll_handler)
    
    def go_first(self):
        """跳转到第一张图片"""
        if self.image_files:
            self.save_current()
            self.current_idx = 0
            self.load_current_image()
    
    def go_last(self):
        """跳转到最后一张图片"""
        if self.image_files:
            self.save_current()
            self.current_idx = len(self.image_files) - 1
            self.load_current_image()
    
    def prev_ten(self):
        """向前跳10张"""
        if self.image_files:
            self.save_current()
            self.current_idx = max(0, self.current_idx - 10)
            self.load_current_image()
    
    def next_ten(self):
        """向后跳10张"""
        if self.image_files:
            self.save_current()
            self.current_idx = min(len(self.image_files) - 1, self.current_idx + 10)
            self.load_current_image()
    
    def on_list_double_click(self, event):
        """双击列表项跳转"""
        selection = self.image_listbox.curselection()
        if selection:
            idx = selection[0]
            self.save_current()
            self.current_idx = idx
            self.load_current_image()
    
    def on_list_click(self, event):
        """单击列表项选中（用于键盘回车确认）"""
        selection = self.image_listbox.curselection()
        if selection:
            idx = selection[0]
            # 可选：高亮显示但不立即跳转，等待用户确认
    
    def update_image_list(self):
        """更新图片列表显示"""
        self.image_listbox.delete(0, tk.END)
        for i, path in enumerate(self.image_files):
            fname = os.path.basename(path)
            # 显示格式：序号 - 文件名
            self.image_listbox.insert(tk.END, f"{i+1:4d} - {fname}")
        # 选中当前图片
        if self.image_files:
            self.image_listbox.selection_set(self.current_idx)
            self.image_listbox.see(self.current_idx)

    def delete_label(self):
        """删除当前选中的标签"""
        current_label = self.label_var.get().strip()
        if not current_label or current_label not in self.manager.labels:
            return
        
        if messagebox.askyesno("确认删除", 
                              f"确定要删除标签 '{current_label}' 吗？\n"
                              f"此操作不会删除已标注的框，仅移除标签选项。"):
            self.manager.labels.remove(current_label)
            
            # 更新 Combobox
            self.label_combo['values'] = self.manager.labels
            if self.manager.labels:
                self.label_var.set(self.manager.labels[0])
            else:
                self.label_var.set("")
            
            self.update_status()

    def modify_label(self):
        """修改当前选中的标签名称"""
        old_label = self.label_var.get().strip()
        if not old_label or old_label not in self.manager.labels:
            messagebox.showwarning("提示", "请先选择一个要修改的标签")
            return
        
        new_label = simpledialog.askstring("修改标签", 
                                         f"将标签 '{old_label}' 修改为：", 
                                         initialvalue=old_label)
        if not new_label or new_label.strip() == old_label:
            return
        
        new_label = new_label.strip()
        if new_label in self.manager.labels:
            messagebox.showwarning("提示", f"标签 '{new_label}' 已存在")
            return
        
        # 更新标签列表
        idx = self.manager.labels.index(old_label)
        self.manager.labels[idx] = new_label
        
        # 更新映射
        self.manager.label_to_id = {name: i + 1 for i, name in enumerate(self.manager.labels)}
        
        # 同步更新所有已保存的标注框中的标签
        for boxes in self.manager.annotations.values():
            for box in boxes:
                if box.get('label') == old_label:
                    box['label'] = new_label
        
        # 更新当前帧的框
        for box in self.current_boxes:
            if box.get('label') == old_label:
                box['label'] = new_label
        
        # 刷新UI
        self.label_combo['values'] = self.manager.labels
        self.label_var.set(new_label)
        
        # 刷新当前画面
        self.drawer.redraw(self.current_boxes)
        self.update_status()
        
        messagebox.showinfo("成功", f"标签已修改：'{old_label}' → '{new_label}'")

    def manual_save(self):
        """手动保存全部标注"""
        if not self.image_files or not self.json_path:
            messagebox.showwarning("警告", "没有打开文件夹或未加载标注")
            return
        
        self.save_current()
        total = self.manager.save(self.json_path, self.image_dir, 
                                self.image_files, self.manager.labels)
        
        messagebox.showinfo("保存成功", 
                          f"标注已保存\n当前共 {total} 个标注框\n文件：{self.json_path}")
    
    def delete_selected_box(self):
        """删除选中框"""
        if self.drawer and self.drawer.selected_box is not None:
            del self.current_boxes[self.drawer.selected_box]
            self.drawer.selected_box = None
            self.drawer.redraw(self.current_boxes)
            self.update_status()
    
    def select_inherit_labels(self):
        """选择要继承的标签"""
        if not self.manager.labels:
            messagebox.showwarning("提示", "暂无标签，请先添加标签")
            return
        
        # 创建对话框窗口
        dialog = tk.Toplevel(self.root)
        dialog.title("选择继承标签")
        dialog.geometry("300x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 使用grid布局：两行一列
        dialog.grid_rowconfigure(0, weight=1)
        dialog.grid_columnconfigure(0, weight=1)
        
        # 第一行：滚动区域
        canvas = tk.Canvas(dialog)
        scrollbar = tk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        tk.Label(scrollable_frame, text="选择需要继承的标签（多选）：", padx=10, pady=10).pack(anchor=tk.W)
        
        # 创建复选框列表（使用当前已保存的状态）
        checkboxes = []
        for label in self.manager.labels:
            var = tk.BooleanVar(value=label in self.inherit_labels)
            cb = tk.Checkbutton(scrollable_frame, text=label, variable=var)
            cb.pack(anchor=tk.W, padx=20, pady=2)
            checkboxes.append((label, var))
        
        # 全选/取消全选按钮
        def toggle_all():
            all_selected = all(var.get() for _, var in checkboxes)
            for _, var in checkboxes:
                var.set(not all_selected)
        
        # 第二行：按钮区域
        btn_frame = tk.Frame(dialog)
        btn_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=10)
        
        # 按钮区使用pack布局
        select_all_btn = tk.Button(btn_frame, text="全选/取消", command=toggle_all)
        select_all_btn.pack(side=tk.LEFT, padx=10)
        
        def confirm():
            # 保存到本地状态和manager（用于持久化）
            selected = {label for label, var in checkboxes if var.get()}
            self.inherit_labels = selected
            self.manager.inherit_labels = list(selected)
            
            # 更新状态显示
            if not self.inherit_labels:
                self.inherit_label_status.config(text="全部", fg="#0066cc")
            else:
                self.inherit_label_status.config(text=f"{len(self.inherit_labels)}个标签", fg="#00cc66")
            
            # 立即保存到文件，确保设置不会丢失
            if self.json_path and self.image_files:
                self.save_current()
                self.manager.save(self.json_path, self.image_dir, 
                                self.image_files, self.manager.labels)
            
            dialog.destroy()
        
        confirm_btn = tk.Button(btn_frame, text="确定", command=confirm)
        confirm_btn.pack(side=tk.RIGHT, padx=10)

    def delete_boxes_by_label(self):
        """按标签删除当前图片的标注框"""
        if not self.current_boxes:
            messagebox.showinfo("提示", "当前图片没有标注框")
            return
        
        # 获取当前图片中实际使用的标签
        current_labels = sorted(list(set(box.get('label', 'object') for box in self.current_boxes)))
        
        if not current_labels:
            return
        
        # 构建选项列表（包含全部）
        options = ["【全部标签】"] + current_labels
        
        choice = simpledialog.askstring(
            "选择删除类型", 
            "请选择要删除的标签：\n\n" + "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)]),
            initialvalue=options[0]
        )
        
        if not choice:
            return
        
        if choice == "【全部标签】":
            if messagebox.askyesno("确认删除", 
                                  f"确定删除当前图片全部 {len(self.current_boxes)} 个框吗？"):
                self.current_boxes.clear()
        else:
            # 删除指定标签
            count = sum(1 for box in self.current_boxes if box.get('label') == choice)
            if count == 0:
                return
            
            if messagebox.askyesno("确认删除", 
                                  f"确定删除标签 '{choice}' 的 {count} 个框吗？"):
                self.current_boxes = [box for box in self.current_boxes 
                                    if box.get('label') != choice]
        
        # 刷新界面
        if self.drawer:
            self.drawer.selected_box = None
            self.drawer.redraw(self.current_boxes)
        self.update_status()

    def on_closing(self):
        """程序退出时保存"""
        if self.image_files and self.json_path:
            if messagebox.askyesno("退出提示", "是否保存标注后退出？"):
                self.save_current()                    # 先更新内存
                total = self.manager.save(self.json_path, self.image_dir, 
                                        self.image_files, self.manager.labels)
                messagebox.showinfo("保存完成", f"已保存全部标注\n共 {total} 个标注框")
        
        self.root.destroy()

root = tk.Tk()
app = FrameAnnotator(root)
root.mainloop()
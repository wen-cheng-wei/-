import os
import shutil

# ====================== 【你只需要改这3个路径】 ======================
folder1 = r"D:\工作\行为检测\DEMO\打螺丝_1\1"    # 第一个图片文件夹
folder2 = r"D:\工作\行为检测\DEMO\打螺丝_1\2"    # 第二个图片文件夹
output_folder = r"D:\工作\行为检测\DEMO\打螺丝_1\总"  # 输出文件夹（自动创建）
# =====================================================================

# 支持的图片格式
IMAGE_FORMATS = ('.jpg', '.jpeg', '.png', '.bmp', '.JPG', '.JPEG', '.PNG', '.BMP')

# 创建输出文件夹
os.makedirs(output_folder, exist_ok=True)

# 收集所有图片
all_images = []

# 遍历文件夹1
for f in os.listdir(folder1):
    if f.endswith(IMAGE_FORMATS):
        all_images.append(os.path.join(folder1, f))

# 遍历文件夹2
for f in os.listdir(folder2):
    if f.endswith(IMAGE_FORMATS):
        all_images.append(os.path.join(folder2, f))

# 开始按数字重命名复制
count = 1
for img_path in all_images:
    # 新名字：1.jpg、2.jpg...
    new_name = f"{count}.jpg"
    new_path = os.path.join(output_folder, new_name)
    
    # 复制过去（不修改原文件）
    shutil.copy(img_path, new_path)
    print(f"已合并：{new_name}")
    
    count += 1

print(f"\n✅ 合并完成！共合并 {count-1} 张图片 → {output_folder}")
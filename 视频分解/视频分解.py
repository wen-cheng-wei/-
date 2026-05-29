import cv2
import os
import numpy as np


def split_video_to_frames(video_path: str, output_dir: str):
    """
    :param video_path: 输入视频的完整路径（支持中文）
    :param output_dir: 分解后图片的保存目录（支持中文）
    """
    os.makedirs(output_dir, exist_ok=True)

    # cap = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG)
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise IOError(f"无法打开视频，请检查路径是否正确：\n{video_path}")

    frame_index = 0
    print(f"开始分解视频...")

    try:
        while True:
            ret, frame = cap.read()

            if not ret:
                break

            filename = f"frame_{frame_index:05d}.jpg"
            save_full_path = os.path.join(output_dir, filename)
            ext = os.path.splitext(filename)[1]
            success, buffer = cv2.imencode(ext, frame)
            
            if success:
                buffer.tofile(save_full_path)
            else:
                print(f"警告：第 {frame_index} 帧编码失败，已跳过")

            frame_index += 1

    finally:
        cap.release()

    print(f"分解完成！共保存 {frame_index} 帧图片至：\n{output_dir}")


if __name__ == "__main__":
    input_video = r"C:\Users\wcw\Desktop\科仕达包装视频\20524144b6bcd23f9abdc9b5dbc4645f.mp4"
    output_folder = r"D:\工作\行为检测\DEMO\科仕达包装\3\图片"
    split_video_to_frames(input_video, output_folder)
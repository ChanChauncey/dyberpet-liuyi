"""检查边缘颜色。"""

import cv2
import numpy as np

# 读取原始帧
frame = cv2.imread('data/pipeline/frames/stand/frame_0000.png')

# 读取 alpha
alpha = cv2.imread('data/pipeline/rgba/stand_matte/debug/frame_0000_rgba_alpha.png', cv2.IMREAD_GRAYSCALE)

# 边缘区域：alpha 在 0.1-0.9 之间
edge_mask = (alpha > 10) & (alpha < 230)

# 提取边缘像素
edge_pixels = frame[edge_mask]

# 计算边缘像素的平均颜色
avg_color = edge_pixels.mean(axis=0)
print(f"边缘平均颜色 (BGR): {avg_color}")
print(f"边缘平均颜色 (RGB): {avg_color[::-1]}")

# 计算每个通道的分布
for i, name in enumerate(['B', 'G', 'R']):
    channel = edge_pixels[:, i]
    print(f"{name} 通道: min={channel.min()}, max={channel.max()}, mean={channel.mean():.1f}")

# 检查绿色过剩
green_excess = frame[:, :, 1].astype(float) - np.maximum(frame[:, :, 0], frame[:, :, 2]).astype(float)
edge_green_excess = green_excess[edge_mask]
print(f"边缘绿色过剩: min={edge_green_excess.min():.1f}, max={edge_green_excess.max():.1f}, mean={edge_green_excess.mean():.1f}")

# 检查蓝色过剩
blue_excess = frame[:, :, 0].astype(float) - np.maximum(frame[:, :, 1], frame[:, :, 2]).astype(float)
edge_blue_excess = blue_excess[edge_mask]
print(f"边缘蓝色过剩: min={edge_blue_excess.min():.1f}, max={edge_blue_excess.max():.1f}, mean={edge_blue_excess.mean():.1f}")

# 检查红色过剩
red_excess = frame[:, :, 2].astype(float) - np.maximum(frame[:, :, 0], frame[:, :, 1]).astype(float)
edge_red_excess = red_excess[edge_mask]
print(f"边缘红色过剩: min={edge_red_excess.min():.1f}, max={edge_red_excess.max():.1f}, mean={edge_red_excess.mean():.1f}")

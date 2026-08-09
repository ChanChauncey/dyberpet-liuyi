"""比较传统色度键和 BiRefNet 的抠图效果。"""

import cv2
import numpy as np

# 读取传统色度键输出
sam2 = cv2.imread('data/pipeline/rgba/stand_sam2/frame_0000_rgba.png', cv2.IMREAD_UNCHANGED)

# 读取 BiRefNet 输出
birefnet = cv2.imread('data/pipeline/rgba/stand/frame_0000_rgba.png', cv2.IMREAD_UNCHANGED)

print('传统色度键 Alpha 统计:')
print(f'  min: {sam2[:,:,3].min()}')
print(f'  max: {sam2[:,:,3].max()}')
print(f'  mean: {sam2[:,:,3].mean():.2f}')
print(f'  非零像素: {np.count_nonzero(sam2[:,:,3])}')
print(f'  总像素: {sam2[:,:,3].size}')
print(f'  覆盖率: {np.count_nonzero(sam2[:,:,3])/sam2[:,:,3].size*100:.1f}%')

print('\nBiRefNet Alpha 统计:')
print(f'  min: {birefnet[:,:,3].min()}')
print(f'  max: {birefnet[:,:,3].max()}')
print(f'  mean: {birefnet[:,:,3].mean():.2f}')
print(f'  非零像素: {np.count_nonzero(birefnet[:,:,3])}')
print(f'  总像素: {birefnet[:,:,3].size}')
print(f'  覆盖率: {np.count_nonzero(birefnet[:,:,3])/birefnet[:,:,3].size*100:.1f}%')

# 计算边缘区域的差异
# 边缘定义：alpha 在 1-254 之间的区域
sam2_edge = (sam2[:,:,3] > 0) & (sam2[:,:,3] < 255)
birefnet_edge = (birefnet[:,:,3] > 0) & (birefnet[:,:,3] < 255)

print('\n边缘区域统计:')
print(f'  传统色度键边缘像素: {np.count_nonzero(sam2_edge)}')
print(f'  BiRefNet 边缘像素: {np.count_nonzero(birefnet_edge)}')

# 计算 alpha 值的差异
diff = np.abs(sam2[:,:,3].astype(float) - birefnet[:,:,3].astype(float))
print(f'\nAlpha 差异统计:')
print(f'  平均差异: {diff.mean():.2f}')
print(f'  最大差异: {diff.max():.2f}')
print(f'  差异 > 50 的像素: {np.count_nonzero(diff > 50)}')

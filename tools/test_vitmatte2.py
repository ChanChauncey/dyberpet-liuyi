from transformers import VitMatteForImageMatting, VitMatteImageProcessor
from PIL import Image
import numpy as np

# 加载模型
processor = VitMatteImageProcessor.from_pretrained("hustvl/vitmatte-base-composition-1k")
model = VitMatteForImageMatting.from_pretrained("hustvl/vitmatte-base-composition-1k")

print("模型输出类型:", type(model))
print("模型方法:", [m for m in dir(model) if not m.startswith('_')])

# 检查输出格式
import torch
dummy_image = Image.fromarray(np.zeros((512, 512, 3), dtype=np.uint8))
dummy_trimap = Image.fromarray(np.full((512, 512), 128, dtype=np.uint8))

inputs = processor(images=dummy_image, trimaps=dummy_trimap, return_tensors="pt")
print("\n输入 keys:", inputs.keys())

with torch.no_grad():
    outputs = model(**inputs)

print("\n输出类型:", type(outputs))
print("输出属性:", [attr for attr in dir(outputs) if not attr.startswith('_')])
print("alphas 形状:", outputs.alphas.shape if hasattr(outputs, 'alphas') else 'N/A')

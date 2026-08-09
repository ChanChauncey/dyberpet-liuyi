from transformers import VitMatteImageProcessor
processor = VitMatteImageProcessor.from_pretrained("hustvl/vitmatte-base-composition-1k")
print(dir(processor))

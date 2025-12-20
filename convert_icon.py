from PIL import Image
import os

png_path = r"C:\Users\ga200\.gemini\antigravity\brain\4a08485f-6d20-4205-b85a-4c661b855dd0\app_icon_design_1766238291358.png"
ico_path = r"C:\Users\ga200\.gemini\antigravity\scratch\video_thumbnail_generator\app_icon.ico"

img = Image.open(png_path)
# Resize to common icon sizes
icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
img.save(ico_path, sizes=icon_sizes)
print(f"Icon saved to {ico_path}")

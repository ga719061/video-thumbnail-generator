from PIL import Image
import os

png_input = r"C:\Users\ga200\.gemini\antigravity\brain\4a08485f-6d20-4205-b85a-4c661b855dd0\app_icon_flat_bg_1766238710264.png"
png_output = r"C:\Users\ga200\.gemini\antigravity\scratch\video_thumbnail_generator\app_icon_transparent.png"
ico_output = r"C:\Users\ga200\.gemini\antigravity\scratch\video_thumbnail_generator\app_icon.ico"

img = Image.open(png_input).convert("RGBA")
datas = img.getdata()

new_data = []
for item in datas:
    # Change all white (or near white) pixels to transparent
    # Threshold for white: R, G, B > 240
    if item[0] > 240 and item[1] > 240 and item[2] > 240:
        new_data.append((255, 255, 255, 0))
    else:
        new_data.append(item)

img.putdata(new_data)
img.save(png_output, "PNG")

# Save as ICO with multiple sizes
icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
img.save(ico_output, format='ICO', sizes=icon_sizes)

print(f"Transparent PNG saved to {png_output}")
print(f"Icon saved to {ico_output}")

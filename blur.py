# 用 Python PIL 一键虚化
from PIL import Image, ImageFilter

img = Image.open("img/icon/backgroundpic5.png")
blurred = img.filter(ImageFilter.GaussianBlur(radius=8))
blurred.save("img/icon/backgroundpic5_blur.png")
# -*- coding: utf-8 -*- 
# @Time : 2021/5/16 21:15 
# @Author : Shawn
# @File : resize.py
# @Desc :

from PIL import Image

im = Image.open(r"..\dataset\JPEGImages\A1225.jpg")
w = im.size[0]
h = im.size[1]

w += 2 * 60
h += 2 * 60
img_new = Image.new('RGB', (w, h), (169, 169, 169))
img_new.paste(im, (60, 60))

img_new.save(r"E:\Study\thesis\A1225.jpg")
img_new.show()


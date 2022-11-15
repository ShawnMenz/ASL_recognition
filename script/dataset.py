# -*- coding: utf-8 -*-
# @Time : 2021/2/13 22:58
# @Author : Shawn
# @File : dataset.py
# @Desc : 制作数据集

import os
import random
import shutil

# 相关路径
testPath = r"E:\Study\thesis\archive\test"
trainPath = r"E:\Study\thesis\archive\train"
path = r"..\dataset\JPEGImages"

# 每个字母的样例图片取出数量
COUNT = 114

# 将train目录下的所有文件夹取出，组成list
trainList = os.listdir(trainPath)
for i in range(0, COUNT):
    for fileDir in trainList:
        # 遍历每个字母的目录
        oldDir = os.path.join(trainPath, fileDir)
        # print(oldDir)
        # 每个字母目录下的所有图片，组成list，值得注意的是，这个list本来就是乱序的
        imageList = os.listdir(oldDir)
        # print(imageList)
        seed = random.randint(0, 2999)
        # print(imageList[seed])
        oldDir = os.path.join(oldDir, imageList[seed])
        # print(oldDir)
        # image = cv2.imread(oldDir)
        # result = cv2.resize(image, (416, 416))
        newDir = os.path.join(path, imageList[seed])
        # print(newDir)
        # cv2.imwrite(newDir, result)
        shutil.copy(oldDir, newDir)

print("Complete!")

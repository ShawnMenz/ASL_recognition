# -*- coding: utf-8 -*- 
# @Time : 2021/4/12 15:25 
# @Author : Shawn
# @File : verify.py
# @Desc : 验证数据集

import os

imageList = os.listdir(r"E:\Study\thesis\sign_language\dataset\JPEGImages")
xmlList = os.listdir(r"E:\Study\thesis\sign_language\dataset\Annotations")
newImageList = []
newXmlList = []
for item in imageList:
    newImageList.append(item[0:-4])
for item in xmlList:
    newXmlList.append(item[0:-4])

resultList = list(set(newImageList) - set(newXmlList))
print(resultList)

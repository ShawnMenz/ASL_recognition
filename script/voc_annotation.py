# -*- coding: utf-8 -*- 
# @Time : 2021/3/12 20:56 
# @Author : Shawn
# @File : voc_annotation.py
# @Desc : 生成voc索引

import os
import random

trainvalPercent = 0.05
trainPercent = 0.95
VOC_path = r'..\dataset'
xmlFilePath = os.path.join(VOC_path, r'Annotations')
txtFilePath = os.path.join(VOC_path, r'ImageSets\Main')
totalXml = os.listdir(xmlFilePath)

num = len(totalXml)
trainvalList = range(num)
tv = int(num * trainvalPercent)
tr = int(tv * trainPercent)
trainval = random.sample(trainvalList, tv)
train = random.sample(trainval, tr)

ftrainval = open(VOC_path + r'\ImageSets\Main\trainval.txt', 'w')
ftest = open(VOC_path + r'\ImageSets\Main\test.txt', 'w')
ftrain = open(VOC_path + r'\ImageSets\Main\train.txt', 'w')
fval = open(VOC_path + r'\ImageSets\Main\val.txt', 'w')

for i in trainvalList:
    name = totalXml[i][:-4] + '\n'
    if i in trainval:
        ftrainval.write(name)
        if i in train:
            ftest.write(name)
        else:
            fval.write(name)
    else:
        ftrain.write(name)

print("complete annotating voc")
ftrainval.close()
ftrain.close()
fval.close()
ftest.close()

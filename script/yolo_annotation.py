# -*- coding: utf-8 -*- 
# @Time : 2021/3/16 15:51 
# @Author : Shawn
# @File : yolo_annotation.py
# @Desc : 生成YOLO索引

import xml.etree.ElementTree as ET


# 用到的函数
def convert_annotation(image_id, list_file):
    """
    获取Annotation中每个xml文件中的标记框真实信息
    :param image_id: xml文件名
    :param list_file: 输出真实框标注信息的文件
    :return:
    """
    in_file = open(r"..\dataset\Annotations\%s.xml" % image_id)
    tree = ET.parse(in_file)
    root = tree.getroot()

    for obj in root.iter('object'):
        difficult = obj.find('difficult').text
        name = obj.find('name').text
        if name not in classes or int(difficult) == 1:
            continue
        nameid = classes.index(name)
        xmlbox = obj.find('bndbox')
        box = (int(xmlbox.find('xmin').text), int(xmlbox.find('ymin').text),
               int(xmlbox.find('xmax').text), int(xmlbox.find('ymax').text))
        list_file.write(" " + ",".join([str(i) for i in box]) + ',' + str(nameid))


imageSets = ['train', 'val', 'test']
classes = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L",
           "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V",
           "W", "X", "Y", "Z", "del", "space"]

# 保存所有对象信息
classes_file = open(r'..\model_data\voc_class.txt', 'w')
for index in classes:
    classes_file.write(str(index))
    classes_file.write("\n")
classes_file.close()


for imgset in imageSets:
    image_ids = open(r"..\dataset\ImageSets\Main\%s.txt" % imgset).read().strip().split()
    # model_data目录下yolo索引txt中加上真实框标注信息
    listFile = open(r'..\model_data\%s.txt' % imgset, 'w')
    for image_id in image_ids:
        listFile.write(r'E:\Study\thesis\sign_language\dataset\JPEGImages\%s.jpg' % image_id)
        convert_annotation(image_id, listFile)
        listFile.write("\n")
    listFile.close()

print("complete annotating yolo")

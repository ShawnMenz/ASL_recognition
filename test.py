# -*- coding: utf-8 -*- 
# @Time : 2021/4/20 18:44 
# @Author : Shawn
# @File : test.py
# @Desc : 测试界面

from ui.home_ui import Ui_MainWindow as home_ui
from ui.picture_ui import Ui_MainWindow as picture_ui
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QMessageBox
import numpy as np
from PIL import Image
from yolo import YOLO
import tensorflow as tf
import cv2
import time
import sys
import os


class HomeUI(QtWidgets.QMainWindow, home_ui):
    """
    主界面
    """
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.vidButton.clicked.connect(self.message)

    def message(self):
        """
        弹窗设计，用于提示用户
        :return: None
        """
        hint = QMessageBox()
        hint.setWindowTitle("提示")
        hint.setText("程序正在运行中，请稍等...")
        hint.setStandardButtons(QMessageBox.Ok)
        hint.button(QMessageBox.Ok).animateClick(1000)
        hint.exec_()

    def video_click(self):
        """
        视频识别按钮按下之后运行识别程序
        :return: None
        """
        capture = cv2.VideoCapture(0)
        fps = 0.0
        while (True):
            t1 = time.time()
            # 读取某一帧
            ref, frame = capture.read()
            # 格式转变，BGRtoRGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # 转变成Image
            frame = Image.fromarray(np.uint8(frame))

            # 进行检测
            frame = np.array(yolo.detect_image(frame))

            # RGBtoBGR满足opencv显示格式
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            fps = (fps + (1. / (time.time() - t1))) / 2
            print("fps= %.2f" % fps)
            frame = cv2.putText(frame, "fps= %.2f" % fps, (0, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            cv2.imshow("video", frame)
            c = cv2.waitKey(30) & 0xff
            if c == 27:
                capture.release()
                cv2.destroyAllWindows()
                break


class PictureUI(QtWidgets.QMainWindow, picture_ui):
    """
    图片识别界面，用于选择需要识别的测试用例图片
    """
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.recButton.clicked.connect(self.picture_click)
        self.listWidget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        fileList = os.listdir(r"test")
        fileList.sort()
        for i in fileList:
            self.listWidget.addItem("test/" + i)
        self.listWidget.currentItemChanged.connect(self.text_change)

    def text_change(self):
        """
        更改label标签，使其与选择的名称一致
        :return: None
        """
        text = self.listWidget.currentItem().text()
        self.showCase.setText(text)

    def picture_click(self):
        """
        图片识别按钮按下之后运行识别程序
        :return: None
        """
        try:
            image = Image.open(self.showCase.text())
        except:
            QMessageBox.warning(self, "警告", "图片路径有误！")
        else:
            hint = QMessageBox()
            hint.setWindowTitle("提示")
            hint.setText("程序正在运行中，请稍等...")
            hint.setStandardButtons(QMessageBox.Ok)
            hint.button(QMessageBox.Ok).animateClick(1000)
            hint.exec_()
            r_image = yolo.detect_image(image)
            r_image.show()


if __name__ == '__main__':
    # GPU配置：使用GPU
    physical_devices = tf.config.experimental.list_physical_devices('GPU')
    tf.config.experimental.set_memory_growth(physical_devices[0], True)
    # 装载YOLO算法
    yolo = YOLO()

    # 初始化Qt界面和界面组件，显示主界面
    app = QtWidgets.QApplication(sys.argv)
    home = HomeUI()
    picture = PictureUI()
    home.show()

    home.picButton.clicked.connect(
        lambda: {home.close(), picture.show()}
    )

    home.vidButton.clicked.connect(HomeUI.video_click)

    picture.returnButton.clicked.connect(
        lambda: {picture.close(), home.show()}
    )

    sys.exit(app.exec_())

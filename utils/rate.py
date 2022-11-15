# -*- coding: utf-8 -*- 
# @Time : 2021/5/16 23:02 
# @Author : Shawn
# @File : rate.py
# @Desc :

import os
import matplotlib.pyplot as plt

loss_list = os.listdir(r"..\logs")
loss_list = loss_list[:-4]
num_list = []
ls_list = []
vls_list = []
for loss in loss_list:
    loss = loss[3:-3]
    num, ls, vls = loss.split("-")
    ls = ls[4:]
    vls = vls[8:]
    num_list.append(float(num))
    ls_list.append(float(ls))
    vls_list.append(float(vls))

acc_list=[0.142,0.651,0.852,0.923,0.930,0.936,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.945,0.946,0.946]
plt.figure(figsize=(12, 8))
plt.plot(num_list, acc_list, label="accuracy")
plt.axhline(y=0.95, color="red", linestyle="--", label="0.95")
plt.xlabel("epoch")
plt.ylabel("accuracy")
plt.legend(loc='lower right')
plt.show()

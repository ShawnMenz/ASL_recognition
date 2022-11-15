# -*- coding: utf-8 -*- 
# @Time : 2021/4/7 17:06 
# @Author : Shawn
# @File : CSPdarknet53.py
# @Desc : CSPdarknet53相关函数

from functools import wraps
from tensorflow.keras import backend as K
from tensorflow.keras.layers import (Add, BatchNormalization, Concatenate, Conv2D, Layer, ZeroPadding2D)
from utils.utils import compose


class Mish(Layer):
    def __init__(self, **kwargs):
        super(Mish, self).__init__(**kwargs)
        self.supports_masking = True

    def call(self, inputs):
        return inputs * K.tanh(K.softplus(inputs))

    def get_config(self):
        config = super(Mish, self).get_config()
        return config

    def compute_output_shape(self, input_shape):
        return input_shape


@wraps(Conv2D)
def DarknetConv2D(*args, **kwargs):
    """
    单次卷积
    """
    darknet_conv_kwargs = {}
    # 如果步长为2则自己设定padding方式
    darknet_conv_kwargs['padding'] = 'valid' if kwargs.get('strides') == (2, 2) else 'same'
    darknet_conv_kwargs.update(kwargs)
    return Conv2D(*args, **darknet_conv_kwargs)


def DarknetConv2D_BN_Mish(*args, **kwargs):
    """
    卷积块 -> 卷积 + 标准化 + 激活函数
    DarknetConv2D + BatchNormalization + Mish
    """
    no_bias_kwargs = {'use_bias': False}
    no_bias_kwargs.update(kwargs)
    return compose(
        DarknetConv2D(*args, **no_bias_kwargs),
        BatchNormalization(),
        Mish())


def resblock_body(x, num_filters, num_blocks, all_narrow=True):
    """
    CSPdarknet的结构块
    """
    # 利用ZeroPadding2D和一个步长为2x2的卷积块进行高和宽的压缩
    preconv1 = ZeroPadding2D(((1, 0), (1, 0)))(x)
    preconv1 = DarknetConv2D_BN_Mish(num_filters, (3, 3), strides=(2, 2))(preconv1)

    # 然后建立一个大的残差边shortconv、这个大残差边绕过了很多的残差结构
    shortconv = DarknetConv2D_BN_Mish(num_filters // 2 if all_narrow else num_filters, (1, 1))(preconv1)

    # 主干部分会对num_blocks进行循环，循环内部是残差结构
    mainconv = DarknetConv2D_BN_Mish(num_filters // 2 if all_narrow else num_filters, (1, 1))(preconv1)
    for i in range(num_blocks):
        y = compose(
            DarknetConv2D_BN_Mish(num_filters // 2, (1, 1)),
            DarknetConv2D_BN_Mish(num_filters // 2 if all_narrow else num_filters, (3, 3)))(mainconv)
        mainconv = Add()([mainconv, y])
    postconv = DarknetConv2D_BN_Mish(num_filters // 2 if all_narrow else num_filters, (1, 1))(mainconv)

    # 将大残差边再堆叠回来
    route = Concatenate()([postconv, shortconv])

    # 最后对通道数进行整合
    return DarknetConv2D_BN_Mish(num_filters, (1, 1))(route)


def darknet_body(x):
    """
    CSPdarknet53 的主体部分
    input: 一张320x320x3的图片
    output: 三个有效特征层
    """
    x = DarknetConv2D_BN_Mish(32, (3, 3))(x)
    x = resblock_body(x, 64, 1, False)
    x = resblock_body(x, 128, 2)
    x = resblock_body(x, 256, 8)
    feat1 = x
    x = resblock_body(x, 512, 8)
    feat2 = x
    x = resblock_body(x, 1024, 4)
    feat3 = x
    return feat1, feat2, feat3

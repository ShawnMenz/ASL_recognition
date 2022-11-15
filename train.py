# -*- coding: utf-8 -*- 
# @Time : 2021/4/7 20:52 
# @Author : Shawn
# @File : train.py
# @Desc : 训练模型

import numpy as np
import tensorflow as tf
from tensorflow.keras.callbacks import (EarlyStopping, ReduceLROnPlateau, TensorBoard)
from tensorflow.keras.layers import Input, Lambda
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import Adam
from nets.loss import yolo_loss
from nets.yolo4 import yolo_body
from utils.utils import (ModelCheckpoint, WarmUpCosineDecayScheduler, get_random_data, get_random_data_with_Mosaic)


def get_classes(classes_path):
    """
    获得类
    :param classes_path: 类名文件路径
    :return: 类名list
    """
    with open(classes_path) as f:
        class_names = f.readlines()
    class_names = [c.strip() for c in class_names]
    return class_names


def get_anchors(anchors_path):
    """
    获得先验框
    :param anchors_path: 先验框文件路径
    :return: 先验框numpy数组
    """
    with open(anchors_path) as f:
        anchors = f.readline()
    anchors = [float(x) for x in anchors.split(',')]
    return np.array(anchors).reshape(-1, 2)


def data_generator(annotation_lines, batch_size, input_shape, anchors, num_classes, mosaic=False, random=True):
    """
    训练数据生成器
    :param annotation_lines: 图片路径和标签
    :param batch_size: 每次训练样本的数量
    :param input_shape: 输入的图片矩阵
    :param anchors: 先验框list
    :param num_classes: 类名list
    :param mosaic: 是否使用mosaic
    :param random: 是否使用随机
    """
    n = len(annotation_lines)
    i = 0
    flag = True
    while True:
        image_data = []
        box_data = []
        for b in range(batch_size):
            if i == 0:
                np.random.shuffle(annotation_lines)
            if mosaic:
                if flag and (i + 4) < n:
                    image, box = get_random_data_with_Mosaic(annotation_lines[i:i + 4], input_shape)
                    i = (i + 4) % n
                else:
                    image, box = get_random_data(annotation_lines[i], input_shape, random=random)
                    i = (i + 1) % n
                flag = bool(1 - flag)
            else:
                image, box = get_random_data(annotation_lines[i], input_shape, random=random)
                i = (i + 1) % n
            image_data.append(image)
            box_data.append(box)
        image_data = np.array(image_data)
        box_data = np.array(box_data)
        y_true = preprocess_true_boxes(box_data, input_shape, anchors, num_classes)
        yield [image_data, *y_true], np.zeros(batch_size)


def preprocess_true_boxes(true_boxes, input_shape, anchors, num_classes):
    """
    读入xml文件，并输出y_true
    :param true_boxes: 真实框矩阵
    :param input_shape: 输入的图片矩阵
    :param anchors: 先验框list
    :param num_classes: 类名list
    :return: y_true
    """
    assert (true_boxes[..., 4] < num_classes).all(), 'class id must be less than num_classes'
    # 一共有三个特征层数
    num_layers = len(anchors) // 3
    # -----------------------------------------------------------#
    #   13x13的特征层对应的anchor是[142, 110], [192, 243], [459, 401]
    #   26x26的特征层对应的anchor是[36, 75], [76, 55], [72, 146]
    #   52x52的特征层对应的anchor是[12, 16], [19, 36], [40, 28]
    # -----------------------------------------------------------#
    anchor_mask = [[6, 7, 8], [3, 4, 5], [0, 1, 2]]

    # 获得框的坐标和图片的大小
    true_boxes = np.array(true_boxes, dtype='float32')
    input_shape = np.array(input_shape, dtype='int32')

    #   通过计算获得真实框的中心和宽高，中心点(m,n,2) 宽高(m,n,2)
    boxes_xy = (true_boxes[..., 0:2] + true_boxes[..., 2:4]) // 2
    boxes_wh = true_boxes[..., 2:4] - true_boxes[..., 0:2]

    # 将真实框归一化到小数形式
    true_boxes[..., 0:2] = boxes_xy / input_shape[::-1]
    true_boxes[..., 2:4] = boxes_wh / input_shape[::-1]

    # 图片数量
    m = true_boxes.shape[0]
    # 网格的shape
    grid_shapes = [input_shape // {0: 32, 1: 16, 2: 8}[l] for l in range(num_layers)]

    # y_true的格式为(m,13,13,3,85)(m,26,26,3,85)(m,52,52,3,85)
    y_true = [np.zeros((m, grid_shapes[l][0], grid_shapes[l][1], len(anchor_mask[l]), 5 + num_classes),
                       dtype='float32') for l in range(num_layers)]

    anchors = np.expand_dims(anchors, 0)
    anchor_maxes = anchors / 2.
    anchor_mins = -anchor_maxes

    # 长宽要大于0才有效
    valid_mask = boxes_wh[..., 0] > 0

    for b in range(m):
        # 对每一张图进行处理
        wh = boxes_wh[b, valid_mask[b]]
        if len(wh) == 0: continue
        wh = np.expand_dims(wh, -2)
        box_maxes = wh / 2.
        box_mins = -box_maxes

        # 计算所有真实框和先验框的交并比
        # intersect_area  [n,9]
        # box_area        [n,1]
        # anchor_area     [1,9]
        # iou             [n,9]
        intersect_mins = np.maximum(box_mins, anchor_mins)
        intersect_maxes = np.minimum(box_maxes, anchor_maxes)
        intersect_wh = np.maximum(intersect_maxes - intersect_mins, 0.)
        intersect_area = intersect_wh[..., 0] * intersect_wh[..., 1]

        box_area = wh[..., 0] * wh[..., 1]
        anchor_area = anchors[..., 0] * anchors[..., 1]

        iou = intersect_area / (box_area + anchor_area - intersect_area)
        best_anchor = np.argmax(iou, axis=-1)

        for t, n in enumerate(best_anchor):
            # 找到每个真实框所属的特征层
            for l in range(num_layers):
                if n in anchor_mask[l]:
                    # floor用于向下取整，找到真实框所属的特征层对应的x、y轴坐标
                    i = np.floor(true_boxes[b, t, 0] * grid_shapes[l][1]).astype('int32')
                    j = np.floor(true_boxes[b, t, 1] * grid_shapes[l][0]).astype('int32')
                    # 当前这个特征点的第k个先验框
                    k = anchor_mask[l].index(n)
                    # 当前这个真实框的种类
                    c = true_boxes[b, t, 4].astype('int32')
                    # y_true的shape为(m,13,13,3,85)(m,26,26,3,85)(m,52,52,3,85)
                    y_true[l][b, j, i, k, 0:4] = true_boxes[b, t, 0:4]
                    y_true[l][b, j, i, k, 4] = 1
                    y_true[l][b, j, i, k, 5 + c] = 1

    return y_true


gpus = tf.config.experimental.list_physical_devices(device_type='GPU')
for gpu in gpus:
    tf.config.experimental.set_memory_growth(gpu, True)

if __name__ == "__main__":
    # 获得图片路径和标签
    annotation_path = 'model_data/train.txt'
    # 训练后的模型保存的位置
    log_dir = 'logs/'
    # classes和anchor的路径
    classes_path = 'model_data/voc_class.txt'
    anchors_path = 'model_data/yolo_anchors.txt'
    # Yolo算法的预训练模型文件
    weights_path = 'model_data/yolo4_weight.h5'
    # 训练用图片大小
    input_shape = (320, 320)
    # 是否对损失进行归一化，用于改变loss的大小
    normalize = False

    # 获取classes和anchor
    class_names = get_classes(classes_path)
    anchors = get_anchors(anchors_path)
    # 类和先验框的数量
    num_classes = len(class_names)
    num_anchors = len(anchors)

    # 马赛克数据增强
    mosaic = False
    # 余弦退火学习率
    Cosine_scheduler = True
    # 标签平滑
    label_smoothing = 0.005

    # 创建yolo模型
    image_input = Input(shape=(None, None, 3))
    h, w = input_shape
    print('Create YOLOv4 model with {} anchors and {} classes.'.format(num_anchors, num_classes))
    model_body = yolo_body(image_input, num_anchors // 3, num_classes)

    # 载入预训练权重
    print('Load weights {}.'.format(weights_path))
    model_body.load_weights(weights_path, by_name=True, skip_mismatch=True)

    # 在这个地方设置损失，将网络的输出结果传入loss函数，把整个模型的输出作为loss
    y_true = [
        Input(shape=(h // {0: 32, 1: 16, 2: 8}[l], w // {0: 32, 1: 16, 2: 8}[l], num_anchors // 3, num_classes + 5)) for
        l in range(3)]
    loss_input = [*model_body.output, *y_true]
    model_loss = Lambda(yolo_loss, output_shape=(1,), name='yolo_loss',
                        arguments={'anchors': anchors, 'num_classes': num_classes, 'ignore_thresh': 0.5,
                                   'label_smoothing': label_smoothing})(loss_input)

    model = Model([model_body.input, *y_true], model_loss)

    # logging表示tensorboard的保存地址
    logging = TensorBoard(log_dir=log_dir)
    # checkpoint用于设置权值保存的细节，period参数用于修改多少epoch保存一次
    checkpoint = ModelCheckpoint(log_dir + "/ep{epoch:03d}-loss{loss:.3f}-val_loss{val_loss:.3f}.h5",
                                 save_weights_only=True, save_best_only=False, period=1)
    # early_stopping用于设定早停，val_loss多次不下降自动结束训练，表示模型基本收敛
    early_stopping = EarlyStopping(min_delta=0, patience=10, verbose=1)

    # 当前划分方式下，验证集和训练集的比例为1:9
    val_split = 0.1
    with open(annotation_path) as f:
        lines = f.readlines()
    np.random.seed(10101)
    np.random.shuffle(lines)
    np.random.seed(None)
    num_val = int(len(lines) * val_split)
    num_train = len(lines) - num_val

    # 主干特征提取网络特征通用，冻结训练可以加快训练速度，也可以在训练初期防止权值被破坏。
    freeze_layers = 249
    for i in range(freeze_layers): model_body.layers[i].trainable = False
    print('Freeze the first {} layers of total {} layers.'.format(freeze_layers, len(model_body.layers)))

    # 调整非主干模型first
    if True:
        # 起始世代
        Init_epoch = 0
        # 冻结训练的世代
        Freeze_epoch = 50
        batch_size = 2
        learning_rate_base = 1e-3

        if Cosine_scheduler:
            # 预热期
            warmup_epoch = int((Freeze_epoch - Init_epoch) * 0.2)
            # 总共的步长
            total_steps = int((Freeze_epoch - Init_epoch) * num_train / batch_size)
            # 预热步长
            warmup_steps = int(warmup_epoch * num_train / batch_size)
            # 学习率
            reduce_lr = WarmUpCosineDecayScheduler(learning_rate_base=learning_rate_base,
                                                   total_steps=total_steps,
                                                   warmup_learning_rate=1e-4,
                                                   warmup_steps=warmup_steps,
                                                   hold_base_rate_steps=num_train,
                                                   min_learn_rate=1e-6
                                                   )
            model.compile(optimizer=Adam(), loss={'yolo_loss': lambda y_true, y_pred: y_pred})
        else:
            reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=3, verbose=1)
            model.compile(optimizer=Adam(learning_rate_base), loss={'yolo_loss': lambda y_true, y_pred: y_pred})

        print('Train on {} samples, val on {} samples, with batch size {}.'.format(num_train, num_val, batch_size))
        model.fit(data_generator(lines[:num_train], batch_size, input_shape, anchors, num_classes, mosaic=mosaic,
                                 random=True),
                  steps_per_epoch=max(1, num_train // batch_size),
                  validation_data=data_generator(lines[num_train:], batch_size, input_shape, anchors, num_classes,
                                                 mosaic=False, random=False),
                  validation_steps=max(1, num_val // batch_size),
                  epochs=Freeze_epoch,
                  initial_epoch=Init_epoch,
                  callbacks=[logging, checkpoint, reduce_lr, early_stopping])
        model.save_weights(log_dir + 'trained_weights_stage_freeze.h5')

    for i in range(freeze_layers): model_body.layers[i].trainable = True

    # 解冻后训练
    if True:
        Freeze_epoch = 50
        # 总训练世代
        Epoch = 100
        batch_size = 2
        learning_rate_base = 1e-4

        if Cosine_scheduler:
            # 预热期
            warmup_epoch = int((Epoch - Freeze_epoch) * 0.2)
            # 总共的步长
            total_steps = int((Epoch - Freeze_epoch) * num_train / batch_size)
            # 预热步长
            warmup_steps = int(warmup_epoch * num_train / batch_size)
            # 学习率
            reduce_lr = WarmUpCosineDecayScheduler(learning_rate_base=learning_rate_base,
                                                   total_steps=total_steps,
                                                   warmup_learning_rate=1e-5,
                                                   warmup_steps=warmup_steps,
                                                   hold_base_rate_steps=num_train // 2,
                                                   min_learn_rate=1e-6
                                                   )
            model.compile(optimizer=Adam(), loss={'yolo_loss': lambda y_true, y_pred: y_pred})
        else:
            reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=3, verbose=1)
            model.compile(optimizer=Adam(learning_rate_base), loss={'yolo_loss': lambda y_true, y_pred: y_pred})

        print('Train on {} samples, val on {} samples, with batch size {}.'.format(num_train, num_val, batch_size))
        model.fit(data_generator(lines[:num_train], batch_size, input_shape, anchors, num_classes, mosaic=mosaic,
                                 random=True),
                  steps_per_epoch=max(1, num_train // batch_size),
                  validation_data=data_generator(lines[num_train:], batch_size, input_shape, anchors, num_classes,
                                                 mosaic=False, random=False),
                  validation_steps=max(1, num_val // batch_size),
                  epochs=Epoch,
                  initial_epoch=Freeze_epoch,
                  callbacks=[logging, checkpoint, reduce_lr, early_stopping])
        model.save_weights(log_dir + 'sign_language_result.h5')

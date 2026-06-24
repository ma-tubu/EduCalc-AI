# 15 类字符识别训练阶段

本阶段目标：把已经跑通的 `0-9` 单数字识别，升级为可识别：

```text
0 1 2 3 4 5 6 7 8 9 + - * / =
```

其中当前演示可以先使用 `0-9 + - * /`，但建议保留 `=` 类，后续完整算式判题需要它。

## 目录结构

```text
06_Training_15Class/
  data/raw/
    digit_0 ... digit_9/      可选：自己采集的数字样本
    op_plus/                  +
    op_minus/                 -
    op_mul/                   *
    op_div/                   /
    op_equal/                 =
  exports/                    保存 h5/tflite/labels
  reports/                    保存混淆矩阵、训练报告
  collect_symbol_samples.py   鼠标采集符号样本
  train_15class_keras.py      训练并导出 Cube.AI 可用模型
  labels_15class.txt          STM32 端类别顺序必须与此一致
```

## 第一步：采集运算符样本

在本目录运行：

```powershell
python .\collect_symbol_samples.py
```

建议每个符号至少采集：

```text
+ - * / =   每类 80-150 张
```

采集时可以故意写得有粗细差异、位置偏移、大小差异。这样模型在真实手写输入时更稳。

## 第二步：检查当前数据集

如果你的数据已经放在本目录的 `data/raw`，并且目录如下：

```text
0 1 2 3 4 5 6 7 8 9 add dec div eq mul sub x y z
```

那么可以直接训练。项目会使用：

```text
0-9
add -> +
sub -> -
mul -> *
div -> /
eq  -> =
```

默认忽略：

```text
dec x y z
```

训练前建议先检查预处理效果：

```powershell
python .\inspect_raw_dataset.py --data-dir .\data\raw --preview .\reports\preprocess_preview.png
```

打开 `reports/preprocess_preview.png`，确认字符是黑底白字、居中、没有被裁坏。

如果你希望把目录 `x` 也当作乘号样本，可以加：

```powershell
python .\inspect_raw_dataset.py --include-x-as-mul
```

## 第三步：转换其他开源数据集

如果使用 `Math_Symbols_Classify` 提到的 Kaggle 数据集，先把数据集解压到某个目录。目录里通常会有：

```text
0 1 2 3 4 5 6 7 8 9 add sub mul div eq
```

或：

```text
train/0 train/add ...
val/0   val/add ...
```

执行转换：

```powershell
python .\prepare_math_symbols_dataset.py --source "D:\你的数据集路径" --output .\data\raw --invert auto
```

转换结果会统一为：

```text
28x28
灰度
黑底白字
类别目录为 digit_0 ... op_equal
```

## 第四步：训练 15 类模型

默认直接使用 `data/raw` 中的本地数据：

```powershell
python .\train_15class_keras.py --epochs 12 --batch-size 128
```

如果想额外加入 MNIST 数字样本，可以使用：

```powershell
python .\train_15class_keras.py --include-mnist --epochs 12 --batch-size 128
```

如果希望把目录 `x` 也当作乘号样本，可以使用：

```powershell
python .\train_15class_keras.py --include-x-as-mul --epochs 12 --batch-size 128
```

训练完成后会生成：

```text
exports\hand_expr_15class.h5
exports\hand_expr_15class.tflite
exports\hand_expr_15class_int8.tflite
exports\labels_15class.txt
reports\training_report.json
reports\confusion_matrix.csv
```

## 第五步：导入 STM32Cube.AI

推荐先导入：

```text
exports\hand_expr_15class.tflite
```

确认 Analyze 通过后，再尝试：

```text
exports\hand_expr_15class_int8.tflite
```

## 关键约定

训练输入和板端输入必须一致：

```text
28x28
灰度
黑底白字
像素范围 0-255
STM32 端除以 255.0 得到 0-1
```

如果 PC 发送工具生成的是白底黑字，需要使用反色选项，使最终送到板端的数据接近 MNIST 风格。

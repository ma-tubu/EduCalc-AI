# EduCalc-AI：基于 STM32F7 与 STM32Cube.AI 的手写算式识别与智能判题系统

> 面向嵌入式 AI 课程设计的端侧手写算式识别系统：手写字符图像输入 → STM32F7 板端字符分割 → STM32Cube.AI 推理 → 置信度判断 → 表达式解析 → 自动判题与交互重写

[![Platform](https://img.shields.io/badge/Platform-STM32F7-blue)](https://www.st.com/en/microcontrollers-microprocessors/stm32f7-series.html)
[![AI](https://img.shields.io/badge/AI-STM32Cube.AI-brightgreen)](https://www.st.com/en/embedded-software/x-cube-ai.html)
[![Model](https://img.shields.io/badge/Model-15--Class%20CNN-orange)](#神经网络模型)
[![Interface](https://img.shields.io/badge/Interface-UART-lightgrey)](#串口通信协议)

---

## 项目简介

EduCalc-AI 是一个运行在 **STM32F7** 开发板上的轻量嵌入式 AI 应用。项目以普通 MNIST 数字识别为基础，将单字符识别扩展为完整的手写算式识别与智能判题系统。

系统当前支持 15 类字符：

```text
0 1 2 3 4 5 6 7 8 9 + - * / =
```

用户可以输入类似下面的手写算式图像：

```text
3+2=5
9*8=64
11*5=55
11*5=54
```

系统在 STM32F7 板端完成：

- 图像数据接收
- 像素归一化
- 字符自动分割
- 单字符 CNN 推理
- 每个字符置信度输出
- 表达式字符串重组
- 算式解析与板端计算
- 正确 / 错误自动判题
- 低置信度字符交互重写
- 答案错误后只重写结果部分

由于本项目使用的 STM32F7 开发板没有触摸屏和 SD 卡，当前演示方式采用 **电脑端生成测试 payload，通过串口发送到 STM32F7**。模型推理、字符分割、表达式解析和判题逻辑均在 STM32 板端完成。

---

## 系统架构

```text
┌──────────────────────────────┐
│             PC 端             │
│                              │
│  数据集样本 / 手写图像        │
│           ↓                  │
│  生成 ASCII 像素 payload      │
│           ↓                  │
│  XCOM / Python 串口发送       │
└──────────────┬───────────────┘
               │ USART1
               ↓
┌──────────────────────────────────────────────┐
│                  STM32F7 端                   │
│                                              │
│  UART 空闲中断接收                            │
│          ↓                                   │
│  输入格式判断：784*N / 28*W / -1 W H          │
│          ↓                                   │
│  图像归一化 + 列投影字符分割                  │
│          ↓                                   │
│  裁剪、缩放、居中填充为 28×28                 │
│          ↓                                   │
│  STM32Cube.AI CNN 推理                        │
│          ↓                                   │
│  字符类别 + softmax 置信度                    │
│          ↓                                   │
│  表达式重组与解析                             │
│          ↓                                   │
│  板端计算正确答案                             │
│          ↓                                   │
│  正确 / 错误 / 低置信度重写提示               │
└──────────────────────────────────────────────┘
```

---

## 硬件与软件环境

| 类型 | 内容 |
|---|---|
| MCU | STM32F767IGTx，Cortex-M7 |
| 开发环境 | Keil MDK-ARM |
| 配置工具 | STM32CubeMX |
| AI 部署 | X-CUBE-AI / STM32Cube.AI |
| 通信方式 | USART1 串口 |
| 上位机工具 | XCOM / Python |
| 训练框架 | TensorFlow / Keras |
| 模型格式 | `.h5`、`.keras`、`.tflite`、INT8 `.tflite` |

当前 Keil 编译资源占用：

```text
Program Size:
Code    = 28008
RO-data = 211152
RW-data = 2732
ZI-data = 156884
```

---

## 功能特性

| 功能 | 说明 | 状态 |
|---|---|:---:|
| 单字符识别 | 输入 784 个像素，识别一个数字或符号 | 已实现 |
| 15 类字符识别 | 支持 `0-9 + - * / =` | 已实现 |
| 固定块多字符输入 | 支持 `784*N` 个数字表示 N 个 28×28 字符 | 已实现 |
| 整行图像自动分割 | 支持高度为 28、宽度任意的整行图像 | 已实现 |
| 任意高宽图像输入 | 支持 `-1 width height pixels...` 格式 | 已实现 |
| 板端字符分割 | STM32F7 上按列投影检测字符边界 | 已实现 |
| Cube.AI 推理 | STM32F7 板端运行 CNN 模型 | 已实现 |
| 置信度判断 | softmax 最大概率作为字符置信度 | 已实现 |
| 低置信度重写 | 低于阈值时提示重写字符 | 已实现 |
| 多低置信度选择 | 多个低置信度字符时可选择下标重写 | 已实现 |
| 表达式解析 | 解析 `A op B = C` 格式 | 已实现 |
| 板端计算 | 在 STM32F7 上计算正确答案 | 已实现 |
| 自动判题 | 判断用户答案正确或错误 | 已实现 |
| 答案错误重写 | 答案错误时可只重写答案部分 | 已实现 |
| 编号测试集 | 提供 01-12 号串口测试 payload | 已实现 |

---

## 目录结构

推荐上传到 GitHub 的核心目录如下：

```text
EduCalc-AI/
├── 01_STM32F7_HandExprJudge_KeilSafe/
│   └── HandExprJudge/                         # STM32F7 Keil 最终工程
│       ├── Core/
│       │   ├── Inc/
│       │   │   ├── app_config.h               # 系统参数配置
│       │   │   ├── app_controller.h           # 应用状态机接口
│       │   │   ├── ai_infer.h                 # Cube.AI 推理接口
│       │   │   ├── image_segment.h            # 图像分割接口
│       │   │   └── expr_judge.h               # 表达式判题接口
│       │   └── Src/
│       │       ├── main.c                     # HAL 初始化、主循环、串口回调
│       │       ├── app_controller.c           # 串口协议、状态机、交互流程
│       │       ├── ai_infer.c                 # Cube.AI 初始化与推理封装
│       │       ├── image_segment.c            # 图像预处理与字符分割
│       │       ├── expr_judge.c               # 表达式解析与智能判题
│       │       ├── usart.c                    # USART1 初始化
│       │       ├── gpio.c                     # GPIO 初始化
│       │       └── crc.c                      # CRC 外设初始化
│       ├── X-CUBE-AI/
│       │   └── App/
│       │       ├── network.c/h                # Cube.AI 生成网络结构
│       │       ├── network_data.c/h           # 模型权重数据
│       │       └── network_data_params.c/h    # 权重参数接口
│       ├── Middlewares/ST/AI/                 # Cube.AI runtime
│       ├── Drivers/                           # STM32 HAL/CMSIS
│       ├── MDK-ARM/
│       │   └── HandExprJudge.uvprojx          # Keil 工程文件
│       └── CODE_STRUCTURE.md                  # 固件代码结构说明
│
├── 02_PC_Tools/                               # PC 端串口发送与参考脚本
│   ├── send_single_28x28_ascii.py             # 28×28 图像转串口 payload
│   └── requirements_baseline.txt
│
├── 03_Models/                                 # 参考模型与 Cube.AI 报告
│
├── 04_Docs/                                   # 项目文档
│   └── 手写算式识别智能判题系统技术说明.md
│
├── 05_Test_Records/                           # 测试记录、截图或日志
│
├── 06_Training_Model_Nodata/                  # 训练脚本与导出模型，不含原始大数据集
│   ├── train_15class_keras.py                 # 15 类 CNN 训练脚本
│   ├── collect_symbol_samples.py              # 运算符样本采集
│   ├── prepare_math_symbols_dataset.py        # 开源数据集整理
│   ├── inspect_raw_dataset.py                 # 数据预处理检查
│   ├── make_expr5_payload.py                  # 生成 784*N 测试 payload
│   ├── make_line28_payload.py                 # 生成整行图像 payload
│   ├── make_uart_payload_from_dataset.py      # 从数据集生成单字符 payload
│   ├── exports/
│   │   ├── hand_expr_15class.tflite
│   │   ├── hand_expr_15class_int8.tflite
│   │   └── labels_15class.txt
│   └── reports/
│       ├── training_report.json
│       └── confusion_matrix.csv
│
└── 07_test_input/
    └── 20260625_numbered_payloads/            # 01-12 编号测试数据
        ├── 01_single_char_8_784.txt
        ├── 02_fixed784_3plus2eq5.txt
        ├── 03_line28_auto_split_3plus2eq5.txt
        ├── 04_header40_auto_split_3plus2eq5.txt
        ├── 05_fixed784_two_digit_11mul5eq55.txt
        ├── 08_lowconf_natural_9mul8eq64_fixed784.txt
        ├── 11_wrong_answer_11mul5eq54_fixed784.txt
        └── README.md
```

---

## 神经网络模型

### 输入与输出

模型输入：

```text
28 × 28 × 1 灰度图像
```

模型输出：

```text
15 类 softmax 概率
```

类别顺序：

```text
0 1 2 3 4 5 6 7 8 9 + - * / =
```

该顺序必须与 STM32 端 `ai_infer.c` 中的 `AIInfer_Labels` 保持一致。

### CNN 结构

模型采用适合 MCU 部署的轻量 CNN：

```text
Input: 28×28×1
    ↓
Conv2D, 8 filters, 3×3, ReLU, same padding
MaxPooling2D, 2×2
    ↓
Conv2D, 16 filters, 3×3, ReLU, same padding
MaxPooling2D, 2×2
    ↓
Flatten
Dense, 64, ReLU
Dense, 15, Softmax
```

选择该模型的原因：

- 网络层数少，适合 STM32F7 的 Flash/RAM 资源。
- 卷积层能够提取手写笔画局部特征。
- 输入规格与 MNIST 风格一致，便于训练与调试。
- softmax 输出天然支持置信度判断。

### 训练结果

训练脚本：

```text
06_Training_Model_Nodata/train_15class_keras.py
```

训练配置：

```text
epochs = 12
batch_size = 128
```

测试集结果：

```text
test_accuracy = 94.71%
test_loss     = 0.1713
```

导出模型：

| 文件 | 用途 | 大小 |
|---|---|---:|
| `hand_expr_15class.tflite` | FP32 TFLite，导入 Cube.AI | 213 KB |
| `hand_expr_15class_int8.tflite` | INT8 量化模型，对比优化 | 57 KB |
| `labels_15class.txt` | 类别顺序表 | 15 类 |

---

## STM32Cube.AI 部署

部署链路：

```text
Keras / TFLite 模型
        ↓
STM32CubeMX 启用 X-CUBE-AI
        ↓
选择 hand_expr_15class.tflite
        ↓
Analyze
        ↓
Generate Code
        ↓
生成 network.c / network_data.c
        ↓
Keil MDK 编译
        ↓
STM32F7 板端运行 ai_network_run()
```

板端推理封装在：

```text
Core/Src/ai_infer.c
```

核心调用流程：

```c
ai_network_create_and_init(...);
ai_network_inputs_get(...);
ai_network_outputs_get(...);
ai_network_run(...);
```

推理输出为 15 类概率，程序取最大概率类别作为识别结果，最大概率值作为置信度。

---

## 串口通信协议

系统通过 USART1 接收 PC 端发送的 ASCII 数字 payload。每个数字代表一个像素值，数字之间可以用空格、换行、Tab 或逗号分隔。

### 格式 1：固定 28×28 字符块

```text
784 * N 个数字
```

例如 `3+2=5` 共 5 个字符：

```text
784 × 5 = 3920 个数字
```

该模式用于验证多字符推理链路。

### 格式 2：固定高度 28 的整行图像

```text
28 * W 个数字
```

板端自动推断宽度：

```text
W = value_count / 28
```

随后在 STM32F7 上执行字符分割。

### 格式 3：任意高宽图像

```text
-1 width height pixels...
```

例如：

```text
-1 91 40 ...
```

表示宽 91、高 40 的整行图像。板端先读取宽高，再进行分割、缩放和补齐。

---

## 字符分割算法

字符分割位于：

```text
Core/Src/image_segment.c
```

核心思想是按列投影检测笔迹区域：

```text
从左到右扫描每一列
    ↓
判断该列是否存在笔迹像素
    ↓
连续有笔迹的列组成一个字符区域
    ↓
空白列作为字符间隔
    ↓
在字符区域内继续寻找 y 方向上下边界
    ↓
得到字符外接矩形
    ↓
裁剪、缩放、居中填充为 28×28
```

板端会输出分割框信息：

```text
box[0]: x=... y=... size=...
```

这使系统从“只能识别单个预裁剪字符”扩展为“可以处理一整行算式图像”。

---

## 表达式解析与智能判题

表达式判题位于：

```text
Core/Src/expr_judge.c
```

系统将识别结果重组为字符串，例如：

```text
11*5=55
```

然后解析为：

```text
left        = 11
operator    = *
right       = 5
user_answer = 55
```

板端计算：

```text
correct_answer = 11 * 5 = 55
```

最后输出：

```text
judge: CORRECT
```

如果答案错误，例如：

```text
11*5=54
```

系统输出：

```text
calculated answer: 55
user answer: 54
judge: WRONG
tip: answer is wrong, please rewrite result.
```

用户可以只发送新的答案 `55`，系统会替换原表达式中的答案部分并重新判题。

---

## 置信度判断与交互重写

每个字符推理后，系统取 softmax 最大概率作为置信度。

当前阈值：

```text
confidence < 0.70          需要重写
0.70 <= confidence < 0.85  给出 warning
confidence >= 0.85         正常接受
```

低置信度示例：

```text
char[0]: label=9 confidence=0.606
low confidence detected.
char[0]=9 confidence=0.606: not clear, please rewrite.
command 0: rewrite unclear char
command 1: rewrite whole expression
command 2: reset for next expression
```

如果多个字符置信度低，系统允许选择字符下标进行局部重写：

```text
multiple low-confidence chars. Enter char index to rewrite: 0, 2
```

这是本项目区别于普通分类 Demo 的重要交互功能。

---

## 快速开始

### 1. 编译并烧录 STM32 工程

打开 Keil 工程：

```text
01_STM32F7_HandExprJudge_KeilSafe/HandExprJudge/MDK-ARM/HandExprJudge.uvprojx
```

在 Keil 中执行：

```text
Rebuild
Download
```

当前工程已经验证可以通过编译。

### 2. 打开串口调试助手

使用 XCOM 或其他串口工具，连接对应 COM 口。

串口参数以 Keil 工程中的 USART1 配置为准。当前项目沿用 STM32 工程串口配置，发送格式为 ASCII 文本。

### 3. 发送测试 payload

测试数据目录：

```text
07_test_input/20260625_numbered_payloads/
```

推荐测试顺序：

```text
01_single_char_8_784.txt
02_fixed784_3plus2eq5.txt
03_line28_auto_split_3plus2eq5.txt
04_header40_auto_split_3plus2eq5.txt
05_fixed784_two_digit_11mul5eq55.txt
08_lowconf_natural_9mul8eq64_fixed784.txt
11_wrong_answer_11mul5eq54_fixed784.txt
```

### 4. 查看串口输出

正常输出示例：

```text
You Have Received 3920 Numbers
input mode: fixed 28x28 blocks, chars=5
segmented chars: 5
char[0]: label=3 confidence=0.972
char[1]: label=+ confidence=0.991
char[2]: label=2 confidence=0.965
char[3]: label== confidence=0.994
char[4]: label=5 confidence=0.981
recognized expression: 3+2=5
calculated answer: 5
user answer: 5
judge: CORRECT
```

---

## 测试数据说明

最新编号测试数据位于：

```text
07_test_input/20260625_numbered_payloads/
```

| 编号 | 文件 | 功能 |
|---:|---|---|
| 01 | `01_single_char_8_784.txt` | 单字符识别 |
| 02 | `02_fixed784_3plus2eq5.txt` | 固定块表达式识别 |
| 03 | `03_line28_auto_split_3plus2eq5.txt` | 28 高度自动分割 |
| 04 | `04_header40_auto_split_3plus2eq5.txt` | 任意高宽自动分割 |
| 05 | `05_fixed784_two_digit_11mul5eq55.txt` | 两位数固定块表达式 |
| 06 | `06_line28_two_digit_11mul5eq55.txt` | 两位数 28 高度自动分割 |
| 07 | `07_header44_two_digit_11mul5eq55.txt` | 两位数任意高宽输入 |
| 08 | `08_lowconf_natural_9mul8eq64_fixed784.txt` | 自然低置信度案例 |
| 09 | `09_lowconf_artificial_3plus_blank_eq5_fixed784.txt` | 人工低置信度案例 |
| 10 | `10_rewrite_char2_as_2_784.txt` | 低置信度字符重写 |
| 11 | `11_wrong_answer_11mul5eq54_fixed784.txt` | 答案错误案例 |
| 12 | `12_rewrite_answer_55_1568.txt` | 答案重写 |

---

## 项目创新点

相比普通 MNIST 手写数字识别，本项目的扩展点包括：

- 从单数字识别扩展到完整算式识别。
- 类别从 10 类扩展到 15 类，加入运算符和等号。
- 在 STM32F7 板端实现整行图像字符分割。
- 支持三种输入格式，适配不同测试场景。
- 在 MCU 上完成表达式解析和整数运算。
- 加入低置信度判断，提高交互可靠性。
- 支持局部重写，不必每次重新输入整个表达式。
- 支持答案错误后只重写答案部分。
- 使用 STM32Cube.AI 完成轻量 CNN 端侧部署。
- 固件代码经过模块化拆分，便于维护和答辩展示。

---

## GitHub 上传建议

建议上传：

```text
01_STM32F7_HandExprJudge_KeilSafe/
02_PC_Tools/
03_Models/
04_Docs/
05_Test_Records/
06_Training_Model_Nodata/
07_test_input/
README.md
```

不建议上传：

```text
01_STM32F7_0_9_baseline/
01_STM32F7_0_9_baseline -备份/
01_STM32F7_0_9_verified_original/
01_STM32F7_15class_from_baseline/
01_STM32F7_HandExprJudge/
06_Training_15Class/
*.zip
*.rar
MDK-ARM/HandExprJudge/
*.o
*.d
*.crf
*.axf
*.hex
*.map
*.build_log.htm
*.uvguix.*
__pycache__/
```

---

## 后续改进方向

- 加入上位机可视化界面，显示字符框、置信度和判题结果。
- 进一步优化字符分割算法，处理字符粘连和倾斜。
- 对 FP32 与 INT8 模型进行更完整的 Flash、RAM、推理时间对比。
- 增加更多训练样本，提高 `6`、`7`、`9` 等易混类别置信度。
- 扩展表达式类型，例如连续运算、括号或负数输入。
- 如果更换带触摸屏开发板，可加入板端手写输入和 LCD 显示。

---

## 许可证

本项目用于嵌入式系统课程设计与学习交流。若后续公开发布，可根据需要补充 MIT、Apache-2.0 或其他开源许可证。

---

## 项目名称

**EduCalc-AI**

全称：

```text
EduCalc-AI：基于 STM32F7 与 STM32Cube.AI 的手写算式识别与智能判题系统
```

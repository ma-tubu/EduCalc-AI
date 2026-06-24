% 读取图片
img = imread('test.jpg');  % 替换为你的图片路径

% 灰度化（如果是彩色图像）
if size(img, 3) == 3
    img_gray = rgb2gray(img);
else
    img_gray = img;
end

% 将图像大小调整为 28*28 的整数倍（例如：784x784）
[rows, cols] = size(img_gray);
block_size = 28;

% 计算需要裁剪到的尺寸
new_rows = floor(rows / block_size) * block_size;
new_cols = floor(cols / block_size) * block_size;
img_cropped = img_gray(1:new_rows, 1:new_cols);

% 每块的像素大小
tile_rows = new_rows / block_size;
tile_cols = new_cols / block_size;

% 初始化输出矩阵
pixel_matrix = zeros(block_size, block_size, 'uint8');

% 分块并计算平均像素（取整）
for i = 1:block_size
    for j = 1:block_size
        row_start = (i-1)*tile_rows + 1;
        row_end   = i*tile_rows;
        col_start = (j-1)*tile_cols + 1;
        col_end   = j*tile_cols;
        
        block = img_cropped(row_start:row_end, col_start:col_end);
        avg_pixel = mean(block(:));
        pixel_matrix(i, j) = uint8(avg_pixel);  % 转为整数
    end
end

% 输出28x28像素矩阵，每个值空格隔开
for i = 1:block_size
    for j = 1:block_size
        fprintf('%3d ', pixel_matrix(i, j));
    end
    fprintf('\n');
end
import yaml
import cv2
import numpy as np

def find_black_pixels(image_path):
    # 读取图像
    img = cv2.imread(image_path)

    # 设置黑色的颜色范围 (RGB 三个通道都接近 0 的范围)
    lower_black = np.array([0, 0, 0])       # 最小黑色值
    upper_black = np.array([50, 50, 50])    # 最大黑色值（允许一定的偏差）

    # 识别黑色区域
    mask = cv2.inRange(img, lower_black, upper_black)

    # 找到黑色像素的坐标
    black_coords = np.column_stack(np.where(mask == 255))

    # 将坐标转换为 (x, y) 元组的格式
    black_coords_tuples = [(int(coord[1]), int(coord[0])) for coord in black_coords]

    return black_coords_tuples


def find_color_center(image_path, lower_color, upper_color):
    # 读取图像
    img = cv2.imread(image_path)

    # 创建颜色范围的掩膜
    mask = cv2.inRange(img, lower_color, upper_color)

    # 计算图像的质心（中心点）
    moments = cv2.moments(mask)

    # 防止除零错误
    if moments["m00"] != 0:
        center_x = int(moments["m10"] / moments["m00"])
        center_y = int(moments["m01"] / moments["m00"])
        return (center_x, center_y)
    else:
        return None
image_path = 'map.png'  # 替换为你的图片路径
black_coords = find_black_pixels(image_path)
def main():
    image_path = 'map.png'  # 替换为你的图片路径
    # 设置颜色范围
    image = cv2.imread('map.png')

    # 将图像转换为HSV颜色空间
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # 定义蓝色的HSV范围
    lower_blue = np.array([100, 150, 0])  # 蓝色范围的下限
    upper_blue = np.array([140, 255, 255])  # 蓝色范围的上限

    # 生成蓝色区域的掩膜
    mask = cv2.inRange(hsv_image, lower_blue, upper_blue)

    # 找到蓝色区域的轮廓
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 遍历每个轮廓，计算其中心点
    for contour in contours:
        M = cv2.moments(contour)
        if M['m00'] != 0:  # 确保区域的面积不为零，避免除以零的错误
            cx = int(M['m10'] / M['m00'])  # 质心的x坐标
            cy = int(M['m01'] / M['m00'])  # 质心的y坐标
            # 打印中心点坐标
            print(f"蓝色区域中心点坐标: ({cx}, {cy})")
            # 标记中心点
            cv2.circle(image, (cx, cy), 5, (0, 255, 0), -1)
        else:
            print("无法计算中心点")

    lower_red = np.array([0, 0, 100])  # 红色范围下限
    upper_red = np.array([100, 100, 255])  # 红色范围上限

    # 找到蓝色和红色部分的中心点
    start1 = cx,cy
    goal1 = find_color_center(image_path, lower_red, upper_red)

    if start1 is None or goal1 is None:
        print("无法找到蓝色或红色区域")
        return
    print(start1,goal1)
    # 动态根据颜色检测设置起点和终点，保留 z 轴为 0
    start = [1, goal1[0], goal1[1]]  # 自动检测的蓝色中心点
    goal = [1, start1[0], start1[1]]  # 自动检测的红色中心点

    # 创建地图
    origin = [0, 0, 0]  # 地图原点坐标 (0, 0, 0)
    dim = [500, 500, 1]  # 地图尺寸：x=500，y=500，z=1
    res = 1  # 分辨率：每个单元格代表1像素

    data = [0] * (dim[0] * dim[1] * dim[2])  # 初始化为全自由空间（占用值为0）

    # 读取黑色区域的坐标
    black_coords = find_black_pixels(image_path)

    # 将黑色区域添加为障碍物
    for (x, y) in black_coords:
        # 将像素坐标转换为地图坐标
        map_x = int(x * res)
        map_y = int(y * res)
        if 0 <= map_x < dim[0] and 0 <= map_y < dim[1]:  # 确保坐标在地图范围内
            id = map_x + dim[0] * map_y  # 计算索引
            data[id] = 1  # 设置障碍物值为100

    # 将地图信息编码为YAML格式
    map_info = {
        'start': start,
        'goal': goal,
        'origin': origin,
        'dim': dim,
        'resolution': res,
        'data': data
    }

    # 打印YAML格式的地图信息
    print("这是示例地图：")
    print(yaml.dump(map_info, default_flow_style=False))

    # 将YAML数据写入文件
    with open("simple.yaml", "w") as file:
        yaml.dump(map_info, file)

if __name__ == "__main__":
    main()
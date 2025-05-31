import os
from flask import Flask, request, redirect, url_for, render_template, flash, jsonify
from flask_cors import CORS
import cv2


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg','yaml', 'yml'}
app.secret_key = 'your_secret_key'
CORS(app)

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

uploaded_file_path = None


# 检查文件扩展名是否允许
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/')
def upload_form():
    return render_template('upload.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    global uploaded_file_path
    if 'file' not in request.files:
        flash('未选择文件')
        return redirect(request.url)

    file = request.files['file']

    if file.filename == '':
        flash('未选择文件')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        original_filename = file.filename  # 获取文件的原始名称
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
        file.save(filepath)

        if original_filename.endswith(('yaml', 'yml')):
            uploaded_file_path = filepath  # 这里需要存储文件的完整路径
        # 检查文件扩展名，处理图像或直接保存YAML文件
        if original_filename.endswith(('.png', '.jpg', '.jpeg')):
            try:
                image = cv2.imread(filepath)
                hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
                lower_blue = np.array([100, 150, 0])
                upper_blue = np.array([140, 255, 255])
                mask = cv2.inRange(hsv_image, lower_blue, upper_blue)
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                cx, cy = None, None  # 初始化变量
                for contour in contours:
                    M = cv2.moments(contour)
                    if M['m00'] != 0:
                        cx = int(M['m10'] / M['m00'])
                        cy = int(M['m01'] / M['m00'])
                        cv2.circle(image, (cx, cy), 5, (0, 255, 0), -1)

                if cx is None or cy is None:
                    raise Exception("无法找到蓝色区域")

                lower_red = np.array([0, 0, 100])
                upper_red = np.array([100, 100, 255])
                start1 = (cx, cy)
                goal1 = find_color_center(filepath, lower_red, upper_red)

                if goal1 is None:
                    raise Exception("无法找到红色区域")

                start = [1, goal1[0], goal1[1]]
                goal = [1, start1[0], start1[1]]
                origin = [0, 0, 0]
                dim = [500, 500, 1]
                res = 1
                data = [0] * (dim[0] * dim[1] * dim[2])

                black_coords = find_black_pixels(filepath)
                for (x, y) in black_coords:
                    map_x = int(x * res)
                    map_y = int(y * res)
                    if 0 <= map_x < dim[0] and 0 <= map_y < dim[1]:
                        id = map_x + dim[0] * map_y
                        data[id] = 1

                map_info = {
                    'start': start,
                    'goal': goal,
                    'origin': origin,
                    'dim': dim,
                    'resolution': res,
                    'data': data
                }

                # 保存 YAML 文件
                yaml_filename = os.path.splitext(original_filename)[0] + ".yaml"
                yaml_filepath = os.path.join(app.config['UPLOAD_FOLDER'], yaml_filename)

                with open(yaml_filepath, "w") as yaml_file:
                    yaml.dump(map_info, yaml_file)

                uploaded_file_path = yaml_filepath  # 存储 YAML 文件的完整路径
                flash(f'文件 "{original_filename}" 上传并成功生成 YAML 文件!')

            except Exception as e:
                flash(f'处理文件时出错: {str(e)}')

        else:
            # 保存YAML文件而不处理
            flash(f'文件 "{original_filename}" 已成功上传！')
            uploaded_file_path = filepath  # 确保路径是完整的
            print(uploaded_file_path)
        return redirect(url_for('upload_form'))

    flash('不支持的文件类型。仅允许 PNG 或 JPG 文件。')
    return redirect(request.url)


@app.route('/generate_path', methods=['POST'])
def generate_path():
    global uploaded_file_path
    try:
        with open(uploaded_file_path, 'r', encoding='utf-8-sig') as f:
            map_info = yaml.safe_load(f)

        dim = map_info['dim']
        data = np.array(map_info['data']).reshape((dim[1], dim[0]))
        start = tuple(map(int, map_info['start'][::-1]))
        end = tuple(map(int, map_info['goal'][::-1]))

        data[start[0], start[1]] = 0
        data[end[0], end[1]] = 0

        print("迷宫左上角500x500区域的视图:")
        print(data[:500, :500])

        path = astar(data, start[:2], end[:2])
        if path:
            print("路径已找到：", path)
            visualize_path(data, path, start, end)  # 确保只传递四个参数
        else:
            print("没有找到路径。")
            return jsonify({"status": "error", "message": "未找到路径。"})

        return jsonify({"status": "success", "path_image_url": url_for('static', filename='path_image.png')})
    except Exception as e:
        print(f"生成路径时出错: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})


# 图像处理和生成 YAML 文件的函数
def find_black_pixels(image_path):
    img = cv2.imread(image_path)
    lower_black = np.array([0, 0, 0])
    upper_black = np.array([50, 50, 50])
    mask = cv2.inRange(img, lower_black, upper_black)
    black_coords = np.column_stack(np.where(mask == 255))
    return [(int(coord[1]), int(coord[0])) for coord in black_coords]


def find_color_center(image_path, lower_color, upper_color):
    img = cv2.imread(image_path)
    mask = cv2.inRange(img, lower_color, upper_color)
    moments = cv2.moments(mask)
    if moments["m00"] != 0:
        center_x = int(moments["m10"] / moments["m00"])
        center_y = int(moments["m01"] / moments["m00"])
        return center_x, center_y
    else:
        return None



import heapq
import matplotlib.pyplot as plt
import numpy as np
import yaml


# 读取 YAML 文件
def read_yaml(file_path):
    with open(file_path, 'r') as file:
        map_info = yaml.safe_load(file)
    return map_info


#########################################################################寻路算法部分
class Node:
    """节点类表示搜索树中的每一个点。"""
    def __init__(self, parent=None, position=None):
        self.parent = parent        # 该节点的父节点
        self.position = position    # 节点在迷宫中的坐标位置
        self.g = 0                  # G值：从起点到当前节点的成本
        self.h = 0                  # H值：当前节点到目标点的估计成本
        self.f = 0                  # F值：G值与H值的和，即节点的总评估成本
        if len(position) != 2:
            raise ValueError("Node position 应该是一个二元组 (x, y)")

    # 比较两个节点位置是否相同
    def __eq__(self, other):
        return self.position == other.position

    # 定义小于操作，以便在优先队列中进行比较
    def __lt__(self, other):
        return self.f < other.f



def astar(maze, start, end):
    """A*算法实现，用于在迷宫中找到从起点到终点的最短路径。"""
    start_node = Node(None, start)  # 创建起始节点
    end_node = Node(None, end)      # 创建终点节点

    open_list = []                  # 开放列表用于存储待访问的节点
    closed_list = []                # 封闭列表用于存储已访问的节点

    heapq.heappush(open_list, (start_node.f, start_node))  # 将起始节点添加到开放列表
    print("添加起始节点到开放列表。")

    # 当开放列表非空时，循环执行
    while open_list:
        current_node = heapq.heappop(open_list)[1]  # 弹出并返回开放列表中 f 值最小的节点
        closed_list.append(current_node)            # 将当前节点添加到封闭列表
        print(f"当前节点: {current_node.position}")

        # 添加调试信息，检查 current_node.position
        if len(current_node.position) != 2:
            print(f"调试信息: current_node.position = {current_node.position}")
            raise ValueError("current_node.position 格式错误，应该是二元组")

        # 如果当前节点是目标节点，则回溯路径
        if current_node == end_node:
            path = []
            while current_node:
                path.append(current_node.position)
                current_node = current_node.parent
            print("找到目标节点，返回路径。")
            return path[::-1]  # 返回反向路径，即从起点到终点的路径

        # 获取当前节点周围的相邻节点
        (x, y) = current_node.position
        neighbors = [(x-1, y), (x+1, y), (x, y-1), (x, y+1)]

        # 遍历相邻节点
        for next in neighbors:
            # 确保相邻节点在迷宫范围内，且不是障碍物
            if 0 <= next[0] < maze.shape[0] and 0 <= next[1] < maze.shape[1]:
                if maze[next[0], next[1]] == 1:
                    continue
                neighbor = Node(current_node, next)  # 创建相邻节点
                # 如果相邻节点已在封闭列表中，跳过不处理
                if neighbor in closed_list:
                    continue
                neighbor.g = current_node.g + 1  # 计算相邻节点的 G 值
                neighbor.h = ((end_node.position[0] - next[0]) ** 2) + ((end_node.position[1] - next[1]) ** 2)  # 计算 H 值
                neighbor.f = neighbor.g + neighbor.h  # 计算 F 值

                # 如果相邻节点的新 F 值较小，则将其添加到开放列表
                if add_to_open(open_list, neighbor):
                    heapq.heappush(open_list, (neighbor.f, neighbor))
                    print(f"添加节点 {neighbor.position} 到开放列表。")
            else:
                print(f"节点 {next} 越界或为障碍。")

    return None  # 如果没有找到路径，返回 None



def add_to_open(open_list, neighbor):
    """检查并添加节点到开放列表。"""
    for node in open_list:
        # 如果开放列表中已存在相同位置的节点且 G 值更低，不添加该节点
        if neighbor == node[1] and neighbor.g > node[1].g:
            return False
    return True  # 如果不存在，则返回 True 以便添加该节点到开放列表


def visualize_path(maze, path, start, end):
    """将找到的路径可视化在迷宫上并保存图像。"""
    maze_copy = np.array(maze)
    for step in path:
        maze_copy[step] = 0.5  # 标记路径上的点

    plt.figure(figsize=(10, 10))
    plt.imshow(maze_copy, cmap='hot', interpolation='nearest')

    path_x = [p[1] for p in path]  # 列坐标
    path_y = [p[0] for p in path]  # 行坐标
    plt.plot(path_x, path_y, color='orange', linewidth=2)

    start_x, start_y = start[1], start[0]
    end_x, end_y = end[1], end[0]
    plt.scatter([start_x], [start_y], color='green', s=100, label='Start', zorder=5)
    plt.scatter([end_x], [end_y], color='red', s=100, label='End', zorder=5)
    plt.legend()
    plt.axis('off')

    # 保存图像到指定路径
    plt.savefig('static/path_image.png')
    plt.close()  # 关闭图形以释放内存

#################################################################################################
#写路径显示
if __name__ == "__main__":
    app.run(debug=True,port=5001,host='0.0.0.0')

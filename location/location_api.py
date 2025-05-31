import serial
import serial.tools.list_ports
from datetime import datetime
import threading
import queue
import time
from fastapi import FastAPI
import uvicorn
from pydantic import BaseModel


# 卡尔曼滤波器类
class KalmanFilter:
    def __init__(self, process_variance, measurement_variance, initial_value=0, max_change=None):
        self.process_variance = process_variance  # 过程噪声方差
        self.measurement_variance = measurement_variance  # 测量噪声方差
        self.estimate = initial_value  # 当前估计值
        self.estimate_error = 1  # 估计误差
        self.last_estimate = initial_value  # 上次估计值
        self.max_change = max_change  # 最大变化限制
        self.initialized = False  # 是否初始化

    def update(self, measurement):
        """更新滤波器状态"""
        if not self.initialized:
            self.estimate = measurement
            self.last_estimate = measurement
            self.initialized = True
            return measurement

        # 限制最大变化量
        if self.max_change is not None:
            max_diff = self.max_change
            measurement = max(min(measurement, self.last_estimate + max_diff),
                              self.last_estimate - max_diff)

        # 卡尔曼滤波计算
        prediction = self.last_estimate
        prediction_error = self.estimate_error + self.process_variance
        kalman_gain = prediction_error / (prediction_error + self.measurement_variance)
        self.estimate = prediction + kalman_gain * (measurement - prediction)
        self.estimate_error = (1 - kalman_gain) * prediction_error
        self.last_estimate = self.estimate

        return self.estimate


# 串口数据处理类
class SerialProcessor:
    def __init__(self, port=None, baudrate=230400):
        self.port = port  # 串口名称
        self.baudrate = baudrate  # 波特率
        self.serial = None  # 串口对象
        self.data_buffer = bytearray()  # 数据缓冲区
        self.HEADER = b'\xff\xff\xff\xff'  # 数据包头
        self.PACKET_LENGTH = 37  # 完整数据包长度
        self.is_running = False  # 运行状态

        # 初始化卡尔曼滤波器
        self.distance_filter = KalmanFilter(0.01, 50, max_change=100)  # 距离滤波器
        self.azimuth_filter = KalmanFilter(0.01, 30, max_change=30)  # 方位角滤波器
        self.elevation_filter = KalmanFilter(0.01, 30, max_change=30)  # 仰角滤波器

        # 当前数据
        self.current_data = {
            'anchor_id': 0,
            'tag_id': 0,
            'distance': 0,
            'azimuth': 0,
            'elevation': 0,
            'timestamp': ''
        }

    def initialize_serial(self):
        """初始化串口连接"""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.1
            )
            print(f'成功打开串口 {self.port}')
            return True
        except serial.SerialException as e:
            print(f'打开串口失败: {str(e)}')
            return False

    def process_buffer(self):
        """处理串口缓冲区数据"""
        if len(self.data_buffer) > self.PACKET_LENGTH * 10:  # 防止缓冲区过大
            self.data_buffer = self.data_buffer[-self.PACKET_LENGTH:]

        while len(self.data_buffer) >= self.PACKET_LENGTH:
            # 查找包头位置
            header_pos = self.data_buffer.find(self.HEADER)

            if header_pos == -1:  # 未找到包头
                self.data_buffer.clear()
                return None

            if header_pos > 0:  # 丢弃包头前的无效数据
                self.data_buffer = self.data_buffer[header_pos:]

            if len(self.data_buffer) >= self.PACKET_LENGTH:  # 提取完整数据包
                packet = self.data_buffer[:self.PACKET_LENGTH]
                self.data_buffer = self.data_buffer[self.PACKET_LENGTH:]
                return packet

        return None

    def parse_packet(self, packet):
        """解析数据包"""
        if len(packet) != self.PACKET_LENGTH:
            return None

        try:
            # 校验包头
            if packet[0:4] != self.HEADER:
                return None

            # 异或校验
            xor = 0
            for b in packet[:-1]:
                xor ^= b
            if xor != packet[-1]:
                print("校验失败：异或校验错误")
                return None

            # 解析数据字段
            return {
                'anchor_id': int.from_bytes(packet[12:16], 'big'),
                'tag_id': int.from_bytes(packet[16:20], 'big'),
                'distance': int.from_bytes(packet[20:24], 'big'),  # 距离(cm)
                'azimuth': int.from_bytes(packet[24:26], 'big', signed=True),  # 方位角(度)
                'elevation': int.from_bytes(packet[26:28], 'big', signed=True)  # 仰角(度)
            }

        except Exception as e:
            print(f'数据包解析错误: {str(e)}')
            return None

    def start_processing(self):
        """开始处理串口数据"""
        if not self.initialize_serial():
            return False

        self.is_running = True
        self.processing_thread = threading.Thread(target=self._processing_loop)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        return True

    def _processing_loop(self):
        """数据处理主循环"""
        while self.is_running:
            try:
                if self.serial.in_waiting:
                    # 读取串口数据
                    new_data = self.serial.read(min(self.serial.in_waiting, 1024))
                    self.data_buffer.extend(new_data)

                    # 处理完整数据包
                    while True:
                        packet = self.process_buffer()
                        if not packet:
                            break

                        fields = self.parse_packet(packet)
                        if fields:
                            # 应用卡尔曼滤波
                            filtered_distance = self.distance_filter.update(fields['distance'])
                            filtered_azimuth = self.azimuth_filter.update(fields['azimuth'])
                            filtered_elevation = self.elevation_filter.update(fields['elevation'])

                            # 更新当前数据
                            self.current_data = {
                                'anchor_id': fields['anchor_id'],
                                'tag_id': fields['tag_id'],
                                'distance': int(filtered_distance),
                                'azimuth': int(filtered_azimuth),
                                'elevation': int(filtered_elevation),
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }

            except serial.SerialException:
                self.is_running = False
                return
            except Exception as e:
                print(f"数据处理错误: {e}")
                break

            time.sleep(0.001)

    def stop_processing(self):
        """停止处理串口数据"""
        self.is_running = False
        if self.serial and self.serial.is_open:
            self.serial.close()
            print(f'串口 {self.port} 已关闭')

    def get_latest_data(self):
        """获取最新滤波后的数据"""
        return self.current_data


# 定义API响应模型
class SensorData(BaseModel):
    anchor_id: int
    tag_id: int
    distance: int
    azimuth: int
    elevation: int
    timestamp: str


# 创建FastAPI应用
app = FastAPI(title="串口数据卡尔曼滤波API")
serial_processor = None


@app.on_event("startup")
async def startup_event():
    """启动时初始化串口处理"""
    global serial_processor
    serial_processor = SerialProcessor(port="COM3", baudrate=230400)  # 修改为你的串口号
    if not serial_processor.start_processing():
        raise RuntimeError("串口数据处理启动失败")


@app.on_event("shutdown")
async def shutdown_event():
    """关闭时停止串口处理"""
    if serial_processor:
        serial_processor.stop_processing()


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """返回HTML页面显示最新数据"""
    data = serial_processor.get_latest_data()
    return f"""
    <html>
        <head>
            <title>串口数据卡尔曼滤波</title>
            <meta http-equiv="refresh" content="1">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                .data-container {{ 
                    background: #f5f5f5; 
                    padding: 20px; 
                    border-radius: 5px; 
                    margin-top: 20px;
                    width: 300px;
                }}
                .data-item {{ margin: 10px 0; }}
                .label {{ font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>卡尔曼滤波后的串口数据</h1>
            <div class="data-container">
                <div class="data-item"><span class="label">基站ID:</span> {data['anchor_id']}</div>
                <div class="data-item"><span class="label">标签ID:</span> {data['tag_id']}</div>
                <div class="data-item"><span class="label">距离:</span> {data['distance']} cm</div>
                <div class="data-item"><span class="label">方位角:</span> {data['azimuth']}°</div>
                <div class="data-item"><span class="label">仰角:</span> {data['elevation']}°</div>
                <div class="data-item"><span class="label">更新时间:</span> {data['timestamp']}</div>
            </div>
        </body>
    </html>
    """


@app.get("/api/data", response_model=SensorData)
async def get_data():
    """返回JSON格式的滤波后数据"""
    return serial_processor.get_latest_data()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
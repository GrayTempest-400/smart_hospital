# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: datachecker.py
# Bytecode version: 3.12.0rc2 (3531)
# Source timestamp: 1970-01-01 00:00:00 UTC (0)

"""\nCreated on Sun Feb 23 15:28:47 2025\n\n@author: roder\n"""
import tkinter as tk
from tkinter import ttk, scrolledtext
import serial.tools.list_ports
from datetime import datetime
import threading
import queue
import time
import binascii
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
import math
from collections import deque


class KalmanFilter:
    def __init__(self, process_variance, measurement_variance, initial_value=0, max_change=None):
        self.process_variance = process_variance
        self.measurement_variance = measurement_variance
        self.estimate = initial_value
        self.estimate_error = 1
        self.last_estimate = initial_value
        self.max_change = max_change
        self.initialized = False

    def update(self, measurement):
        if not self.initialized:
            self.estimate = measurement
            self.last_estimate = measurement
            self.initialized = True
            return measurement
        if self.max_change is not None:
            max_diff = self.max_change
            measurement = max(min(measurement, self.last_estimate + max_diff), self.last_estimate - max_diff)
        prediction = self.last_estimate
        prediction_error = self.estimate_error + self.process_variance
        kalman_gain = prediction_error / (prediction_error + self.measurement_variance)
        self.estimate = prediction + kalman_gain * (measurement - prediction)
        self.estimate_error = (1 - kalman_gain) * prediction_error
        self.last_estimate = self.estimate
        return self.estimate

    def reset(self):
        """重置滤波器状态"""
        self.estimate = 0
        self.estimate_error = 1
        self.last_estimate = 0
        self.initialized = False


class PlotFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.fig = Figure(figsize=(6, 4))
        self.ax = self.fig.add_subplot(111, projection='polar')
        self.ax.set_theta_zero_location('N')
        self.ax.set_theta_direction((-1))
        self.ax.set_thetamin((-90))
        self.ax.set_thetamax(90)
        self.ax.set_rlim(0, 500)
        self.ax.set_rticks([100, 200, 300, 400, 500])
        self.ax.set_rlabel_position(0)
        self.ax.set_thetagrids([(-90), (-45), 0, 45, 90])
        self.fig.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)
        self.scatter = self.ax.scatter([], [], c='red', s=100)
        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.draw()
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)

    def update_plot(self, distance, azimuth):
        """更新图形显示"""
        if azimuth > 180:
            azimuth = azimuth - 360
        if azimuth < (-90) or azimuth > 90:
            return None
        azimuth_rad = math.radians(azimuth)
        self.scatter.set_offsets(np.c_[azimuth_rad, distance])
        self.ax.draw_artist(self.scatter)
        self.canvas.draw()


class SerialLogger:
    def __init__(self, port=None, baudrate=230400, output_file='data.txt'):
        self.port = port
        self.baudrate = baudrate
        self.output_file = output_file
        self.serial = None
        self.data_buffer = bytearray()
        self.HEADER = b'\xff\xff\xff\xff'  # 协议规定的4字节包头
        self.PACKET_LENGTH = 37  # 协议规定的完整包长度
        self.MAX_BUFFER_SIZE = 10240

    def list_available_ports(self):
        """列出所有可用的串口"""
        ports = serial.tools.list_ports.comports()
        if not ports:
            print('没有找到可用的串口!')
            return []
        print('\n可用的串口:')
        for port in ports:
            print(f'- {port.device}: {port.description}')
        return ports

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
            print(f'\n成功打开串口 {self.port}')
            return True
        except serial.SerialException as e:
            print(f'打开串口失败: {str(e)}')
            return False

    def process_buffer(self):
        """优化后的缓冲区处理逻辑"""
        # 防止缓冲区过大
        if len(self.data_buffer) > self.MAX_BUFFER_SIZE:
            self.data_buffer = self.data_buffer[-self.PACKET_LENGTH:]

        while len(self.data_buffer) >= self.PACKET_LENGTH:
            # 查找包头位置
            header_pos = self.data_buffer.find(self.HEADER)

            # 未找到包头则清空无效数据
            if header_pos == -1:
                self.data_buffer.clear()
                return None

            # 丢弃包头前的杂乱数据
            if header_pos > 0:
                self.data_buffer = self.data_buffer[header_pos:]

            # 提取完整数据包
            if len(self.data_buffer) >= self.PACKET_LENGTH:
                packet = self.data_buffer[:self.PACKET_LENGTH]
                self.data_buffer = self.data_buffer[self.PACKET_LENGTH:]
                return packet

        return None

    def parse_packet(self, packet):
        """按 ALX-AOA-FIT 协议解析数据包"""
        if len(packet) != self.PACKET_LENGTH:
            return None

        try:
            # 校验头
            if packet[0:4] != self.HEADER:
                return None

            # 异或校验
            xor = 0
            for b in packet[:-1]:
                xor ^= b
            if xor != packet[-1]:
                print("校验失败：XOR 错误")
                return None

            fields = {
                'MessageHeader': packet[0:4],
                'PacketLength': int.from_bytes(packet[4:6], 'big'),
                'SequenceID': int.from_bytes(packet[6:8], 'big'),
                'RequestCommand': int.from_bytes(packet[8:10], 'big'),
                'VersionID': int.from_bytes(packet[10:12], 'big'),
                'AnchorID': int.from_bytes(packet[12:16], 'big'),
                'TagID': int.from_bytes(packet[16:20], 'big'),
                'Distance': int.from_bytes(packet[20:24], 'big'),  # 单位 cm
                'Azimuth': int.from_bytes(packet[24:26], 'big', signed=True),  # 单位 °
                'Elevation': int.from_bytes(packet[26:28], 'big', signed=True),  # 单位 °
                'TagStatus': int.from_bytes(packet[28:30], 'big'),
                'BatchSn': int.from_bytes(packet[30:32], 'big'),
                'Reserve': packet[32:36],
                'XorByte': packet[36]
            }

            return fields

        except Exception as e:
            print(f'数据包解析异常: {str(e)}')
            return None


    def close(self):
        """关闭串口连接"""
        if self.serial and self.serial.is_open:
            self.serial.close()
            print(f'串口 {self.port} 已关闭')


class SerialGUI:
    def __init__(self, root):
        self.root = root
        self.root.title('串口数据监控')
        self.root.geometry('1200x800')
        self.data_queue = queue.Queue(maxsize=100)
        self.log_queue = queue.Queue(maxsize=50)
        self.distance_process_var = tk.DoubleVar(value=0.01)
        self.distance_measure_var = tk.DoubleVar(value=50)
        self.distance_max_change = tk.DoubleVar(value=100)
        self.angle_process_var = tk.DoubleVar(value=0.01)
        self.angle_measure_var = tk.DoubleVar(value=30)
        self.angle_max_change = tk.DoubleVar(value=30)
        self.filter_enabled = tk.BooleanVar(value=True)
        self.init_filters()
        self.create_frames()
        self.create_widgets()
        self.serial_logger = SerialLogger()
        self.is_logging = False
        self.last_gui_update = time.time()
        self.last_plot_update = time.time()
        self.GUI_UPDATE_INTERVAL = 0.05
        self.PLOT_UPDATE_INTERVAL = 0.1
        self.update_ports()
        self.update_display()

    def init_filters(self):
        """初始化卡尔曼滤波器"""
        self.distance_filter = KalmanFilter(
            process_variance=self.distance_process_var.get(),
            measurement_variance=self.distance_measure_var.get(),
            max_change=self.distance_max_change.get()
        )
        self.azimuth_filter = KalmanFilter(
            process_variance=self.angle_process_var.get(),
            measurement_variance=self.angle_measure_var.get(),
            max_change=self.angle_max_change.get()
        )
        self.elevation_filter = KalmanFilter(
            process_variance=self.angle_process_var.get(),
            measurement_variance=self.angle_measure_var.get(),
            max_change=self.angle_max_change.get()
        )

    def create_frames(self):
        """创建主要框架"""
        self.left_frame = ttk.Frame(self.root)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.right_frame = ttk.Frame(self.root)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    def create_widgets(self):
        """创建控件"""
        control_frame = ttk.LabelFrame(self.left_frame, text='控制面板', padding='5')
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        serial_frame = ttk.Frame(control_frame)
        serial_frame.pack(fill=tk.X, pady=5)
        ttk.Label(serial_frame, text='串口:').grid(row=0, column=0, padx=5)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(serial_frame, textvariable=self.port_var)
        self.port_combo.grid(row=0, column=1, padx=5)
        ttk.Button(serial_frame, text='刷新串口', command=self.update_ports).grid(row=0, column=2, padx=5)
        ttk.Label(serial_frame, text='波特率:').grid(row=0, column=3, padx=5)
        self.baud_var = tk.StringVar(value='230400')
        baud_combo = ttk.Combobox(serial_frame, textvariable=self.baud_var,
                                  values=['9600', '115200', '230400', '460800'])
        baud_combo.grid(row=0, column=4, padx=5)
        self.start_button = ttk.Button(serial_frame, text='开始', command=self.toggle_logging)
        self.start_button.grid(row=0, column=5, padx=5)
        ttk.Button(serial_frame, text='清除显示', command=self.clear_display).grid(row=0, column=6, padx=5)

        filter_frame = ttk.LabelFrame(control_frame, text='滤波器参数设置', padding='5')
        filter_frame.pack(fill=tk.X, pady=5)

        filter_toggle_frame = ttk.Frame(filter_frame)
        filter_toggle_frame.pack(fill=tk.X, pady=2)
        ttk.Label(filter_toggle_frame, text='滤波器状态:').pack(side=tk.LEFT, padx=5)
        self.filter_toggle = ttk.Checkbutton(filter_toggle_frame, text='启用滤波', variable=self.filter_enabled,
                                             command=self.toggle_filter)
        self.filter_toggle.pack(side=tk.LEFT, padx=5)

        distance_frame = ttk.LabelFrame(filter_frame, text='距离滤波器', padding='5')
        distance_frame.pack(fill=tk.X, pady=2)
        self.create_parameter_row(distance_frame, '过程噪声:', self.distance_process_var, 0, 0.001, 1.0, 0)
        self.create_parameter_row(distance_frame, '测量噪声:', self.distance_measure_var, 0, 1.0, 200.0, 1)
        self.create_parameter_row(distance_frame, '最大变化:', self.distance_max_change, 0, 1.0, 500.0, 2)

        angle_frame = ttk.LabelFrame(filter_frame, text='角度滤波器', padding='5')
        angle_frame.pack(fill=tk.X, pady=2)
        self.create_parameter_row(angle_frame, '过程噪声:', self.angle_process_var, 0, 0.001, 1.0, 0)
        self.create_parameter_row(angle_frame, '测量噪声:', self.angle_measure_var, 0, 1.0, 200.0, 1)
        self.create_parameter_row(angle_frame, '最大变化:', self.angle_max_change, 0, 1.0, 180.0, 2)

        ttk.Button(filter_frame, text='应用参数', command=self.apply_filter_params).pack(pady=5)

        display_frame = ttk.LabelFrame(self.left_frame, text='数据显示', padding='5')
        display_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        station_frame = ttk.LabelFrame(display_frame, text='基站信息', padding='5')
        station_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(station_frame, text='基站ID:').grid(row=0, column=0, padx=5)
        self.anchor_id_var = tk.StringVar(value='--')
        ttk.Label(station_frame, textvariable=self.anchor_id_var).grid(row=0, column=1, padx=5)
        ttk.Label(station_frame, text='标签ID:').grid(row=0, column=2, padx=5)
        self.tag_id_var = tk.StringVar(value='--')
        ttk.Label(station_frame, textvariable=self.tag_id_var).grid(row=0, column=3, padx=5)

        data_frame = ttk.LabelFrame(display_frame, text='实时数据', padding='5')
        data_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(data_frame, text='距离:').grid(row=0, column=0, padx=5)
        self.distance_var = tk.StringVar(value='-- cm')
        ttk.Label(data_frame, textvariable=self.distance_var).grid(row=0, column=1, padx=5)
        ttk.Label(data_frame, text='方位角:').grid(row=0, column=2, padx=5)
        self.azimuth_var = tk.StringVar(value='-- °')
        ttk.Label(data_frame, textvariable=self.azimuth_var).grid(row=0, column=3, padx=5)
        ttk.Label(data_frame, text='仰角:').grid(row=0, column=4, padx=5)
        self.elevation_var = tk.StringVar(value='-- °')
        ttk.Label(data_frame, textvariable=self.elevation_var).grid(row=0, column=5, padx=5)

        self.log_text = scrolledtext.ScrolledText(display_frame, height=20)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        plot_frame = ttk.LabelFrame(self.right_frame, text='位置可视化', padding='5')
        plot_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.plot = PlotFrame(plot_frame)
        self.plot.pack(fill=tk.BOTH, expand=True)

    def create_parameter_row(self, parent, label, variable, column, min_val, max_val, row):
        """创建参数调整行"""
        ttk.Label(parent, text=label).grid(row=row, column=column, padx=5)
        spinbox = ttk.Spinbox(parent, from_=min_val, to=max_val, increment=0.001, textvariable=variable, width=10)
        spinbox.grid(row=row, column=column + 1, padx=5)
        scale = ttk.Scale(parent, from_=min_val, to=max_val, variable=variable, orient=tk.HORIZONTAL)
        scale.grid(row=row, column=column + 2, padx=5, sticky='ew')
        parent.grid_columnconfigure(column + 2, weight=1)

    def toggle_filter(self):
        """切换滤波器状态"""
        if self.filter_enabled.get():
            self.log_message('已启用滤波器')
            self.init_filters()
        else:
            self.log_message('已禁用滤波器')

    def apply_filter_params(self):
        """应用新的滤波器参数"""
        self.init_filters()
        self.log_message('已更新滤波器参数')

    def update_ports(self):
        """更新可用串口列表"""
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports:
            self.port_combo.set(ports[0])

    def toggle_logging(self):
        """切换数据记录状态"""
        if not self.is_logging:
            self.distance_filter.reset()
            self.azimuth_filter.reset()
            self.elevation_filter.reset()
            self.serial_logger.port = self.port_var.get()
            self.serial_logger.baudrate = int(self.baud_var.get())
            if self.serial_logger.initialize_serial():
                self.is_logging = True
                self.start_button['text'] = '停止'
                self.log_thread = threading.Thread(target=self.logging_thread)
                self.log_thread.daemon = True
                self.log_thread.start()
                self.log_message('开始记录数据...')
            else:
                self.log_message('打开串口失败!')
        else:
            self.is_logging = False
            self.start_button['text'] = '开始'
            self.serial_logger.close()
            self.log_message('停止记录数据')

    def logging_thread(self):
        """优化的数据记录线程"""
        while self.is_logging:
            try:
                if self.serial_logger.serial.in_waiting:
                    new_data = self.serial_logger.serial.read(min(self.serial_logger.serial.in_waiting, 1024))
                    self.serial_logger.data_buffer.extend(new_data)

                    while True:
                        packet = self.serial_logger.process_buffer()
                        if not packet:
                            break

                        fields = self.serial_logger.parse_packet(packet)
                        if fields:
                            try:
                                self.data_queue.put_nowait(fields)
                            except queue.Full:
                                pass

                            hex_data = binascii.hexlify(packet).decode('utf-8')
                            hex_formatted = ' '.join((hex_data[i:i + 2] for i in range(0, len(hex_data), 2)))
                            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                            parsed_info = f"基站ID: {fields['AnchorID']}, 标签ID: {fields['TagID']}, 距离: {fields['Distance']}cm, 方位角: {fields['Azimuth']}°, 仰角: {fields['Elevation']}°"
                            log_line = f'[{timestamp}] {hex_formatted}\n解析结果: {parsed_info}\n'

                            try:
                                self.log_queue.put_nowait(log_line)
                            except queue.Full:
                                pass
            except serial.SerialException:
                self.is_logging = False
                return
            except Exception as e:
                print(f"Error in logging thread: {e}")
                break

            time.sleep(0.001)

    def update_display(self):
        """优化的显示更新"""
        current_time = time.time()

        if current_time - self.last_gui_update >= self.GUI_UPDATE_INTERVAL:
            try:
                data_processed = False
                last_fields = None

                while not self.data_queue.empty():
                    fields = self.data_queue.get_nowait()
                    last_fields = fields
                    data_processed = True

                    if self.filter_enabled.get():
                        filtered_distance = self.distance_filter.update(fields['Distance'])
                        filtered_azimuth = self.azimuth_filter.update(fields['Azimuth'])
                        filtered_elevation = self.elevation_filter.update(fields['Elevation'])
                    else:
                        filtered_distance = fields['Distance']
                        filtered_azimuth = fields['Azimuth']
                        filtered_elevation = fields['Elevation']

                    self.anchor_id_var.set(f"{fields['AnchorID']}")
                    self.tag_id_var.set(f"{fields['TagID']}")
                    self.distance_var.set(f'{int(filtered_distance)} cm')
                    self.azimuth_var.set(f'{int(filtered_azimuth)} °')
                    self.elevation_var.set(f'{int(filtered_elevation)} °')

                    fields['Distance'] = int(filtered_distance)
                    fields['Azimuth'] = int(filtered_azimuth)
                    fields['Elevation'] = int(filtered_elevation)

                if data_processed and last_fields and (
                        current_time - self.last_plot_update >= self.PLOT_UPDATE_INTERVAL):
                    self.plot.update_plot(last_fields['Distance'], last_fields['Azimuth'])
                    self.last_plot_update = current_time

            except queue.Empty:
                pass

            log_text = ''
            while not self.log_queue.empty():
                try:
                    log_text += self.log_queue.get_nowait()
                except queue.Empty:
                    break

            if log_text:
                self.log_text.insert(tk.END, log_text)
                self.log_text.see(tk.END)

            self.last_gui_update = current_time

        self.root.after(1, self.update_display)

    def log_message(self, message):
        """添加日志消息"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        log_line = f'[{timestamp}] {message}\n'
        try:
            self.log_queue.put_nowait(log_line)
        except queue.Full:
            pass

    def clear_display(self):
        """清除显示"""
        self.log_text.delete(1.0, tk.END)

    def on_closing(self):
        """关闭窗口时的处理"""
        if self.is_logging:
            self.is_logging = False
            self.serial_logger.close()
        self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    app = SerialGUI(root)
    root.protocol('WM_DELETE_WINDOW', app.on_closing)
    root.mainloop()
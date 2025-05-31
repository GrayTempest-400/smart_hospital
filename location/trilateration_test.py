# test_trilateration.py

import sys     # 引入 sys 模块，用于脚本退出和命令行交互
import math    # 引入 math 模块，如果需要做数学运算（此处主要保留以备扩展）

def print_help():
    """
    打印帮助信息：
    说明脚本用途及联系方式
    """
    print("这是一个单元测试，演示如何使用")
    print("Navigine 的三边测距算法类来根据距离测量获取用户的平面坐标")
    print("如有更多问题，请联系 aleksei.smirnov@navigine.com")
    print()  # 空行分隔

# ——————————————————————————————————————————————————————————————————————————————
class Beacon:
    """
    Beacon 类：代表地图上已知的发射器（如蓝牙 iBeacon）
    包含其平面坐标、唯一 ID、名称和子位置（楼层）信息
    """
    def __init__(self, x=0.0, y=0.0, beacon_id="", name="", location_name=""):
        # 构造函数：初始化各属性
        self.x = x                          # 平面 X 坐标
        self.y = y                          # 平面 Y 坐标
        self.id = beacon_id                 # 唯一标识符（可以包括 UUID、major/minor 等）
        self.name = name                    # 信标名称
        self.location_name = location_name  # 子位置名称（如“floor13”）

    def fill_data(self, x, y, beacon_id, name, location_name):
        """
        填充信标所有属性的便捷方法
        :param x: X 坐标
        :param y: Y 坐标
        :param beacon_id: 唯一 ID
        :param name: 信标名称
        :param location_name: 子位置信息
        """
        self.x = x
        self.y = y
        self.id = beacon_id
        self.name = name
        self.location_name = location_name

# ——————————————————————————————————————————————————————————————————————————————
class BeaconMeas:
    """
    BeaconMeas 类：代表一次从 Beacon 接收到的测量
    包含 RSSI、距离以及对应的 Beacon 引用（后续填充）
    """
    def __init__(self, beacon_id="", rssi=0.0, distance=0.0):
        # 构造函数：初始化测量数据
        self.beacon_id = beacon_id    # 测量对应的信标 ID
        self.rssi = rssi              # 接收信号强度指示
        self.distance = distance      # 根据信号强度换算的伪距离
        self.beacon_ptr = None        # 后续会指向实际的 Beacon 对象

    def set_beacon_id(self, beacon_id):
        """设置测量对应的 Beacon ID"""
        self.beacon_id = beacon_id

    def set_rssi(self, rssi):
        """设置测量的 RSSI"""
        self.rssi = rssi

    def set_distance(self, distance):
        """设置测量的距离"""
        self.distance = distance

    def set_beacon_ptr(self, beacon):
        """将测量关联到具体的 Beacon 对象"""
        self.beacon_ptr = beacon

    def __lt__(self, other):
        """
        支持基于 distance 的排序：
        使得 sorted(list_of_meas) 会按距离从小到大排列
        """
        return self.distance < other.distance

# ——————————————————————————————————————————————————————————————————————————————
class Trilateration:
    """
    Trilateration 类：实现核心的三边测距流程
    步骤包括：
      1. 删除重复测量并平均
      2. 按距离升序排序
      3. 过滤地图上不存在的信标测量
      4. 对最强的前三条测量做加权平均定位
    """
    ERROR_NO_SOLUTION = 4
    ERROR_IN_TRILATER = 28

    def __init__(self):
        """构造函数：初始化测量和地图信标列表，以及结果坐标"""
        self.beacon_measurements = []  # 存放 BeaconMeas 对象
        self.map_beacons = []          # 存放 Beacon 对象
        self.x = 0.0                   # 最终计算的 X 坐标
        self.y = 0.0                   # 最终计算的 Y 坐标

    def update_measurements(self, measurements):
        """
        更新测量列表（接收到新测量时调用）
        :param measurements: BeaconMeas 对象列表
        """
        self.beacon_measurements = measurements.copy()

    def fill_location_beacons(self, beacons):
        """
        填充地图上已知信标列表（初始化或切换楼层时调用）
        :param beacons: Beacon 对象列表
        """
        self.map_beacons = beacons.copy()

    def calculate_coordinates(self):
        """
        核心定位函数：
        1. 删除重复测量并平均
        2. 排序
        3. 过滤未知信标
        4. 加权平均定位
        返回错误码：0 成功，其它为失败
        """
        # --- 1. 去重并平均 ---
        unique = {}
        for m in self.beacon_measurements:
            if m.beacon_id not in unique:
                unique[m.beacon_id] = [m.rssi, m.distance, 1]
            else:
                unique[m.beacon_id][0] += m.rssi
                unique[m.beacon_id][1] += m.distance
                unique[m.beacon_id][2] += 1

        # 构造去重后的测量列表
        self.beacon_measurements = []
        for bid, (rs, ds, cnt) in unique.items():
            avg = BeaconMeas(bid, rs/cnt, ds/cnt)
            self.beacon_measurements.append(avg)

        # 测量数不足 3 条，无法定位
        if len(self.beacon_measurements) < 3:
            return Trilateration.ERROR_NO_SOLUTION

        # --- 2. 按距离升序排序 ---
        self.beacon_measurements.sort()

        # --- 3. 过滤地图上不存在的信标 ---
        filtered = []
        for m in self.beacon_measurements:
            for b in self.map_beacons:
                if b.id == m.beacon_id:
                    m.set_beacon_ptr(b)
                    filtered.append(m)
                    break
        self.beacon_measurements = filtered
        if len(self.beacon_measurements) < 3:
            return Trilateration.ERROR_NO_SOLUTION

        # --- 4. 对最强的前三条测量做加权平均定位 ---
        top3 = self.beacon_measurements[:3]
        norm = sum(1.0/abs(m.distance) for m in top3)
        x_sum = 0.0
        y_sum = 0.0
        for m in top3:
            w = (1.0/abs(m.distance)) / norm   # 权重 = 归一化后距离的倒数
            x_sum += w * m.beacon_ptr.x      # 加权累加 X
            y_sum += w * m.beacon_ptr.y      # 加权累加 Y

        # 保存结果
        self.x, self.y = x_sum, y_sum
        return 0

    def get_x(self):
        """返回计算得到的 X 坐标"""
        return self.x

    def get_y(self):
        """返回计算得到的 Y 坐标"""
        return self.y

# ——————————————————————————————————————————————————————————————————————————————
def main():
    """
    程序入口：
    1. 打印帮助
    2. 初始化 Trilateration
    3. 填充地图信标
    4. 填充测量数据
    5. 执行定位并输出结果
    """
    print_help()

    # 1. 创建三边测距实例
    trilat = Trilateration()

    # 2. 填充地图信标（3 个已知）
    beacons = []
    b = Beacon()
    b.fill_data(54.69, 29.51,
                "(53580,22667,F7826DA6-4FA2-4E98-8024-BC5B71E0893E)",
                "beacon1", "floor13")
    beacons.append(b)
    b = Beacon()
    b.fill_data(54.68, 29.51,
                "(49599,56896,F7826DA6-4FA2-4E98-8024-BC5B71E0893E)",
                "beacon2", "floor13")
    beacons.append(b)
    b = Beacon()
    b.fill_data(49.05, 32.16,
                "(57506,19633,F7826DA6-4FA2-4E98-8024-BC5B71E0893E)",
                "beacon3", "floor13")
    beacons.append(b)
    trilat.fill_location_beacons(beacons)

    # 3. 填充测量数据（含一条未知信标）
    meas = []
    meas.append(BeaconMeas("(53580,22667,F7826DA6-4FA2-4E98-8024-BC5B71E0893E)", -86.57, 4.47))
    meas.append(BeaconMeas("(49599,56896,F7826DA6-4FA2-4E98-8024-BC5B71E0893E)", -90.80, 14.13))
    meas.append(BeaconMeas("(57506,19633,F7826DA6-4FA2-4E98-8024-BC5B71E0893E)", -86.41, 15.85))
    meas.append(BeaconMeas("22211,00231", -21.41, 15.85))  # 来自未知信标

    trilat.update_measurements(meas)

    # 4. 执行定位并输出
    err = trilat.calculate_coordinates()
    x, y = trilat.get_x(), trilat.get_y()
    print(f"x = {x:.3f}  y = {y:.3f}")

    if err != 0:
        print("测试未通过，请检查测量数据或算法实现。")
        sys.exit(err)
    else:
        print("test passed!")

if __name__ == "__main__":
    main()

# trilateration.py
#
# 作者: Aleksei Smirnov <aleksei.smirnov@navigine.ru>
# 版权所有 (c) 2014 Navigine。保留所有权利。

import math
from typing import List, Optional, Tuple


class Beacon:
    """
    Beacon 类：表示地图上的信标（发射器），包含其平面坐标及标识信息
    """
    def __init__(self, x: float = 0.0, y: float = 0.0,
                 beacon_id: str = "", name: str = "", location_name: str = "", location_id: int = 0):
        self.x = x                        # 平面 X 坐标
        self.y = y                        # 平面 Y 坐标
        self.id = beacon_id               # 信标唯一标识符
        self.name = name                  # 信标名称
        self.location_name = location_name  # 子位置名称（如楼层）
        self.location_id = location_id    # 子位置 ID

    def fill_data(self, x: float, y: float, beacon_id: str, name: str, location_name: str):
        """
        一次性填充所有属性
        """
        self.x = x
        self.y = y
        self.id = beacon_id
        self.name = name
        self.location_name = location_name

    def __eq__(self, other: 'Beacon') -> bool:
        return self.id == other.id


class BeaconMeas:
    """
    BeaconMeas 类：表示一次信标测量，包含 RSSI、距离以及对应的信标引用
    """
    TRANSMITTER_POINT_UNUSED = 1

    def __init__(self, beacon_id: str = "", rssi: float = TRANSMITTER_POINT_UNUSED,
                 distance: float = 0.0):
        self.beacon_id = beacon_id    # 测量对应的信标 ID
        self.rssi = rssi              # 接收信号强度指示 (RSSI)
        self.distance = distance      # 根据信号计算的距离（伪距离）
        self.beacon_ptr: Optional[Beacon] = None  # 可选：指向实际 Beacon 对象

    def set_beacon_ptr(self, beacon: Beacon):
        """
        设置测量对应的 Beacon 对象引用
        """
        self.beacon_ptr = beacon

    def __lt__(self, other: 'BeaconMeas') -> bool:
        """
        按距离升序排序（距离越小权重越大）
        """
        return self.distance < other.distance

    def __eq__(self, other: 'BeaconMeas') -> bool:
        return self.beacon_id == other.beacon_id


def compare_beacon_meas_by_name(a: BeaconMeas, b: BeaconMeas) -> bool:
    """
    按 beacon_id 字母序排序，用于去重前的排序
    """
    return a.beacon_id < b.beacon_id


def find_beacon_for_meas(map_beacons: List[Beacon], measure_id: str) -> Optional[Beacon]:
    """
    在地图信标列表中查找与测量 ID 匹配的信标
    """
    for b in map_beacons:
        if b.id == measure_id:
            return b
    return None


class Trilateration:
    """
    Trilateration 类：实现三边测距流程，包括去重、过滤、
    权重计算、最小二乘求解等步骤
    """
    ERROR_IN_TRILATER = -1
    ERROR_NO_SOLUTION_TRILATERATION = -2

    def __init__(self):
        # 最终计算出的 [x, y]
        self.xy: List[float] = [0.0, 0.0]
        # 当前子位置 ID
        self.current_location_id: int = 0
        # 地图上已知的信标列表
        self.location_beacons: List[Beacon] = []
        # 当前可见的测量列表
        self.beacon_meas: List[BeaconMeas] = []
        # 错误消息
        self.error_message: str = ""

    def update_measurements(self, measurements: List[BeaconMeas]):
        """
        更新所有测量数据
        """
        self.beacon_meas = measurements.copy()

    def fill_location_beacons(self, beacons: List[Beacon]):
        """
        填充地图信标列表
        """
        self.location_beacons = beacons.copy()

    def set_current_location_id(self, loc_id: int):
        """
        设置当前定位的子位置 ID
        """
        self.current_location_id = loc_id

    def calculate_coordinates(self) -> int:
        """
        核心流程：去重→排序→过滤→三边测距→（可选最小二乘）→返回 x, y
        :return: 0 成功，负值错误
        """
        # 1. 删除重复测量并平均 RSSI／距离
        err = self._delete_duplicate_measurements()
        if err:
            return err

        # 2. 按距离升序排序（越近权重越大）
        self.beacon_meas.sort()

        # 3. 过滤出地图上不存在的信标
        self._filter_unknown_beacons()
        if not self.beacon_meas:
            self.error_message = f"可见信标数量为 0"
            return Trilateration.ERROR_NO_SOLUTION_TRILATERATION

        # 4. 取最强的前三个测量（或全部，如果少于 3 个）
        strongest = self.beacon_meas[:3]

        # 5. 基于权重的加权平均三边测距
        err = self._calculate_trilateration_coordinates(strongest)
        if err:
            return err

        # 6. （可选）最小二乘法 refinement
        # self._get_least_squares_coordinates()

        return 0

    def get_x(self) -> float:
        return self.xy[0]

    def get_y(self) -> float:
        return self.xy[1]

    def _filter_unknown_beacons(self):
        """
        删除那些在地图信标列表中找不到的测量
        """
        filtered: List[BeaconMeas] = []
        for meas in self.beacon_meas:
            beacon = find_beacon_for_meas(self.location_beacons, meas.beacon_id)
            if beacon:
                meas.set_beacon_ptr(beacon)
                filtered.append(meas)
        self.beacon_meas = filtered

    def _delete_duplicate_measurements(self) -> int:
        """
        删除重复测量并对同一信标的多次测量做平均
        """
        # 按 ID 排序以便去重
        self.beacon_meas.sort(key=lambda m: m.beacon_id)
        unique: List[BeaconMeas] = []
        i = 0
        n = len(self.beacon_meas)

        while i < n:
            # 统计连续相同 ID 的测量
            j = i
            sum_rssi = 0.0
            sum_dist = 0.0
            count = 0
            while j < n and self.beacon_meas[j].beacon_id == self.beacon_meas[i].beacon_id:
                if self.beacon_meas[j].distance < 0:
                    self.error_message = f"测量距离为负: {self.beacon_meas[j].beacon_id}"
                    return Trilateration.ERROR_IN_TRILATER
                sum_rssi += self.beacon_meas[j].rssi
                sum_dist += self.beacon_meas[j].distance
                count += 1
                j += 1

            # 平均
            avg = BeaconMeas(
                beacon_id=self.beacon_meas[i].beacon_id,
                rssi=sum_rssi / count,
                distance=sum_dist / count
            )
            unique.append(avg)
            i = j

        if len(unique) < 3:
            self.error_message = "可见信标不足 3 个，无法定位"
            return Trilateration.ERROR_NO_SOLUTION_TRILATERATION

        self.beacon_meas = unique
        return 0

    def _calculate_trilateration_coordinates(self, meas: List[BeaconMeas]) -> int:
        """
        基于距离的加权平均计算坐标
        """
        # 归一化系数：距离越小权重越大
        norm = sum(1.0 / abs(m.distance) for m in meas)

        x_sum = 0.0
        y_sum = 0.0
        for m in meas:
            if not m.beacon_ptr:
                self.error_message = f"信标指针为空: {m.beacon_id}"
                return Trilateration.ERROR_IN_TRILATER
            weight = (1.0 / abs(m.distance)) / norm
            x_sum += weight * m.beacon_ptr.x
            y_sum += weight * m.beacon_ptr.y

        self.xy = [x_sum, y_sum]
        return 0

    # 以下方法可选：通过最小二乘法精化结果
    def _get_least_squares_coordinates(self):
        """
        使用普通最小二乘法解线性化后的方程组，进一步逼近
        """
        n = len(self.beacon_meas)
        dim = 2
        # 构建 A 矩阵和 b 向量
        A = [0.0] * ((n - 1) * dim)
        b = [0.0] * (n - 1)
        self._get_linear_system(A, b, dim)
        self._solve_linear_system(A, b, n - 1, dim)

    def _get_linear_system(self, A: List[float], b: List[float], dim: int):
        """
        构造线性方程组 A·[x,y]^T = b
        """
        x0 = self.beacon_meas[0].beacon_ptr.x
        y0 = self.beacon_meas[0].beacon_ptr.y
        d0 = self.beacon_meas[0].distance
        norm0 = x0*x0 + y0*y0

        for i in range(len(b)):
            xi = self.beacon_meas[i+1].beacon_ptr.x
            yi = self.beacon_meas[i+1].beacon_ptr.y
            di = self.beacon_meas[i+1].distance
            A[i*dim]     = 2*(xi - x0)
            A[i*dim + 1] = 2*(yi - y0)
            b[i] = d0*d0 - di*di - norm0 + (xi*xi + yi*yi)

    def _solve_linear_system(self, A: List[float], b: List[float], eqs: int, dim: int):
        """
        求解超定线性系统，采用伪逆矩阵法（仅适用于 dim=2）
        结果写回 self.xy
        """
        # 构造 A^T·A
        ATA = [0.0] * (dim*dim)
        for r in range(dim):
            for c in range(dim):
                ATA[r*dim + c] = sum(A[k*dim + r] * A[k*dim + c] for k in range(eqs))

        # 2x2 行列式及逆矩阵
        det = ATA[0]*ATA[3] - ATA[1]*ATA[2]
        inv = [ATA[3]/det, -ATA[1]/det, -ATA[2]/det, ATA[0]/det]

        # 伪逆 A⁺ = inv(ATA) · A^T
        Ap = [0.0] * (dim*eqs)
        for r in range(dim):
            for c in range(eqs):
                Ap[r*eqs + c] = sum(inv[r*dim + k] * A[c*dim + k] for k in range(dim))

        # 最终解 x = A⁺ · b
        sol = [sum(Ap[r*eqs + c] * b[c] for c in range(eqs)) for r in range(dim)]
        self.xy = sol


# 测试示例（可移到单独的 test 文件中）
if __name__ == "__main__":
    # 初始化
    trilat = Trilateration()
    beacons = [
        Beacon(54.69, 29.51, "(53580,22667,F7826DA6-4FA2-4E98-8024-BC5B71E0893E)"),
        Beacon(54.68, 29.51, "(49599,56896,F7826DA6-4FA2-4E98-8024-BC5B71E0893E)"),
        Beacon(49.05, 32.16, "(57506,19633,F7826DA6-4FA2-4E98-8024-BC5B71E0893E)")
    ]
    trilat.fill_location_beacons(beacons)

    measurements = [
        BeaconMeas("(53580,22667,F7826DA6-4FA2-4E98-8024-BC5B71E0893E)", -86.57, 4.47),
        BeaconMeas("(49599,56896,F7826DA6-4FA2-4E98-8024-BC5B71E0893E)", -90.80, 14.13),
        BeaconMeas("(57506,19633,F7826DA6-4FA2-4E98-8024-BC5B71E0893E)", -86.41, 15.85),
        BeaconMeas("22211,00231", -21.41, 15.85),
    ]
    trilat.update_measurements(measurements)
    err = trilat.calculate_coordinates()
    print(f"x = {trilat.get_x():.3f}, y = {trilat.get_y():.3f}, error = {err}")

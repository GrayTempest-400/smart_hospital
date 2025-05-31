class Beacon:
    def __init__(self):
        # 初始化 Beacon 对象，设置默认值
        self.mX = 0.0
        self.mY = 0.0
        self.mLocationId = 0
        self.mId = ""
        self.mName = ""
        self.mLocationName = ""

    def __copy__(self):
        # 复制构造函数
        beacon = Beacon()
        beacon.mX = self.mX
        beacon.mY = self.mY
        beacon.mId = self.mId
        beacon.mName = self.mName
        beacon.mLocationName = self.mLocationName
        beacon.mLocationId = self.mLocationId
        return beacon

    def set_beacon_id(self, beacon_id):
        # 设置 Beacon 的 ID
        self.mId = beacon_id

    def fill_data(self, x, y, beacon_id, name, location_name):
        # 填充 Beacon 数据
        self.mX = x
        self.mY = y
        self.mId = beacon_id
        self.mName = name
        self.mLocationName = location_name

    def get_id(self):
        # 获取 Beacon 的 ID
        return self.mId

    def get_x(self):
        # 获取 Beacon 的 x 坐标
        return self.mX

    def get_y(self):
        # 获取 Beacon 的 y 坐标
        return self.mY

    def set_x(self, x):
        # 设置 Beacon 的 x 坐标
        self.mX = x

    def set_y(self, y):
        # 设置 Beacon 的 y 坐标
        self.mY = y

    def set_location_name(self, name):
        # 设置 Beacon 的位置名称
        self.mLocationName += name

    def set_location_id(self, subloc_id):
        # 设置 Beacon 的位置 ID
        self.mLocationId = subloc_id

    def get_location_id(self):
        # 获取 Beacon 的位置 ID
        return self.mLocationId

    def __eq__(self, other):
        # 判断两个 Beacon 是否相等
        return self.mId == other.mId

    def __ne__(self, other):
        # 判断两个 Beacon 是否不相等
        return self.mId != other.mId


class IBeacon(Beacon):
    def __init__(self):
        # 初始化 IBeacon 对象，继承自 Beacon
        super().__init__()
        self.uuid = ""
        self.major = 0
        self.minor = 0

    def __copy__(self):
        # 复制构造函数
        ibeacon = IBeacon()
        ibeacon.uuid = self.uuid
        ibeacon.major = self.major
        ibeacon.minor = self.minor
        return ibeacon

    def get_uuid(self):
        # 获取 IBeacon 的 UUID
        return self.uuid

    def get_major(self):
        # 获取 IBeacon 的 major 值
        return self.major

    def get_minor(self):
        # 获取 IBeacon 的 minor 值
        return self.minor

    def set_major(self, major):
        # 设置 IBeacon 的 major 值
        self.major = major

    def set_minor(self, minor):
        # 设置 IBeacon 的 minor 值
        self.minor = minor

    def set_uuid(self, uuid):
        # 设置 IBeacon 的 UUID
        self.uuid = uuid


class BeaconMeas:
    def __init__(self):
        # 初始化 BeaconMeas 对象，设置默认值
        self.mBeaconPtr = None
        self.mRssi = float('-inf')
        self.mDistance = 0.0
        self.mBeaconId = ""

    def __init__(self, beacon, rssi, distance):
        # 带参数的构造函数
        self.mBeaconPtr = beacon
        self.mRssi = rssi
        self.mDistance = distance
        self.mBeaconId = beacon.get_id()

    def __copy__(self):
        # 复制构造函数
        beacon_meas = BeaconMeas()
        beacon_meas.mBeaconId = self.mBeaconId
        beacon_meas.mBeaconPtr = self.mBeaconPtr
        beacon_meas.mRssi = self.mRssi
        beacon_meas.mDistance = self.mDistance
        return beacon_meas

    def __del__(self):
        # 析构函数，清空 Beacon 指针
        self.mBeaconPtr = None

    def get_rssi(self):
        # 获取 BeaconMeas 的 RSSI 值
        return self.mRssi

    def get_distance(self):
        # 获取 BeaconMeas 的距离值
        return self.mDistance

    def set_rssi(self, rssi):
        # 设置 BeaconMeas 的 RSSI 值
        self.mRssi = rssi

    def set_distance(self, distance):
        # 设置 BeaconMeas 的距离值
        self.mDistance = distance

    def __lt__(self, other):
        # 比较两个 BeaconMeas 对象的距离，返回 True 如果当前对象距离更小
        return self.mDistance < other.mDistance

    def __gt__(self, other):
        # 比较两个 BeaconMeas 对象的距离，返回 True 如果当前对象距离更大
        return self.mDistance > other.mDistance

    def __eq__(self, other):
        # 判断两个 BeaconMeas 对象是否相等
        return self.mBeaconId == other.mBeaconId

    def __ne__(self, other):
        # 判断两个 BeaconMeas 对象是否不相等
        return self.mBeaconId != other.mBeaconId

    def set_beacon_ptr(self, beacon_ptr):
        # 设置 BeaconMeas 中的 Beacon 指针
        self.mBeaconPtr = beacon_ptr

    def get_beacon_ptr(self):
        # 获取 BeaconMeas 中的 Beacon 指针
        if self.mBeaconPtr is None:
            print(f"ERROR: beaconId = {self.get_beacon_id()} : mBeaconPtr == NULL")
        return self.mBeaconPtr

    def set_beacon_id(self, beacon_id):
        # 设置 BeaconMeas 的 Beacon ID
        self.mBeaconId = beacon_id

    def get_beacon_id(self):
        # 获取 BeaconMeas 的 Beacon ID
        return self.mBeaconId

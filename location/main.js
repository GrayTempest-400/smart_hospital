// 初始化地图
const map = L.map('map').setView([0, 0], 18);

// 添加一个简单的底图（这里使用空图，实际应用中可以使用室内地图）
L.tileLayer('', {
    attribution: 'Indoor Navigation'
}).addTo(map);

// 室内地图数据 - GeoJSON格式
const indoorMap = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "name": "Room 101",
                "type": "room"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [0, 0], [10, 0], [10, 10], [0, 10], [0, 0]
                ]]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "name": "Room 102",
                "type": "room"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [10, 0], [20, 0], [20, 10], [10, 10], [10, 0]
                ]]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "name": "Corridor",
                "type": "corridor",
                "walkable": true
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [0, 10], [20, 10], [20, 15], [0, 15], [0, 10]
                ]]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "name": "Staircase",
                "type": "staircase",
                "walkable": true
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [20, 0], [25, 0], [25, 15], [20, 15], [20, 0]
                ]]
            }
        }
    ]
};

// 将GeoJSON添加到地图
L.geoJSON(indoorMap, {
    style: function(feature) {
        return {
            fillColor: feature.properties.type === 'corridor' ? 'lightgray' : 
                      feature.properties.type === 'staircase' ? 'brown' : 'lightblue',
            weight: 1,
            opacity: 1,
            color: 'white',
            fillOpacity: 0.7
        };
    },
    onEachFeature: function(feature, layer) {
        if (feature.properties && feature.properties.name) {
            layer.bindPopup(feature.properties.name);
        }
    }
}).addTo(map);

// 调整地图视图以显示整个室内地图
map.fitBounds(L.geoJSON(indoorMap).getBounds());

// 路径规划相关变量
let startPoint = null;
let endPoint = null;
let pathLayer = null;

// 设置起点和终点的标记
const startIcon = L.icon({
    iconUrl: 'https://cdn.rawgit.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34]
});

const endIcon = L.icon({
    iconUrl: 'https://cdn.rawgit.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34]
});

// 控制按钮事件
document.getElementById('setStart').addEventListener('click', function() {
    map.on('click', setStart);
});

document.getElementById('setEnd').addEventListener('click', function() {
    map.on('click', setEnd);
});

document.getElementById('clear').addEventListener('click', clearPath);

function setStart(e) {
    if (startPoint) {
        map.removeLayer(startPoint);
    }
    startPoint = L.marker(e.latlng, {icon: startIcon}).addTo(map)
        .bindPopup("起点").openPopup();
    map.off('click', setStart);
    
    if (startPoint && endPoint) {
        calculatePath();
    }
}

function setEnd(e) {
    if (endPoint) {
        map.removeLayer(endPoint);
    }
    endPoint = L.marker(e.latlng, {icon: endIcon}).addTo(map)
        .bindPopup("终点").openPopup();
    map.off('click', setEnd);
    
    if (startPoint && endPoint) {
        calculatePath();
    }
}

function clearPath() {
    if (pathLayer) {
        map.removeLayer(pathLayer);
        pathLayer = null;
    }
    if (startPoint) {
        map.removeLayer(startPoint);
        startPoint = null;
    }
    if (endPoint) {
        map.removeLayer(endPoint);
        endPoint = null;
    }
}

// A*算法实现
function calculatePath() {
    if (!startPoint || !endPoint) return;
    
    // 清除现有路径
    clearPath();
    
    // 创建网格表示 (简化版，实际应用中需要更精细的网格)
    const gridSize = 1; // 网格大小
    const bounds = L.geoJSON(indoorMap).getBounds();
    const gridWidth = Math.ceil((bounds.getEast() - bounds.getWest()) / gridSize);
    const gridHeight = Math.ceil((bounds.getNorth() - bounds.getSouth()) / gridSize);
    
    // 创建网格并标记可通行区域
    const grid = [];
    for (let y = 0; y < gridHeight; y++) {
        grid[y] = [];
        for (let x = 0; x < gridWidth; x++) {
            const lat = bounds.getSouth() + y * gridSize;
            const lng = bounds.getWest() + x * gridSize;
            const point = L.latLng(lat, lng);
            
            // 检查点是否在可通行区域 (走廊或楼梯)
            let walkable = false;
            L.geoJSON(indoorMap, {
                filter: function(feature) {
                    return feature.properties.walkable === true;
                },
                pointToLayer: function(point, latlng) {
                    return null;
                }
            }).eachLayer(function(layer) {
                if (layer.getBounds().contains(point) || 
                    (layer instanceof L.Polygon && pointInPolygon(point, layer.getLatLngs()[0]))) {
                    walkable = true;
                }
            });
            
            grid[y][x] = walkable ? 0 : 1; // 0 = 可通行, 1 = 障碍物
        }
    }
    
    // 转换起点和终点为网格坐标
    const startX = Math.floor((startPoint.getLatLng().lng - bounds.getWest()) / gridSize);
    const startY = Math.floor((startPoint.getLatLng().lat - bounds.getSouth()) / gridSize);
    const endX = Math.floor((endPoint.getLatLng().lng - bounds.getWest()) / gridSize);
    const endY = Math.floor((endPoint.getLatLng().lat - bounds.getSouth()) / gridSize);
    
    // 确保起点和终点在可通行区域
    if (grid[startY][startX] !== 0 || grid[endY][endX] !== 0) {
        alert("起点或终点位于不可通行区域!");
        return;
    }
    
    // A*算法
    class Node {
        constructor(x, y) {
            this.x = x;
            this.y = y;
            this.g = 0; // 从起点到当前节点的成本
            this.h = 0; // 从当前节点到终点的启发式估计成本
            this.f = 0; // g + h
            this.parent = null;
        }
    }
    
    function heuristic(node, endNode) {
        // 曼哈顿距离
        return Math.abs(node.x - endNode.x) + Math.abs(node.y - endNode.y);
    }
    
    function getNeighbors(node, grid) {
        const neighbors = [];
        const {x, y} = node;
        
        // 上下左右四个方向
        const directions = [
            [0, 1], [1, 0], [0, -1], [-1, 0]
        ];
        
        for (const [dx, dy] of directions) {
            const newX = x + dx;
            const newY = y + dy;
            
            // 检查边界和可通行性
            if (newX >= 0 && newX < grid[0].length && 
                newY >= 0 && newY < grid.length && 
                grid[newY][newX] === 0) {
                neighbors.push(new Node(newX, newY));
            }
        }
        
        return neighbors;
    }
    
    const openList = [];
    const closedList = [];
    const startNode = new Node(startX, startY);
    const endNode = new Node(endX, endY);
    
    openList.push(startNode);
    
    while (openList.length > 0) {
        // 找到f值最小的节点
        let currentIndex = 0;
        for (let i = 1; i < openList.length; i++) {
            if (openList[i].f < openList[currentIndex].f) {
                currentIndex = i;
            }
        }
        
        const currentNode = openList[currentIndex];
        
        // 如果到达终点
        if (currentNode.x === endNode.x && currentNode.y === endNode.y) {
            const path = [];
            let current = currentNode;
            while (current !== null) {
                path.push([current.x, current.y]);
                current = current.parent;
            }
            path.reverse();
            
            // 将路径转换为LatLng坐标并显示
            const latLngs = path.map(([x, y]) => {
                const lng = bounds.getWest() + x * gridSize + gridSize/2;
                const lat = bounds.getSouth() + y * gridSize + gridSize/2;
                return L.latLng(lat, lng);
            });
            
            pathLayer = L.polyline(latLngs, {color: 'blue', weight: 3}).addTo(map);
            return;
        }
        
        // 将当前节点移到closedList
        openList.splice(currentIndex, 1);
        closedList.push(currentNode);
        
        // 检查邻居
        const neighbors = getNeighbors(currentNode, grid);
        for (const neighbor of neighbors) {
            // 如果邻居在closedList中，跳过
            if (closedList.some(node => node.x === neighbor.x && node.y === neighbor.y)) {
                continue;
            }
            
            // 计算g值
            const gScore = currentNode.g + 1;
            
            // 检查是否找到了更好的路径
            const openNode = openList.find(node => node.x === neighbor.x && node.y === neighbor.y);
            if (!openNode || gScore < openNode.g) {
                neighbor.g = gScore;
                neighbor.h = heuristic(neighbor, endNode);
                neighbor.f = neighbor.g + neighbor.h;
                neighbor.parent = currentNode;
                
                if (!openNode) {
                    openList.push(neighbor);
                }
            }
        }
    }
    
    // 如果没有找到路径
    alert("无法找到路径!");
}

// 辅助函数：检查点是否在多边形内
function pointInPolygon(point, polygon) {
    let inside = false;
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
        const xi = polygon[i].lng, yi = polygon[i].lat;
        const xj = polygon[j].lng, yj = polygon[j].lat;
        
        const intersect = ((yi > point.lat) !== (yj > point.lat))
            && (point.lng < (xj - xi) * (point.lat - yi) / (yj - yi) + xi);
        if (intersect) inside = !inside;
    }
    return inside;
}
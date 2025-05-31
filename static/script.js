// 存储各科室排队信息的对象
const queues = {};

// 存储叫号记录
const calledRecords = [];

// 初始化科室信息
const departments = [
    "儿科", "耳鼻咽喉科", "风湿免疫科", "妇产科", "感染科 传染科",
    "骨科", "呼吸内科", "乳腺外科", "精神心理科", "口腔科",
    "泌尿外科", "内分泌科", "皮肤科", "普通内科", "普外科",
    "神经内科", "神经外科", "疼痛科 麻醉科", "消化内科", "心血管内科",
    "性病科", "血液科", "眼科", "疫苗科", "影像检验科",
    "肿瘤科", "肛肠外科", "中医科", "胸外科", "烧伤科",
    "整形科", "肝胆外科", "急诊科", "头颈外科"
];

// 初始化每个科室的排队信息
departments.forEach(department => {
    queues[department] = {
        count: 0,                // 当前科室排队人数
        patients: [],            // 当前科室的所有患者姓名
        joinTimeList: [],        // 记录患者的入队时间
        patientTimers: []        // 每个患者的计时器
    };
});

// 获取页面元素
const queueDepartmentSelect = document.getElementById('queue-department-select');
const queuePatientNameInput = document.getElementById('queue-patient-name');
const queueButton = document.getElementById('queue-button');
const queueTableBody = document.getElementById('queue-table').getElementsByTagName('tbody')[0];
const detailedQueueTableBody = document.getElementById('detailed-queue-table').getElementsByTagName('tbody')[0];

// 搜索框
const searchPatientNameInput = document.getElementById('search-patient-name');
const searchButton = document.getElementById('search-button');

// 叫号记录表格
const calledTableBody = document.getElementById('called-table').getElementsByTagName('tbody')[0];

// 自动化设置科室选择
const urlParams = new URLSearchParams(window.location.search);
const prediction = urlParams.get('prediction'); // 获取 URL 参数中的 prediction 值

if (prediction) {
    const departmentIndex = departments.indexOf(prediction); // 获取 prediction 对应的科室索引
    if (departmentIndex !== -1) {
        queueDepartmentSelect.value = departments[departmentIndex]; // 设置为对应的科室选项
    } else {
        console.warn(`未找到与 "${prediction}" 对应的科室`);
    }
}

// 排队按钮点击事件处理
queueButton.addEventListener('click', function () {
    const selectedDepartment = queueDepartmentSelect.value; // 获取用户选择的科室
    const patientName = queuePatientNameInput.value.trim(); // 获取患者姓名，去掉首尾空格

    // 校验输入
    if (!selectedDepartment) {
        alert('请选择科室');
        return;
    }
    if (!patientName) {
        alert('请输入患者姓名');
        return;
    }

    // 校验科室有效性
    const departmentIndex = departments.indexOf(selectedDepartment);
    if (departmentIndex === -1) {
        alert('科室信息无效');
        return;
    }

    // 将患者添加到对应科室的排队队列中，并记录入队时间
    queues[selectedDepartment].patients.push(patientName);
    queues[selectedDepartment].joinTimeList.push(Date.now());
    queues[selectedDepartment].count++;

    // 为新加入的患者创建计时器
    const timerInterval = setInterval(() => {
        updateDetailedQueueTable();
    }, 1000); // 每秒更新一次

    queues[selectedDepartment].patientTimers.push(timerInterval);

    // 清空输入框
    queuePatientNameInput.value = '';

    // 更新表格显示
    updateQueueTable();
    updateDetailedQueueTable();

    // 提示跳转到寻路网站
    if (confirm("您已排队，是否跳转到寻路网站？")) {
        window.location.href = `/navigate?department=${encodeURIComponent(departments[departmentIndex])}`; // 跳转到寻路页面并传递科室信息
    }
});

// 更新科室排队表格
function updateQueueTable() {
    queueTableBody.innerHTML = ''; // 清空表格

    Object.entries(queues).forEach(([department, info]) => {
        if (info.count > 0) {
            const row = document.createElement('tr');
            const departmentCell = document.createElement('td');
            departmentCell.textContent = department;

            const countCell = document.createElement('td');
            countCell.textContent = info.count;

            const estimatedTimeCell = document.createElement('td');
            const estimatedTime = info.count * 30; // 预计排队时间（每个患者固定30秒）

            estimatedTimeCell.textContent = estimatedTime;

            row.appendChild(departmentCell);
            row.appendChild(countCell);
            row.appendChild(estimatedTimeCell);

            queueTableBody.appendChild(row);
        }
    });
}

// 更新详细排队时间表
function updateDetailedQueueTable() {
    detailedQueueTableBody.innerHTML = ''; // 清空表格

    Object.entries(queues).forEach(([department, info]) => {
        info.patients.forEach((patientName, index) => {
            const row = document.createElement('tr');
            
            const departmentCell = document.createElement('td');
            departmentCell.textContent = department;

            const patientCell = document.createElement('td');
            patientCell.textContent = patientName;

            const queueTimeCell = document.createElement('td');
            const queueTime = Math.floor((Date.now() - info.joinTimeList[index]) / 1000); // 计算排队时间（真实时间）
            queueTimeCell.textContent = queueTime;

            const joinTimeCell = document.createElement('td');
            joinTimeCell.textContent = formatTime(info.joinTimeList[index]);

            // 根据患者在队列中的位置，动态计算预计排队时间
            const estimatedTimeCell = document.createElement('td');
            const estimatedTime = (index + 1) * 30;  // 预计排队时间，第一位患者为30秒，第二位为60秒，以此类推767
            estimatedTimeCell.textContent = estimatedTime;

            // 结束时间：入队时间 + 预计排队时间
            const endTimeCell = document.createElement('td');
            const endTime = new Date(info.joinTimeList[index] + (estimatedTime * 1000));
            endTimeCell.textContent = formatTime(endTime);

            row.appendChild(departmentCell);
            row.appendChild(patientCell);
            row.appendChild(queueTimeCell);
            row.appendChild(joinTimeCell);
            row.appendChild(estimatedTimeCell);
            row.appendChild(endTimeCell);

            detailedQueueTableBody.appendChild(row);
        });
    });
}

// 格式化时间戳
function formatTime(timestamp) {
    const date = new Date(timestamp);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}

// 搜索患者排队信息
searchButton.addEventListener('click', function () {
    const searchName = searchPatientNameInput.value.trim();
    if (!searchName) {
        alert('请输入患者姓名');
        return;
    }

    let found = false;

    // 遍历所有科室寻找匹配的患者
    Object.entries(queues).forEach(([department, info]) => {
        info.patients.forEach((patientName, index) => {
            if (patientName === searchName) {
                found = true;
                const queueTime = Math.floor((Date.now() - info.joinTimeList[index]) / 1000);
                const estimatedTime = (index + 1) * 30; // 根据患者位置计算预计排队时间
                const endTime = new Date(info.joinTimeList[index] + estimatedTime * 1000);
                alert(`患者: ${patientName}\n科室: ${department}\n排队时间: ${queueTime}秒\n预计排队时间: ${estimatedTime}秒\n结束时间: ${formatTime(endTime)}`);
            }
        });
    });

    if (!found) {
        alert('未找到匹配的患者信息');
    }
});

// 叫号功能：定时检查是否有患者的排队时间到了
function checkQueueTime() {
    Object.entries(queues).forEach(([department, info]) => {
        if (info.count > 0) {
            const patientName = info.patients[0];
            const joinTime = info.joinTimeList[0];
            const queueTime = Math.floor((Date.now() - joinTime) / 1000); // 计算排队时间

            if (queueTime >= 30) { // 排队超过 30 秒就开始叫号
                // 发出叫号
                alert(`请注意：患者 ${patientName} 在 ${department} 科的排队时间已到，开始叫号！`);

                // 显示询问是否跳转到寻路网站
                if (confirm(`患者 ${patientName} 的排队时间已到，是否跳转到 ${department} 科的寻路页面？`)) {
                    window.location.href = `/navigate?department=${encodeURIComponent(department)}`;
                }

                // 将该患者从排队队列中移除
                queues[department].patients.shift();
                queues[department].joinTimeList.shift();
                queues[department].count--;

                // 清除计时器
                const timerInterval = queues[department].patientTimers.shift();
                clearInterval(timerInterval);

                // 记录叫号信息
                calledRecords.push({
                    time: new Date(),
                    department: department,
                    patientName: patientName,
                    reserved: false
                });

                // 更新叫号记录表格
                updateCalledTable();

                // 更新排队表格
                updateQueueTable();
                updateDetailedQueueTable();
            }
        }
    });
}

// 更新叫号记录表格
function updateCalledTable() {
    calledTableBody.innerHTML = ''; // 清空表格

    calledRecords.forEach(record => {
        const row = document.createElement('tr');

        const timeCell = document.createElement('td');
        timeCell.textContent = formatTime(record.time);

        const departmentCell = document.createElement('td');
        departmentCell.textContent = record.department;

        const patientNameCell = document.createElement('td');
        patientNameCell.textContent = record.patientName;

        const reservedCell = document.createElement('td');
        

        row.appendChild(timeCell);
        row.appendChild(departmentCell);
        row.appendChild(patientNameCell);
        row.appendChild(reservedCell);

        calledTableBody.appendChild(row);
    });
}

// 每秒钟检查排队时间，自动叫号
setInterval(checkQueueTime, 1000);

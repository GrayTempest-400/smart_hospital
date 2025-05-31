document.getElementById('confirm-button').addEventListener('click', function() {
    const selectedDepartment = document.getElementById('department-select').value;
    const img = document.getElementById('department-pic');

    if (selectedDepartment) {
        img.src = 'static/img/' + selectedDepartment + '.png'; // 根据选择设置图片路径
        img.style.display = 'block'; // 显示图片
    } else {
        img.style.display = 'none'; // 隐藏图片
        alert("请先选择科室。");
    }
});

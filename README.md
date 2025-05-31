# smart_hospital
智能医院系统 by sss.Beyonder,monooo,QYSN
#前端部分
vue版本文件多，只能传网盘
医院管理系统.zip
链接: https://pan.baidu.com/s/1PQSChYzqQ6GEwDMieGqmfA 提取码: 1234




github主页的是pythonflask后端+bert文本分类（科室预测）+html前端的版本。
![image](https://github.com/user-attachments/assets/bb256159-5e46-4143-94fe-335cbcfa3387)
ai助手接入deepseek api可以在bert.html的245行添加您的apikey密钥
![image](https://github.com/user-attachments/assets/defc1b02-dae0-401f-947e-41ef54b3d60f)
主输入框为bert模型预测，bert模型预测症状描述要长一些才能准确
![image](https://github.com/user-attachments/assets/1dc432a7-8ee9-4b8c-9110-eaf071e41bba)
排队界面
![image](https://github.com/user-attachments/assets/a4b14ba0-7813-4a94-b426-bca19eca79f1)
导航界面

网站采用传参方式，在各个界面自动填入bert模型预测的科室

Vue版本运行步骤

```bash
#启动API服务：
uvicorn api_support:app --reload
```
进入前端目录：

```bash
cd \医院管理系统\HospitalVue
#运行前端：

npm run serve
node server.js
```
```bash
#若报错则使用：

set NODE_OPTIONS=--openssl-legacy-provider
npm run serve
```

```bash
#启动后端：

cd \医院管理系统\medical-master
mvn spring-boot:run
```
测试账号
角色	账号	密码
患者	1534590	password
管理员	201701	admin
医生	201900	1234

具体看数据库文件.sql

患者：
![image](https://github.com/user-attachments/assets/85fa91c5-be4d-4e6f-8372-b87e57322975)
登入页
![image](https://github.com/user-attachments/assets/2dfd62c8-8210-40ce-8e99-b004b6c4ac88)
首页
![image](https://github.com/user-attachments/assets/59c80f9c-39e6-4967-93fe-5f25153803e8)
科室推荐
![image](https://github.com/user-attachments/assets/f9773ccb-135b-4798-b89d-a8c18f3f9782)
挂号
其他不重要的省略
管理员：
![image](https://github.com/user-attachments/assets/2a1becb1-9cd9-43f8-9ae9-2ab7c62dc1c2)
首页
![image](https://github.com/user-attachments/assets/76640ce8-7708-47e6-895f-99433e002f14)
数据分析
![image](https://github.com/user-attachments/assets/12eff1d4-41c5-4556-b7c2-a24aff49f518)
![image](https://github.com/user-attachments/assets/c8e1e1b4-9cf7-4a26-9126-ee59784cd35b)
![image](https://github.com/user-attachments/assets/20a3c039-0efc-4c03-b37f-50b517fe5a2e)
![image](https://github.com/user-attachments/assets/0f81c63f-7433-48a4-b466-7dc1122036ae)
![image](https://github.com/user-attachments/assets/3494fa9f-54b0-4269-a5cb-83929db032be)
![image](https://github.com/user-attachments/assets/4dc81be7-aafe-4b8a-80a3-2f084503d92c)
![image](https://github.com/user-attachments/assets/d99f614e-5808-4e0e-86b5-f686743b3aef)
其他界面

医生：
![image](https://github.com/user-attachments/assets/f1269f75-45a4-42db-8e0e-9c14c0fe6c19)
![image](https://github.com/user-attachments/assets/f32e1101-3aa9-4d57-85e5-3edc8b469574)

地图创建工具maptool界面
![image](https://github.com/user-attachments/assets/fecc3198-88f1-4692-9c04-cbdf60bce41c)
map_web.py
png转栅格化地图，基于opencv图像识别，yml格式栅格地图输出0表示通路1表示障碍
png图像需黑白化，黑色当障碍白当通路
在地图上用绿色点一个点代表起点，红色点一个点代表终点，具体看源代码
![path_image](https://github.com/user-attachments/assets/eb359dbf-e44f-4a2c-8862-bf3860f4dd37)
![image](https://github.com/user-attachments/assets/00b4e0fd-d60f-48c0-b3e5-30bb8c6c79d5)


室内定位看location文件夹
AOA.py为定位展示界面
硬件要购买爱蓝信的uwbAOA硬件
![image](https://github.com/user-attachments/assets/81a426f3-03cf-479c-a2b7-f3763f3df25d)
其他的beacon定位未进行测试，不知道能不能用
imu pdr行人行位推算定位为江科的开源代码，硬件为stm32103c8t6+mpu6050+oled显示屏



优化md文件外观

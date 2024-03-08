## 部署方式

## 部署Lambda
- 在cdk部署所在的Ec2中，执行如下命令部署
```bash
sh deploy.sh {region} {agent_tool_name} #for example agent_tool_name = 'airline'
```

## 数据摄入脚本

- 连接QAChatDeployStack/Ec2Stack/ProxyInstance, 执行如下脚本进行进行数据摄入。
  + 连接mysql，连接参数请从上一步部署的Lambda的环境变量中进行获取
  + 需要指定本地数据文件，需要上传到这个ec2上
```bash
sudo yum -y install python-pip
pip3 install pymysql pandas sqlalchemy

#注入数据
bash ingest_data.sh ${region} 
#如何想要清空数据，可以执行如下语句
bash ingest_data.sh ${region} "truncate"
```



## 测试lambda. 进入lambda控制台，使用如下参数，进行测试
```bash
#case 1
{"param" : { "flightno" : "3U" }, "query" : "3U 的称谓规则是什么"}

#case 2
{"param" : { "flightno" : "BK" }, "query" : "保盛是否可以预定航司BK的机票"}
```

## 添加fewshot
使用airline.example作为fel shot ,在知识库web界面添加fewshot
# Kubernetes Monitoring Scripts for Gomall

## 概述 (Overview)

这些脚本用于自动监控 Gomall 微服务应用的 Kubernetes 部署状态，并执行基础的 API 测试。

These scripts automatically monitor the Kubernetes deployment status of the Gomall microservices application and perform basic API tests.

## 功能特性 (Features)

- ✅ **Pod 状态检查** - 自动检查所有 Pod 是否处于 Running 状态
- 🧪 **API 测试** - 对所有微服务执行基础 API 测试
- 📊 **服务信息** - 显示服务配置和端点信息
- 🔄 **连续监控** - 支持定时重复检查
- 🎨 **彩色输出** - 美观的表格和状态指示
- ⚙️ **可配置** - 通过 YAML 文件配置监控参数

## 安装依赖 (Installation)

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 或者
pip install kubernetes requests colorama tabulate pyyaml
```

## 使用方法 (Usage)

### 1. 完整健康检查 (Full Health Check)
```bash
python k8s_monitor.py
```

### 2. 仅检查 Pod 状态 (Pod Status Only)
```bash
python k8s_monitor.py --pods-only
```

### 3. 仅执行 API 测试 (API Tests Only)
```bash
python k8s_monitor.py --api-only
```

### 4. 显示服务信息 (Service Information)
```bash
python k8s_monitor.py --services
```

### 5. 快速检查 (Quick Check)
```bash
python run_tests.py quick
```

### 6. 连续监控 (Continuous Monitoring)
```bash
# 每 60 秒检查一次
python run_tests.py continuous

# 每 30 秒检查一次
python run_tests.py continuous 30
```

## 脚本说明 (Script Description)

### k8s_monitor.py
主要监控脚本，包含以下功能：
- `check_pods_health()` - 检查 Pod 健康状态
- `run_api_tests()` - 执行 API 测试
- `get_service_info()` - 获取服务信息
- `run_full_check()` - 运行完整检查

### run_tests.py
测试运行器，支持：
- 单次快速检查
- 连续监控模式

### monitor_config.yaml
配置文件，包含：
- 服务端口配置
- 健康检查端点
- 监控阈值设置

## 输出示例 (Sample Output)

### Pod 状态检查 (Pod Status Check)
```
🔍 Checking Pod Status...
================================================================================
┌────────┬─────────────────────────────────┬─────────────┬─────────┬─────────────┬───────┐
│ Status │ Pod Name                        │ Phase       │ Ready   │ Restarts    │ Age   │
├────────┼─────────────────────────────────┼─────────────┼─────────┼─────────────┼───────┤
│ ✅     │ cart-858fff8fc7-t44ht           │ Running     │ 1/1     │ No restarts │ 13h   │
│ ✅     │ frontend-9b55b5b68-dfwbx        │ Running     │ 1/1     │ No restarts │ 13h   │
│ ✅     │ gomall-mysql-0                  │ Running     │ 1/1     │ No restarts │ 13h   │
└────────┴─────────────────────────────────┴─────────────┴─────────┴─────────────┴───────┘

🎉 All 11 pods are healthy and running!
```

### API 测试结果 (API Test Results)
```
🧪 Running API Tests...
================================================================================
┌────────┬───────────┬────────┬─────────────────┬───────────────┐
│ Status │ Service   │ Result │ Endpoint        │ Response Time │
├────────┼───────────┼────────┼─────────────────┼───────────────┤
│ ✅     │ frontend  │ PASS   │ :8080/          │ 0.234s       │
│ ✅     │ cart      │ PASS   │ :8883/          │ 0.156s       │
│ ✅     │ checkout  │ PASS   │ :8884/          │ 0.178s       │
└────────┴───────────┴────────┴─────────────────┴───────────────┘

🎉 All API tests passed!
```

## 故障排除 (Troubleshooting)

### 常见问题 (Common Issues)

1. **Kubeconfig 文件未找到**
   ```bash
   # 确保 kind-kubeconfig.yaml 文件存在
   ls -la kind-kubeconfig.yaml
   ```

2. **端口转发失败**
   ```bash
   # 检查 kubectl 是否正常工作
   kubectl get pods
   ```

3. **API 测试失败**
   ```bash
   # 检查服务是否正在运行
   kubectl get services
   kubectl logs deployment/service-name
   ```

## 自定义配置 (Customization)

编辑 `monitor_config.yaml` 文件来自定义：
- 监控的服务列表
- 健康检查端点
- 超时和重试设置
- 告警阈值

## 集成到 CI/CD (CI/CD Integration)

```bash
# 在 CI/CD 管道中使用
python run_tests.py quick
if [ $? -eq 0 ]; then
    echo "All tests passed"
else
    echo "Tests failed"
    exit 1
fi
```

## 许可证 (License)

本项目采用 MIT 许可证。 
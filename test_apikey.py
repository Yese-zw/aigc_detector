#!/usr/bin/env python3
"""
API Key 功能测试脚本
用于测试 API Key 的创建、使用和管理
"""
import requests
import json
import sys


BASE_URL = "http://localhost:8001"


def print_section(title):
    """打印分节标题"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_response(response):
    """美化打印响应"""
    try:
        data = response.json()
        print(f"状态码: {response.status_code}")
        print(f"响应:\n{json.dumps(data, ensure_ascii=False, indent=2)}")
    except:
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")


def test_create_apikey():
    """测试创建 API Key"""
    print_section("1. 创建 API Key")
    
    url = f"{BASE_URL}/apikey/create"
    data = {
        "name": "测试密钥",
        "quota": 10000,
        "description": "用于测试的 API Key"
    }
    
    print(f"请求: POST {url}")
    print(f"数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
    
    response = requests.post(url, json=data)
    print_response(response)
    
    if response.status_code == 200:
        api_key = response.json()["data"]["key"]
        print(f"\n✅ 创建成功！")
        print(f"API Key: {api_key}")
        return api_key
    else:
        print(f"\n❌ 创建失败！")
        return None


def test_list_apikeys():
    """测试获取 API Key 列表"""
    print_section("2. 获取 API Key 列表")
    
    url = f"{BASE_URL}/apikey/list"
    print(f"请求: GET {url}")
    
    response = requests.get(url)
    print_response(response)
    
    if response.status_code == 200:
        total = response.json()["total"]
        print(f"\n✅ 获取成功！共 {total} 个 API Key")
    else:
        print(f"\n❌ 获取失败！")


def test_get_apikey_info(api_key):
    """测试获取 API Key 详细信息"""
    print_section("3. 获取 API Key 详细信息")
    
    url = f"{BASE_URL}/apikey/info/{api_key}"
    print(f"请求: GET {url}")
    
    response = requests.get(url)
    print_response(response)
    
    if response.status_code == 200:
        print(f"\n✅ 获取成功！")
    else:
        print(f"\n❌ 获取失败！")


def test_detector_without_apikey():
    """测试不带 API Key 的检测（应该失败）"""
    print_section("4. 测试不带 API Key 的检测（预期失败）")
    
    url = f"{BASE_URL}/ai/detector"
    data = {
        "text": "这是一段测试文本",
        "language": "zh"
    }
    
    print(f"请求: POST {url}")
    print(f"数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
    print("请求头: (没有 X-API-Key)")
    
    response = requests.post(url, json=data)
    print_response(response)
    
    if response.status_code == 401:
        print(f"\n✅ 按预期返回 401 Unauthorized")
    else:
        print(f"\n⚠️  未返回预期的 401 状态码")


def test_detector_with_apikey(api_key):
    """测试带 API Key 的检测"""
    print_section("5. 测试带 API Key 的检测")
    
    url = f"{BASE_URL}/ai/detector"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key
    }
    data = {
        "text": "这是一段测试文本，用于检测是否为AI生成内容。",
        "language": "zh"
    }
    
    print(f"请求: POST {url}")
    print(f"请求头: X-API-Key: {api_key[:20]}...")
    print(f"数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
    
    response = requests.post(url, json=data, headers=headers)
    print_response(response)
    
    if response.status_code == 200:
        result = response.json()
        if "quota_info" in result:
            print(f"\n✅ 检测成功！")
            print(f"使用额度: {result['quota_info']['used']}")
            print(f"剩余额度: {result['quota_info']['remaining']}")
        else:
            print(f"\n✅ 检测成功！（但未返回额度信息）")
    else:
        print(f"\n❌ 检测失败！")


def test_get_usage_stats(api_key):
    """测试获取使用统计"""
    print_section("6. 获取使用统计")
    
    url = f"{BASE_URL}/apikey/usage/{api_key}"
    print(f"请求: GET {url}")
    
    response = requests.get(url)
    print_response(response)
    
    if response.status_code == 200:
        stats = response.json()["data"]
        print(f"\n✅ 获取成功！")
        print(f"已用额度: {stats['used_quota']}")
        print(f"剩余额度: {stats['remaining_quota']}")
        print(f"使用率: {stats['usage_percentage']}%")
    else:
        print(f"\n❌ 获取失败！")


def test_update_apikey(api_key):
    """测试更新 API Key（增加额度）"""
    print_section("7. 测试更新 API Key（增加额度）")
    
    url = f"{BASE_URL}/apikey/update/{api_key}?add_quota=5000"
    print(f"请求: PUT {url}")
    
    response = requests.put(url)
    print_response(response)
    
    if response.status_code == 200:
        print(f"\n✅ 更新成功！已增加 5000 额度")
    else:
        print(f"\n❌ 更新失败！")


def test_disable_apikey(api_key):
    """测试禁用 API Key"""
    print_section("8. 测试禁用 API Key")
    
    url = f"{BASE_URL}/apikey/update/{api_key}?is_active=false"
    print(f"请求: PUT {url}")
    
    response = requests.put(url)
    print_response(response)
    
    if response.status_code == 200:
        print(f"\n✅ 禁用成功！")
    else:
        print(f"\n❌ 禁用失败！")


def test_detector_with_disabled_apikey(api_key):
    """测试使用禁用的 API Key 检测（应该失败）"""
    print_section("9. 测试使用禁用的 API Key 检测（预期失败）")
    
    url = f"{BASE_URL}/ai/detector"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key
    }
    data = {
        "text": "测试文本",
        "language": "zh"
    }
    
    print(f"请求: POST {url}")
    print(f"使用已禁用的 API Key")
    
    response = requests.post(url, json=data, headers=headers)
    print_response(response)
    
    if response.status_code == 403:
        print(f"\n✅ 按预期返回 403 Forbidden")
    else:
        print(f"\n⚠️  未返回预期的 403 状态码")


def test_enable_apikey(api_key):
    """测试启用 API Key"""
    print_section("10. 测试启用 API Key")
    
    url = f"{BASE_URL}/apikey/update/{api_key}?is_active=true"
    print(f"请求: PUT {url}")
    
    response = requests.put(url)
    print_response(response)
    
    if response.status_code == 200:
        print(f"\n✅ 启用成功！")
    else:
        print(f"\n❌ 启用失败！")


def test_delete_apikey(api_key):
    """测试删除 API Key"""
    print_section("11. 测试删除 API Key")
    
    url = f"{BASE_URL}/apikey/delete/{api_key}"
    print(f"请求: DELETE {url}")
    
    response = requests.delete(url)
    print_response(response)
    
    if response.status_code == 200:
        print(f"\n✅ 删除成功！")
    else:
        print(f"\n❌ 删除失败！")


def main():
    """主测试流程"""
    print("\n" + "🚀" * 35)
    print("  API Key 功能完整测试")
    print("🚀" * 35)
    
    print(f"\n服务地址: {BASE_URL}")
    print("确保服务已启动！")
    
    try:
        # 测试服务是否可用
        response = requests.get(f"{BASE_URL}/ping", timeout=3)
        if response.status_code != 200:
            print("\n❌ 服务未响应，请先启动服务！")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ 无法连接到服务: {str(e)}")
        print("请确保服务已启动（运行: python run.py）")
        sys.exit(1)
    
    # 执行测试
    api_key = test_create_apikey()
    if not api_key:
        print("\n❌ 创建 API Key 失败，测试终止")
        sys.exit(1)
    
    test_list_apikeys()
    test_get_apikey_info(api_key)
    test_detector_without_apikey()
    test_detector_with_apikey(api_key)
    test_get_usage_stats(api_key)
    test_update_apikey(api_key)
    test_disable_apikey(api_key)
    test_detector_with_disabled_apikey(api_key)
    test_enable_apikey(api_key)
    
    # 询问是否删除
    print("\n" + "=" * 70)
    answer = input(f"\n是否删除测试用的 API Key ({api_key[:20]}...)? (y/N): ")
    if answer.lower() == 'y':
        test_delete_apikey(api_key)
    else:
        print(f"\n✅ API Key 已保留，你可以继续使用它")
        print(f"API Key: {api_key}")
    
    print("\n" + "✅" * 35)
    print("  测试完成！")
    print("✅" * 35 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ 测试出错: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


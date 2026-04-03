# import requests
#
# # 接口地址
# url = "https://xrzbk.lanbeike.online/document/direct-upload/policy"
#
# # 请求体数据
# payload = {
#     "filename": "rwea.docx",
#     "fileSize": 14504,
#     "contentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
# }
#
# # 请求头（添加 Authorization 认证）
# headers = {
#     "Content-Type": "application/json",
#     "Authorization": "Bearer eyJhbGciOiJIUzM4NCJ9.eyJsb2dpblV1aWQiOiI4ZTA5MWFkYy1iNmNmLTRmMzYtOWJjZi1jMzlhYjgwOTMzNzUiLCJ1c2VyVHlwZSI6InVzZXIiLCJ1c2VySWQiOjc2LCJ1c2VybmFtZSI6IueUqOaItzJVM1RGOTQ4Iiwic3ViIjoiNzYiLCJpYXQiOjE3NzMwNzAzNDksImV4cCI6MTc3MzExMzU0OX0.Z-VkdqlTCvHW6_MXBOnR2p7l9iIsWnm8hyqngw7PjBlTohYVQmJ9UIm0RnGZbEqR"
# }
#
# try:
#     # 发送POST请求
#     response = requests.post(
#         url=url,
#         json=payload,
#         headers=headers,
#         timeout=10  # 10秒超时保护
#     )
#
#     # 打印响应信息
#     print(f"响应状态码: {response.status_code}")
#     print("响应内容:")
#     try:
#         # 优先解析JSON格式响应
#         response_json = response.json()
#         # 格式化输出JSON，更易读
#         import json
#
#         print(json.dumps(response_json, ensure_ascii=False, indent=2))
#     except ValueError:
#         # 非JSON响应打印原始文本
#         print(response.text)
#
# # 异常处理
# except requests.exceptions.ConnectionError:
#     print("错误：无法连接到服务器，请检查网络/接口地址")
# except requests.exceptions.Timeout:
#     print("错误：请求超时，服务器响应过慢")
# except requests.exceptions.RequestException as e:
#     print(f"请求失败：{str(e)}")
import requests



import requests

url = "https://api.lingsiai.cn/ai/AIRewrite"
headers = {
    "X-API-Key": "sk__YWPFq0Dpwsk8Tk-sBYfrqgMCGTGts6sEpOlE6E30IQ",
    "Content-Type": "application/json"
}
data = {
    "text": "有效地解决传统教学运作所存的效率难题，还为以数据为引领，智能协同的新式教学模式考察赋予了 practical 的技术开展途径。。",
    "combination_id": '10030'
}

response = requests.post(url, headers=headers, json=data)
print(response.json())
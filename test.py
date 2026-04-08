#
#
# print({'authority': 'ai.lanbeike.online', 'method': 'POST', 'scheme': 'https', 'accept': '*/*', 'accept-encoding': 'gzip, deflate, br, zstd', 'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6', 'content-type': 'application/json', 'origin': 'https://ai.lanbeike.online', 'priority': 'u=1, i', 'referer': 'https://ai.lanbeike.online/index/index/editor?history_id=150751', 'sec-ch-ua': '"Not;A=Brand";v="99", "Microsoft Edge";v="139", "Chromium";v="139"', 'sec-ch-ua-mobile': '?0', 'sec-ch-ua-platform': '"Windows"', 'sec-fetch-dest': 'empty', 'sec-fetch-mode': 'cors', 'sec-fetch-site': 'same-origin', 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0', 'cookie': 'SESSION_ID=b2a1b4b0413bda41b403d8abda6500c8; uid=41; token=b98483603e29cc28fe5554381b80801f; uuid=1a1484e9db41bb0250f68df34080f736', 'page-timestamp': '1760364622', 'content-length': '54'}
# )
#
# import time
# print(str(int(time.time()*1000)))
#
# # 1760365392
# # 1760362703857
#
# import requests
# import json
#
# # API地址
# url = "http://124.221.97.191:9851/ai/AIRewrite"
#
# # 请求头
# headers = {
#     "accept": "application/json",
#     "X-API-Key": "sk_hmNr4B67JZRrPSUcimM-JavekTpUTN26hN3rzBMA71I",
#     "Content-Type": "application/json"
# }
#
# # 请求数据
# data = {
#     "text": "二小时的解剖实验，趴在实验室的课桌上打盹，可此刻身下却是铺着粗麻布的木板床，窗外飘着的也不是深秋的冷雨，而是鹅毛般的大雪。​“姑娘醒了？” 脆生生的声音响起，穿着青色襦裙的小丫鬟端着陶碗走近，鬓边还别着朵风干的野菊，“阿澈哥说你许是从山崖上摔下来伤了头，让我多熬些粟米粥给你补身子。”​林薇挣扎着坐起身，脑袋里像塞进了一团乱麻。她低头看向自己的手，纤细却布满细小的划伤，指甲缝里还嵌着泥土 —— 这绝不是她那双常年握手术刀、涂着淡粉色指甲油的手。墙上挂着的蓑衣还在滴水，竹篓里散落着几株她只在《本草纲目》插图里见过的草药，最让她心头一震的是铜镜里的倒影：柳叶眉，杏核眼，一身洗得发白的浅紫襦裙，分明是个陌生的唐朝少女模样。​“阿澈是谁？” 她哑着嗓子问，努力让自己的语气听起来不那么惊慌。​“就是救你的采药郎呀。” 小丫鬟放下陶碗，絮絮叨叨地说，“昨日雪下得紧，阿澈哥在寒云峰下发现你时，你手里还攥着这个怪东西呢。”​那是一支黑色的钢笔，笔帽上还刻着她医学院的校徽。林薇紧紧攥住钢笔，冰凉的金属触感让她稍稍冷静 —— 她竟真的穿越了，穿到了这个连消毒水都没有的盛唐。​接下来的几日，林薇靠着现代医学知识勉强应付着身体的不适。她教小丫鬟用烈酒煮沸消毒伤口，用干净的麻布代替纱布，甚至凭着记忆画出简易的夹板，帮隔壁砍柴摔伤腿的老伯固定骨折处。这些在现代习以为常的处理方式，在村民眼里却成了 “神仙手段”，连带着救她回来的阿澈也对她多了几分好奇。",
#     "combination_id": "20"
# }
#
# response = requests.post(
#         url,
#         headers=headers,
#         data=json.dumps(data),
#         timeout=600  # 超时时间设置为600秒
#     )
#
# # 检查响应状态码
# if response.status_code == 200:
#     print("请求成功！")
#     print("响应内容：", response.json())
# else:
#     print(f"请求失败，状态码：{response.status_code}")
#     print("响应内容：", response.text)

import requests

# 请求 URL
url = "https://xrzbk.lanbeike.online/index/user/emailLogin"

# 请求头（完全和你 curl 一致）
headers = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "zh-CN,zh;q=0.9,zh-HK;q=0.8",
    "content-type": "application/json",
    "origin": "https://ai.lanbeike.online",
    "priority": "u=1, i",
    "referer": "https://ai.lanbeike.online/",
    "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
}

# 请求数据
data = {
    "email": "1762389546@qq.com",
    "password": "xrz1762389546"
}

# 发送 POST 请求（json 参数自动处理 content-type）
response = requests.post(url, headers=headers, json=data)

# 输出结果
print("状态码:", response.status_code)
print("返回内容:", response.text)

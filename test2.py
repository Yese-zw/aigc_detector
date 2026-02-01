import redis
from redis.exceptions import RedisError


def save_token_to_redis(token, redis_key="ai_detector_auth", host="124.221.97.191", port=6379, db=3, password=960777365):
    """
    将用户输入的token保存到Redis中

    参数:
        token: 要存储的token字符串
        redis_key: 存储token使用的Redis键名，默认是"user_token"
        host: Redis服务器地址，默认本地
        port: Redis端口，默认6379
        db: Redis数据库编号，默认0
        password: Redis密码，如果没有设置密码则为None
    """
    try:
        # 建立Redis连接
        r = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True  # 自动将返回值解码为字符串（否则是bytes类型）
        )

        # 验证连接
        r.ping()
        print("成功连接到Redis服务器")

        # 将token存入Redis，设置过期时间（可选，比如24小时，单位秒）
        # 如果不需要过期时间，去掉 ex=86400 即可
        r.set(redis_key, token, ex=86400)

        # 验证存储结果
        saved_token = r.get(redis_key)
        if saved_token == token:
            print(f"Token已成功存入Redis，key: {redis_key}")
            print(f"存储的token值: {saved_token}")
        else:
            print("Token存储失败")

    except RedisError as e:
        print(f"Redis操作出错: {e}")
    except Exception as e:
        print(f"未知错误: {e}")


if __name__ == "__main__":
    # 获取用户输入的token
    user_token = input("请输入要存储的token: ").strip()

    # 校验输入是否为空
    if not user_token:
        print("错误：token不能为空！")
    else:
        # 调用函数存储token（如果你的Redis有密码，需要修改password参数）
        save_token_to_redis(
            token=user_token,
            # password="你的Redis密码"  # 有密码时取消注释并填写
        )
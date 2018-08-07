import redis

class Config(object):
    SECRET_KEY = "abcdefghijklmn"

    SQLALCHEMY_DATABASE_URI = "mysql://root:mysql@127.0.0.1:3306/information01"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    REDIS_HOST = "127.0.0.1"
    REDIS_PORT = 6379

    # 设置session的存储数据类型
    SESSION_TYPE = "redis"
    # 创建一个session-redis,用来存储会话的session
    SESSION_REDIS = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT)
    # 使用session的签名
    SESSION_USE_SIGNER = True
    # 设置session的有效期,有效期的单位是秒,86400表示一天有效
    PREMANENT_SESSION_LIFETIME = 86400 * 3



# 在做项目期间,我们使用的是测试模式
class DevelopmentConfig(Config):
    DEBUG = True


# 项目正式上线,我们使用的是正式的上线模式
class ProductionConfig(Config):
    DEBUG = False


config_map = {
    "develop": DevelopmentConfig,
    "production": ProductionConfig
}

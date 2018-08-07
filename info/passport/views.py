import random
import re

from datetime import datetime

from flask import current_app
from flask import make_response, jsonify
from flask import request
from flask import session

from info import constants, db
from info import redis_store
from info.lib.yuntongxun.sms import CCP
from info.models import User
from info.utils.captcha.captcha import captcha
from info.utils.response_code import RET
from . import passport_blue  # 在包内部导入模块时不能使用包名

"""
用户图片验证码
"""


@passport_blue.route('/image_code')
def passport():
    # print("前端请求的url地址 = " + request.url)

    # 获取从前端传递过来的一个验证码.?后面的属性内容request.args.get("code_id")
    code_id = request.args.get("code_id")

    # name表示图片验证码的名字
    # test表示图片验证码的内容
    # image表示包含验证码的图片
    # 生成图片验证码
    name, text, image = captcha.generate_captcha()
    print("图片验证码的内容 = " + text)

    # 我们需要把图片验证码内容存在redis的数据库当中
    # image_code_xxxx
    # 第一个参数表示key
    # 第二个参数表示图片验证码的内容
    # 第三个参数表示过期时间
    redis_store.set("image_code" + code_id, text, 300)
    # 获取到redis里面的值的byte,所以在读取的时候需要解码

    # make_response表示响应体对象,这个对象的参数表示图片形式的验证码
    resp = make_response(image)

    # 告诉系统,我们当前需要展示的是图片
    resp.headers["Content-Type"] = "image/jpg"
    return resp


"""
用户短信验证码
"""


@passport_blue.route('/sms_code', methods=["GET", "POST"])
def sms_code():
    # 获取前端传递过来的json数据
    mobile = request.json.get("mobile")

    # 参数表示图片验证码的内容
    image_code = request.json.get("image_code")

    # 表示图片验证码的id
    image_code_id = request.json.get("image_code_id")

    # 校验前端传递过来的数据是否有值
    if not all([mobile, image_code, image_code_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="请输入参数")

    # 校验用户传递过来的手机号是否正确
    if not re.match(r"^1[3456789]\d{9}$", mobile):
        return jsonify(errno=RET.PARAMERR, errmsg="请输入正确的手机号码")

    # 获取到redis中的图片验证码
    real_image_code = redis_store.get("image_code" + image_code_id)

    # 判断redis中的验证码是否过期
    if not real_image_code:
        return jsonify(errno=RET.NODATA, errmsg="当前验证码已过期")

    # 到了这里说明验证码还在有效期,判断用户输入的验证码是否和redis中保存的相同,都转换为小写,方便用户体验
    if image_code.lower() != real_image_code.lower():
        return jsonify(errno=RET.PARAMERR, errmsg="请输入正确的验证码")

    # 通过随机数生成一个6位的验证码,并用0占位补齐六位
    random_sms_code = "%06d" % random.randint(0, 999999)

    # 将产生的随机数短信内容储存在redis中,方便注册的时候进行验证
    # 第一个参数表示key,  第二个参数表示六位随机数字,  第三个参数表示数据有效期,单位是秒
    redis_store.set("sms_code_" + mobile, random_sms_code, constants.SMS_CODE_REDIS_EXPIRES)

    print("短信内容 = " + random_sms_code)

    # 发送短信到指定的手机号码>>括号中数据1>手机号码2>随机数字,5分钟有效,返回状态码为1

    statuCode = CCP().send_template_sms(mobile, [random_sms_code, 5], 1)
    print(statuCode)
    if statuCode != 0:
        return jsonify(errno=RET.THIRDERR, errmsg="短信发送失败")

    return jsonify(errno=RET.OK, errmsg="发送短信成功")


"""
用户注册
"""


@passport_blue.route('/register', methods=["GET", "POST"])
def register():
    # 用户输入的手机号
    mobile = request.json.get("mobile")
    # 用户输入的短信验证码
    smscode = request.json.get("smscode")
    # 用户输入的密码
    password = request.json.get("password")

    # 获取redis服务器里面存储的短信验证码
    real_sms_code = redis_store.get("sms_code_" + mobile)

    if not real_sms_code:
        return jsonify(errno=RET.NODATA, errmsg="短信验证码已失效")

    # 判断用户输入的短信验证码是否和服务器里面存储的一致
    if smscode != real_sms_code:
        return jsonify(errno=RET.PARAMERR, errmsg="请输入正确的短信验证码")

    # 创建一个用户对象用来注册用户
    user = User()
    user.mobile = mobile
    user.password = password
    user.nick_name = mobile
    # 获取当前时间,用来记录注册时间
    user.last_login = datetime.now()
    # 网数据库进行持久化操作
    db.session.add(user)
    db.session.commit()
    return jsonify(errno=RET.OK, errmsg="注册成功")


"""
用户登陆
"""


@passport_blue.route('/login', methods=["GET", "POST"])
def login():
    mobile = request.json.get("mobile")
    password = request.json.get("password")
    # 通过手机号查询当前是否有这个用户
    try:
        user = User.query.filter(User.mobile == mobile).first()
    except Exception as e:
        # 把错误信息存储到log日志里面
        current_app.logger.error(e)
    # 判断是否有这个用户
    if not user:
        return jsonify(errno=RET.NODATA, errmsg="用户不存在,请先注册")

    # 通过系统的源码帮我们检查用户的密码是否正确
    if not user.check_password(password):
        return jsonify(errno=RET.PWDERR, errmsg="密码输入错误")

    # 对用户进行状态保持,跟网易新闻一样,session进行实现,保持用户信息到session里面
    session["user_id"] = user.id
    session["nick_name"] = user.nick_name
    session["mobile"] = user.mobile
    # 更新最后的登陆时间
    user.last_login = datetime.now()
    # 把数据提交到数据库
    db.session.commit()

    return jsonify(errno=RET.OK, errmsg="登陆成功")


"""
用户登出
"""


@passport_blue.route("/logout", methods=["GET", "POST"])
def logout():
    # 删除session中的数据就可以完成退出
    session.pop("user_id", None)
    session.pop("nick_name", None)
    session.pop("mobile", None)
    session.pop("is_admin", None)  # 防止用户登录后台管理页面
    return jsonify(errno=RET.OK, errmsg="退出成功")

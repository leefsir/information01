import functools

from flask import g
from flask import session

from info.models import User


def do_index_class(index):
    """自定义热门新闻样式过滤器"""
    if index == 0:
        return "first"
    elif index == 1:
        return "second"
    elif index == 2:
        return "third"
    else:
        return ""


def user_login_data(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        # 因为在登陆的时候, 我们把数据存储到session里面, 所以从session里面获取到当前登陆的用户
        user_id = session.get("user_id")
        user = None
        # 需要判断当前用户是否登陆
        if user_id:
            # 通过user_id查询是否有当前这个用户
            user = User.query.get(user_id)
        g.user = user
        return f(*args,**kwargs)
    return wrapper

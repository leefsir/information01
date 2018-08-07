from flask import Blueprint
from flask import redirect
from flask import request
from flask import session

admin_blue = Blueprint("admin",__name__,url_prefix="/admin")

from . import views


@admin_blue.before_request
def check_admin():
    """在每次请求前进行登录用户身份验证"""
    # 读取session中的is_admin属性值,默认为none(False)
    is_admin = session.get("is_admin", None)
    # 如果不是管理员,就不允许请求后台管理员界面
    if not is_admin and not request.url.endswith("/admin/login"):
        return redirect("/")
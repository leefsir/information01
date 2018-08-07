from flask import g
from flask import request, jsonify
from flask import session

from info.models import User, News, Category
from info.utils.common import user_login_data
from info.utils.response_code import RET
from . import index_blue
from flask import render_template, current_app

"""
current_app代理app对象
"""


@index_blue.route("/favicon.ico")
def send_favicon():
    # 发送图标到浏览器
    return current_app.send_static_file("news/favicon.ico")


@index_blue.route('/')
@user_login_data
def index():
    """
    判断用户是否登陆成功
    """
    user = g.user

    """
    获取10条新闻按照点击量倒序排列
    """
    news = News.query.order_by(News.clicks.desc()).limit(10)
    news_list = []
    for new_mode in news:
        news_list.append(new_mode.to_dict())

    """
    获取首页的新闻分类的标题
    """
    categories = Category.query.all()  # Category的所有对象
    category_list = []
    for category in categories:
        category_list.append(category.to_dict())  # 对象调用属性
    data = {
        "user_info": user.to_dict() if user else None,
        "click_news_list": news_list,
        "categories": category_list
    }

    # 在模板文件放入templates文件夹之前要先取消mark模式,模板会自动匹配其样式加载路径
    return render_template("news/index.html", data=data)


"""
返回新闻列表
"""


@index_blue.route('/news_list')
def newslist():
    # 获取到前端页面传递过来的数据,表示第几个页面,第二个参数表示默认值是从第一页开始
    page = request.args.get("page", 1)
    # 分类id
    cid = request.args.get("cid", 1)
    # 每页有多少条数据,默认是10条
    per_page = request.args.get("per_page", 10)

    # http协议传递过来的都是字符串
    try:
        page = int(page)
        cid = int(cid)
        per_page = int(per_page)
    except Exception as e:
        page = 1
        cid = 1
        per_page = 10

    filter = [News.status == 0]  # 新闻状态为审核通过的才可以显示
    if cid != 1:
        filter.append(News.category_id == cid)
    paginate = News.query.filter(*filter).order_by(News.create_time.desc()).paginate(page, per_page, False)
    # 获取当前页面需要展示的数据(此处10条)
    items = paginate.items
    # 表示当前页面
    current_page = paginate.page
    # 表示总页数
    total_page = paginate.pages

    news_list = []
    for item in items:
        news_list.append(item.to_dict())

    data = {
        "current_page": current_page,
        "total_page": total_page,
        "news_dict_li": news_list
    }
    return jsonify(errno=RET.OK, errmsg="ojbk", data=data)

import time
from datetime import datetime, timedelta

from flask import current_app
from flask import g, jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for

from info import constants
from info import db
from info.models import User, News, Category
from info.utils.common import user_login_data
from info.utils.image_storage import storage
from info.utils.response_code import RET
from . import admin_blue


@admin_blue.route('/index')
@user_login_data
def admin_index():
    # 这里有bug
    user = g.user

    return render_template("admin/index.html", user=user.to_dict())


"""管理员登陆页面"""


@admin_blue.route('/login', methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        user_id = session.get("user_id", None)
        is_admin = session.get("is_admin", None)
        if user_id and is_admin:  # 管理员登录就跳转后台主页面
            return redirect(url_for("admin.admin_index"))
        return render_template("admin/login.html")

    username = request.form.get("username")
    password = request.form.get("password")

    user = User.query.filter(User.mobile == username, User.is_admin == True).first()

    if not user:
        return render_template("admin/login.html", errmsg="没有这个用户")

    if not user.check_password(password):
        return render_template("admin/login.html", errmsg="密码输入错误")

    # 将登陆用户信息存储到session
    session["user_id"] = user.id
    session["nick_name"] = user.nick_name
    session["mobile"] = user.mobile
    session["is_admin"] = user.is_admin

    # 如果登陆成功,需要跳转到主页面,跳转视图函数时注意要加上蓝图别名
    return redirect(url_for("admin.admin_index"))


"""用户数量动态检测"""


@admin_blue.route('/user_count')
def user_count():
    # 总人数
    total_count = 0
    # 每月新增加的人数
    mon_count = 0
    # 每天新增的人数
    day_count = 0
    # 获取到总人数:注意管理人员要去除
    total_count = User.query.filter(User.is_admin == False).count()

    # 获取现在的时间
    t = time.localtime()

    # 获取本月初一
    mon_begin = "%d-%02d-01" % (t.tm_year, t.tm_mon)

    # 将字符串转换为时间类型2018-08-01 >> 2018-08-01 00:00:00
    mon_begin_date = datetime.strptime(mon_begin, '%Y-%m-%d')

    # 获取到本月的人数
    mon_count = User.query.filter(User.is_admin == False, User.create_time >= mon_begin_date).count()

    # 与上面类似,获取本日新增人数
    day_begin = "%d-%02d-%02d" % (t.tm_year, t.tm_mon, t.tm_mday)  # 本日0点0分0秒
    day_begin_date = datetime.strptime(day_begin, '%Y-%m-%d')

    day_count = User.query.filter(User.is_admin == False, User.create_time >= day_begin_date).count()

    active_count = []
    active_time = []
    for i in range(0, 31):
        # 一天的开始时间0:0:0
        begin_date = day_begin_date - timedelta(days=i)
        # 一天的结束时间(下一天的开始时间)
        end_date = day_begin_date - timedelta(days=(i - 1))
        # 一天之内登陆过的总人数
        count = User.query.filter(User.is_admin == False, User.last_login >= begin_date,
                                  User.last_login < end_date).count()
        active_count.append(count)
        # strftime("%Y-%m-%d")将时间转换为字符串格式
        active_time.append(begin_date.strftime("%Y-%m-%d"))
    # 因为显示的时间是从前往后,而添加的时间是从后往前,所以需要对列表数据进行反转
    active_count.reverse()
    active_time.reverse()
    data = {
        "total_count": total_count,
        "mon_count": mon_count,
        "day_count": day_count,
        "active_count": active_count,
        "active_time": active_time
    }

    return render_template("admin/user_count.html", data=data)


"""获取所有注册用户的列表"""


@admin_blue.route('/user_list')
def user_list():
    page = request.args.get("p", 1)
    try:
        page = int(page)
    except Exception as e:
        page = 1

    paginate = User.query.filter(User.is_admin == False).order_by(User.last_login.desc()).paginate(page, 10, False)
    items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages
    user_list = []
    for item in items:
        user_list.append(item.to_admin_dict())

    data = {
        "users": user_list,
        "current_page": current_page,
        "total_page": total_page
    }
    return render_template("admin/user_list.html", data=data)


"""新闻审核"""


@admin_blue.route("/news_review")
def news_review():
    page = request.args.get("p", 1)
    keywords = request.args.get("keywords")
    try:
        page = int(page)
    except Exception as e:
        page = 1
    filter = [News.status != 0]  # 审核通过的不再显示
    if keywords:
        # 添加新闻标题过滤,显示新闻标题
        filter.append(News.title.contains(keywords))
    paginate = News.query.filter(*filter).order_by(News.create_time.desc()).paginate(page, 10, False)
    items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages
    user_list = []
    for item in items:
        user_list.append(item.to_review_dict())
    data = {
        "news_list": user_list,
        "current_page": current_page,
        "total_page": total_page
    }
    return render_template("admin/news_review.html", data=data)


"""新闻审核详情"""


@admin_blue.route("/news_review_detail", methods=["GET", "POST"])
def news_review_detail():
    if request.method == "GET":
        # 展示需要审核的新闻
        news_id = request.args.get("news_id")
        news = News.query.get(news_id)
        data = {
            "news": news.to_dict()
        }
        return render_template("admin/news_review_detail.html", data=data)

    # 进行具体的新闻审核操作
    action = request.json.get("action")
    news_id = request.json.get("news_id")

    # 根据回传的新闻id来查询出要审核的新闻
    news = News.query.get(news_id)
    if action == "accept":
        # 表示通过审核,更改新闻状态
        news.status = 0
    else:
        # 如果审核不通过,需要给出拒绝的原因
        reason = request.json.get("reason")
        if not reason:
            return jsonify(errno=RET.PARAMERR, errmsg="请给出未通过的原因")
        # 修改新闻状态
        news.status = -1
        news.reason = reason
    db.session.commit()
    return jsonify(errno=RET.OK, errmsg="ok")


# """新闻编辑"""
@admin_blue.route("/news_edit")
def news_edit():
    page = request.args.get("p", 1)
    keywords = request.args.get("keywords")
    try:
        page = int(page)
    except Exception as e:
        page = 1

    paginate = News.query.order_by(News.create_time.desc()).paginate(page, 10, False)
    items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages

    user_list = []
    for item in items:
        user_list.append(item.to_review_dict())

    data = {
        "news_list": user_list,
        "current_page": current_page,
        "total_page": total_page,
    }
    return render_template("admin/news_edit.html", data=data)


"""新闻审核详情"""


@admin_blue.route("/news_edit_detail", methods=["GET", "POST"])
def news_edit_detail():
    if request.method == "GET":
        news_id = request.args.get("news_id")
        news = News.query.get(news_id)
        categorys = Category.query.all()
        category_list = []
        for category in categorys:
            category_list.append(category.to_dict())

        category_list.pop(0)
        data = {
            "news": news.to_dict(),
            "categories": category_list
        }
        return render_template("admin/news_edit_detail.html", data=data)

    news_id = request.form.get("news_id")
    title = request.form.get("title")
    digest = request.form.get("digest")
    content = request.form.get("content")
    index_image = request.files.get("index_image")
    category_id = request.form.get("category_id")
    # 1.1 判断数据是否有值
    if not all([title, digest, content, category_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数有误")

    # news = None
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)

    if not news:
        return jsonify(errno=RET.NODATA, errmsg="未查询到新闻数据")

    try:
        index_image = index_image.read()
        key = storage(index_image)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="第三方系统错误")

    news.title = title
    news.digest = digest
    news.content = content
    news.index_image_url = constants.QINIU_DOMIN_PREFIX + key
    news.category_id = category_id
    db.session.commit()
    return jsonify(errno=RET.OK, errmsg="ok")


"""新闻分类"""


@admin_blue.route("/news_type")
def news_type():
    categorys = Category.query.all()
    category_list = []
    for category in categorys:
        category_list.append(category.to_dict())

    category_list.pop(0)  # 把最新这个分类去除
    return render_template("admin/news_type.html", data={"categories": category_list})


"""编辑新闻分类页面"""


@admin_blue.route("/add_category", methods=["GET", "POST"])
def add_category():
    # 获取前端页面回传数据
    cid = request.json.get("id")
    name = request.json.get("name")
    # 如果有这个分类id说明此处已经有新闻分类标题,可以修改
    # 如果没有分类id就说明是添加标题
    if cid:
        category = Category.query.get(cid)
        category.name = name
    else:

        category = Category()
        category.name = name
        db.session.add(category)

    db.session.commit()
    return jsonify(errno=RET.OK, errmsg="保存数据成功")

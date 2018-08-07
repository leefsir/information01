from flask import current_app
from flask import g, jsonify
from flask import redirect
from flask import render_template
from flask import request
from info import constants
from info import db
from info.models import Category, News, User
from info.utils.common import user_login_data
from info.utils.image_storage import storage
from info.utils.response_code import RET
from . import user_blue

"""个人中心主页面"""


@user_blue.route('/info')
@user_login_data
def get_user_info():
    user = g.user
    if not user:  # 如果用户未登录,则回到主页面
        return redirect("/")
    data = {
        "user_info": user.to_dict() if user else None
    }
    return render_template("news/user.html", data=data)


"""个人中心基本资料页面"""


@user_blue.route('/base_info', methods=["GET", "POST"])
@user_login_data
def base_info():
    user = g.user
    if request.method == "GET":  # 在显示页面的时候是get请求
        data = {
            "user_info": user.to_dict() if user else None
        }
        return render_template("news/user_base_info.html", data=data)

    # 代码到这里说明用户需要修改基本资料,为post请求
    nick_name = request.json.get("nick_name")
    signature = request.json.get("signature")
    gender = request.json.get("gender")

    if not all([nick_name, signature, gender]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不完整")

    user.nick_name = nick_name
    user.signature = signature
    user.gender = gender
    db.session.commit()  # 修改数据表属性值
    return jsonify(errno=RET.OK, errmsg="ok")


"""头像设置"""


@user_blue.route("/pic_info", methods=["GET", "POST"])
@user_login_data
def pic_info():
    user = g.user
    if request.method == "GET":
        data = {
            "user_info": user.to_dict() if user else None
        }
        return render_template("news/user_pic_info.html", data=data)

    # 获取到用户传递过来的头像参数
    avatar_url = request.files.get("avatar").read()
    # 在传递到七牛之后,七牛会返回一个key,返回的目的是帮助我们取访问图片
    key = storage(avatar_url)

    user.avatar_url = key
    # 将用户头像地址存储到数据库
    db.session.commit()
    return jsonify(errno=RET.OK, errmsg="头像上传成功", data={"avatar_url": constants.QINIU_DOMIN_PREFIX + key})


"""用户中心修改密码"""


@user_blue.route("/pass_info", methods=["GET", "POST"])
@user_login_data
def pass_info():
    user = g.user
    if request.method == "GET":
        data = {
            "user_info": user.to_dict() if user else None
        }
        return render_template("news/user_pass_info.html", data=data)

    # 获取新旧密码
    old_password = request.json.get("old_password")
    new_password = request.json.get("new_password")

    # 检查旧密码是否正确
    if not user.check_password(old_password):
        return jsonify(errno=RET.PWDERR, errmsg="密码错误")

    user.password = new_password
    db.session.commit()
    return jsonify(errno=RET.OK, errmsg="密码修改成功")


"""用户中心新闻收藏页面"""


@user_blue.route("/collection")
@user_login_data
def collection():
    user = g.user
    page = request.args.get("p", 1)  # 获取当前新闻收藏页数,默认第一页

    try:
        page = int(page)  # http传递过来的是字符串,此处需要int整型
    except Exception as e:
        page = 1  # 强转

    paginate = user.collection_news.paginate(page, 2, False)
    items = paginate.items  # 获取当前页面的所有信息
    current_page = paginate.page  # 获取当前页码数
    total_page = paginate.pages  # 获取总页数

    items_list = []
    for item in items:
        items_list.append(item.to_review_dict())

    data = {
        "collections": items_list,
        "current_page": current_page,
        "total_page": total_page
    }
    # 将收藏的新闻展示到页面
    return render_template("news/user_collection.html", data=data)


"""用户中心发布新闻页面"""


@user_blue.route("/news_release", methods=["GET", "POST"])
@user_login_data
def news_release():
    user = g.user
    if request.method == "GET":
        # 查询获取所有新闻的类别分类名,在写新闻的时候需要选择种类
        categorys = Category.query.all()
        category_list = []
        for category in categorys:
            category_list.append(category.to_dict())
        # 将分类名为"最新"的种类名排除
        category_list.pop(0)
        data = {
            "categories": category_list
        }
        return render_template("news/user_news_release.html", data=data)

    # 1.获取表单中要提交的数据
    title = request.form.get("title")
    source = "个人发布"  # 发布来源
    digest = request.form.get("digest")  # 新闻摘要
    content = request.form.get("content")  # 新闻内容
    index_image = request.files.get("index_image").read()  # 新闻图片,存到七牛云
    category_id = request.form.get("category_id")  # 新闻分类id
    # 1.1 判断数据是否有值
    if not all([title, source, digest, content, index_image, category_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数有误")

    key = storage(index_image)  # 新闻图片存到七牛云

    news = News()  # 创建新闻对象
    # 给新闻对象设定各种属性
    news.title = title
    news.source = source
    news.digest = digest
    news.content = content
    news.index_image_url = constants.QINIU_DOMIN_PREFIX + key
    news.category_id = category_id
    news.user_id = user.id
    news.status = 1  # 新闻状态(是否通过审核)

    db.session.add(news)
    db.session.commit()
    return jsonify(errno=RET.OK, errmsg="发布成功,请等待审核")


"""个人发布的新闻列表"""


@user_blue.route("/news_list")
@user_login_data
def news_list():
    user = g.user
    page = request.args.get("p", 1)  # 获取当前新闻收藏页数,默认第一页

    try:
        page = int(page)  # http传递过来的是字符串,此处需要int整型
    except Exception as e:
        page = 1  # 强转

    paginate = News.query.filter(News.user_id == user.id).paginate(page, 2, False)
    items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages

    items_list = []
    for item in items:
        items_list.append(item.to_review_dict())

    data = {
        "news_list": items_list,
        "current_page": current_page,
        "total_page": total_page
    }
    return render_template("news/user_news_list.html", data=data)


"""我的关注页面"""


@user_blue.route('/follow')
@user_login_data
def follow():
    """关注页面,需要用到分页显示"""
    user = g.user
    page = request.args.get("p", 1)

    try:
        page = int(page)
    except Exception as e:
        page = 1

    paginate = user.followed.paginate(page, 4, False)
    items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages
    # 关注列表
    other_list = []
    for item in items:
        other_list.append(item.to_dict())

    data = {
        "users": other_list,
        "current_page": current_page,
        "total_page": total_page,
    }
    return render_template("news/user_follow.html", data=data)


"""被关注的作者的详细信息页面"""


@user_blue.route("/other_info")
@user_login_data
def other_info():
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="请登陆")
    # 获取到作者id
    other_id = request.args.get("id")
    # 查询到作者
    other = User.query.get(other_id)

    """这个页面也可以直接关注和取关"""
    # 表示我关注了哪些人,默认情况下,第一次进来,我谁都没有关注,所以设置成false
    is_followed = False
    # 如果我想关注别人的话,那么必须新闻有作者
    # 如果有作者就可以关注,所以必须有作者,因为是我需要关注这个作者,所以用户必须要登陆
    if other and user:
        if other in user.followed:
            # 如果当前新闻的作者在我关注的人列表里面,说明我就关注了这个新闻的作者,那么我就可以is_followed = True
            is_followed = True

    data = {
        "user_info": user.to_dict(),
        "other_info": other.to_dict(),
        "is_followed": is_followed
    }
    return render_template("news/other.html", data=data)


"""其他新闻作者的详细页面"""


@user_blue.route("/other_news_list")
def other_news_list():
    # 获取页数
    p = request.args.get("p", 1)
    user_id = request.args.get("user_id")
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    # 查询作者的信息
    user = User.query.get(user_id)
    paginate = News.query.filter(News.user_id == user.id).paginate(p, 10, False)
    # 获取当前页数据
    news_li = paginate.items
    # 获取当前页
    current_page = paginate.page
    # 获取总页数
    total_page = paginate.pages

    news_dict_li = []

    for news_item in news_li:
        news_dict_li.append(news_item.to_review_dict())
    data = {
        "news_list": news_dict_li,
        "total_page": total_page,
        "current_page": current_page
    }
    return jsonify(errno=RET.OK, errmsg="OK", data=data)

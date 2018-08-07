from flask import current_app
from flask import request, jsonify

from info import db
from info.models import News, Comment, CommentLike, User
from info.utils.common import user_login_data
from flask import g

from info.utils.response_code import RET
from . import news_blue
from flask import render_template


@news_blue.route('/<int:news_id>')  # 从前端传递参数给视图函数
@user_login_data
def news_ditail(news_id):
    user = g.user

    """
    获取到新闻详情的数据
    """
    news = News.query.get(news_id)

    """
    获取热门新闻数据
    """
    news_model = News.query.order_by(News.clicks.desc()).limit(10)
    news_list = []
    for news_dict in news_model:
        news_list.append(news_dict.to_dict())

    """
    新闻收藏(页面展示操作):
        1:进入到新闻详情页面之后,如果用户已经收藏了该新闻,则显示已收藏,is_collected = true
        2:点击则为取消收藏,反之点击则收藏该新闻,is_collected = false
        3:如果要收藏新闻,那么收藏的动作是用户的行为,所以收藏这个地方用户名user必须是登录状态才可以
        4:因为我们要收藏的是新闻,所以新闻news必须要有值
        5:要收藏的新闻必须在收藏列表当中,这样就是把is_collected = true
    """

    is_collected = False  # 默认是未收藏状态
    if user:
        if news in user.collection_news:
            is_collected = True

    # 获取当前新闻的评论
    comments = []
    try:
        comments = Comment.query.filter(Comment.news_id == news_id).order_by(Comment.create_time.desc()).all()
    except Exception as e:
        current_app.logger.error(e)
    comment_list = []

    """
    获取到新闻详情页面所有评论点赞的数据
    """
    commentlike_list = []
    comment_like_ids = []
    if user:
        # 取到当前用户在当前新闻的所有评论点赞的记录
        commentlike_list = CommentLike.query.filter(CommentLike.user_id == g.user.id).all()
        # 取出记录中所有的评论id
        comment_like_ids = [comment_like.comment_id for comment_like in commentlike_list]
    for comment in comments:
        comment_dict = comment.to_dict()
        comment_dict["is_like"] = False  # 默认没有点赞
        if comment.id in comment_like_ids:  # 已经点过赞了
            comment_dict["is_like"] = True
        comment_list.append(comment_dict)

    """
     关注:     
    1 第一次进来肯定没有关注任何人,所以默认值是false     
    2 必须登陆,判断user是否有值     
    3 必须有作者,因为如果是爬虫爬过来的数据,那么就没有新闻作者     
    4 如果当前新闻有作者,并且在我关注的人的列表当中,
    就说明我是新闻作者的粉 丝,所以设置ture
    """
    is_followed = False
    if news.user and user:
        if news.user in user.followed:
            # 如果当前新闻的作者在我关注的人列表里面,说明我就关注了这个新闻的作者,那么我就可以is_followed = True
            is_followed = True




    data = {
        "user_info": user.to_dict() if user else None,
        "click_news_list": news_list,
        "news": news.to_dict(),
        "is_collected": is_collected,
        "is_followed": is_followed,
        "comments": comment_list
    }
    return render_template("news/detail.html", data=data)


@news_blue.route("/news_collect", methods=["POST"])
@user_login_data
def news_collect():
    user = g.user
    news_id = request.json.get("news_id")
    # 用户传递过来的动作,收藏新闻,或者取消新闻收藏
    action = request.json.get("action")

    """
    新闻收藏(数据库操作):
        1:我们必须得知道,当前用户收藏的是哪条新闻,如果想知道用户收藏的是哪条新闻,那么直接通过news_id进行查询
        2:如果想收藏新闻,那么必须登录,所以判断用户是否已经登录就可以
        3:判断用户的动作,到底是想收藏,还是想取消收藏
        4:如果用户是收藏新闻的动作,那么直接把新闻丢到用户的收藏列表中
    """
    news = News.query.get(news_id)  # 查询获取当前新闻
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    if action == "collect":
        user.collection_news.append(news)  # 添加新闻收藏
    else:
        user.collection_news.remove(news)  # 删除新闻收藏

    db.session.commit()
    return jsonify(errno=RET.OK, errmsg="收藏成功")


"""新闻评论视图函数"""
@news_blue.route("/news_comment", methods=["POST"])
@user_login_data
def news_comment():
    """新闻评论"""
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="请登录")
    news_id = request.json.get("news_id")
    # 评论的内容
    comment_str = request.json.get("comment")
    # 评论的父id
    parent_id = request.json.get("parent_id")

    """
    用户评论:
        用户如果在登录的情况下,可以进行评论,未登录,点击评论弹出登录框
        用户可以直接评论当前新闻,也可以回复别人发的评论
        1:用户必须先登陆才能进行评论,如果不登录,直接返回
        2:如果需要评论,那么就需要知道当前评论的是哪条新闻,如果想知道是哪条新闻,那么就可以通过news_id查询出来新闻
        3:如果评论成功之后,那么我们需要把用户的评论信息存储到数据库以便下次用户进来的时候可以看到评论

    """
    news = News.query.get(news_id)
    comment = Comment()
    comment.user_id = user.id
    comment.news_id = news.id
    comment.content = comment_str
    # 不是所有的评论都是神评论,都会有回复
    if parent_id:
        comment.parent_id = parent_id
    db.session.add(comment)
    db.session.commit()

    return jsonify(errno=RET.OK, errmsg="评论成功", data=comment.to_dict())


@news_blue.route("/comment_like", methods=["POST"])
@user_login_data
def comment_like():
    """评论点赞"""
    user = g.user
    """
    对新闻的评论进行点赞:
    1:点赞的行为都是人为操作,所以用户必须登录
    2:点赞的行为针对的是当前的评论,有评论才需要点赞,如果没有评论就不需要点赞,所以需要先把评论查询出来
    3:查询点赞评论,在查询点赞评论的时候,需要根据当前的评论id和用户id进行查询
    4:查询出来评论之后,当前这条评论是否有已经被点赞,如果没有被点赞才可以进行点赞
    """
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="请登录")
    comment_id = request.json.get("comment_id")
    # news_id = request.json.get("news_id")  # 暂时用不到的说
    # 判断当前用户的动作,到底是想点赞,还是想取消点赞
    action = request.json.get("action")
    comment = Comment.query.get(comment_id)  # 按照评论id查询出要操作的评论
    if action == "add":
        # 用户想点赞
        comment_like = CommentLike.query.filter(CommentLike.comment_id == comment_id,
                                                CommentLike.user_id == user.id).first()
        # 查讯出来后,需要判断当前这条评论用户是否已经点赞,如果查讯出来为空,说明之前未点赞,那么就可以点赞
        if not comment_like:
            comment_like = CommentLike()  # 创建点赞表对象
            comment_like.comment_id = comment_id
            comment_like.user_id = user.id
            db.session.add(comment_like)
            # 因为点赞了,所以需要把当前的评论点赞数进行加1
            comment.like_count += 1
    else:
        # 取消点赞的动作
        comment_like = CommentLike.query.filter(CommentLike.comment_id == comment_id,
                                                CommentLike.user_id == user.id).first()
        # 查讯出来后,需要判断当前这条评论用户是否已经点赞,那么才可以取消点赞
        if comment_like:
            db.session.delete(comment_like)
            comment.like_count -= 1
    db.session.commit()
    return jsonify(errno=RET.OK, errmsg="点赞成功")


"""作者关注页面"""
@news_blue.route("/followed_user",methods=["GET","POST"])
@user_login_data
def followed_user():
    user = g.user
    if not user:
        return jsonify(errno = RET.SESSIONERR,errmsg="请先登录")
    # 获取我关注的的作者的id
    user_id = request.json.get("user_id")
    # 获取页面用户的操作(关注或者取消关注)
    action = request.json.get("action")
    """
    关注和取消关注:
    1 必须是用户行为,那么用户必须要登陆
    2 根据我关注的那个人的id,查询出,我需要关注那个人的信息
    3 判断当前的动作是关注还是取消关注
    """
    # 查询到被关注的对象
    other = User.query.get(user_id)
    if action == "follow":
        # 关注
        # 如果是关注的动作,说明我之前没有关注这个用户,那么就需要关注,如果我之前已经关注了,那么就应该提示一个错误信息
        # 向我的关注列表中添加要关注的对象
        if other not in user.followed:
            # user.followed:表示我关注的人的列表
            user.followed.append(other)
        else:
            return jsonify(errno = RET.PARAMERR,errmsg = "已经关注了该用户")
    else:
        # 取消关注
        # 如果之前已经关注了该用户,才能取消,如果之前压根就没有关注这个用户,就不需要取消
        # 取消关注,移除对应的关注对象
        if other in user.followed:
            user.followed.remove(other)
        else:
            return jsonify(errno=RET.PARAMERR, errmsg="没有在我关注的人列表当中")

    db.session.commit()
    return jsonify(errno=RET.OK,errmsg="ok")
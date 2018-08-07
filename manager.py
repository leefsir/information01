from flask.ext.migrate import Migrate, MigrateCommand
from flask.ext.script import Manager
from info import create_app, db
from info import models
from info.models import User

"""
manager.py的作用是入口程序
"""
app = create_app("develop")

# 添加扩展命令行
manager = Manager(app)

# 数据库迁移
Migrate(app, db)
manager.add_command("mysql", MigrateCommand)

"""创建管理员对象"""


@manager.option("-u", "--name", dest="name")
@manager.option("-p", "--password", dest="password")
def create_super_user(name, password):
    """使用方法: python manager.py create_super_user -u admin -p 123456"""
    user = User()
    user.mobile = name
    user.nick_name = name
    user.password = password
    user.is_admin = True

    db.session.add(user)
    db.session.commit()


if __name__ == '__main__':
    # print(app.url_map)
    manager.run()

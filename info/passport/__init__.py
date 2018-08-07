from flask import Blueprint

# //var imageCodeUrl = "/passport/image_code?code_id=" + imageCodeId;
passport_blue = Blueprint("passport",__name__,url_prefix="/passport")

from . import views
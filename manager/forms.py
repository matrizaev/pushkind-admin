from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField, StringField, HiddenField
from wtforms.validators import DataRequired, Optional
from wtforms.fields.html5 import EmailField, URLField
from flask_wtf.file import FileField, FileRequired, FileAllowed

from manager import app

class SigninForm (FlaskForm):
	secret = PasswordField('Пароль', validators=[DataRequired()])
	submit = SubmitField('Войти')

class ModifyStoreForm  (FlaskForm):
	storeId = HiddenField ('storeId', validators=[DataRequired()])
	owner = StringField ('Контакт', validators=[Optional()])
	section = StringField ('Корневая категория', validators=[Optional()])
	modify = SubmitField('Сохранить')
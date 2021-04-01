import hashlib
from datetime import datetime

from flask import Flask, request, jsonify
from flask.views import MethodView
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import exc

SALT = 'qwerty'
POSTGRE_DSN = 'postgresql://web_py:12345@127.0.0.1:5432/web_py'


app = Flask(__name__)
app.config.from_mapping(SQLALCHEMY_DATABASE_URI=POSTGRE_DSN)
db = SQLAlchemy(app)
migrate = Migrate(app, db)


class BasicException(Exception):
    status_code = 0
    default_message = 'Unknown Error'

    def __init__(self, message=None, status_code=None):
        super().__init__(message)
        self.message = message
        request.status = self.status_code
        if status_code is not None:
            self.status_code = status_code

    def to_dict(self):

        return {
            'message': self.message or self.default_message
        }


class NotFound(BasicException):
    status_code = 404
    default_message = 'Not found'


class AuthError(BasicException):
    status_code = 401
    default_message = 'Auth error'


class BadLuck(BasicException):
    status_code = 400
    default_message = 'Bad luck'


@app.errorhandler(BadLuck)
@app.errorhandler(NotFound)
@app.errorhandler(AuthError)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


class BaseModelMixin:

    @classmethod
    def by_id(cls, obj_id):
        obj = cls.query.get(obj_id)
        if obj:
            return obj
        else:
            raise NotFound

    def add(self):
        db.session.add(self)
        try:
            db.session.commit()
        except exc.IntegrityError:
            raise BadLuck

    def delete(self):
        db.session.delete(self)
        try:
            db.session.commit()
        except exc.IntegrityError:
            raise BadLuck


class User(db.Model, BaseModelMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    ads = db.relationship('Ad', backref='author', lazy=True)

    def __str__(self):
        return f'User {self.username}'

    def __repr__(self):
        return str(self)

    def set_password(self, raw_password):
        raw_password = f'{raw_password}{SALT}'
        self.password = hashlib.md5(raw_password.encode()).hexdigest()

    def check_password(self, raw_password):
        raw_password = f'{raw_password}{SALT}'
        return self.password == hashlib.md5(raw_password.encode()).hexdigest()

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            "email": self.email
        }


class Ad(db.Model, BaseModelMixin):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    description = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __str__(self):
        return f'Post {self.title}, created {self.created_at}'

    def __repr__(self):
        return str(self)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'user_id': self.user_id
        }


class UserView(MethodView):

    @staticmethod
    def get(user_id):
        user = User.by_id(user_id)
        return jsonify(user.to_dict())

    @staticmethod
    def post():
        user = User(**request.json)
        user.set_password(request.json['password'])
        user.add()
        return jsonify(user.to_dict())

    @staticmethod
    def delete(user_id):
        user = User.by_id(user_id)
        user.delete()
        return jsonify({'response': 'User has been deleted'})


app.add_url_rule('/users/<int:user_id>', view_func=UserView.as_view('user_get'), methods=['GET', ])
app.add_url_rule('/users/', view_func=UserView.as_view('user_create'), methods=['POST', ])
app.add_url_rule('/users/<int:user_id>', view_func=UserView.as_view('user_delete'), methods=['DELETE', ])


class AdView(MethodView):

    @staticmethod
    def get(ad_id):
        ad = Ad.by_id(ad_id)
        return jsonify(ad.to_dict())

    @staticmethod
    def post():
        ad = Ad(**request.json)
        ad.add()
        return jsonify(ad.to_dict())

    @staticmethod
    def delete(ad_id):
        ad = Ad.by_id(ad_id)
        ad.delete()
        return jsonify({'response': 'Ad has been deleted'})


app.add_url_rule('/ad/<int:ad_id>', view_func=AdView.as_view('ad_get'), methods=['GET', ])
app.add_url_rule('/ads/', view_func=AdView.as_view('ad_create'), methods=['POST', ])
app.add_url_rule('/ad/<int:ad_id>', view_func=AdView.as_view('ad_delete'), methods=['DELETE', ])

db.create_all(app=app)

app.run()

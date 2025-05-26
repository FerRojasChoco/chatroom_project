from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

#~~~ Tables creation (class definition) ~~~#
#This is done so we can treat each table as an object and use SQLalchemy functions on them
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=True, unique=True)
    password = db.Column(db.String(80), nullable=True)
    score = db.Column(db.BigInteger, nullable=True, default=0)

    sent_requests = db.relationship(
        'Friendship',
        foreign_keys='Friendship.user_id',
        backref='sender', 
        lazy='dynamic'
    )

    received_requests = db.relationship(
        'Friendship', 
        foreign_keys='Friendship.friend_id',
        backref='receiver', 
        lazy='dynamic'
    )

    @property
    def friends(self):
        return User.query.join(
            Friendship,
            db.or_(
                db.and_(
                    Friendship.user_id == self.id,
                    Friendship.friend_id == User.id,
                    Friendship.status == 'accepted'
                ),
                db.and_(
                    Friendship.friend_id == self.id,
                    Friendship.user_id == User.id,
                    Friendship.status == 'accepted'
                )
            )
        ).all()


class Code(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_code = db.Column(db.Text, nullable=False)
    error_line_number = db.Column(db.Integer, nullable=False)
    correct_line = db.Column(db.String(255), nullable=False) #fixed size since one line of code won't be that long

class GlobalLeaderboard(db.Model):
    __tablename__ = "global_leaderboard"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(64), unique=True, nullable=False)
    username = db.Column(db.String(128), nullable=False)
    score = db.Column(db.Integer, default=0)

class Friendship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.Enum('pending', 'accepted', 'blocked', 
                         name='friendship_status'), 
                         nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    __table_args__ = (
        db.UniqueConstraint('user_id', 'friend_id', name='unique_friendship'),
    )
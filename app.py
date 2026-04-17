import profile
import random
from datetime import datetime, timezone
import re
from email.policy import default
from flask import Flask, jsonify, request, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, join_room, send, emit
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from sqlalchemy import or_, and_, desc, CheckConstraint
from flask import request, jsonify
import traceback
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import jwt
import logging
from sqlalchemy import func
from flask_migrate import Migrate
from collections import deque


app = Flask(__name__)
app.config[
    'SQLALCHEMY_DATABASE_URI'] = "postgresql://inshaapp12_render_example_user:zeu0jaQcwVljK6fBZbDTZY0zp6vIsCk2@dpg-d6tuuvsr85hc73abgtjg-a.frankfurt-postgres.render.com/inshaapp12_render_example"
socketio = SocketIO(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)  # 2️⃣ migrate second, now db exists

# Set the upload folder configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = 'a8f4c2e1b5d6f7a8c9e0d1f2b3a4c5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2'
SECRET_KEY = app.config['SECRET_KEY']

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Configure logging
logging.basicConfig(level=logging.INFO)  # Logs INFO and above
logger = logging.getLogger(__name__)

# Ensure the uploads folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# Check if the file extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


class User(db.Model):
    __tablename__ = 'userdetails'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)

    created_at = db.Column(db.DateTime,default=datetime.utcnow,nullable=False)


class UserProfile(db.Model):
    __tablename__ = 'user_profile'

    id = db.Column(db.Integer, primary_key=True)
    user_auth_id = db.Column(db.Integer,db.ForeignKey('userdetails.id'),nullable=False,unique=True)
    firstname = db.Column(db.String(255))
    lastname = db.Column(db.String(255))
    gender = db.Column(db.String(50))
    email = db.Column(db.String(200))
    age = db.Column(db.String(10))
    phone_number = db.Column(db.String(50))
    sect = db.Column(db.String(50))
    lookingfor = db.Column(db.String(255))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('profile', uselist=False))


class UserInfo(db.Model):
    __tablename__ = 'user_info'

    id = db.Column(db.Integer, primary_key=True)
    user_profile_id = db.Column(db.Integer,db.ForeignKey('user_profile.id'),nullable=False,unique=True)
    hobbies = db.Column(db.ARRAY(db.String))
    preferences = db.Column(db.ARRAY(db.String))
    bio = db.Column(db.Text)
    alcoholstatus = db.Column(db.String(25))
    childrenstatus = db.Column(db.String(25))
    maritalstatus = db.Column(db.String(25))
    smokestatus = db.Column(db.String(25))
    halalfood = db.Column(db.String(25))

    profile = db.relationship('UserProfile',backref=db.backref('info', uselist=False))


class UserCharacter(db.Model):
    __tablename__ = 'user_character'

    id = db.Column(db.Integer, primary_key=True)
    user_profile_id = db.Column(db.Integer,db.ForeignKey('user_profile.id'),nullable=False,unique=True)
    muslimstatus = db.Column(db.String(25))
    practicing = db.Column(db.String(25))
    nationality = db.Column(db.String(50))

    personality_type = db.Column(db.String(100))

    profile = db.relationship('UserProfile',backref=db.backref('character', uselist=False))


class UserImages(db.Model):
    __tablename__ = 'userImage'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_auth_id = db.Column(db.Integer, db.ForeignKey('userdetails.id'), nullable=False)
    email = db.Column(db.String(200))  # Ensure this column exists
    imageString = db.Column(db.String())
    user = db.relationship('User', backref=db.backref('user_image', lazy=True))


class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('userdetails.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('userdetails.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    sender = db.relationship('User', foreign_keys=[sender_id], backref=db.backref('sent_messages', lazy=True))
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref=db.backref('received_messages', lazy=True))


class EventHost(db.Model):
    __tablename__ = 'event_hosts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), unique=True, nullable=False)


class EventCategory(db.Model):
    __tablename__ = 'event_categories'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), unique=True, nullable=False)


class LocationInfo(db.Model):
    __tablename__ = 'locationInfo'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    maxAttendees = db.Column(db.Integer)
    maleAttendees = db.Column(db.Integer)
    femaleAttendees = db.Column(db.Integer)
    date = db.Column(db.String(200))
    time = db.Column(db.String(20))
    location = db.Column(db.String(200))
    description = db.Column(db.String(500))  # NEW FIELD    
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    totalPrice = db.Column(db.Integer)
    checkin_closed = db.Column(db.Boolean, default=False)

    # NEW FIELD
    matchmake = db.Column(db.Boolean, default=False)

    event_category_id = db.Column(db.Integer, db.ForeignKey('event_categories.id'))
    event_category = db.relationship("EventCategory")
    
    # Host (NEW)
    event_host_id = db.Column(db.Integer, db.ForeignKey('event_hosts.id'))
    event_host = db.relationship("EventHost")

    current_round = db.Column(db.Integer, default=1)


class CheckIn(db.Model):
    __tablename__ = 'checkins'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('userdetails.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('locationInfo.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    user = db.relationship('User', backref=db.backref('checkins', lazy=True))
    location = db.relationship('LocationInfo', backref=db.backref('checkins', lazy=True))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'location_id', name='unique_user_location_checkin'),
    )


class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('userdetails.id', ondelete='CASCADE'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('locationInfo.id', ondelete='CASCADE'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    hasAttended = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref=db.backref('attendances', lazy=True, cascade='all, delete-orphan'))
    location = db.relationship('LocationInfo', backref=db.backref('attendances', lazy=True, cascade='all, delete-orphan'))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'location_id', name='unique_user_location_attendance'),
    )


class UserPreference(db.Model):
    __tablename__ = 'user_preference'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('userdetails.id', ondelete='CASCADE'), nullable=False)
    preferred_user_id = db.Column(db.Integer, db.ForeignKey('userdetails.id', ondelete='CASCADE'), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id', ondelete='CASCADE'), nullable=False)
    preference = db.Column(db.String(20), nullable=False)  # 'like', 'reject', 'save_later'
    timestamp = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('preferences', lazy=True, cascade='all, delete-orphan'))
    preferred_user = db.relationship('User', foreign_keys=[preferred_user_id], backref=db.backref('preferred_by', lazy=True, cascade='all, delete-orphan'))
    match = db.relationship('Match', backref=db.backref('preferences', lazy=True, cascade='all, delete-orphan'))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'preferred_user_id', 'match_id', name='unique_user_match_preference'),
    )


class Match(db.Model):
    __tablename__ = 'matches'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('userdetails.id'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('userdetails.id'), nullable=False)
    match_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    visible_after = db.Column(db.Integer)
    status = db.Column(db.String(20), default='pending')  # 'active or expired'
    consent = db.Column(db.String(20), default='pending')  # 'pending', 'active', 'deleted'
    location_id = db.Column(db.Integer, db.ForeignKey('locationInfo.id'), nullable=True)
    matched_expired = db.Column(db.Boolean, default=False)  # <-- New boolean column
    round_number = db.Column(db.Integer, default=1)  # 🆕 round-robin tracking

    # Relationships
    user1 = db.relationship('User', foreign_keys=[user1_id], backref=db.backref('matches_as_user1', lazy=True))
    user2 = db.relationship('User', foreign_keys=[user2_id], backref=db.backref('matches_as_user2', lazy=True))
    location = db.relationship('LocationInfo', backref=db.backref('matches_at_location', lazy=True))


# 1️⃣ Association tables FIRST
post_hashtag = db.Table(
    'post_hashtag',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True),
    db.Column('hashtag_id', db.Integer, db.ForeignKey('hashtag.id'), primary_key=True)
)
    
    
class Post(db.Model):
    __tablename__ = 'post'

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('userdetails.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    post_type = db.Column(db.String(20))
    media_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_deleted = db.Column(db.Boolean, default=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=True)
    hashtags = db.relationship('Hashtag', secondary='post_hashtag', backref='posts')
    likes = db.relationship('Like', backref='post', lazy=True, cascade="all, delete-orphan")
    comments = db.relationship('Comment', backref='post', lazy=True, cascade="all, delete-orphan")
    author = db.relationship('User', backref='posts', foreign_keys=[author_id])  # ✅ added

    __table_args__ = (
        db.Index('idx_post_created', 'created_at'),
    )


class Comment(db.Model):
    __tablename__ = 'comment'

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'), nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey('userdetails.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id', ondelete='CASCADE'), nullable=True, index=True)
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]), cascade="all, delete-orphan", lazy=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_deleted = db.Column(db.Boolean, default=False)

    __table_args__ = (
        db.Index('ix_comment_post_parent', 'post_id', 'parent_id'),
        db.Index('ix_comment_created', 'created_at'),
    )                                                             # ✅ Nothing after this


class Hashtag(db.Model):
    __tablename__ = 'hashtag'

    id = db.Column(db.Integer, primary_key=True)
    tag = db.Column(db.String(50), unique=True, nullable=False)


class Like(db.Model):
    __tablename__ = 'like'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('userdetails.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.CheckConstraint(
            '(post_id IS NOT NULL AND comment_id IS NULL) OR '
            '(post_id IS NULL AND comment_id IS NOT NULL)',
            name='like_on_post_or_comment'
        ),
        db.UniqueConstraint('user_id', 'post_id', name='unique_user_post_like'),
        db.UniqueConstraint('user_id', 'comment_id', name='unique_user_comment_like'),
    )
    

class Follow(db.Model):
    __tablename__ = 'follow'

    follower_id = db.Column(db.Integer,db.ForeignKey('userdetails.id'),primary_key=True)
    following_id = db.Column(db.Integer,db.ForeignKey('userdetails.id'),primary_key=True)
    created_at = db.Column(db.DateTime,default=datetime.utcnow,nullable=False)

    __table_args__ = (
        CheckConstraint('follower_id != following_id', name='no_self_follow'),
    )

    
class Report(db.Model):
    __tablename__ = 'report'

    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('userdetails.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)
    reported_user_id = db.Column(db.Integer, db.ForeignKey('userdetails.id'), nullable=True)
    reason = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.CheckConstraint(
            '(post_id IS NOT NULL AND comment_id IS NULL) OR '
            '(post_id IS NULL AND comment_id IS NOT NULL)',
            name='report_on_post_or_comment'
        ),
    )
    

# 1️⃣ Association table MUST come first
group_members = db.Table(
    'group_members',
    db.Column('group_id', db.Integer, db.ForeignKey('groups.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('userdetails.id'), primary_key=True)
)


class Groups(db.Model):
    __tablename__ = 'groups'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(255))
    gender_restriction = db.Column(db.String(50), default="all", nullable=False)  # "all", "male", "female"
    
    creator_id = db.Column(
        db.Integer,
        db.ForeignKey('userdetails.id'),
        nullable=False
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', backref='created_groups')
    members = db.relationship(
        'User',
        secondary=group_members,
        backref='groups'
    )
    posts = db.relationship('Post', backref='group', lazy=True)

    @property 
    def members_count(self):
        return len(self.members)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "image_url": self.image_url,
            "members_count": self.members_count,
            "gender_restriction": self.gender_restriction,
            "created_at": self.created_at.isoformat(),
        }


with app.app_context():
    # Match.__table__.drop(db.engine)
    # UserPreference.__table__.drop(db.engine)
    # Attendance.__table__.drop(db.engine)
    # CheckIn.__table__.drop(db.engine)
    db.create_all()


# API Endpoints

def get_comments(post_id):
    return Comment.query.filter_by(
        post_id=post_id,
        parent_id=None
    ).order_by(Comment.created_at.asc()).all()
    
# EVENT HOSTS -> Start
    
@app.route('/event-hosts', methods=['GET'])
def get_all_event_hosts():
    try:
        hosts = EventHost.query.order_by(EventHost.id.asc()).all()
        results = [{"id": host.id, "name": host.name} for host in hosts]
        return jsonify(results), 200

    except Exception as e:
        logger.error("Fatal error in GET /event-hosts", exc_info=True)
        return jsonify({"error": "internal_server_error"}), 500
    
#EVENT HOSTS -> END

# MAKE SOCIAL MEDIA POSTS -> Start

@app.route('/posts', methods=['POST'])
def create_post():
    # ✅ Auth header check
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return jsonify({"error": "Missing authorization"}), 401

    parts = auth_header.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return jsonify({"error": "Invalid authorization format"}), 401

    token = parts[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        author_id = payload.get("user_id")
    except Exception:
        return jsonify({"error": "Invalid token"}), 401

    # ✅ Body check
    data = request.json
    if not data:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    # ✅ Text validation
    text = data.get('text', '').strip()
    if not text:
        return jsonify({"error": "Post text is required"}), 400

    post = Post(
        author_id=author_id,
        text=text,
        post_type=data.get('post_type', 'text'),
        media_url=data.get('media_url'),
    )

    db.session.add(post)
    db.session.commit()

    return jsonify({
        "id": post.id,
        "text": post.text,
        "post_type": post.post_type,
        "media_url": post.media_url,
        "created_at": post.created_at.isoformat(),
        "is_deleted": False,
        "hashtags": [],
        "isFollowing": False
    }), 201


# Get all users posts in the app feed
@app.route('/posts/feed', methods=['GET'])
def get_all_posts():
    current_user = get_current_user_from_token()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    limit = request.args.get('limit', 10, type=int)
    cursor = request.args.get('cursor')

    query = Post.query.filter_by(is_deleted=False).order_by(Post.created_at.desc())

    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
            query = query.filter(Post.created_at < cursor_dt)
        except ValueError:
            return jsonify({"error": "Invalid cursor format"}), 400

    posts = query.limit(limit + 1).all()
    has_more = len(posts) > limit
    posts = posts[:limit]

    if not posts:
        return jsonify({"posts": [], "next_cursor": None, "has_more": False}), 200

    next_cursor = posts[-1].created_at.isoformat() if has_more else None
    post_ids = [p.id for p in posts]

    # ── 1. Fetch all comments for these posts in ONE query ──────────────────
    all_comments = Comment.query.filter(
        Comment.post_id.in_(post_ids),
        Comment.is_deleted == False
    ).order_by(Comment.created_at.asc()).all()

    # ── 2. Batch-fetch all author profiles + images ──────────────────────────
    author_ids = {c.author_id for c in all_comments}
    profile_map = {
        p.user_auth_id: p
        for p in UserProfile.query.filter(UserProfile.user_auth_id.in_(author_ids)).all()
    }
    image_map = {
        img.user_auth_id: img
        for img in UserImages.query.filter(UserImages.user_auth_id.in_(author_ids)).all()
    }

    # ── 3. Batch-fetch like counts for all comments ──────────────────────────
    comment_ids = [c.id for c in all_comments]
    like_map = {
        comment_id: count
        for comment_id, count in db.session.query(
            Like.comment_id,
            func.count(Like.user_id)
        ).filter(Like.comment_id.in_(comment_ids))
         .group_by(Like.comment_id).all()
    } if comment_ids else {}

    # ── 4. Build serialized comment nodes ────────────────────────────────────
    comment_map = {}
    for c in all_comments:
        profile = profile_map.get(c.author_id)
        user_image = image_map.get(c.author_id)
        comment_map[c.id] = {
            "id": c.id,
            "post_id": c.post_id,
            "author_name": f"{profile.firstname} {profile.lastname}" if profile else "",
            "text": c.content or "",
            "created_at": c.created_at.isoformat(),
            "like_count": like_map.get(c.id, 0),
            "parent_id": c.parent_id,
            "user_image": user_image.imageString if user_image else None,
            "replies": []
        }

    # ── 5. Nest replies under their parent comments ───────────────────────────
    post_root_comments = {pid: [] for pid in post_ids}
    for c in all_comments:
        node = comment_map[c.id]
        if c.parent_id and c.parent_id in comment_map:
            comment_map[c.parent_id]["replies"].append(node)
        elif not c.parent_id:
            post_root_comments[c.post_id].append(node)
    
            
    # ── 6. Batch-fetch follow statuses for all post authors ──────────────────
    post_author_ids = [p.author_id for p in posts]
    followed_ids = {
        f.following_id
        for f in Follow.query.filter(
            Follow.follower_id == current_user.id,
            Follow.following_id.in_(post_author_ids)
        ).all()
    }
    
    print(f"DEBUG current_user.id: {current_user.id}")
    print(f"DEBUG post_author_ids: {post_author_ids}")
    print(f"DEBUG followed_ids: {followed_ids}")

    # ── 7. Attach comments to each serialized post ───────────────────────────
    serialized_posts = []
    for post in posts:
        p = serialize_post(post, current_user, is_following=post.author_id in followed_ids)
        p["comments"] = post_root_comments.get(post.id, [])
        p["comment_count"] = len(p["comments"])
        serialized_posts.append(p)

    return jsonify({
        "posts": serialized_posts,
        "next_cursor": next_cursor,
        "has_more": has_more
    }), 200


# Get only the logged-in user's posts
@app.route('/posts/my_posts', methods=['GET'])
def get_my_posts():
    # Get the currently logged-in user from the token
    user = get_current_user_from_token()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    # Fetch only posts authored by this user
    posts = (
        Post.query
        .filter_by(author_id=user.id, is_deleted=False)
        .order_by(Post.created_at.desc())
        .all()
    )

    # Serialize posts
    return jsonify({
        "posts": [serialize_post(post) for post in posts]
    }), 200


def serialize_post(post: Post, current_user=None, is_following: bool = False):
    profile = UserProfile.query.filter_by(user_auth_id=post.author_id).first()
    user_image = UserImages.query.filter_by(user_auth_id=post.author_id).first()
    like_count = Like.query.filter_by(post_id=post.id).count()

    user_liked = False
    if current_user:
        user_liked = Like.query.filter_by(post_id=post.id, user_id=current_user.id).first() is not None

    return {
        "id": post.id,
        "author_id": post.author_id,
        "author_name": f"{profile.firstname} {profile.lastname}" if profile else None,
        "author_email": profile.email if profile else None,
        "user_image": user_image.imageString if user_image else None,
        "text": post.text,
        "post_type": post.post_type,
        "media_url": post.media_url,
        "created_at": post.created_at.isoformat(),
        "is_deleted": post.is_deleted,
        "hashtags": [tag.name for tag in post.hashtags],
        "like_count": like_count,
        "user_liked": user_liked,
        "is_following": is_following   # ← added
    }
    

# This endpoint allows users to create comments on posts. Comments can also be replies to other comments, allowing for nested threads.
@app.route('/posts/<int:post_id>/comments', methods=['POST'])
def create_comment(post_id):
    current_user = get_current_user_from_token()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    # ✅ Ignore deleted posts
    post = Post.query.filter_by(id=post_id, is_deleted=False).first()
    if not post:
        return jsonify({"error": "Post not found"}), 404

    data = request.get_json() or {}
    text = data.get("text")
    parent_id = data.get("parent_id")

    if not text or not text.strip():
        return jsonify({"error": "Text is required"}), 400

    # ✅ Ignore deleted parent comments
    if parent_id:
        parent_comment = Comment.query.filter_by(id=parent_id, is_deleted=False).first()
        if not parent_comment:
            return jsonify({"error": "Parent comment not found"}), 404
        if parent_comment.post_id != post_id:
            return jsonify({"error": "Invalid parent comment"}), 400

    comment = Comment(
        post_id=post_id,
        author_id=current_user.id,
        content=text.strip(),
        parent_id=parent_id
    )

    db.session.add(comment)
    db.session.commit()

    return jsonify({
        "id": comment.id,
        "post_id": comment.post_id,
        "parent_id": comment.parent_id,
        "content": comment.content,
        "created_at": comment.created_at.isoformat()
    }), 201


# Fetches comments for a given post
@app.route('/posts/<int:post_id>/comments', methods=['GET'])
def get_post_comments(post_id):
    current_user = get_current_user_from_token()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    all_comments = Comment.query.filter(
        Comment.post_id == post_id,
        Comment.is_deleted == False
    ).order_by(Comment.created_at.asc()).all()

    if not all_comments:
        return jsonify({"post_id": post_id, "comments": []}), 200

    author_ids = {c.author_id for c in all_comments}

    profiles = UserProfile.query.filter(UserProfile.user_auth_id.in_(author_ids)).all()
    profile_map = {p.user_auth_id: p for p in profiles}

    images = UserImages.query.filter(UserImages.user_auth_id.in_(author_ids)).all()
    image_map = {img.user_auth_id: img for img in images}

    like_counts = db.session.query(
        Like.comment_id,
        func.count(Like.user_id)
    ).filter(
        Like.comment_id.in_([c.id for c in all_comments])
    ).group_by(Like.comment_id).all()
    like_map = {comment_id: count for comment_id, count in like_counts}

    comment_map = {}
    roots = []

    for c in all_comments:
        profile = profile_map.get(c.author_id)
        user_image = image_map.get(c.author_id)

        comment_map[c.id] = {
            "id": c.id,
            "author_name": f"{profile.firstname} {profile.lastname}" if profile else "",
            "text": c.content or "",
            "created_at": c.created_at.isoformat(),
            "like_count": like_map.get(c.id, 0),
            "parent_id": c.parent_id,
            "user_image": user_image.imageString if user_image else None,
            "replies": []
        }

    for c in all_comments:
        if c.parent_id:
            parent = comment_map.get(c.parent_id)
            if parent:
                parent["replies"].append(comment_map[c.id])
        else:
            roots.append(comment_map[c.id])

    return jsonify({
        "post_id": post_id,
        "comments": roots
    }), 200
    
    
# This endpoint allows users to edit their own comments. Admins can also edit any comment.    
@app.route('/posts/<int:comment_id>', methods=['PUT'])
def edit_comment(comment_id):
    current_user = get_current_user_from_token()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    comment = Post.query.get_or_404(comment_id)

    # Ensure this is a comment
    if comment.parent_id is None:
        return jsonify({"error": "Not a comment"}), 400

    # Prevent editing deleted comments
    if comment.is_deleted:
        return jsonify({"error": "Comment deleted"}), 400

    # Ownership check
    if comment.author_id != current_user.id:
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json() or {}
    new_text = data.get("text")

    if not new_text or not new_text.strip():
        return jsonify({"error": "Text is required"}), 400

    comment.text = new_text.strip()
    db.session.commit()

    return jsonify(serialize_post(comment, current_user)), 200


# This endpoint performs a soft delete by setting is_deleted=True
@app.route('/posts/<int:comment_id>', methods=['DELETE'])
def delete_comment(comment_id):
    current_user = get_current_user_from_token()
    comment = Post.query.get_or_404(comment_id)

    if not (
        comment.author_id == current_user.id or current_user.is_admin
    ):
        return jsonify({"error": "Forbidden"}), 403

    comment.is_deleted = True
    db.session.commit()

    return jsonify({"success": True}), 200


# This endpoint toggles like/unlike for a post
@app.route('/posts/<int:post_id>/like', methods=['POST'])
def toggle_like(post_id):
    current_user = get_current_user_from_token()

    like = Like.query.filter_by(
        user_id=current_user.id,
        post_id=post_id
    ).first()

    if like:
        db.session.delete(like)
        db.session.commit()
        return jsonify({"liked": False}), 200

    db.session.add(Like(user_id=current_user.id, post_id=post_id))
    db.session.commit()
    return jsonify({"liked": True}), 200


# MAKE SOCIAL MEDIA POSTS -> END

# CREATE A GROUP -> START
@app.route('/groups', methods=['POST'])
def create_group(): 
    current_user = get_current_user_from_token()

    data = request.json
    name = data.get("name")
    description = data.get("description")
    image_url = data.get("image_url")
    gender_restriction = data.get("gender_restriction")

    if not name:
        return jsonify({"error": "Group name is required"}), 400

    if Groups.query.filter_by(name=name).first():
        return jsonify({"error": "Group name already exists"}), 409

    try: 
        group = Groups(
            name=name,
            description=description,
            image_url=image_url,
            gender_restriction=gender_restriction,
            creator_id=current_user.id
        )

        group.members.append(current_user)

        db.session.add(group)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "status": "group_created",
        "group": {
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "image_url": group.image_url,
            "creator_id": group.creator_id,
            "gender_restriction": group.gender_restriction,
            "members_count": group.members_count,
            "created_at": group.created_at.isoformat()
        }
    }), 201


@app.route('/groups', methods=['GET'])
def get_all_groups():
    current_user = get_current_user_from_token()
    user_id = current_user.id if current_user else None

    try:
        groups = Groups.query.order_by(Groups.created_at.desc()).all()
        results = []

        for group in groups:
            top_post = max(group.posts, key=lambda p: len(p.likes)) if group.posts else None

            results.append({
                "id": group.id,
                "name": group.name,
                "description": group.description,
                "image_url": group.image_url,
                "creator": {
                    "id": group.creator.id,
                    "email": group.creator.email
                },
                "members_count": group.members_count,
                "is_member": user_id in [u.id for u in group.members],
                "gender_restriction": group.gender_restriction,
                "top_post": {
                    "id": top_post.id,
                    "text": top_post.text,
                    "post_type": top_post.post_type,
                    "media_url": top_post.media_url,
                    "created_at": top_post.created_at.isoformat(),
                    "is_deleted": top_post.is_deleted,
                    "group_id": top_post.group_id,
                    "likes_count": len(top_post.likes),
                    "comments_count": len(top_post.comments),
                    "hashtags": [h.name for h in top_post.hashtags],
                    "author": {
                        "id": top_post.author.id,
                        "email": top_post.author.email,
                    }
                } if top_post else None,
                "created_at": group.created_at.isoformat()
            })

        return jsonify(results), 200

    except Exception as e:
        logger.error("Fatal error in GET /groups", exc_info=True)
        return jsonify({"error": "internal_server_error"}), 500


@app.route('/groups/<int:group_id>/join', methods=['POST'])
def join_group(group_id):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return jsonify({"error": "Missing authorization"}), 401

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401

    user_id = payload.get("user_id")
    if not user_id:
        return jsonify({"error": "Invalid token payload"}), 401

    group = db.session.get(Groups, group_id)
    if not group:
        return jsonify({"error": "Group not found"}), 404

    user = db.session.get(User, user_id)
    if user in group.members:
        return jsonify({"error": "User already a member"}), 400

    try:
        group.members.append(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "status": "joined",
        "group_id": group.id,
        "members_count": group.members_count
    }), 200



@app.route('/groups/<int:group_id>/leave', methods=['POST'])
def leave_group(group_id):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return jsonify({"error": "Missing authorization"}), 401

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401

    user_id = payload.get("user_id")
    if not user_id:
        return jsonify({"error": "Invalid token payload"}), 401

    group = db.session.get(Groups, group_id)
    if not group:
        return jsonify({"error": "Group not found"}), 404

    user = db.session.get(User, user_id)
    if user not in group.members:
        return jsonify({"error": "User is not a member of this group"}), 400

    # Optional: prevent creator from leaving their own group
    if group.creator_id == user_id:
        return jsonify({"error": "Group creator cannot leave their own group"}), 400

    try:
        group.members.remove(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "status": "left",
        "group_id": group.id,
        "members_count": group.members_count
    }), 200


# CREATE A GROUP -> END

# LIKE POSTS -> Start

@app.route("/like", methods=["POST"])
def create_like():
    current_user = get_current_user_from_token()
    if not current_user:
        return jsonify({"error": "Unauthorized or token expired"}), 401

    data = request.json
    post_id = data.get("post_id")
    comment_id = data.get("comment_id")

    # ✅ Must have one, but not both
    if not post_id and not comment_id:
        return jsonify({"error": "Either post_id or comment_id is required"}), 400
    if post_id and comment_id:
        return jsonify({"error": "Cannot like both a post and comment at the same time"}), 400

    try:
        new_like = Like(
            user_id=current_user.id,
            post_id=post_id,
            comment_id=comment_id
        )
        db.session.add(new_like)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"message": "Already liked"}), 200

    return jsonify({
        "user_id": current_user.id,
        "post_id": post_id,
        "comment_id": comment_id,
        "created_at": new_like.created_at.isoformat()
    }), 201


@app.route("/like/<int:post_id>", methods=["DELETE"])
def delete_like(post_id):
    current_user = get_current_user_from_token()

    existing_like = Like.query.filter_by(
        user_id=current_user.id,
        post_id=post_id
    ).first()

    if not existing_like:
        return jsonify({"message": "Like does not exist"}), 404

    db.session.delete(existing_like)
    db.session.commit()

    return jsonify({
        "user_id": current_user.id,
        "post_id": post_id,
        "message": "Like removed"
    }), 200


# LIKE POSTS -> END

# FOLLOW USERS -> START

@app.route('/follow', methods=['POST'])
def follow_user():
    current_user = get_current_user_from_token()

    data = request.json
    following_id = data.get("following_id")
    if not following_id:
        return jsonify({"error": "following_id is required"}), 400

    if current_user.id == following_id:
        return jsonify({"error": "You cannot follow yourself"}), 400

    try:
        follow = Follow(
            follower_id=current_user.id,
            following_id=following_id
        )
        db.session.add(follow)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"message": "Already following"}), 200

    return jsonify({
        "follower_id": current_user.id,
        "following_id": following_id,
        "is_following": True        # ← just confirms the action result
    }), 201

    
@app.route('/unfollow/<int:following_id>', methods=['DELETE'])
def unfollow_user(following_id):
    current_user = get_current_user_from_token()

    if current_user.id == following_id:
        return jsonify({"error": "You cannot unfollow yourself"}), 400

    follow = Follow.query.filter_by(
        follower_id=current_user.id,
        following_id=following_id
    ).first()

    if not follow:
        return jsonify({"message": "Not following"}), 200

    db.session.delete(follow)
    db.session.commit()

    return jsonify({
        "follower_id": current_user.id,
        "following_id": following_id,
        "is_following": False,      # ← just confirms the action result
        "message": "Unfollowed successfully"
    }), 200

# FOLLOW USERS -> END


@app.route('/feed/<int:user_id>')
def feed(user_id):
    followed = db.session.query(Follow.following_id)\
        .filter(Follow.follower_id == user_id)

    posts = Post.query.filter(
        Post.author_id.in_(followed),
        Post.parent_id.is_(None)
    ).order_by(Post.created_at.desc()).limit(50).all()

    return [{"id": p.id, "text": p.text} for p in posts]


# REPORT USERS -> START

@app.route('/report', methods=['POST'])
def report_post():
    current_user = get_current_user_from_token()

    data = request.json
    print("REPORT REQUEST DATA:", data)  # ✅ add here
    post_id = data.get("post_id")
    reason = data.get("reason")
    reported_user_id = data.get("reported_user_id")  # ✅ added

    if not post_id or not reason:
        return jsonify({"error": "post_id and reason are required"}), 400

    # ✅ Check if post exists
    post = db.session.get(Post, post_id)
    if not post:
        return jsonify({"error": f"Post with id {post_id} not found"}), 404

    try:
        report = Report(
            reporter_id=current_user.id,
            post_id=post_id,
            reason=reason,
            reported_user_id=reported_user_id  # ✅ added
        )
        db.session.add(report)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "status": "reported",
        "reporter_id": current_user.id,
        "post_id": post_id,
        "reported_user_id": reported_user_id  # ✅ added
    }), 201


# REPORT USERS -> END

def has_user_checked_in(user_id, location_id):
    return db.session.query(CheckIn).filter_by(user_id=user_id, location_id=location_id).first() is not None


def create_token(user):
    payload = {
        "user_id": user.id,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm="HS256")


def get_current_user_from_token():
    auth_header = request.headers.get('Authorization', None)
    if not auth_header or not auth_header.startswith("Bearer "):
        print("No Authorization header or wrong format")
        return None

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        print("Decoded JWT payload:", payload)
        user_id = payload.get('user_id')
        user = User.query.get(user_id)
        print("Fetched user from DB:", user)
        return user
    except jwt.ExpiredSignatureError:
        print("JWT expired")
        return None
    except jwt.InvalidTokenError as e:
        print("JWT invalid:", e)
        return None


@app.route('/sign-in', methods=['POST'])
def sign_in():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        user = User.query.filter_by(email=email).first()
        if not user or password != user.password:
            return jsonify({'message': 'Invalid credentials'}), 401

        payload = {
            'user_id': user.id,
            'exp': datetime.utcnow() + timedelta(days=7)
        }
        token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
        if isinstance(token, bytes):
            token = token.decode('utf-8')

        return jsonify({'message': 'Sign in successful', 'token': token}), 200
    except Exception as e:
        print("Sign-in error:", e)
        return jsonify({'error': str(e)}), 500


@app.route('/sign-in', methods=['GET'])
def get_signin_data():
    signin = User.query.all()
    data = [
        {
            'id': rel.id,
            'email': rel.email,
            'password': rel.password,
        }
        for rel in signin
    ]
    return jsonify(data)


# USER SIGNIN METHOD -> End

# METHOD TO GET AUTHENTICATED USERS LIST -> Start

@app.get("/users")
def home():
    tasks = User.query.all()
    task_list = [
        {'id': task.id, 'email': task.email, 'password': task.password} for task in tasks
    ]
    return jsonify({"user_details": task_list})


# POST USER CREDENTIALS TO DATABASE

@app.route('/users', methods=['POST'])
def postData():
    try:
        data = request.get_json()
        new_email = data.get('email')
        new_password = data.get('password')

        if not new_email or not new_password:
            return jsonify({'error': 'Email and password are required'}), 400

        # Validate email
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_regex, new_email):
            return jsonify({'message': 'Invalid email format'}), 400

        # Check if email exists
        if User.query.filter_by(email=new_email).first():
            return jsonify({'message': 'Email already exists'}), 400

        # Create user
        new_user = User(email=new_email, password=new_password)
        db.session.add(new_user)
        db.session.commit()

        # Create token
        payload = {
            'user_id': new_user.id,
            'exp': datetime.utcnow() + timedelta(days=7)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        if isinstance(token, bytes):
            token = token.decode('utf-8')

        return jsonify({'message': "New User added", 'token': token}), 201

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# Added from wingit matchmaking logic -> START

def update_match_consent_status(user1_id, user2_id, match_id):
    """
    Checks both users' preferences and updates match consent.
    - If both 'like' → consent = 'active'
    - If any 'reject' → consent = 'deleted'
    - Else → consent = 'pending'
    """
    match = Match.query.get(match_id)

    if not match:
        print(f"No match found for match_id {match_id}")
        return

    pref1 = UserPreference.query.filter_by(user_id=user1_id, preferred_user_id=user2_id, match_id=match.id).first()
    pref2 = UserPreference.query.filter_by(user_id=user2_id, preferred_user_id=user1_id, match_id=match.id).first()

    if not pref1 or not pref2:
        # Not both preferences submitted yet
        return

    # New consent logic
    p1 = pref1.preference
    p2 = pref2.preference

    if p1 == 'like' and p2 == 'like':
        match.consent = 'active'
    elif p1 == 'reject' or p2 == 'reject':
        match.consent = 'deleted'
    else: # Handles (like, save_later), (save_later, like), and (save_later, save_later)
        match.consent = 'pending'

    db.session.commit()
    print(f"✅ Match consent updated for users {user1_id} and {user2_id}: {match.consent}")


def end_matchmaking_round(location_id):
    """
    Expires active matches for the current round and increments the round counter.

    Returns:
        bool: True if a next round should be triggered, False if matchmaking is complete.
    """
    active_matches = Match.query.filter_by(
        location_id=location_id,
        status='active',
        matched_expired=False
    ).all()

    if not active_matches:
        print(f"No active matches to end for location {location_id}")
        # If there are no active matches, no new round should be triggered from here.
        return False

    for match in active_matches:
        match.status = 'expired'
        match.matched_expired = True

    location = LocationInfo.query.get(location_id)
    if not location:
        return False  # Cannot proceed

    # Get male/female counts from checked-in users to be precise
    checkins = CheckIn.query.filter_by(location_id=location_id).all()
    user_ids = [c.user_id for c in checkins]
    users = UserProfile.query.filter(UserProfile.user_auth_id.in_(user_ids)).all()
    
    num_males = sum(1 for u in users if u.gender and u.gender.lower() in ['male', 'man', 'men'])
    num_females = sum(1 for u in users if u.gender and u.gender.lower() in ['female', 'woman', 'women'])
    
    total_possible_pairs = num_males * num_females
    
    # Count pairs already made
    matches_made_count = Match.query.filter_by(location_id=location_id).count()

    # Increment the round number before the check
    location.current_round += 1
    db.session.commit()

    # If all possible pairs have been made, signal to stop.
    if matches_made_count >= total_possible_pairs:
        print(f"All {total_possible_pairs} possible matches have been made for location {location_id}. Matchmaking finished.")
        return False  # Signal that matchmaking is complete

    return True  # Signal to continue to the next round


def get_unix_timestamp(datatime):
    # Convert to Unix timestamp (seconds since epoch)
    unix_ts = int(datatime.timestamp())

    return unix_ts


def hopcroft_karp(males, females, allowed_pairs):
    """
    males: list of male user IDs
    females: list of female user IDs
    allowed_pairs: list of (male_id, female_id) tuples that can be paired
    Returns: list of matched pairs [(male_id, female_id), ...]
    """
    # Build bipartite graph
    graph = {m: [] for m in males}
    for m, f in allowed_pairs:
        graph[m].append(f)

    pair_u = {m: None for m in males}      # male -> female
    pair_v = {f: None for f in females}    # female -> male
    dist = {}

    def bfs():
        queue = deque()
        for u in males:
            if pair_u[u] is None:
                dist[u] = 0
                queue.append(u)
            else:
                dist[u] = float('inf')
        dist[None] = float('inf')

        while queue:
            u = queue.popleft()
            if dist[u] < dist[None]:
                for v in graph[u]:
                    if dist[pair_v[v]] == float('inf'):
                        dist[pair_v[v]] = dist[u] + 1
                        queue.append(pair_v[v])
        return dist[None] != float('inf')

    def dfs(u):
        if u is None:
            return True
        for v in graph[u]:
            if dist[pair_v[v]] == dist[u] + 1:
                if dfs(pair_v[v]):
                    pair_u[u] = v
                    pair_v[v] = u
                    return True
        dist[u] = float('inf')
        return False

    matching = 0
    while bfs():
        for u in males:
            if pair_u[u] is None:
                if dfs(u):
                    matching += 1

    return [(m, f) for m, f in pair_u.items() if f is not None]


def generate_ordered_round_robin(males, females, round_number):
    """
    Generates pairs for a specific round using a deterministic round-robin algorithm,
    matching the pattern M(i) -> F(i + round - 1).

    This ensures a predictable and ordered sequence of matches for each round.

    Args:
        males (list): A list of male user IDs, sorted to ensure consistency.
        females (list): A list of female user IDs, sorted to ensure consistency.
        round_number (int): The current round number (1-based).

    Returns:
        list: A list of tuples, where each tuple is a (male_id, female_id) pair.
              Returns an empty list if no pairings are possible.
    """
    num_males = len(males)
    num_females = len(females)

    # If either group is empty, no pairs can be made.
    if not num_males or not num_females:
        return []

    pairs = []

    # Use a deque for efficient rotation of the females list.
    from collections import deque
    females_deque = deque(females)

    # The rotation amount is based on the round number.
    # For round 1, rotate by 0. For round 2, rotate left by 1, and so on.
    # This creates the shifting pattern M(i) -> F(i + shift).
    rotation_amount = -(round_number - 1)
    females_deque.rotate(rotation_amount)
    
    rotated_females = list(females_deque)

    # The number of pairs in a round is limited by the smaller group size.
    # Users in the larger group may be left out in any given round.
    pairing_size = min(num_males, num_females)

    # Create pairs between the fixed males list and the rotated females list.
    for i in range(pairing_size):
        pairs.append((males[i], rotated_females[i]))

    return pairs


def is_round_complete(location_id):
    """
    Returns True if all matches in the current round have been decided.
    A match is decided if:
    - It has been rejected by at least one user.
    - It has preferences from both users.
    """
    location = LocationInfo.query.get(location_id)
    if not location:
        return False

    # Get all matches for the current round, regardless of status.
    all_matches_for_round = Match.query.filter_by(
        location_id=location_id,
        round_number=location.current_round
    ).all()

    if not all_matches_for_round:
        return False  # No matches in the round, so it's not "complete".

    for match in all_matches_for_round:
        pref1 = UserPreference.query.filter_by(user_id=match.user1_id, preferred_user_id=match.user2_id, match_id=match.id).first()
        pref2 = UserPreference.query.filter_by(user_id=match.user2_id, preferred_user_id=match.user1_id, match_id=match.id).first()

        # A match is only decided when both users have submitted their preference.
        if not pref1 or not pref2:
            return False  # This match is still undecided.

    # If we get through the whole loop, all matches are decided.
    return True


def trigger_matchmaking_for_location(location_id):
    """
    Trigger matchmaking for all checked-in users at a specific location.
    - Maximal male-female matches per round using Hopcroft-Karp.
    - Each user appears only once per round.
    - Only create matches that have never occurred at this location.
    - Automatically expires previous round matches and increments round counter.
    """
    try:
        # 1️⃣ Get location info
        location = LocationInfo.query.get(location_id)
        if not location:
            print(f"⚠️ Location {location_id} not found")
            return None

        # ✅ Use the current round directly, do not recalculate or increment
        current_round = location.current_round
        print(f"Starting matchmaking for round {current_round} at location {location_id}")
        
        # ⚠️ Add the safety check here BEFORE creating new matches
        if Match.query.filter_by(location_id=location_id, round_number=location.current_round, status='active').first():
            print("Skipping: round already active")
            return None
        
        # 🧩 ADD THIS SAFETY CHECK HERE 👇
        last_match = (
            Match.query.filter_by(location_id=location_id)
            .order_by(Match.id.desc())
            .first()
        )
        if last_match and last_match.round_number == location.current_round:
            print(f"⚠️ Round {location.current_round} already active at location {location_id}. Skipping duplicate trigger.")
            return None

        # 2️⃣ Expire previous active matches
        active_matches = Match.query.filter_by(
            location_id=location_id,
            status='active',
            matched_expired=False
        ).all()
        for m in active_matches:
            m.status = 'expired'
            m.matched_expired = True
        db.session.commit()
        if active_matches:
            print(f"Marked {len(active_matches)} previous active matches as expired")

        # 3️⃣ Get checked-in users
        checkins = CheckIn.query.filter_by(location_id=location_id).all()
        user_ids = [c.user_id for c in checkins]
        if len(user_ids) < 2:
            print(f"Not enough users for matchmaking at location {location_id}")
            return None

        users = [User.query.get(uid) for uid in user_ids if User.query.get(uid)]
        if len(users) < 2:
            print(f"Not enough valid users for matchmaking at location {location_id}")
            return None

        # 4️⃣ Separate users by gender
        males, females = [], []
        for u in users:
            udata = UserProfile.query.filter_by(user_auth_id=u.id).first()
            if not udata or not udata.gender:
                continue
            gender = udata.gender.lower()
            if gender in ['male', 'man', 'men']:
                males.append(u.id)
            elif gender in ['female', 'woman', 'women']:
                females.append(u.id)

        if not males or not females:
            print(f"No male-female pairs possible at location {location_id}")
            return None

        # 5️⃣ Determine previously paired users at this location
        previous_matches = Match.query.filter_by(location_id=location_id).all()
        previous_pairs = set((m.user1_id, m.user2_id) for m in previous_matches)

        # 6️⃣ Generate potential pairs for the current round using the ordered round-robin algorithm
        potential_pairs_for_this_round = generate_ordered_round_robin(sorted(males), sorted(females), current_round)

        # 7️⃣ Filter out pairs that have already occurred in previous rounds
        selected_pairs = []
        for m, f in potential_pairs_for_this_round:
            # Ensure the pair (m, f) or (f, m) has not been matched before
            if (m, f) not in previous_pairs and (f, m) not in previous_pairs:
                selected_pairs.append((m, f))

        if not selected_pairs:
            print(f"No new matches available for round {current_round} at location {location_id}. All possible unique pairs have been exhausted or this round's pairs already occurred.")
            return None

        # 8️⃣ Create matches
        for m, f in selected_pairs:
            visible_after = int((datetime.now(timezone.utc) + timedelta(minutes=20)).timestamp())
            new_match = Match(
                user1_id=m,
                user2_id=f,
                status='active',
                matched_expired=False,
                location_id=location_id,
                visible_after=visible_after,
                round_number=current_round
            )
            db.session.add(new_match)

        # 9️⃣ Commit (increment of round happens in end_matchmaking_round)
        db.session.commit()

        print(f"✅ Round {current_round} created with {len(selected_pairs)} matches: {selected_pairs}")
        return {
            "location_id": location_id,
            "round": current_round,
            "matches_created": len(selected_pairs)
        }

    except Exception as e:
        print(f"Error in trigger_matchmaking_for_location: {str(e)}")
        db.session.rollback()
        return None


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def check_and_trigger_next_round(location_id):
    """
    Checks if the current round is complete and, if so, triggers the next one.
    A new round is triggered only if all preferences for the current round are in.
    """
    if is_round_complete(location_id):
        print(f"✅ Round complete for location {location_id}. Triggering next round.")
        if end_matchmaking_round(location_id):
            trigger_matchmaking_for_location(location_id)
    else:
        print(f"ℹ️ Round ongoing for location {location_id}. Waiting for all preferences.")



# Added from wingit matchmaking logic -> END


# # I changed this, be aware!
# def process_potential_match(user1_id, user2_id):
#     """
#     Process potential match between two users based on their preferences and location.
#     """

#     # Get preferences in both directions
#     pref1 = UserPreference.query.filter_by(user_id=user1_id, preferred_user_id=user2_id).first()
#     pref2 = UserPreference.query.filter_by(user_id=user2_id, preferred_user_id=user1_id).first()

#     # If either preference doesn't exist yet, no match to process
#     if not pref1 or not pref2:
#         return

#     # Check if there's an existing match
#     existing_match = Match.query.filter(
#         or_(
#             and_(Match.user1_id == user1_id, Match.user2_id == user2_id),
#             and_(Match.user1_id == user2_id, Match.user2_id == user1_id)
#         )
#     ).first()

#     # Case I: Both users like each other
#     if pref1.preference == 'like' and pref2.preference == 'like':
#         if existing_match:
#             # Update match status
#             existing_match.status = 'active'
#             existing_match.visible_after = get_unix_timestamp(datetime.now(timezone.utc) + timedelta(minutes=20))
#         else:
#             # Create new match with 20 minute delay
#             new_match = Match(
#                 user1_id=user1_id,
#                 user2_id=user2_id,
#                 visible_after=get_unix_timestamp(datetime.now(timezone.utc) + timedelta(minutes=20)),
#                 status='active'
#             )
#             db.session.add(new_match)
#     # Case II: One or both users rejected
#     elif pref1.preference == 'reject' or pref2.preference == 'reject':
#         if existing_match:
#             # Mark match as deleted
#             existing_match.status = 'deleted'
#     # Case III & IV: Save for later scenarios
#     elif pref1.preference == 'save_later' or pref2.preference == 'save_later':
#         # Only proceed if neither preference is 'reject'
#         if pref1.preference != 'reject' and pref2.preference != 'reject':
#             if not existing_match:
#                 # Create pending match
#                 new_match = Match(
#                     user1_id=user1_id,
#                     user2_id=user2_id,
#                     status='pending',
#                     visible_after=get_unix_timestamp(datetime.now(timezone.utc))  # Visible immediately, but pending
#                 )
#                 db.session.add(new_match)


# def get_match_score(user1_data, user2_data):
#     """Calculate a simple match score between two users based on age and hobbies"""
#     score = 0

#     # Age compatibility
#     try:
#         age_diff = abs(float(user1_data.age) - float(user2_data.age))
#         if age_diff <= 5:
#             score += 30
#         elif age_diff <= 10:
#             score += 20
#         elif age_diff <= 15:
#             score += 10
#     except (ValueError, TypeError):
#         pass

#     # Common hobbies
#     if user1_data.hobbies and user2_data.hobbies:
#         common_hobbies = set(user1_data.hobbies).intersection(set(user2_data.hobbies))
#         score += min(len(common_hobbies) * 10, 30)

#     return score


# def get_match_status(user_id, other_user_id):
#     try:

#         # Get user preferences
#         user_pref = UserPreference.query.filter_by(
#             user_id=user_id, preferred_user_id=other_user_id
#         ).first()

#         other_pref = UserPreference.query.filter_by(
#             user_id=other_user_id, preferred_user_id=user_id
#         ).first()

#         current_time = datetime.now(timezone.utc)

#         matches = Match.query.filter(
#             or_(
#                 Match.user1_id == user_id,
#                 Match.user2_id == user_id
#             ),
#             Match.status != 'deleted',
#             Match.visible_after <= current_time
#         ).all()
#         for match in matches:
#             # Determine the other user ID
#             matched_user_id = match.user2_id if match.user1_id == user_id else match.user1_id

#             # Checks if the required match is found else continue
#             if matched_user_id != other_user_id:
#                 continue

#             # Determine match status from user's perspective
#             if match.status == 'active':
#                 # Both liked each other
#                 display_status = 'matched'
#                 show_message_button = True
#             else:  # status is 'pending'
#                 if user_pref and user_pref.preference == 'save_later':
#                     display_status = 'decide'  # User needs to decide
#                     show_message_button = False
#                 elif other_pref and other_pref.preference == 'save_later':
#                     display_status = 'pending'  # Waiting for other user
#                     show_message_button = False
#                 else:
#                     display_status = 'pending'  # Generic pending
#                     show_message_button = False
#             return [display_status, show_message_button]
#         return ""
#     except Exception as e:
#         print(f"Error in get_status: {str(e)}")
#         return ""



# def get_user_matches(user_id, limit=5):
#     """Get top matches for a user"""
#     try:
#         # First get the user's gender
#         user = UserProfile.query.filter_by(user_auth_id=user_id).first()
#         if not user:
#             print(f"No user found for ID: {user_id}")
#             return []

#         # Normalize gender values for consistent comparison
#         user_gender = user.gender.lower() if user.gender else None

#         # Get users of opposite gender, handling different gender formats
#         if user_gender == 'men' or user_gender == 'man':
#             target_gender = ['Woman', 'woman', 'Women', 'women', 'Female', 'female']
#         elif user_gender == 'woman' or user_gender == 'women':
#             target_gender = ['Men', 'men', 'Man', 'man', 'Male', 'male']
#         else:
#             # If gender is something else or not specified, get any user
#             target_gender = ['Men', 'men', 'Man', 'man', 'Male', 'male', 'Woman', 'woman', 'Women', 'women', 'Female',
#                              'female']

#         # Get existing matches and preferences to avoid duplicates
#         existing_matches = Match.query.filter(
#             or_(Match.user1_id == user_id, Match.user2_id == user_id),
#             # and_(Match.status != 'deleted', Match.status != 'active')
#             Match.status != 'deleted'
#         ).all()

#         existing_preferences = UserPreference.query.filter_by(user_id=user_id).all()

#         # Create sets of already matched/preferred user IDs
#         matched_users = set()
#         for match in existing_matches:
#             if match.user1_id == user_id:
#                 matched_users.add(match.user2_id)
#             else:
#                 matched_users.add(match.user1_id)

#         preferred_users = set([pref.preferred_user_id for pref in existing_preferences])

#         # Find potential matches (users of opposite gender not already matched/preferred)
#         potential_matches = UserProfile.query.filter(
#             UserProfile.gender.in_(target_gender),
#             UserProfile.user_auth_id != user_id,
#             ~UserProfile.user_auth_id.in_(matched_users.union(preferred_users))
#         ).all()

#         # Calculate match scores and sort
#         scored_matches = []
#         for potential_match in potential_matches:
#             score = get_match_score(user, potential_match)
#             scored_matches.append((potential_match, score))

#         # Sort by score (highest first)
#         scored_matches.sort(key=lambda x: x[1], reverse=True)

#         # Format results with top matches
#         result = []
#         for match, score in scored_matches[:limit]:
#             # Get user image if available
#             user_image = UserImages.query.filter_by(user_auth_id=match.user_auth_id).first()
#             image_url = None
#             if user_image and user_image.imageString:
#                 image_url = f"/uploads/{user_image.imageString}"

#             result.append({
#                 'user_id': match.user_auth_id,
#                 'email': match.email,
#                 'firstname': match.firstname,
#                 'lastname': match.lastname,
#                 'preferences': match.preferences,
#                 'age': match.age,
#                 'bio': match.bio,
#                 'hobbies': match.hobbies,
#                 'match_score': score,
#                 'image_url': image_url
#             })

#         return result
#     except Exception as e:
#         print(f"Error in get_user_matches: {str(e)}")
#         return []


# def match_all_users():
#     """Match all users with someone from opposite gender"""
#     try:
#         # Get all users with complete profiles
#         all_users = UserProfile.query.all()

#         # Initialize results dictionary
#         matches = {}

#         used_users = set()  # Track who is already matched # Work: 41410282

#         # Get all existing matches and preferences
#         existing_matches = Match.query.all()
#         existing_preferences = UserPreference.query.all()

#         # Create sets of user pairs who already have matches or preferences
#         matched_pairs = set()
#         for match in existing_matches:
#             matched_pairs.add((match.user1_id, match.user2_id))
#             matched_pairs.add((match.user2_id, match.user1_id))  # Add reverse pair too

#         preference_pairs = set()
#         for pref in existing_preferences:
#             preference_pairs.add((pref.user_id, pref.preferred_user_id))

#         # Group users by gender
#         gender_groups = {}
#         for user in all_users:
#             gender = user.gender.lower() if user.gender else "unknown"
#             if gender not in gender_groups:
#                 gender_groups[gender] = []
#             gender_groups[gender].append(user)

#         # Map genders to opposite genders
#         opposite_genders = {
#             "men": "women",
#             "man": "woman",
#             "male": "female",
#             "women": "men",
#             "woman": "man",
#             "female": "male"
#         }

#         # Process each user
#         for user in all_users:

#             # Old logic to skip
#             # Skip if user already has matches in the result
#             # if user.user_auth_id in matches:
#             #    continue

#             # # Skip if user already has matches in the result
#             if user.user_auth_id in used_users:  # Work: 41410282
#                 continue  # Work: 41410282

#             user_gender = user.gender.lower() if user.gender else "unknown"

#             # Determine opposite gender
#             opposite_gender = opposite_genders.get(user_gender)

#             # If we can't determine opposite gender, skip
#             if not opposite_gender or opposite_gender not in gender_groups:
#                 continue

#             # Find best match among opposite gender
#             best_score = -1
#             best_match = None

#             for potential_match in gender_groups.get(opposite_gender, []):
#                 # Skip if they already have a match or preference
#                 if ((user.user_auth_id, potential_match.user_auth_id) in matched_pairs or
#                         (user.user_auth_id, potential_match.user_auth_id) in preference_pairs or
#                         (potential_match.user_auth_id, user.user_auth_id) in preference_pairs or
#                         potential_match.user_auth_id in matches):  # Skip if already matched in this run
#                     continue

#                 score = get_match_score(user, potential_match)
#                 if score > best_score:
#                     best_score = score
#                     best_match = potential_match

#             # Create the match
#             if best_match:
#                 # Get profile images if available
#                 user_image = UserImages.query.filter_by(user_auth_id=user.user_auth_id).first()
#                 match_image = UserImages.query.filter_by(user_auth_id=best_match.user_auth_id).first()

#                 user_image_url = f"/uploads/{user_image.imageString}" if user_image and user_image.imageString else None
#                 match_image_url = f"/uploads/{match_image.imageString}" if match_image and match_image.imageString else None

#                 # Add match for current user
#                 matches[user.user_auth_id] = {
#                     'match_id': best_match.user_auth_id,
#                     'firstname': best_match.firstname,
#                     'age': best_match.age,
#                     'score': best_score,
#                     'image_url': match_image_url
#                 }

#                 # Add match for the matched user
#                 matches[best_match.user_auth_id] = {
#                     'match_id': user.user_auth_id,
#                     'firstname': user.firstname,
#                     'age': user.age,
#                     'score': best_score,
#                     'image_url': user_image_url
#                 }

#                 # Mark both as used # Work: 41410282
#                 used_users.add(user.user_auth_id)  # Work: 41410282
#                 used_users.add(best_match.user_auth_id)  # Work: 41410282

#                 # Mark this pair as matched to avoid duplicates
#                 matched_pairs.add((user.user_auth_id, best_match.user_auth_id))
#                 matched_pairs.add((best_match.user_auth_id, user.user_auth_id))

#         return matches

#     except Exception as e:
#         print(f"Error in match_all_users: {str(e)}")
#         return {}


# def trigger_matchmaking_for_location(location_id):
#     """
#     Trigger automatic matchmaking for all checked-in users at a specific location.
#     This is called when all slots are filled or check-in period ends.
#     """
#     try:
#         # Get all users who checked in to this location
#         checkins = CheckIn.query.filter_by(location_id=location_id).all()
#         checked_in_user_ids = [checkin.user_id for checkin in checkins]

#         print(f"Triggered matchmaking for location {location_id}")

#         if len(checked_in_user_ids) < 2:
#             print(f"Not enough users checked in for matchmaking at location {location_id}")
#             return None

#         # Get location details for matchmaking
#         location = LocationInfo.query.get(location_id)
#         if not location:
#             print(f"Location {location_id} not found")
#             return None

#         # Get the actual checked-in users
#         checked_in_users = []
#         for user_id in checked_in_user_ids:
#             user = User.query.get(user_id)
#             if user:
#                 checked_in_users.append(user)

#         if len(checked_in_users) < 2:
#             print(f"Not enough valid users for matchmaking at location {location_id}")
#             return None

#         # Query to get all existing active matches at this location for all the checked in users
#         existing_matches = (
#             db.session.query(Match)
#             .filter(
#                 Match.status == 'active',
#                 or_(
#                     Match.user1_id.in_(checked_in_user_ids),
#                     Match.user2_id.in_(checked_in_user_ids)
#                 ),
#                 Match.location_id == location_id,
#             )
#             .all()
#         )
#         existing_matches_tuple = []
#         if existing_matches:
#             for match in existing_matches:
#                 user_1 = match.user1_id
#                 user_2 = match.user2_id
#                 existing_matches_tuple.append((user_1, user_2))
#                 existing_matches_tuple.append((user_2, user_1))

#         # Separate users by gender for proper matching
#         male_users = []
#         female_users = []

#         for user in checked_in_users:
#             user_data = UserProfile.query.filter_by(user_auth_id=user.id).first()
#             if user_data and user_data.gender:
#                 gender = user_data.gender.lower()
#                 if gender in ['men', 'man', 'male']:
#                     male_users.append(user)
#                 elif gender in ['women', 'woman', 'female']:
#                     female_users.append(user)

#         print(f"Checked-in users: {len(checked_in_users)}, Male: {len(male_users)}, Female: {len(female_users)}")

#         # Create ALL possible matches between opposite genders
#         matches_created = 0
#         users_left_out = []

#         # Handle odd numbers with fair rotation
#         if len(male_users) != len(female_users):
#             # Determine which gender has more users
#             if len(male_users) > len(female_users):
#                 excess_users = male_users
#                 base_users = female_users
#                 excess_gender = "male"
#             else:
#                 excess_users = female_users
#                 base_users = male_users
#                 excess_gender = "female"

#             # Get the last matchmaking session to determine who was left out
#             last_matchmaking = Match.query.order_by(Match.match_date.desc()).first()

#             # Implement fair rotation
#             if last_matchmaking:
#                 # Check who was left out in the last session
#                 last_match_date = last_matchmaking.match_date
#                 recent_matches = Match.query.filter(
#                     Match.match_date >= last_match_date - timedelta(hours=1)
#                 ).all()

#                 # Get users who were matched recently
#                 recently_matched = set()
#                 for match in recent_matches:
#                     recently_matched.add(match.user1_id)
#                     recently_matched.add(match.user2_id)

#                 # Find users who were NOT matched recently (potential candidates to leave out)
#                 unmatched_candidates = [user for user in excess_users if user.id not in recently_matched]

#                 if unmatched_candidates:
#                     # Leave out a different user this time
#                     user_to_leave_out = random.choice(unmatched_candidates)
#                     excess_users.remove(user_to_leave_out)
#                     users_left_out.append(user_to_leave_out)
#                     print(
#                         f"Fair rotation: Leaving out {excess_gender} user {user_to_leave_out.id} ({user_to_leave_out.email}) this time")
#                 else:
#                     # If no recent matches, just leave out a random user
#                     user_to_leave_out = random.choice(excess_users)
#                     excess_users.remove(user_to_leave_out)
#                     users_left_out.append(user_to_leave_out)
#                     print(
#                         f"Random rotation: Leaving out {excess_gender} user {user_to_leave_out.id} ({user_to_leave_out.email})")
#             else:
#                 # First time matchmaking, leave out a random user
#                 user_to_leave_out = random.choice(excess_users)
#                 excess_users.remove(user_to_leave_out)
#                 users_left_out.append(user_to_leave_out)
#                 print(
#                     f"First time: Leaving out {excess_gender} user {user_to_leave_out.id} ({user_to_leave_out.email})")

#             # Now we have equal numbers - use the updated lists
#             if excess_gender == "male":
#                 male_users = excess_users
#                 female_users = base_users
#             else:
#                 male_users = base_users
#                 female_users = excess_users

#         # Shuffle both lists to ensure random matching
#         random.shuffle(male_users)
#         random.shuffle(female_users)

#         # Create matches one-to-one
#         for i in range(min(len(male_users), len(female_users))):
#             male_user = male_users[i]
#             female_user = female_users[i]

#             # CRITICAL FIX: Prevent self-matching
#             if male_user.id == female_user.id:
#                 print(f"SKIPPING: Self-match detected for user {male_user.id}")
#                 continue

#             if (male_user.id, female_user.id) in existing_matches_tuple:
#                 print(f"SKIPPING: Existing match found ({male_user.id}, {female_user.id}) with active status")
#                 continue

#             # Get user preferences
#             user_pref = UserPreference.query.filter_by(
#                 user_id=male_user.id, preferred_user_id=female_user.id
#             ).first()

#             other_pref = UserPreference.query.filter_by(
#                 user_id=female_user.id, preferred_user_id=male_user.id
#             ).first()

#             if user_pref and user_pref.preference == 'reject':
#                 print(f"SKIPPING: Preference already rejected for user {female_user.id} by user {male_user.id}")
#                 continue
#             elif other_pref and other_pref.preference == 'reject':
#                 print(f"SKIPPING: Preference already rejected for user {male_user.id} by user {female_user.id}")
#                 continue

#             visible_after_timestamp = get_unix_timestamp(datetime.now(timezone.utc) + timedelta(minutes=20))
#             # Create mutual match
#             new_match = Match(
#                 user1_id=male_user.id,
#                 user2_id=female_user.id,
#                 status='active',
#                 location_id=location_id,
#                 visible_after=visible_after_timestamp
#             )
#             db.session.add(new_match)
#             matches_created += 1
#             print(
#                 f"At: {datetime.now(timezone.utc)}, Created mutual match: User {male_user.id} ({male_user.email}) ↔ User {female_user.id} ({female_user.email}), visible after: {visible_after_timestamp}")

#         db.session.commit()
#         print(f"Automatic matchmaking completed for location {location_id}: {matches_created} matches created")

#         # Return summary for debugging
#         return {
#             'location_id': location_id,
#             'total_users': len(checked_in_users),
#             'male_users': len(male_users),
#             'female_users': len(female_users),
#             'matches_created': matches_created,
#             'users_left_out': [user.email for user in users_left_out],
#             'matches_per_user': matches_created // len(male_users) if male_users else 0
#         }

#     except Exception as e:
#         print(f"Error in automatic matchmaking: {str(e)}")
#         db.session.rollback()
#         return None

# METHOD TO GET AUTHENTICATED USERS LIST -> End

# Fetch loggedinusers info -> Start


@app.route("/loggedinUserProfileData", methods=["GET"])
def logged_in_user_profile():
    logging.debug("➡️  /loggedinUserProfileData endpoint hit")

    # Get current user
    user = get_current_user_from_token()
    logging.debug(f"User from token: {user}")

    if not user:
        logging.warning("❌ Unauthorized access: No user from token")
        return jsonify({"error": "Unauthorized"}), 401

    # Fetch profile
    logging.debug(f"Fetching UserProfile for user_auth_id={user.id}")
    profile = UserProfile.query.filter_by(user_auth_id=user.id).first()

    if not profile:
        logging.warning(f"❌ Profile not found for user_auth_id={user.id}")
        return jsonify({"error": "Profile not found"}), 404

    logging.debug(f"✅ Profile found: profile_id={profile.id}")

    # Related tables
    info = profile.info
    character = profile.character

    logging.debug(f"Info object: {info}")
    logging.debug(f"Character object: {character}")

    # Images
    logging.debug(f"Fetching images for user_auth_id={user.id}")
    images = UserImages.query.filter_by(user_auth_id=user.id).all()
    logging.debug(f"Images count: {len(images)}")

    # Final response
    logging.debug("✅ Building response payload")

    response = {
        "auth": {
            "user_id": user.id,
            "email": getattr(user, "email", None)
        },
        "profile": {
            "firstname": profile.firstname,
            "lastname": profile.lastname,
            "gender": profile.gender,
            "email": profile.email,
            "age": profile.age,
            "phone_number": profile.phone_number,
            "sect": profile.sect,
            "lookingfor": profile.lookingfor,
        },
        "info": {
            "hobbies": info.hobbies if info else [],
            "preferences": info.preferences if info else [],
            "bio": info.bio if info else None,
            "alcoholstatus": info.alcoholstatus if info else None,
            "childrenstatus": info.childrenstatus if info else None,
            "maritalstatus": info.maritalstatus if info else None,
            "smokestatus": info.smokestatus if info else None,
            "halalfood": info.halalfood if info else None,
        },
        "character": {
            "muslimstatus": character.muslimstatus if character else None,
            "practicing": character.practicing if character else None,
            "nationality": character.nationality if character else None,
            "personality_type": character.personality_type if character else None,
        },
        "images": [
            {"id": img.id, "imageString": img.imageString} for img in images
        ]
    }

    logging.debug("✅ Response successfully built and returned")
    return jsonify(response), 200


# Fetch loggedinusers info -> End


# USERPROFILE -> Start

@app.route('/userProfile', methods=['POST'])
def postUserProfileData():
    user = get_current_user_from_token()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()

    profile = UserProfile.query.filter_by(user_auth_id=user.id).first()
    if not profile:
        profile = UserProfile(user_auth_id=user.id)
        db.session.add(profile)

    profile.firstname = data.get('firstname')
    profile.lastname = data.get('lastname')
    profile.gender = data.get('gender')
    profile.email = data.get('email')  # optional, backend can rely on user.email
    profile.phone_number = data.get('phone_number')
    profile.age = data.get('age')
    profile.sect = data.get('sect')
    profile.lookingfor = data.get('lookingfor')

    db.session.commit()
    return jsonify({'message': 'Profile saved'}), 200


@app.route('/userProfile', methods=['GET'])
def getUserProfileData():
    try:
        profiles = UserProfile.query.all()
        users = []

        for profile in profiles:
            # Access the UserImages via Task relationship
            task_user = profile.user  # Task object
            user_images = getattr(task_user, 'user_image', [])  # list of UserImages
            user_image = user_images[0] if user_images else None

            # Construct image URL if available
            if user_image and getattr(user_image, 'imageString', None):
                image_url = request.host_url.rstrip('/') + '/uploads/' + user_image.imageString
            else:
                image_url = None

            user_data = {
                'id': profile.user_auth_id,
                'firstname': profile.firstname,
                'lastname': profile.lastname,
                'gender': profile.gender,
                'email': profile.email,
                'phone_number': profile.phone_number,
                'age': profile.age,
                'sect': profile.sect,
                'lookingfor': profile.lookingfor,            
                'image_url': image_url,
                'current_server_time': get_unix_timestamp(datetime.now(timezone.utc)),
            }
            users.append(user_data)

        return jsonify({'users': users}), 200

    except Exception as e:
        return jsonify({'error': f'Internal Server Error: {e}'}), 500

# USERPROFILE -> End

# USERINFO -> Start

@app.route('/userInfo', methods=['POST'])
def postUserInfo():
    try:
        print("📥 /userInfo called")

        # --- Auth ---
        user = get_current_user_from_token()
        if not user:
            print("⛔ Unauthorized: invalid or missing token")
            return jsonify({'error': 'Unauthorized'}), 401

        print(f"✅ Authenticated user_id={user.id}")

        # --- Profile ---
        profile = UserProfile.query.filter_by(user_auth_id=user.id).first()
        if not profile:
            print(f"❌ No UserProfile found for user_id={user.id}")
            return jsonify({'error': 'UserProfile not found'}), 404

        print(f"📄 UserProfile found: profile_id={profile.id}")

        # --- Request body ---
        data = request.get_json()
        if not data:
            print("⚠️ Empty JSON body received")
            return jsonify({'error': 'Invalid JSON'}), 400

        print(f"📦 Payload received: {data}")

        # --- UserInfo ---
        prefs = profile.info
        if not prefs:
            print("➕ Creating new UserInfo record")
            prefs = UserInfo(profile=profile)
            db.session.add(prefs)
            message = "Created user info"
        else:
            print(f"✏️ Updating UserInfo id={prefs.id}")
            message = "Updated user info"

        # --- Assign fields ---
        prefs.hobbies = data.get('hobbies', [])
        prefs.preferences = data.get('preferences', [])
        prefs.bio = data.get('bio')
        prefs.alcoholstatus = data.get('alcoholstatus')
        prefs.childrenstatus = data.get('childrenstatus')
        prefs.maritalstatus = data.get('maritalstatus')
        prefs.smokestatus = data.get('smokestatus')
        prefs.halalfood = data.get('halalfood')

        print("💾 Committing changes to DB")
        db.session.commit()

        print("✅ /userInfo completed successfully")
        return jsonify({'message': message}), 200

    except Exception as e:
        db.session.rollback()
        print("🔥 ERROR in /userInfo")
        print(str(e))
        import traceback
        traceback.print_exc()

        return jsonify({'error': 'Internal Server Error'}), 500


# get ALL users preferences
@app.route('/userInfo', methods=['GET'])
def getUserInfo():
    try:
        all_prefs = UserInfo.query.all()
        result = []

        for prefs in all_prefs:
            profile = prefs.profile
            user_data = {
                'user_profile_id': profile.id,
                'firstname': profile.firstname,
                'lastname': profile.lastname,
                'hobbies': prefs.hobbies,
                'preferences': prefs.preferences,
                'bio': prefs.bio,
                'alcoholstatus': prefs.alcoholstatus,
                'childrenstatus': prefs.childrenstatus,
                'maritalstatus': prefs.maritalstatus,
                'smokestatus': prefs.smokestatus,
                'halalfood': prefs.halalfood
            }
            result.append(user_data)

        return jsonify({'user_info': result}), 200

    except Exception as e:
        return jsonify({'error': f'Internal Server Error: {e}'}), 500

# get SINGLE users preferences

@app.route('/userInfo/<int:user_profile_id>', methods=['GET'])
def getUserInfoById(user_profile_id):
    try:
        prefs = UserInfo.query.filter_by(user_profile_id=user_profile_id).first()
        if not prefs:
            return jsonify({'error': 'UserInfo not found'}), 404

        profile = prefs.profile
        user_data = {
            'user_profile_id': profile.id,
            'firstname': profile.firstname,
            'lastname': profile.lastname,
            'hobbies': prefs.hobbies,
            'preferences': prefs.preferences,
            'bio': prefs.bio,
            'alcoholstatus': prefs.alcoholstatus,
            'childrenstatus': prefs.childrenstatus,
            'maritalstatus': prefs.maritalstatus,
            'smokestatus': prefs.smokestatus,
            'halalfood': prefs.halalfood
        }
        return jsonify({'user_info': user_data}), 200

    except Exception as e:
        return jsonify({'error': f'Internal Server Error: {e}'}), 500

# USERPREFERENCES -> End

# USERCHARACTER -> Start

@app.route('/userCharacter', methods=['POST'])
def postUserCharacter():
    try:
        user = get_current_user_from_token()
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401

        profile = UserProfile.query.filter_by(user_auth_id=user.id).first()
        if not profile:
            return jsonify({'error': 'UserProfile not found'}), 404

        data = request.get_json()

        character = profile.character
        if not character:
            character = UserCharacter(profile=profile)
            db.session.add(character)

        character.muslimstatus = data.get('muslimstatus')
        character.practicing = data.get('practicing')
        character.nationality = data.get('nationality')
        character.personality_type = data.get('personality_type')

        db.session.commit()
        return jsonify({'message': 'User character saved'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# get ALL users character
@app.route('/userCharacter', methods=['GET'])
def getUserCharacter():
    try:
        all_chars = UserCharacter.query.all()
        result = []

        for char in all_chars:
            profile = char.profile
            char_data = {
                'user_profile_id': profile.id,
                'firstname': profile.firstname,
                'lastname': profile.lastname,
                'muslimstatus': char.muslimstatus,
                'practicing': char.practicing,
                'nationality': char.nationality,
                'personality_type': char.personality_type
            }
            result.append(char_data)

        return jsonify({'user_characters': result}), 200

    except Exception as e:
        return jsonify({'error': f'Internal Server Error: {e}'}), 500
    
# get SINGLE users character
@app.route('/userCharacter/<int:user_profile_id>', methods=['GET'])
def getUserCharacterById(user_profile_id):
    try:
        character = UserCharacter.query.filter_by(user_profile_id=user_profile_id).first()
        if not character:
            return jsonify({'error': 'UserCharacter not found'}), 404

        profile = character.profile
        char_data = {
            'user_profile_id': profile.id,
            'firstname': profile.firstname,
            'lastname': profile.lastname,
            'muslimstatus': character.muslimstatus,
            'practicing': character.practicing,
            'nationality': character.nationality,
            'personality_type': character.personality_type
        }

        return jsonify({'user_character': char_data}), 200

    except Exception as e:
        return jsonify({'error': f'Internal Server Error: {e}'}), 500


# USERCHARACTER -> End

# IMAGE UPLOAD AND RETRIEVAL -> Start

@app.route('/upload_image', methods=['POST'])
def upload_image():
    try:
        # Check if the request contains a file
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400

        file = request.files['image']
        new_email = request.form.get('email')

        # Check if email is provided
        if not new_email:
            return jsonify({"error": "Email is required"}), 400

        user = User.query.filter_by(email=new_email).first()

        if not user:
            return jsonify({'error': "No user registered with this email"}), 400

        user_auth_id = user.id

        # Check if the file is allowed
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)

            # Save the file in the 'uploads' folder
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Check if an image already exists for this user
            user_image = UserImages.query.filter_by(user_auth_id=user_auth_id).first()

            if user_image:
                # Update existing image
                user_image.imageString = filename
                message = "Updated user image"
            else:
                # Add new image
                user_image = UserImages(
                    user_auth_id=user_auth_id,
                    email=new_email,
                    imageString=filename
                )
                db.session.add(user_image)
                message = "Added new user image"

            db.session.commit()

            # Generate the image URL
            image_url = request.host_url + 'uploads/' + filename
            return jsonify({"message": message, "image_url": image_url}), 201

        else:
            return jsonify({"error": "Invalid image format"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/get_image/<int:user_auth_id>', methods=['GET'])
def get_image(user_auth_id):
    # Query the database for a single record matching the user_auth_id
    user_image = UserImages.query.filter_by(user_auth_id=user_auth_id).first()

    if user_image:
        # Return the image as an object
        return jsonify({
            "id": user_image.id,
            "email": user_image.email,
            "user_auth_id": user_image.user_auth_id,
            "imageString": user_image.imageString
        }), 200
    else:
        return jsonify({"error": "No image found for the given user_auth_id"}), 404
    
# IMAGE UPLOAD AND RETRIEVAL -> End

# LOCATIONINFO -> Start

@app.route('/locationInfo', methods=['POST'])
def postLocationInfo():
    try:
        user = get_current_user_from_token()
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401

        profile = UserProfile.query.filter_by(user_auth_id=user.id).first()
        if not profile:
            return jsonify({'error': 'UserProfile not found'}), 404

        data = request.get_json()
        print("POST /locationInfo received:", data)

        # ===== CATEGORY =====
        category_name = data.get("event_category")
        if not category_name:
            return jsonify({"error": "event_category is required"}), 400

        try:
            category = EventCategory.query.filter_by(name=category_name).first()
            if not category:
                category = EventCategory(name=category_name)
                db.session.add(category)
                db.session.commit()
            print("Category OK:", category.name)
        except SQLAlchemyError as e:
            print("Error processing category:", e)
            traceback.print_exc()
            db.session.rollback()
            return jsonify({"error": "Category processing failed"}), 500

        # ===== HOST =====
        host_id = data.get("event_host_id")
        if host_id is None:
            return jsonify({"error": "event_host_id is required"}), 400

        try:
            host = EventHost.query.get(host_id)
            if not host:
                return jsonify({"error": "Invalid event_host_id"}), 400
            print("Host OK:", host.id)
        except SQLAlchemyError as e:
            print("Error processing host:", e)
            traceback.print_exc()
            return jsonify({"error": "Host processing failed"}), 500

        # ===== OTHER FIELDS =====
        try:
            lat = data.get('lat')
            lng = data.get('lng')
            totalPrice = data.get('totalPrice')
            maxAttendees = data.get('maxAttendees')
            date = data.get('date')
            time = data.get('time')
            location = data.get('location')
            description = data.get('description')
            location = data.get('location')

            newLocationDetails = LocationInfo(
                maxAttendees=maxAttendees,
                maleAttendees=0,
                femaleAttendees=0,
                date=date,
                time=time,
                location=location,
                lat=lat,
                lng=lng,
                totalPrice=totalPrice,
                description=description,
                event_category_id=category.id,
                event_host_id=host.id,
                matchmake=bool(data.get("matchmake", False))
            )

            db.session.add(newLocationDetails)
            db.session.commit()
            print("Location added:", newLocationDetails.id)

        except (TypeError, ValueError) as e:
            print("Invalid input type:", e)
            traceback.print_exc()
            db.session.rollback()
            return jsonify({"error": "Invalid input types"}), 400
        except SQLAlchemyError as e:
            print("Error creating LocationInfo:", e)
            traceback.print_exc()
            db.session.rollback()
            return jsonify({"error": "Failed to add location"}), 500

        return jsonify({'message': "New Location added", "id": newLocationDetails.id}), 201

    except Exception as e:
        print("Unexpected error in /locationInfo:", e)
        traceback.print_exc()
        return jsonify({"error": "Internal server error"}), 500


@app.route('/locationInfo', methods=['GET'])
def getLocationInfo():
    locationInfo = LocationInfo.query.all()
    data = [
        {
            'id': userloc.id,
            'maxAttendees': userloc.maxAttendees,
            'maleAttendees': userloc.maleAttendees,
            'femaleAttendees': userloc.femaleAttendees,
            'date': userloc.date,
            'time': userloc.time,
            'location': userloc.location,
            'lat': userloc.lat,
            'lng': userloc.lng,
            'totalPrice': userloc.totalPrice,
            'description': userloc.description,  # NEW
            'matchmake': userloc.matchmake,      # NEW
            'event_category': userloc.event_category.name if userloc.event_category else None,
            'event_category_id': userloc.event_category_id,
            'event_host': userloc.event_host.name if hasattr(userloc, 'event_host') and userloc.event_host else None,  # NEW
            'event_host_id': userloc.event_host_id if hasattr(userloc, 'event_host_id') else None,  # NEW
            'current_round': userloc.current_round
        }
        for userloc in locationInfo
    ]
    return jsonify(data)

# LOCATIONINFO -> End

# TICKETS -> Start

# @app.route('/my_tickets', methods=['GET'])
# def get_user_tickets():
#     user_id = request.args.get('user_id')

#     if not user_id:
#         return jsonify({'message': 'user_id is required'}), 400

#     attendances = Attendance.query.filter_by(user_id=user_id).all()
#     tickets = []

#     for attendance in attendances:
#         location = LocationInfo.query.get(attendance.location_id)
#         if not location:
#             continue

#         checked_in = has_user_checked_in(user_id, location.id)

#         tickets.append({
#             'location_id': location.id,
#             'event_category': location.event_category.name if location.event_category else None,
#             'event_category_id': location.event_category_id,
#             'event_host': location.event_host.name if location.event_host else None,  # NEW
#             'event_host_id': location.event_host_id,
#             'description': location.description,  # NEW
#             'matchmake': location.matchmake,      # NEW
#             'date': location.date,
#             'time': location.time,
#             'location': location.location,
#             'checked_in': checked_in,
#             'maleAttendees': location.maleAttendees or 0,
#             'femaleAttendees': location.femaleAttendees or 0,
#             'maxAttendees': location.maxAttendees or 0
#         })

#     return jsonify({'tickets': tickets}), 200

@app.route('/my_tickets', methods=['GET'])
def get_user_tickets():
    user = get_current_user_from_token()
    if not user:
        return jsonify({'message': 'Unauthorized'}), 401

    user_id = user.id

    attendances = Attendance.query.filter_by(user_id=user_id).all()
    tickets = []

    for attendance in attendances:
        location = LocationInfo.query.get(attendance.location_id)
        if not location:
            continue

        checked_in = has_user_checked_in(user_id, location.id)

        tickets.append({
            'location_id': location.id,
            'event_category': location.event_category.name if location.event_category else None,
            'event_category_id': location.event_category_id,
            'event_host': location.event_host.name if location.event_host else None,
            'event_host_id': location.event_host_id,
            'description': location.description,
            'matchmake': location.matchmake,
            'date': location.date,
            'time': location.time,
            'location': location.location,
            'checked_in': checked_in,
            'maleAttendees': location.maleAttendees or 0,
            'femaleAttendees': location.femaleAttendees or 0,
            'maxAttendees': location.maxAttendees or 0
        })

    return jsonify({'tickets': tickets}), 200

# TICKETS -> End

# CHECK-IN AND ATTENDANCE -> Start

# ✅ Route: Perform check-in
# @app.route('/checkin', methods=['POST'])
# def checkin():
#     data = request.get_json()
#     user_id = data.get('user_id')
#     location_id = data.get('location_id')

#     if not user_id or not location_id:
#         return jsonify({'message': 'user_id and location_id are required'}), 400

#     # Validate location
#     user = User.query.get(user_id)
#     location = LocationInfo.query.get(location_id)
#     if not user or not location:
#         return jsonify({'message': 'Invalid location or Id'}), 404

#     # User must have marked attendance first
#     attendance = Attendance.query.filter_by(user_id=user_id, location_id=location_id).first()
#     if not attendance:
#         return jsonify({'message': 'User must attend before check-in'}), 403

#     # Check if already checked in
#     existing_checkin = CheckIn.query.filter_by(user_id=user_id, location_id=location_id).first()
#     if existing_checkin:
#         return jsonify({'message': 'User already checked in'}), 400

#     # Validate if check-in already closed for this location # Work: 41410282
#     if location.checkin_closed:  # Work: 41410282
#         return jsonify({'message': 'Check-in is closed for this event'}), 400  # Work: 41410282

#     # Slot Limit Enforcement
#     checkin_count = CheckIn.query.filter_by(location_id=location_id).count()
#     if checkin_count >= location.maxAttendees and not location.checkin_closed:  # Checks for the limit and if checkin is not closed to avoid duplicate matches
#         location.checkin_closed = True  # Work: 41410282
#         db.session.commit()  # Work: 41410282
#         trigger_matchmaking_for_location(location_id)  # Work: 41410282
#         return jsonify({'message': f'All {location.maxAttendees} slots are filled'}), 400

#     # Time-Based Restrictions (10 minutes after event time)
#     try:
#         event_time = datetime.strptime(f"{location.date} {location.time}", "%Y-%m-%d %H:%M")
#         current_time = datetime.now()
#         time_diff = (current_time - event_time).total_seconds()

#         if time_diff > 600:
#             location.checkin_closed = True  # Work: 41410282
#             db.session.commit()  # Work: 41410282
#             # Trigger matchmaking when time expires (even if slots aren't full)
#             trigger_matchmaking_for_location(location_id)
#             return jsonify({'message': 'Check-in period has ended (10 minutes after event time)'}), 400
#     except Exception as e:
#         print(f"Error parsing event time: {str(e)}")

#     # Create check-in
#     new_checkin = CheckIn(user_id=user_id, location_id=location_id)
#     db.session.add(new_checkin)
#     db.session.commit()

#     # Check if this check-in completes the slots or triggers end phase
#     updated_checkin_count = CheckIn.query.filter_by(location_id=location_id).count()
#     if updated_checkin_count >= location.maxAttendees:
#         location.checkin_closed = True  # Work: 41410282
#         db.session.commit()  # Work: 41410282
#         # All slots filled - trigger automatic matchmaking
#         trigger_matchmaking_for_location(location_id)

#     return jsonify({
#         'message': 'Check-in successful',
#         'user_id': user_id,
#         'location_id': location_id,
#         'timestamp': new_checkin.timestamp.isoformat(),
#         'checkin_status': f"{updated_checkin_count}/{location.maxAttendees} checked in"
#     }), 200


# @app.route('/checkin', methods=['GET'])
# def check_checkin():
#     user_id = request.args.get('user_id')
#     location_id = request.args.get('location_id')

#     if not user_id or not location_id:
#         return jsonify({'message': 'Missing user_id or location_id'}), 400

#     checkin = CheckIn.query.filter_by(user_id=user_id, location_id=location_id).first()

#     if checkin:
#         location = checkin.location

#         # Count total check-ins at this location
#         checkin_count = CheckIn.query.filter_by(location_id=location_id).count()
#         max_attendees = location.maxAttendees

#     if checkin:
#         location = checkin.location
#         return jsonify({
#             'checked_in': True,
#             'timestamp': checkin.timestamp,
#             'checkin_status': f"{checkin_count}/{max_attendees} checked in",
#             'location': {
#                 'id': location.id,
#                 'location': location.location,
#                 'date': location.date,
#                 'time': location.time,
#                 'lat': location.lat,
#                 'lng': location.lng,
#                 'event_type': location.event_type,
#                 'maxAttendees': location.maxAttendees,
#                 'maleAttendees': location.maleAttendees,
#                 'femaleAttendees': location.femaleAttendees,
#                 'totalPrice': location.totalPrice
#             }
#         }), 200
#     else:
#         return jsonify({'checked_in': False}), 200

@app.route('/checkin', methods=['POST'])
def checkin():
    user = get_current_user_from_token()
    if not user:
        return jsonify({'message': 'Unauthorized'}), 401

    user_id = user.id
    data = request.get_json()
    location_id = data.get('location_id')

    if not location_id:
        return jsonify({'message': 'location_id is required'}), 400

    location = LocationInfo.query.get(location_id)
    if not location:
        return jsonify({'message': 'Invalid location or Id'}), 404

    attendance = Attendance.query.filter_by(user_id=user_id, location_id=location_id).first()
    if not attendance:
        return jsonify({'message': 'User must attend before check-in'}), 403

    existing_checkin = CheckIn.query.filter_by(user_id=user_id, location_id=location_id).first()
    if existing_checkin:
        return jsonify({'message': 'User already checked in'}), 400

    if location.checkin_closed:
        return jsonify({'message': 'Check-in is closed for this event'}), 400

    checkin_count = CheckIn.query.filter_by(location_id=location_id).count()
    if checkin_count >= location.maxAttendees and not location.checkin_closed:
        location.checkin_closed = True
        db.session.commit()
        trigger_matchmaking_for_location(location_id)
        return jsonify({'message': f'All {location.maxAttendees} slots are filled'}), 400

    try:
        event_time = datetime.strptime(f"{location.date} {location.time}", "%Y-%m-%d %H:%M")
        current_time = datetime.now()
        time_diff = (current_time - event_time).total_seconds()

        if time_diff > 600:
            location.checkin_closed = True
            db.session.commit()
            trigger_matchmaking_for_location(location_id)
            return jsonify({'message': 'Check-in period has ended (10 minutes after event time)'}), 400
    except Exception as e:
        print(f"Error parsing event time: {str(e)}")

    new_checkin = CheckIn(user_id=user_id, location_id=location_id)
    db.session.add(new_checkin)
    db.session.commit()

    updated_checkin_count = CheckIn.query.filter_by(location_id=location_id).count()
    if updated_checkin_count >= location.maxAttendees:
        location.checkin_closed = True
        db.session.commit()
        trigger_matchmaking_for_location(location_id)

    return jsonify({
        'message': 'Check-in successful',
        'user_id': user_id,
        'location_id': location_id,
        'timestamp': new_checkin.timestamp.isoformat(),
        'checkin_status': f"{updated_checkin_count}/{location.maxAttendees} checked in"
    }), 200


@app.route('/checkin', methods=['GET'])
def check_checkin():
    user = get_current_user_from_token()
    if not user:
        return jsonify({'message': 'Unauthorized'}), 401

    user_id = user.id
    location_id = request.args.get('location_id')

    if not location_id:
        return jsonify({'message': 'Missing location_id'}), 400

    checkin = CheckIn.query.filter_by(user_id=user_id, location_id=location_id).first()

    if checkin:
        location = checkin.location
        checkin_count = CheckIn.query.filter_by(location_id=location_id).count()
        max_attendees = location.maxAttendees

        return jsonify({
            'checked_in': True,
            'timestamp': checkin.timestamp,
            'checkin_status': f"{checkin_count}/{max_attendees} checked in",
            'location': {
                'id': location.id,
                'location': location.location,
                'date': location.date,
                'time': location.time,
                'lat': location.lat,
                'lng': location.lng,
                'maxAttendees': location.maxAttendees,
                'maleAttendees': location.maleAttendees,
                'femaleAttendees': location.femaleAttendees,
                'totalPrice': location.totalPrice
            }
        }), 200
    else:
        return jsonify({'checked_in': False}), 200


# @app.route('/attend', methods=['POST'])
# def attend_location():
#     data = request.get_json()
#     user_id = data.get('user_id')
#     location_id = data.get('location_id')

#     if not user_id or not location_id:
#         return jsonify({'message': 'Missing user_id or location_id'}), 400

#     user = User.query.get(user_id)
#     location = LocationInfo.query.get(location_id)
#     profile = UserProfile.query.filter_by(user_auth_id=user_id).first()

#     if not user or not location:
#         return jsonify({'message': 'Invalid user or location'}), 404

#     if not profile or not profile.gender:
#         return jsonify({'message': 'User profile or gender not set'}), 400

#     if Attendance.query.filter_by(user_id=user_id, location_id=location_id).first():
#         return jsonify({'message': 'User already marked as attending'}), 400

#     # ✅ Mark attendance with hasAttended = True
#     attendance = Attendance(user_id=user_id, location_id=location_id, hasAttended=True)
#     db.session.add(attendance)

#     # Update gender-based counts
#     gender = profile.gender.lower()
#     if gender.lower() in ['men', 'man', 'male']:
#         location.maleAttendees = (location.maleAttendees or 0) + 1
#     elif gender.lower() in ['women', 'woman', 'female']:
#         location.femaleAttendees = (location.femaleAttendees or 0) + 1

#     db.session.commit()

#     return jsonify({'message': 'User marked as attending and counts updated'}), 200

@app.route('/attend', methods=['POST'])
def attend_location():
    user = get_current_user_from_token()  # ← get user from token
    
    if not user:
        return jsonify({'message': 'Unauthorized'}), 401
    
    user_id = user.id  # ← extract id from the returned user object

    data = request.get_json()
    location_id = data.get('location_id')

    if not location_id:
        return jsonify({'message': 'Missing location_id'}), 400

    location = LocationInfo.query.get(location_id)
    profile = UserProfile.query.filter_by(user_auth_id=user_id).first()

    if not location:
        return jsonify({'message': 'Invalid location'}), 404 

    if not profile or not profile.gender:
        return jsonify({'message': 'User profile or gender not set'}), 400

    if Attendance.query.filter_by(user_id=user_id, location_id=location_id).first():
        return jsonify({'message': 'User already marked as attending'}), 400

    attendance = Attendance(user_id=user_id, location_id=location_id, hasAttended=True)
    db.session.add(attendance)

    gender = profile.gender.lower()
    if gender in ['men', 'man', 'male']:
        location.maleAttendees = (location.maleAttendees or 0) + 1
    elif gender in ['women', 'woman', 'female']:
        location.femaleAttendees = (location.femaleAttendees or 0) + 1

    db.session.commit()

    return jsonify({'message': 'User marked as attending and counts updated'}), 200


@app.route('/attend', methods=['GET'])
def get_attendance():
    user = get_current_user_from_token()
    if not user:
        return jsonify({'message': 'Unauthorized'}), 401

    location_id = request.args.get('location_id')
    if not location_id:
        return jsonify({'message': 'location_id is required'}), 400

    location = LocationInfo.query.get(location_id)
    if not location:
        return jsonify({'message': 'Location not found'}), 404

    attendances = Attendance.query.filter_by(location_id=location.id).all()

    attendee_list = []
    for attendance in attendances:
        attendee_user = User.query.get(attendance.user_id)
        profile = UserProfile.query.filter_by(user_auth_id=attendee_user.id).first()
        checked_in = CheckIn.query.filter_by(user_id=attendee_user.id, location_id=location.id).first() is not None

        attendee_list.append({
            'user_id': attendee_user.id,
            'email': attendee_user.email,
            'gender': profile.gender if profile else None,
            'attending_at': attendance.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'checked_in': checked_in,
            'hasAttended': attendance.hasAttended
        })

    total_attendees = (location.maleAttendees or 0) + (location.femaleAttendees or 0)

    return jsonify({
        'location': location.location,
        'date': location.date,
        'time': location.time,
        'maleAttendees': location.maleAttendees or 0,
        'femaleAttendees': location.femaleAttendees or 0,
        'totalAttendees': total_attendees,
        'maxAttendees': location.maxAttendees or 0,
        'attendees': attendee_list
    }), 200


@app.route('/attendances/<int:location_id>', methods=['GET'])
def get_user_attendance_for_location(location_id):
    user = get_current_user_from_token()
    if not user:
        return jsonify({'message': 'Unauthorized'}), 401

    record = Attendance.query.filter_by(user_id=user.id, location_id=location_id).first()
    return jsonify({'hasAttended': record.hasAttended if record else False})


# @app.route('/attend', methods=['GET'])
# def get_attendance():
#     location_id = request.args.get('location_id')
#     if not location_id:
#         return jsonify({'message': 'location_id is required'}), 400

#     location = LocationInfo.query.get(location_id)
#     if not location:
#         return jsonify({'message': 'Location not found'}), 404

#     attendances = Attendance.query.filter_by(location_id=location.id).all()

#     attendee_list = []
#     for attendance in attendances:
#         user = User.query.get(attendance.user_id)
#         profile = getattr(user, 'user_data', None)
#         checked_in = CheckIn.query.filter_by(user_id=user.id, location_id=location.id).first() is not None

#         attendee_list.append({
#             'user_id': user.id,
#             'email': user.email,
#             'gender': profile.gender if profile else None,
#             'attending_at': attendance.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
#             'checked_in': checked_in,
#             'hasAttended': attendance.hasAttended
#         })

#     total_attendees = (location.maleAttendees or 0) + (location.femaleAttendees or 0)

#     return jsonify({
#         'location': location.location,
#         'date': location.date,
#         'time': location.time,
#         'maleAttendees': location.maleAttendees or 0,
#         'femaleAttendees': location.femaleAttendees or 0,
#         'totalAttendees': total_attendees,
#         'maxAttendees': location.maxAttendees or 0,
#         'attendees': attendee_list
#     }), 200


# @app.route('/attendances/<int:user_id>/<int:location_id>', methods=['GET'])
# def get_user_attendance_for_location(user_id, location_id):
#     record = Attendance.query.filter_by(user_id=user_id, location_id=location_id).first()
#     return jsonify({'hasAttended': record.hasAttended if record else False})

# CHECK-IN AND ATTENDANCE -> End

# MATCHES FOR LOCATION -> Start

# @app.route('/matches_at_location/<int:user_id>/<int:location_id>', methods=['GET'])
# def get_user_matches_for_location(user_id, location_id):
#     try:
#         create_new_matches = request.args.get('create_new_matches')

#         if create_new_matches and create_new_matches == 'true':
#             match_making_result = trigger_matchmaking_for_location(location_id)
#             print(f"Match making at location result: {match_making_result}")

#         # Query to get all existing active matches for a given user at a specific location
#         existing_matches = (
#             db.session.query(Match)
#             .join(CheckIn, or_(
#                 CheckIn.user_id == Match.user1_id,
#                 CheckIn.user_id == Match.user2_id
#             ))
#             .filter(
#                 or_(Match.user1_id == user_id, Match.user2_id == user_id),
#                 Match.status == 'active',
#                 Match.location_id == location_id
#             )
#             .order_by(desc(Match.visible_after))
#             .all()
#         )

#         if len(existing_matches) == 0:
#             return jsonify({'message': 'No matches left for this event'}), 400

#         preferences = (UserPreference.query
#                        .filter(
#                             or_(UserPreference.user_id == user_id, UserPreference.preferred_user_id == user_id)
#                        ).all())

#         preference_pairs = set()
#         for pref in preferences:
#             preference_pairs.add((pref.user_id, pref.preferred_user_id))
#             preference_pairs.add((pref.preferred_user_id, pref.user_id)) # Add reverse pair also

#         # Format results with matches
#         result = []
#         for match in existing_matches:

#             matched_user_id = int(
#                 match.user2_id if match.user1_id == user_id else match.user1_id)  # get opposite match id

#             # Checking if this match already has a preference available
#             if (user_id, matched_user_id) in preference_pairs:
#                 print(f"SKIPPING: Existing preference found")
#                 continue

#             # Get user image if available
#             user_image = UserImages.query.filter_by(user_auth_id=matched_user_id).first()
#             image_url = None
#             if user_image and user_image.imageString:
#                 image_url = f"/uploads/{user_image.imageString}"

#             other_user_data = UserProfile.query.filter_by(user_auth_id=matched_user_id).first()

#             result.append({
#                 'user_id': matched_user_id,
#                 'email': other_user_data.email,
#                 'firstname': other_user_data.firstname,
#                 'lastname': other_user_data.lastname,
#                 'preferences': other_user_data.preferences,
#                 'age': other_user_data.age,
#                 'bio': other_user_data.bio,
#                 'hobbies': other_user_data.hobbies,
#                 'gender': other_user_data.gender,
#                 'phone_number': other_user_data.phone_number,
#                 'image_url': image_url,
#                 'status': match.status,
#                 'location': match.location_id,
#                 'current_server_time': get_unix_timestamp(datetime.now(timezone.utc)),
#                 'visible_after': match.visible_after
#             })

#         if len(result) == 0:
#             return jsonify({'message': 'No matches left for this event'}), 400

#         return jsonify({'matches': result})

#     except Exception as e:
#         print(f"Error in get_user_matches: {str(e)}")
#         return jsonify({'matches': []})

@app.route('/matches_at_location/<int:location_id>', methods=['GET'])
def get_user_matches_for_location(location_id):
    try:
        user = get_current_user_from_token()
        if not user:
            return jsonify({'message': 'Unauthorized'}), 401

        user_id = user.id

        # ✅ Fetch the location so we can access current_round
        location = LocationInfo.query.filter_by(id=location_id).first()
        if not location:
            return jsonify({'error': f'Location {location_id} not found'}), 404

        create_new_matches = request.args.get('create_new_matches')
        if create_new_matches and create_new_matches == 'true':
            match_making_result = trigger_matchmaking_for_location(location_id)
            print(f"Match making at location result: {match_making_result}")

        existing_matches = (
            db.session.query(Match)
            .join(CheckIn, or_(
                CheckIn.user_id == Match.user1_id,
                CheckIn.user_id == Match.user2_id
            ))
            .filter(
                or_(Match.user1_id == user_id, Match.user2_id == user_id),
                Match.status == 'active',
                Match.matched_expired == False,  # ✅ filter expired matches
                Match.location_id == location_id,
                Match.round_number == location.current_round  # ✅ prevents duplicate old rounds
            )
            .order_by(desc(Match.visible_after))
            .all()
        )

        if len(existing_matches) == 0:
            return jsonify({'message': 'No matches left for this event'}), 400

        preferences = (UserPreference.query
                       .filter(
                            or_(UserPreference.user_id == user_id, UserPreference.preferred_user_id == user_id)
                       ).all())

        preference_pairs = set()
        for pref in preferences:
            preference_pairs.add((pref.user_id, pref.preferred_user_id))
            preference_pairs.add((pref.preferred_user_id, pref.user_id))

        result = []
        for match in existing_matches:
            matched_user_id = int(
                match.user2_id if match.user1_id == user_id else match.user1_id)

            if (user_id, matched_user_id) in preference_pairs:
                print(f"SKIPPING: Existing preference found")
                continue

            user_image = UserImages.query.filter_by(user_auth_id=matched_user_id).first()
            image_url = None
            if user_image and user_image.imageString:
                image_url = f"/uploads/{user_image.imageString}"

            other_user_data = UserProfile.query.filter_by(user_auth_id=matched_user_id).first()
            other_user_info = UserInfo.query.filter_by(user_profile_id=other_user_data.id).first()
            other_user_character = UserCharacter.query.filter_by(user_profile_id=other_user_data.id).first()

            result.append({
                'user_id': matched_user_id,
                'email': other_user_data.email,
                'firstname': other_user_data.firstname,
                'lastname': other_user_data.lastname,
                'preferences': other_user_info.preferences if other_user_info else [],
                'age': other_user_data.age,
                'bio': other_user_info.bio if other_user_info else None,
                'hobbies': other_user_info.hobbies if other_user_info else [],
                'gender': other_user_data.gender,
                'phone_number': other_user_data.phone_number,
                'image_url': image_url,
                'status': match.status,
                'location': match.location_id,
                'match_id': match.id,  # ← rename from 'match' to 'match_id'
                'current_server_time': get_unix_timestamp(datetime.now(timezone.utc)),
                'visible_after': match.visible_after,
                'round_number': match.round_number,  # ✅ from Doc 1
                'muslimstatus': other_user_character.muslimstatus if other_user_character else None,
                'practicing': other_user_character.practicing if other_user_character else None,
                'nationality': other_user_character.nationality if other_user_character else None,
                'personality_type': other_user_character.personality_type if other_user_character else None,
            })

        if len(result) == 0:
            return jsonify({'message': 'No matches left for this event'}), 400

        return jsonify({'matches': result})

    except Exception as e:
        print(f"Error in get_user_matches: {str(e)}")
        return jsonify({'matches': []})

# MATCHES FOR LOCATION -> End

# PREFERENCE HANDLING -> Start

@app.route('/preference', methods=['POST'])
def set_preference():
    """
    Save or update user preference.
    When all users in a location have submitted preferences,
    update match consent status for each pair.
    """
    try:
        data = request.get_json()
        user_email = data.get('user_email')
        preferred_user_email = data.get('preferred_user_email')
        match_id = data.get('match_id')
        preference = data.get('preference')  # 'like', 'reject', 'save_later'

        # ✅ Validate inputs
        if not user_email or not preferred_user_email or not match_id or not preference:
            return jsonify({'error': 'Missing required fields'}), 400
        if preference not in ['like', 'reject', 'save_later']:
            return jsonify({'error': 'Invalid preference type'}), 400

        # ✅ Fetch match and validate it exists
        match = Match.query.get(match_id)
        if not match:
            return jsonify({'error': 'Match not found'}), 404

        # ✅ Get users
        user = UserProfile.query.filter_by(email=user_email).first()
        preferred_user = UserProfile.query.filter_by(email=preferred_user_email).first()
        if not user or not preferred_user:
            return jsonify({'error': 'One or both users not found'}), 404

        # ✅ Validate that the users are the participants of the match
        if not ((match.user1_id == user.id and match.user2_id == preferred_user.id) or
                (match.user1_id == preferred_user.id and match.user2_id == user.id)):
            return jsonify({'error': 'Provided users do not match the participants of the given match_id'}), 400

        # ✅ Find or create preference
        existing_pref = UserPreference.query.filter_by(
            user_id=user.id,
            preferred_user_id=preferred_user.id,
            match_id=match_id
        ).first()

        if existing_pref:
            if existing_pref.preference == preference:
                return jsonify({
                    'message': f'Preference already set to "{preference}" by {user.email} for {preferred_user.email}',
                    'match_id': match_id
                }), 200
            existing_pref.preference = preference
            existing_pref.timestamp = datetime.now(timezone.utc)
        else:
            db.session.add(UserPreference(
                user_id=user.id,
                preferred_user_id=preferred_user.id,
                match_id=match_id,
                preference=preference
            ))

        db.session.commit()

        # Update consent status for the pair
        update_match_consent_status(user.id, preferred_user.id, match_id)

        # Check if this preference completes the round
        match = Match.query.get(match_id)
        if match and match.location_id:
            check_and_trigger_next_round(match.location_id)

        return jsonify({
            'message': f'Preference "{preference}" set by {user.email} for {preferred_user.email}',
            'match_id': match_id
        }), 200

    except Exception as e:
        print(f"❌ Error in set_preference: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal Server Error'}), 500


# @app.route('/matches/<email>', methods=['GET'])
# def get_user_matches(email):
#     try:
#         user = User.query.filter_by(email=email).first()
#         if not user:
#             return jsonify({'error': 'User not found'}), 404

#         # Get all matches for this user that are visible now
#         current_time = datetime.now(timezone.utc)
#         matches = Match.query.filter(
#             or_(
#                 Match.user1_id == user.id,
#                 Match.user2_id == user.id
#             ),
#             Match.status != 'deleted',
#             Match.visible_after <= get_unix_timestamp(current_time)
#         ).all()

#         # Format the response
#         result = []
#         for match in matches:
#             # Determine the other user ID
#             other_user_id = match.user2_id if match.user1_id == user.id else match.user1_id
#             other_user = User.query.get(other_user_id)
#             other_user_data = UserProfile.query.filter_by(user_auth_id=other_user_id).first()

#             if not other_user or not other_user_data:
#                 continue

#             # Get user preferences
#             user_pref = UserPreference.query.filter_by(
#                 user_id=user.id, preferred_user_id=other_user_id
#             ).first()

#             other_pref = UserPreference.query.filter_by(
#                 user_id=other_user_id, preferred_user_id=user.id
#             ).first()

#             # Determine match status from user's perspective
#             if match.status == 'active':
#                 # Both liked each other
#                 display_status = 'matched'
#                 show_message_button = True
#             else:  # status is 'pending'
#                 if user_pref and user_pref.preference == 'save_later':
#                     display_status = 'decide'  # User needs to decide
#                     show_message_button = False
#                 elif other_pref and other_pref.preference == 'save_later':
#                     display_status = 'pending'  # Waiting for other user
#                     show_message_button = False
#                 else:
#                     display_status = 'pending'  # Generic pending
#                     show_message_button = False

#             # Get profile image
#             user_image = UserImages.query.filter_by(user_auth_id=other_user_id).first()
#             image_url = None
#             if user_image and user_image.imageString:
#                 image_url = request.host_url + 'uploads/' + user_image.imageString

#             # Add match to result
#             result.append({
#                 'match_id': match.id,
#                 'user_id': other_user_id,
#                 'firstname': other_user_data.firstname,
#                 'email': other_user.email,
#                 'age': other_user_data.age,
#                 'bio': other_user_data.bio,
#                 'status': display_status,
#                 'show_message_button': show_message_button,
#                 'match_date': match.match_date,
#                 'image_url': image_url
#             })

#         return jsonify({'matches': result}), 200

#     except Exception as e:
#         print(f"Error in get_user_matches: {str(e)}")
#         return jsonify({'error': 'Internal Server Error'}), 500


@app.route('/matches/me', methods=['GET'])
def get_user_matches():
    user = get_current_user_from_token()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        current_time = datetime.now(timezone.utc)
        matches = Match.query.filter(
            or_(
                Match.user1_id == user.id,
                Match.user2_id == user.id
            ),
            Match.status != 'deleted',
            Match.visible_after <= get_unix_timestamp(current_time)
        ).all()

        result = []
        for match in matches:
            other_user_id = match.user2_id if match.user1_id == user.id else match.user1_id
            other_user = User.query.get(other_user_id)
            other_user_data = UserProfile.query.filter_by(user_auth_id=other_user_id).first()

            if not other_user or not other_user_data:
                continue

            # Fetch all related tables
            other_user_info = UserInfo.query.filter_by(user_profile_id=other_user_data.id).first()
            other_user_character = UserCharacter.query.filter_by(user_profile_id=other_user_data.id).first()

            user_pref = UserPreference.query.filter_by(
                user_id=user.id, preferred_user_id=other_user_id
            ).first()

            other_pref = UserPreference.query.filter_by(
                user_id=other_user_id, preferred_user_id=user.id
            ).first()

            if match.status == 'active':
                display_status = 'matched'
                show_message_button = True
            else:
                if user_pref and user_pref.preference == 'save_later':
                    display_status = 'decide'
                    show_message_button = False
                elif other_pref and other_pref.preference == 'save_later':
                    display_status = 'pending'
                    show_message_button = False
                else:
                    display_status = 'pending'
                    show_message_button = False

            user_image = UserImages.query.filter_by(user_auth_id=other_user_id).first()
            image_url = None
            if user_image and user_image.imageString:
                image_url = request.host_url + 'uploads/' + user_image.imageString

            result.append({
                # Match info
                'match_id': match.id,
                'status': display_status,
                'show_message_button': show_message_button,
                'match_date': match.match_date.isoformat() if match.match_date else None,
                'location_id': match.location_id,

                # UserProfile
                'user_id': other_user_id,
                'firstname': other_user_data.firstname,
                'lastname': other_user_data.lastname,
                'email': other_user.email,
                'age': other_user_data.age,
                'gender': other_user_data.gender,
                'sect': other_user_data.sect,
                'lookingfor': other_user_data.lookingfor,
                'phone_number': other_user_data.phone_number,

                # UserInfo
                'bio': other_user_info.bio if other_user_info else None,
                'hobbies': other_user_info.hobbies if other_user_info else [],
                'preferences': other_user_info.preferences if other_user_info else [],
                'alcohol_status': other_user_info.alcoholstatus if other_user_info else None,
                'children_status': other_user_info.childrenstatus if other_user_info else None,
                'marital_status': other_user_info.maritalstatus if other_user_info else None,
                'smoke_status': other_user_info.smokestatus if other_user_info else None,
                'halal_food': other_user_info.halalfood if other_user_info else None,

                # UserCharacter
                'muslim_status': other_user_character.muslimstatus if other_user_character else None,
                'practicing': other_user_character.practicing if other_user_character else None,
                'nationality': other_user_character.nationality if other_user_character else None,
                'personality_type': other_user_character.personality_type if other_user_character else None,

                # Image
                'image_url': image_url
            })

        return jsonify({'matches': result}), 200

    except Exception as e:
        print(f"Error in get_user_matches: {str(e)}")
        return jsonify({'error': 'Internal Server Error'}), 500


# Only for users that are saved for later and waiting a decision (accept or reject) inside Matches screen on frontend -> Post their decision
@app.route('/update_match_status', methods=['POST'])
def update_match_status():
    """
    Handles user's 'accept' or 'reject' for a pending 'save_later' case.
    Updates UserPreference accordingly and triggers match consent recalculation.
    If all preferences for a location are submitted, checks whether the round is complete.
    """
    try:
        data = request.get_json()
        match_id = data.get('match_id')
        user_email = data.get('user_email')
        decision = data.get('decision')  # 'accept' or 'reject'

        # 1️⃣ Validate inputs
        if not match_id or not user_email or not decision:
            return jsonify({'error': 'Missing required fields'}), 400
        if decision not in ['accept', 'reject']:
            return jsonify({'error': 'Invalid decision'}), 400

        # 2️⃣ Get models
        user = UserProfile.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        match = Match.query.get(match_id)
        if not match:
            return jsonify({'error': 'Match not found'}), 404

        # Ensure user is one of the participants
        if match.user1_id != user.id and match.user2_id != user.id:
            return jsonify({'error': 'User not authorized for this match'}), 403

        other_user_id = match.user2_id if match.user1_id == user.id else match.user1_id
        location_id = match.location_id

        # 3️⃣ Fetch the user's current preference
        pref = UserPreference.query.filter_by(
            user_id=user.id,
            preferred_user_id=other_user_id,
            match_id=match_id
        ).first()

        new_preference = 'like' if decision == 'accept' else 'reject'

        if pref:
            # If a preference already exists and is not 'save_later', it cannot be changed again.
            if pref.preference in ['like', 'reject']:
                return jsonify({'error': 'Preference cannot be changed once set to like or reject'}), 403
            pref.preference = new_preference
            pref.timestamp = datetime.now(timezone.utc)
        else:
            pref = UserPreference(
                user_id=user.id,
                preferred_user_id=other_user_id,
                match_id=match_id,
                preference=new_preference
            )
            db.session.add(pref)
        
        db.session.commit()

        # 5️⃣ Update the consent for this pair
        update_match_consent_status(user.id, other_user_id, match_id)

        # 6️⃣ Check if this decision completes the round
        if location_id:
            check_and_trigger_next_round(location_id)

        return jsonify({
            'message': f'User {user.id} set decision "{decision}" for match {match_id}',
            'new_preference': new_preference
        }), 200

    except Exception as e:
        print(f"❌ Error in update_match_status: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal Server Error'}), 500

# PREFERENCE HANDLING -> End

# MATCHMAKING LOGIC UTILITIES -> Start

# Given a user id returns the best 5 matches sorted
# @app.route('/match/<int:user_id>', methods=['GET'])
# def get_matches_endpoint(user_id):
#     matches = get_user_matches(user_id)
#     return jsonify({
#         'user_id': user_id,
#         'matches': matches
#     })


# Get all users best matches
# @app.route('/matches', methods=['GET'])
# def get_all_matches():
#     matches = match_all_users()
#     return jsonify({'matches': matches})


# MATCHMAKING LOGIC UTILITIES -> End


# CHAT FUNCTIONALITY -> Start

@app.route('/send_message', methods=['POST'])
def send_message():
    sender_email = request.form.get('sender_email')
    receiver_email = request.form.get('receiver_email')
    message = request.form.get('message')

    # Check if any of the fields are missing
    if not sender_email or not receiver_email or not message:
        return jsonify({'error': 'Missing data'}), 400

    # Look up user IDs based on emails
    sender = User.query.filter_by(email=sender_email).first()
    receiver = User.query.filter_by(email=receiver_email).first()

    if not sender or not receiver:
        return jsonify({'error': 'Sender or receiver not found'}), 404

    # Store the message in the database
    new_message = Message(sender_id=sender.id, receiver_id=receiver.id, message=message)
    db.session.add(new_message)
    db.session.commit()

    # Emit the message to the receiver's room using receiver's email
    socketio.emit('receive_message', {
        'sender_email': sender_email,
        'receiver_email': receiver_email,
        'message': message
    }, room=receiver_email)

    return jsonify({'status': 'Message sent'})


@socketio.on('send_message')
def handle_message(data):
    sender_email = data['sender_email']
    receiver_email = data['receiver_email']
    message = data['message']

    # Look up user IDs based on emails
    sender = User.query.filter_by(email=sender_email).first()
    receiver = User.query.filter_by(email=receiver_email).first()

    if not sender or not receiver:
        emit('error', {'error': 'Sender or receiver not found'})
        return

    # Store the message in the database
    new_message = Message(sender_id=sender.id, receiver_id=receiver.id, message=message)
    db.session.add(new_message)
    db.session.commit()

    # Emit the message to the receiver's room using receiver's email
    emit('receive_message', {
        'sender_email': sender_email,
        'receiver_email': receiver_email,
        'message': message
    }, room=receiver_email)


@socketio.on('join')
def on_join(data):
    user_email = data['user_email']
    user = User.query.filter_by(email=user_email).first()

    if not user:
        emit('error', {'error': 'User not found'})
        return

    join_room(user_email)  # Join the room based on email
    emit('status', {'msg': f'User {user_email} has entered the room.'}, room=user_email)


@app.route('/get_chats', methods=['GET'])
def get_chats():
    email1 = request.args.get('email1')
    email2 = request.args.get('email2')

    if not email1 or not email2:
        return jsonify({'error': 'Missing email addresses'}), 400

    # Retrieve user IDs based on the provided emails
    user1 = User.query.filter_by(email=email1).first()
    user2 = User.query.filter_by(email=email2).first()

    if not user1 or not user2:
        return jsonify({'error': 'One or both users not found'}), 404

    # Fetch the chat history between the two users
    messages = Message.query.filter(
        ((Message.sender_id == user1.id) & (Message.receiver_id == user2.id)) |
        ((Message.sender_id == user2.id) & (Message.receiver_id == user1.id))
    ).order_by(Message.timestamp).all()

    # Prepare the chat history for response, adding sender and receiver emails
    chat_history = [
        {
            'sender_id': msg.sender_id,
            'sender_email': user1.email if msg.sender_id == user1.id else user2.email,
            'receiver_id': msg.receiver_id,
            'receiver_email': user2.email if msg.receiver_id == user2.id else user1.email,
            'message': msg.message,
            'timestamp': msg.timestamp
        }
        for msg in messages
    ]

    return jsonify(chat_history)

# CHAT FUNCTIONALITY -> End

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
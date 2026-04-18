
from datetime import datetime, time, timezone
import re, os
from email.policy import default
from flask import Flask, jsonify, request, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, join_room, disconnect, emit
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
import enum
from sqlalchemy.orm import validates
from PIL import Image                    # ✅ NEW: For image resizing
from functools import lru_cache
from io import BytesIO                    # ✅ NEW: For in-memory file handling
import boto3
import uuid
import botocore
from xml.etree.ElementTree import Comment
from uuid import uuid4
from flask import redirect
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.config[
    'SQLALCHEMY_DATABASE_URI'] = "postgresql://wingit06_render_example_user:rLG7cWFSshdcxYoWMiYiHhaGapGLZ9Nv@dpg-d7hlf7pf9bms73fmiing-a.frankfurt-postgres.render.com/wingit06_render_example"
socketio = SocketIO(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)  # 2️⃣ migrate second, now db exists
bcrypt = Bcrypt()

# Set the upload folder configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = 'a8f4c2e1b5d6f7a8c9e0d1f2b3a4c5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2'
SECRET_KEY = app.config['SECRET_KEY']
# ✅ NEW: Configuration constants
MAX_FILE_SIZE = 50 * 1024 * 1024        # 50MB
MAX_IMAGE_WIDTH = 4000
MAX_IMAGE_HEIGHT = 4000

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


class GenderEnum(enum.Enum):
    male = "Male"
    female = "Female"

class GenderRestriction(enum.Enum):
    everyone = "Everyone"  # check exact casing/value here
    male_only = "Male-only"   # check exact casing/value here
    female_only = "Female-only"

class User(db.Model):
    __tablename__ = 'user_credentials'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    profile = db.relationship('UserProfile', back_populates='user', uselist=False, cascade='all, delete-orphan')
    preferences = db.relationship('UserPreferences', back_populates='user', uselist=False, cascade='all, delete-orphan')
    images = db.relationship('UserImages', back_populates='user', cascade='all, delete-orphan', lazy=True)
    attendances = db.relationship('Attendance', back_populates='user', lazy=True, cascade='all, delete-orphan')
    checkins = db.relationship('CheckIn', back_populates='user', lazy=True, cascade='all, delete-orphan')
    sent_messages = db.relationship('ChatMessage', foreign_keys='ChatMessage.sender_id', back_populates='sender')
    received_messages = db.relationship('ChatMessage', foreign_keys='ChatMessage.receiver_id', back_populates='receiver')
    matches_as_user1 = db.relationship('Match', foreign_keys='Match.user1_id', back_populates='user1')
    matches_as_user2 = db.relationship('Match', foreign_keys='Match.user2_id', back_populates='user2')
    user_match_decisions = db.relationship('MatchDecision', foreign_keys='MatchDecision.user_id', back_populates='user')
    preferred_by = db.relationship('MatchDecision', foreign_keys='MatchDecision.preferred_user_id', back_populates='preferred_user')
    created_groups = db.relationship('Groups', back_populates='creator')
    group_memberships = db.relationship('GroupMember', back_populates='user', cascade='all, delete-orphan')


class UserProfile(db.Model):
    __tablename__ = 'user_profile'

    id = db.Column(db.Integer, primary_key=True)
    user_auth_id = db.Column(db.Integer, db.ForeignKey('user_credentials.id', ondelete='CASCADE'), nullable=False, unique=True)
    gender = db.Column(db.Enum(GenderEnum))
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    date_of_birth = db.Column(db.Date)
    phone_number = db.Column(db.String(20))
    bio = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    user = db.relationship('User', back_populates='profile', lazy=True)


class UserPreferences(db.Model):
    __tablename__ = 'user_preferences'

    id = db.Column(db.Integer, primary_key=True)
    user_auth_id = db.Column(db.Integer, db.ForeignKey('user_credentials.id', ondelete='CASCADE'), nullable=False, unique=True)
    looking_for = db.Column(db.String(255))
    open_for = db.Column(db.String(255))
    hobbies = db.Column(db.ARRAY(db.String))
    preferences = db.Column(db.ARRAY(db.String))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    user = db.relationship('User', back_populates='preferences')


class UserImages(db.Model):
    __tablename__ = 'user_images'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_credentials.id', ondelete='CASCADE'), nullable=False, index=True)
    image_url = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='images')


class EventHost(db.Model):
    __tablename__ = 'event_hosts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), unique=True, nullable=False)


class EventCategory(db.Model):
    __tablename__ = 'event_categories'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), unique=True, nullable=False)


class EventLocation(db.Model):
    __tablename__ = 'event_locations'

    id = db.Column(db.Integer, primary_key=True)
    max_attendees = db.Column(db.Integer, nullable=False)
    max_male_attendees = db.Column(db.Integer, nullable=True)
    max_female_attendees = db.Column(db.Integer, nullable=True)
    start_time = db.Column(db.DateTime, nullable=False)
    location_name = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    description = db.Column(db.String(500))
    total_price = db.Column(db.Numeric(10, 2))
    currency = db.Column(db.String(10), default="SEK")
    is_checkin_closed = db.Column(db.Boolean, default=False)
    is_matchmaking_enabled = db.Column(db.Boolean, default=False)
    current_round = db.Column(db.Integer, default=1)
    event_category_id = db.Column(db.Integer, db.ForeignKey('event_categories.id'), nullable=False)
    event_host_id = db.Column(db.Integer, db.ForeignKey('event_hosts.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    event_category = db.relationship('EventCategory', lazy='selectin')
    event_host = db.relationship('EventHost', lazy='selectin')
    attendances = db.relationship('Attendance', back_populates='location', lazy=True, cascade='all, delete-orphan')
    checkins = db.relationship('CheckIn', back_populates='location', lazy=True, cascade='all, delete-orphan')
    matches_at_location = db.relationship('Match', back_populates='location', cascade='all, delete-orphan')  # ✅ added cascade

    @validates('max_male_attendees', 'max_female_attendees')
    def validate_gender_limits(self, key, value):
        if value is not None and value < 0:
            raise ValueError(f"{key} cannot be negative")
        return value

    def validate_attendee_totals(self):
        validate_attendee_totals(self.max_attendees, self.max_male_attendees, self.max_female_attendees)

    def _count_by_gender(self, gender: GenderEnum) -> int:
        return (
            Attendance.query
            .join(User, User.id == Attendance.user_id)
            .join(UserProfile, UserProfile.user_auth_id == User.id)
            .filter(Attendance.location_id == self.id, UserProfile.gender == gender)
            .count()
        )

    def can_register(self, gender: GenderEnum) -> tuple[bool, str]:
        total = Attendance.query.filter_by(location_id=self.id).count()
        if total >= self.max_attendees:
            return False, "Event is fully booked"
        if gender == GenderEnum.male and self.max_male_attendees is not None:
            if self._count_by_gender(GenderEnum.male) >= self.max_male_attendees:
                return False, f"No male spots remaining ({self.max_male_attendees} max)"
        if gender == GenderEnum.female and self.max_female_attendees is not None:
            if self._count_by_gender(GenderEnum.female) >= self.max_female_attendees:
                return False, f"No female spots remaining ({self.max_female_attendees} max)"
        return True, ""


class Attendance(db.Model):
    __tablename__ = 'user_attendance'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_credentials.id', ondelete='CASCADE'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('event_locations.id', ondelete='CASCADE'), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))  # ✅ lambda
    hasAttended = db.Column(db.Boolean, default=False)

    user = db.relationship('User', back_populates='attendances')
    location = db.relationship('EventLocation', back_populates='attendances')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'location_id', name='unique_user_location_attendance'),
    )


class CheckIn(db.Model):
    __tablename__ = 'user_checkins'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_credentials.id', ondelete='CASCADE'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('event_locations.id', ondelete='CASCADE'), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))  # ✅ lambda

    user = db.relationship('User', back_populates='checkins')
    location = db.relationship('EventLocation', back_populates='checkins')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'location_id', name='unique_user_location_checkin'),
    )


class MatchDecision(db.Model):
    __tablename__ = 'user_match_decision'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_credentials.id', ondelete='CASCADE'), nullable=False)
    preferred_user_id = db.Column(db.Integer, db.ForeignKey('user_credentials.id', ondelete='CASCADE'), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id', ondelete='CASCADE'), nullable=False)
    preference = db.Column(db.String(20), nullable=False)  # 'like', 'reject', 'save_later'
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))  # ✅ lambda

    user = db.relationship('User', foreign_keys=[user_id], back_populates='user_match_decisions')
    preferred_user = db.relationship('User', foreign_keys=[preferred_user_id], back_populates='preferred_by')
    match = db.relationship('Match', back_populates='decisions')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'preferred_user_id', 'match_id', name='unique_user_match_decision'),
    )


class Match(db.Model):
    __tablename__ = 'matches'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('user_credentials.id', ondelete='CASCADE'), nullable=False)  # ✅ cascade
    user2_id = db.Column(db.Integer, db.ForeignKey('user_credentials.id', ondelete='CASCADE'), nullable=False)  # ✅ cascade
    match_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))  # ✅ lambda
    visible_after = db.Column(db.Integer)
    status = db.Column(db.String(20), default='pending')
    consent = db.Column(db.String(20), default='pending')
    location_id = db.Column(db.Integer, db.ForeignKey('event_locations.id'), nullable=True)
    matched_expired = db.Column(db.Boolean, default=False)
    round_number = db.Column(db.Integer, default=1)

    user1 = db.relationship('User', foreign_keys=[user1_id], back_populates='matches_as_user1')
    user2 = db.relationship('User', foreign_keys=[user2_id], back_populates='matches_as_user2')
    location = db.relationship('EventLocation', back_populates='matches_at_location')
    decisions = db.relationship('MatchDecision', back_populates='match', cascade='all, delete-orphan')


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user_credentials.id', ondelete='CASCADE'), nullable=False)  # ✅ cascade
    receiver_id = db.Column(db.Integer, db.ForeignKey('user_credentials.id', ondelete='CASCADE'), nullable=False)  # ✅ cascade
    message = db.Column(db.Text, nullable=False)
    reply_to_id = db.Column(db.Integer, db.ForeignKey('chat_messages.id'), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    image_url = db.Column(db.String())

    sender = db.relationship('User', foreign_keys=[sender_id], back_populates='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], back_populates='received_messages')
    reply_to = db.relationship('ChatMessage', foreign_keys=[reply_to_id], remote_side=[id], back_populates='replies')  # ✅ foreign_keys
    replies = db.relationship('ChatMessage', foreign_keys=[reply_to_id], back_populates='reply_to')  # ✅ foreign_keys


class GroupMember(db.Model):
    __tablename__ = 'group_members'

    group_id = db.Column(db.Integer, db.ForeignKey('groups.id', ondelete='CASCADE'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_credentials.id', ondelete='CASCADE'), primary_key=True)
    role = db.Column(db.String(20), default='member')
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    group = db.relationship('Groups', back_populates='memberships')
    user = db.relationship('User', back_populates='group_memberships')


class Groups(db.Model):
    __tablename__ = 'groups'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(255))
    gender_restriction = db.Column(db.Enum(GenderRestriction), default=GenderRestriction.everyone, nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user_credentials.id', ondelete='SET NULL'), nullable=True)  # ✅ SET NULL so group survives if creator deleted
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', back_populates='created_groups')
    memberships = db.relationship('GroupMember', back_populates='group', cascade='all, delete-orphan')

    @property
    def members(self):
        return [m.user for m in self.memberships]

    @property
    def members_count(self):
        return GroupMember.query.filter_by(group_id=self.id).count()

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "image_url": self.image_url,
            "members_count": self.members_count,
            "gender_restriction": self.gender_restriction.value,
            "created_at": self.created_at.isoformat(),
        }



with app.app_context():
    # Match.__table__.drop(db.engine)
    # UserPreference.__table__.drop(db.engine)
    # Attendance.__table__.drop(db.engine)
    # CheckIn.__table__.drop(db.engine)
    db.create_all()

# Define functions

def create_token(user):
    payload = {
        "user_id": user.id,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def get_current_user_from_token():
    auth_header = request.headers.get('Authorization', None)
    if not auth_header or not auth_header.startswith("Bearer "):
        print("No Authorization header or wrong format")
        return None

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
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


def validate_attendee_totals(max_attendees: int, max_male: int | None, max_female: int | None):
    male = max_male or 0
    female = max_female or 0

    if max_male is not None and male > max_attendees:
        raise ValueError(f"max_male_attendees ({male}) exceeds max_attendees ({max_attendees})")

    if max_female is not None and female > max_attendees:
        raise ValueError(f"max_female_attendees ({female}) exceeds max_attendees ({max_attendees})")

    if max_male is not None and max_female is not None:
        if male + female > max_attendees:
            raise ValueError(
                f"Combined gender limits ({male} + {female} = {male + female}) "
                f"exceed max_attendees ({max_attendees})"
            )


def generate_temp_filename(file):
    """
    Generate a safe, unique filename for an uploaded image in the pattern:
        temp_image_file<timestamp>.<extension>
    
    Example:
        temp_image_file1741434790790.jpg
    """
    # Extract the extension from the original filename
    _, ext = os.path.splitext(secure_filename(file.filename))

    # Generate a timestamp-based unique filename
    timestamp = int(time() * 1000)

    # Combine into final format
    return f"temp_image_file{timestamp}{ext}"


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def process_potential_match(user1_id, user2_id, location_id=None):
    """
    Handles active matchmaking updates based on mutual preferences.
    - Runs during the active matchmaking round.
    - Updates match consent: 'active', 'pending', or 'deleted'.
    - Marks rejected matches as expired and sets matched_expired = True.
    - Only affects active, non-expired matches for the current round.
    """

    try:
        # Fetch both user preferences
        pref1 = UserPreferences.query.filter_by(user_id=user1_id, preferred_user_id=user2_id).first()
        pref2 = UserPreferences.query.filter_by(user_id=user2_id, preferred_user_id=user1_id).first()

        pref1_val = pref1.preference if pref1 else None
        pref2_val = pref2.preference if pref2 else None

        # Build base query for the current match
        match_query = Match.query.filter(
            or_(
                and_(Match.user1_id == user1_id, Match.user2_id == user2_id),
                and_(Match.user1_id == user2_id, Match.user2_id == user1_id)
            ),
            Match.status == 'active',
            Match.matched_expired == False
        )

        # Restrict to current round if location_id is provided
        if location_id:
            location = EventLocation.query.get(location_id)
            if location:
                match_query = match_query.filter(Match.round_number == location.current_round)

        existing_match = match_query.first()

        if not existing_match:
            print(f"⚠️ No active match found between users {user1_id} and {user2_id}")
            return

        # Determine consent logic
        new_consent = "pending"
        if pref1_val == "reject" or pref2_val == "reject":
            new_consent = "deleted"
        elif pref1_val == "like" and pref2_val == "like":
            new_consent = "active"
        elif (pref1_val == "save_later" or pref2_val == "save_later") and "reject" not in [pref1_val, pref2_val]:
            new_consent = "pending"

        # Apply updates if consent changes OR if it's a rejected match
        if existing_match.consent != new_consent or new_consent == "deleted":
            print(f"🔄 Updating match {existing_match.id} consent: {existing_match.consent} → {new_consent}")

            existing_match.consent = new_consent
            existing_match.last_updated = datetime.now(timezone.utc)

            # Delay visibility for mutual likes
            if new_consent == "active":
                existing_match.visible_after = get_unix_timestamp(
                    datetime.now(timezone.utc) + timedelta(minutes=20)
                )

            # Mark rejected matches as expired
            if new_consent == "deleted":
                existing_match.status = "expired"
                existing_match.matched_expired = True

            db.session.add(existing_match)
            db.session.commit()
        else:
            print(f"ℹ️ No consent change for match {existing_match.id} (still {new_consent})")

    except Exception as e:
        print(f"❌ Error in process_potential_match: {str(e)}")
        db.session.rollback()


def get_unix_timestamp(datatime):
    # Convert to Unix timestamp (seconds since epoch)
    unix_ts = int(datatime.timestamp())

    return unix_ts


def get_round_status(location_id):
    """
    Checks the status of the current matchmaking round at a location.

    Returns:
        A tuple: (all_preferences_in, has_save_later)
        - all_preferences_in (bool): True if all possible preferences for the round have been submitted.
        - has_save_later (bool): True if any of the submitted preferences are 'save_later'.
    """
    location = EventLocation.query.get(location_id)
    if not location:
        return False, False

    # Get all active matches for the current round
    matches_for_round = Match.query.filter_by(
        location_id=location_id,
        round_number=location.current_round,
        status='active'
    ).all()

    if not matches_for_round:
        return True, False  # No active matches = round complete

    all_preferences_in = True
    has_save_later = False

    for match in matches_for_round:
        # Check if both sides submitted preferences
        pref1 = UserPreferences.query.filter_by(
            user_id=match.user1_id,
            preferred_user_id=match.user2_id,
            match_id=match.id
        ).first()
        pref2 = UserPreferences.query.filter_by(
            user_id=match.user2_id,
            preferred_user_id=match.user1_id,
            match_id=match.id
        ).first()

        # Missing any preference? Round not complete yet
        if not pref1 or not pref2:
            all_preferences_in = False

        # Note if any preference is 'save_later'
        if (pref1 and pref1.preference == 'save_later') or \
           (pref2 and pref2.preference == 'save_later'):
            has_save_later = True

    return all_preferences_in, has_save_later
     
    
def has_user_checked_in(user_id, location_id):
    return db.session.query(CheckIn).filter_by(user_id=user_id, location_id=location_id).first() is not None
  
# New code    
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

    pref1 = UserPreferences.query.filter_by(user_id=user1_id, preferred_user_id=user2_id, match_id=match.id).first()
    pref2 = UserPreferences.query.filter_by(user_id=user2_id, preferred_user_id=user1_id, match_id=match.id).first()

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

    location = EventLocation.query.get(location_id)
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
    location = EventLocation.query.get(location_id)
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
        pref1 = UserPreferences.query.filter_by(user_id=match.user1_id, preferred_user_id=match.user2_id, match_id=match.id).first()
        pref2 = UserPreferences.query.filter_by(user_id=match.user2_id, preferred_user_id=match.user1_id, match_id=match.id).first()

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
        location = EventLocation.query.get(location_id)
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


# ✅ NEW: Validate file size before processing
def validate_image_size(file):
    """Check file size before processing"""
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        return False, f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds maximum of {MAX_FILE_SIZE / 1024 / 1024:.0f}MB"
    return True, None


# ✅ NEW: Resize and optimize images
def resize_image_if_needed(file, max_width=MAX_IMAGE_WIDTH, max_height=MAX_IMAGE_HEIGHT):
    """
    Resize image if it exceeds maximum dimensions.
    Returns: BytesIO object with resized image and detected format
    """
    try:
        image = Image.open(file)
        original_format = image.format or 'JPEG'
        
        # Check dimensions and resize if needed (maintains aspect ratio)
        if image.width > max_width or image.height > max_height:
            image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Convert to RGB if necessary (for JPEG compatibility)
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        
        # Save to BytesIO for upload
        output = BytesIO()
        output.seek(0)
        image.save(output, format=original_format, quality=85, optimize=True)
        output.seek(0)
        
        return output, original_format.lower()
    
    except Exception as e:
        raise ValueError(f"Image processing failed: {str(e)}")    


# API Endpoints

# USER SIGNIN METHOD
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
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        if isinstance(token, bytes):
            token = token.decode('utf-8')

        return jsonify({'message': 'Sign in successful', 'token': token}), 200
    except Exception as e:
        print("Sign-in error:", e)
        return jsonify({'error': str(e)}), 500


# Getting Sign-in DATA
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


# Delete users from the app
@app.route('/delete_user/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    # 1. Verify the token and get the current user
    current_user = get_current_user_from_token()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    # 2. Allow if it's the user themselves OR an admin
    if current_user.id != user_id and not current_user.is_admin:
        return jsonify({"error": "Forbidden: You can only delete your own account"}), 403

    # 3. Fetch the user to delete
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "User and all related data deleted successfully"}), 200


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
            return jsonify({'message': 'Email already exists'}), 409  # ✅ 409 Conflict is more accurate than 400

        # Hash password before storing ✅
        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        new_user = User(email=new_email, password_hash=hashed_password)
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


# METHOD TO GET AUTHENTICATED USERS LIST — admin only ✅
@app.route("/users", methods=["GET"])
def home():
    current_user = get_current_user_from_token()

    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    # ✅ Only admins can list all users
    if not current_user.is_admin:
        return jsonify({"error": "Forbidden: Admins only"}), 403

    tasks = User.query.all()
    task_list = [
        {'id': task.id, 'email': task.email} for task in tasks  # ✅ Never expose passwords
    ]
    return jsonify({"user_details": task_list})


@app.route("/loggedinUserProfileData", methods=["GET"])
def logged_in_user_profile():

    user = get_current_user_from_token()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    profile = user.profile  # ✅ Use relationship instead of querying manually

    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    preferences = user.preferences  # ✅ Was profile.info/profile.character — now UserPreferences

    # ✅ Use relationship, grab first image, match field name image_url not imageString
    user_image = user.images[0] if user.images else None

    response = {
        "auth": {
            "id": user.id,
            "email": user.email,
            "created_at": user.created_at.isoformat(),
        },
        "profile": {
            "first_name": profile.first_name,       
            "last_name": profile.last_name,          
            "gender": profile.gender.value if profile.gender else None,  
            "date_of_birth": profile.date_of_birth.isoformat() if profile.date_of_birth else None,  # ✅ was age — now date_of_birth
            "phone_number": profile.phone_number,
            "bio": profile.bio,                      
        },
        "preferences": {                              
            "looking_for": preferences.looking_for if preferences else None,
            "open_for": preferences.open_for if preferences else None,
            "hobbies": preferences.hobbies if preferences else [],
            "preferences": preferences.preferences if preferences else [],
        },
        # ✅ was user_image.imageString — correct field is image_url
        "image_url": user_image.image_url if user_image else None
    }

    return jsonify(response), 200


# PUT METHOD TO UPDATE USER PROFILE
@app.route("/updateUserProfile", methods=["PUT"])
def update_user_profile():

    # Get current user
    user = get_current_user_from_token()

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    # ✅ Use relationship instead of querying manually
    profile = user.profile

    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    # Get JSON body
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    # ✅ Update profile fields — matched to UserProfile column names
    if "firstName" in data:
        profile.first_name = data["firstName"]          
    if "lastName" in data:
        profile.last_name = data["lastName"]            
    if "phoneNumber" in data:
        profile.phone_number = data["phoneNumber"]
    if "dateOfBirth" in data:
        profile.date_of_birth = data["dateOfBirth"]     
    if "gender" in data:
        profile.gender = data["gender"]
    if "bio" in data:
        profile.bio = data["bio"]                       

    preferences = user.preferences

    if preferences:
        if "lookingFor" in data:
            preferences.looking_for = data["lookingFor"]   
        if "openFor" in data:
            preferences.open_for = data["openFor"]
        if "hobbies" in data:
            preferences.hobbies = data["hobbies"]
        if "preferences" in data:
            preferences.preferences = data["preferences"]
    else:
        # Create preferences record if it doesn't exist
        if any(k in data for k in ["lookingFor", "openFor", "hobbies", "preferences"]):
            preferences = UserPreferences(
                user_auth_id=user.id,
                looking_for=data.get("lookingFor"),
                open_for=data.get("openFor"),
                hobbies=data.get("hobbies", []),
                preferences=data.get("preferences", []),
            )
            db.session.add(preferences)

    # Commit all changes
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to update profile", "details": str(e)}), 500

    return jsonify({"message": "Profile updated successfully"}), 200


# POST USER PROFILE INFO
@app.route('/userProfile', methods=['POST'])
def postUserProfileData():
    user = get_current_user_from_token()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # ✅ Use relationship instead of querying manually
    profile = user.profile
    if not profile:
        profile = UserProfile(user_auth_id=user.id)
        db.session.add(profile)

    # ✅ Match UserProfile column names exactly
    if 'firstName' in data:
        profile.first_name = data.get('firstName')     
    if 'lastName' in data:
        profile.last_name = data.get('lastName')      
    if 'gender' in data:
        profile.gender = data.get('gender')
    if 'dateOfBirth' in data:
        profile.date_of_birth = data.get('dateOfBirth') # was age
    if 'phoneNumber' in data:
        profile.phone_number = data.get('phoneNumber')
    if 'bio' in data:
        profile.bio = data.get('bio')

    preference_keys = ['lookingFor', 'openFor', 'hobbies', 'preferences']
    if any(k in data for k in preference_keys):
        preferences = user.preferences
        if not preferences:
            preferences = UserPreferences(user_auth_id=user.id)
            db.session.add(preferences)

        if 'lookingFor' in data:
            preferences.looking_for = data.get('lookingFor')   
        if 'openFor' in data:
            preferences.open_for = data.get('openFor')
        if 'hobbies' in data:
            preferences.hobbies = data.get('hobbies')
        if 'preferences' in data:
            preferences.preferences = data.get('preferences')

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to save profile', 'details': str(e)}), 500

    return jsonify({'message': 'Profile saved'}), 201


# GET ALL USER PROFILES — admin only
@app.route('/userProfile', methods=['GET'])
def getUserProfileData():
    # ✅ Protect this endpoint — it returns all users' data
    current_user = get_current_user_from_token()
    if not current_user:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        profiles = UserProfile.query.all()
        users = []

        for profile in profiles:
            auth_user = profile.user                            
            user_image = auth_user.images[0] if auth_user.images else None  

            user_data = {
                'id': profile.user_auth_id,
                'first_name': profile.first_name,               
                'last_name': profile.last_name,                 
                'gender': profile.gender.value if profile.gender else None,  
                'email': auth_user.email,                       
                'date_of_birth': profile.date_of_birth.isoformat() if profile.date_of_birth else None,  # ✅ was age
                'phone_number': profile.phone_number,
                'bio': profile.bio,                             
                'looking_for': auth_user.preferences.looking_for if auth_user.preferences else None,
                'open_for': auth_user.preferences.open_for if auth_user.preferences else None,
                'image_url': user_image.image_url if user_image else None,  
                'current_server_time': get_unix_timestamp(datetime.now(timezone.utc)),
            }
            users.append(user_data)

        return jsonify({'users': users}), 200

    except Exception as e:
        return jsonify({'error': f'Internal Server Error: {e}'}), 500


@app.route('/upload_image', methods=['POST'])
def upload_image():
    user = get_current_user_from_token()
    if not user:
        return jsonify({'message': 'Unauthorized'}), 401

    user_id = user.id  # ✅ Extract ID once

    try:
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400

        file = request.files['image']

        if not file or not allowed_file(file.filename):
            return jsonify({"error": "Invalid image format"}), 400

        is_valid, error_msg = validate_image_size(file)
        if not is_valid:
            return jsonify({"error": error_msg}), 413

        try:
            processed_image, image_format = resize_image_if_needed(file)
            content_type = f"image/{image_format}"
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        filename = secure_filename(file.filename)
        
        # ✅ CRITICAL: Use user_id for folder organization
        object_key = f"user_uploads/{user_id}/{uuid4()}_{filename}"

        try:
            s3 = get_s3_client()
            s3.put_object(
                Bucket=os.environ.get('DO_SPACE_NAME'),
                Key=object_key,
                Body=processed_image,
                ACL='public-read',
                ContentType=content_type,
                CacheControl='max-age=31536000'
            )

            image_url = f"{os.environ.get('DO_SPACE_URL')}/{object_key}"

        except botocore.exceptions.ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                return jsonify({'message': 'Storage misconfiguration'}), 500
            elif error_code == 'AccessDenied':
                return jsonify({'message': 'Storage access denied'}), 500
            else:
                return jsonify({'message': 'Image upload failed'}), 500

        except Exception as e:
            return jsonify({'message': 'Image upload failed'}), 500

        # ✅ CRITICAL: Use user_id, NOT user.id
        user_image = UserImages.query.filter_by(user_auth_id=user_id).first()
        if user_image:
            user_image.imageString = image_url
            message = "Updated user image"
        else:
            user_image = UserImages(
                user_auth_id=user_id,
                email=user.email,
                imageString=image_url
            )
            db.session.add(user_image)
            message = "Added new user image"

        db.session.commit()

        response_data = {
            "message": message,
            "image_url": image_url,
            "image_format": image_format
        }

        return jsonify(response_data), 201

    except Exception as e:
        import traceback
        print(traceback.format_exc())  # ✅ Shows actual error
        return jsonify({
            "error": "Image upload failed",
            "details": str(e)
        }), 500


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    # Construct the public URL for the file in DigitalOcean Spaces
    file_url = f"{os.environ.get('DO_SPACE_URL')}/{filename}"
    return redirect(file_url)


@app.route('/get_image/me', methods=['GET'])
def get_my_image():
    user = get_current_user_from_token()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    # ✅ Use relationship and correct FK column name (user_id, not user_auth_id)
    user_image = user.images[0] if user.images else None

    if user_image:
        return jsonify({
            "id": user_image.id,
            "user_id": user_image.user_id,        
            "image_url": user_image.image_url,    
            "created_at": user_image.created_at.isoformat(),
        }), 200
    else:
        return jsonify({"error": "No image found for this user"}), 404


@app.route('/eventLocationInfo', methods=['POST'])
def postLocationInfo():
    try:
        # ===== AUTH =====
        user = get_current_user_from_token()
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401

        # ===== REQUEST DATA =====
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

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
        except SQLAlchemyError as e:
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
        except SQLAlchemyError as e:
            traceback.print_exc()
            return jsonify({"error": "Host processing failed"}), 500

        # ===== FIELDS =====
        try:
            # ✅ date + time merged into a single start_time DateTime
            date_str = data.get('date')         # "YYYY-MM-DD"
            time_str = data.get('time')         # "HH:MM"
            if not date_str or not time_str:
                return jsonify({"error": "date and time are required"}), 400

            start_time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

            new_event = EventLocation(
                max_attendees=int(data.get('maxAttendees')),
                max_male_attendees=int(data['maxMaleAttendees']) if data.get('maxMaleAttendees') is not None else None,
                max_female_attendees=int(data['maxFemaleAttendees']) if data.get('maxFemaleAttendees') is not None else None,
                start_time=start_time,                              
                location_name=data.get('location'),                 
                latitude=float(data.get('lat')),                    
                longitude=float(data.get('lng')),                   
                total_price=float(data.get('totalPrice')),          
                currency=data.get('currency', 'SEK'),               
                description=data.get('description'),
                is_matchmaking_enabled=bool(data.get("matchmake", False)),  # ✅ was matchmake
                event_category_id=category.id,
                event_host_id=host.id,
            )

            # ✅ Validate gender limits before committing
            new_event.validate_attendee_totals()

            db.session.add(new_event)
            db.session.commit()

        except (TypeError, ValueError) as e:
            traceback.print_exc()
            db.session.rollback()
            return jsonify({"error": "Invalid input types", "details": str(e)}), 400
        except SQLAlchemyError as e:
            traceback.print_exc()
            db.session.rollback()
            return jsonify({"error": "Failed to add location"}), 500

        return jsonify({'message': "New event location added", "id": new_event.id}), 201

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Internal server error"}), 500


@app.route('/eventLocationInfo', methods=['GET'])
def getLocationInfo():
    user = get_current_user_from_token()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    # ✅ Left join attendance scoped to this user
    results = (
        db.session.query(EventLocation, Attendance.hasAttended)
        .outerjoin(
            Attendance,
            and_(
                Attendance.location_id == EventLocation.id,
                Attendance.user_id == user.id
            )
        )
        .all()
    )

    data = [
        {
            'id': loc.id,
            'max_attendees': loc.max_attendees,                     # ✅ was maxAttendees
            'max_male_attendees': loc.max_male_attendees,           # ✅ was maleAttendees
            'max_female_attendees': loc.max_female_attendees,       # ✅ was femaleAttendees
            'start_time': loc.start_time.isoformat(),               # ✅ was separate date + time
            'location_name': loc.location_name,                     # ✅ was location
            'latitude': loc.latitude,                               # ✅ was lat
            'longitude': loc.longitude,                             # ✅ was lng
            'total_price': float(loc.total_price) if loc.total_price else None,  # ✅ was totalPrice
            'currency': loc.currency,                               # ✅ new field
            'description': loc.description,
            'is_matchmaking_enabled': loc.is_matchmaking_enabled,   # ✅ was matchmake
            'is_checkin_closed': loc.is_checkin_closed,             # ✅ new field
            'current_round': loc.current_round,
            'event_category': loc.event_category.name if loc.event_category else None,
            'event_category_id': loc.event_category_id,
            'event_host': loc.event_host.name if loc.event_host else None,
            'event_host_id': loc.event_host_id,
            'hasAttended': bool(attended) if attended is not None else False,
        }
        for loc, attended in results
    ]
    return jsonify(data), 200


@app.route('/event-hosts', methods=['GET'])
def get_all_event_hosts():
    try:
        hosts = EventHost.query.order_by(EventHost.id.asc()).all()
        results = [{"id": host.id, "name": host.name} for host in hosts]
        return jsonify(results), 200

    except Exception as e:
        logger.error("Fatal error in GET /event-hosts", exc_info=True)
        return jsonify({"error": "internal_server_error"}), 500


@app.route('/my_tickets', methods=['GET'])
def get_user_tickets():
    user = get_current_user_from_token()
    if not user:
        return jsonify({'message': 'Unauthorized'}), 401

    user_id = user.id
    attendances = Attendance.query.filter_by(user_id=user_id).all()
    tickets = []

    for attendance in attendances:
        location = db.session.get(EventLocation, attendance.location_id)
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
            'is_matchmaking_enabled': location.is_matchmaking_enabled,
            'start_time': location.start_time.isoformat(),
            'location_name': location.location_name,
            'checked_in': checked_in,
            'male_attendees': location._count_by_gender(GenderEnum.male),
            'female_attendees': location._count_by_gender(GenderEnum.female),
            'max_attendees': location.max_attendees
        })

    return jsonify({'tickets': tickets}), 200



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

    location = EventLocation.query.get(location_id)
    profile = UserProfile.query.filter_by(user_auth_id=user_id).first()

    if not location:
        return jsonify({'message': 'Invalid location'}), 404 

    if not profile or not profile.gender:
        return jsonify({'message': 'User profile or gender not set'}), 400

    if Attendance.query.filter_by(user_id=user_id, location_id=location_id).first():
        return jsonify({'message': 'User already marked as attending'}), 400

    can_attend, reason = location.can_register(profile.gender)
    if not can_attend:
       return jsonify({'message': reason}), 400
   
    attendance = Attendance(user_id=user_id, location_id=location_id, hasAttended=True)
    db.session.add(attendance)
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

    location = EventLocation.query.get(location_id)
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
            'gender': profile.gender.value if profile and profile.gender else None,
            'attending_at': attendance.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'checked_in': checked_in,
            'hasAttended': attendance.hasAttended
        })

    male_count = location._count_by_gender(GenderEnum.male)
    female_count = location._count_by_gender(GenderEnum.female)

    return jsonify({
       'location_name': location.location_name,
       'start_time': location.start_time.isoformat(),
       'male_attendees': male_count,
       'female_attendees': female_count,
       'total_attendees': male_count + female_count,
       'max_attendees': location.max_attendees,
        'attendees': attendee_list
    }), 200


@app.route('/attendances/<int:location_id>', methods=['GET'])
def get_user_attendance_for_location(location_id):
    user = get_current_user_from_token()
    if not user:
        return jsonify({'message': 'Unauthorized'}), 401

    record = Attendance.query.filter_by(user_id=user.id, location_id=location_id).first()
    return jsonify({'hasAttended': record.hasAttended if record else False})


# ✅ Route: Perform check-in
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

    location = EventLocation.query.get(location_id)
    if not location:
        return jsonify({'message': 'Invalid location or Id'}), 404

    attendance = Attendance.query.filter_by(user_id=user_id, location_id=location_id).first()
    if not attendance:
        return jsonify({'message': 'User must attend before check-in'}), 403

    existing_checkin = CheckIn.query.filter_by(user_id=user_id, location_id=location_id).first()
    if existing_checkin:
        return jsonify({'message': 'User already checked in'}), 400

    if location.is_checkin_closed:
        return jsonify({'message': 'Check-in is closed for this event'}), 400

    checkin_count = CheckIn.query.filter_by(location_id=location_id).count()
    if checkin_count >= location.max_attendees and not location.is_checkin_closed:
        location.is_checkin_closed = True
        db.session.commit()
        trigger_matchmaking_for_location(location_id)
        return jsonify({'message': f'All {location.max_attendees} slots are filled'}), 400

    try:
        time_diff = (datetime.now(timezone.utc) - location.start_time).total_seconds()
        if time_diff > 600:
            location.is_checkin_closed = True
            db.session.commit()
            trigger_matchmaking_for_location(location_id)
            return jsonify({'message': 'Check-in period has ended (10 minutes after event time)'}), 400
    except Exception as e:
        print(f"Error parsing event time: {str(e)}")

    new_checkin = CheckIn(user_id=user_id, location_id=location_id)
    db.session.add(new_checkin)
    db.session.commit()

    updated_checkin_count = CheckIn.query.filter_by(location_id=location_id).count()
    if updated_checkin_count >= location.max_attendees:
        location.is_checkin_closed = True
        db.session.commit()
        trigger_matchmaking_for_location(location_id)

    return jsonify({
        'message': 'Check-in successful',
        'user_id': user_id,
        'location_id': location_id,
        'timestamp': new_checkin.timestamp.isoformat(),
        'checkin_status': f"{updated_checkin_count}/{location.max_attendees} checked in"
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

        return jsonify({
            'checked_in': True,
            'timestamp': checkin.timestamp.isoformat(),  # add .isoformat()
            'checkin_status': f"{checkin_count}/{location.max_attendees} checked in",
            'location': {
                'id': location.id,
                'location_name': location.location_name,
                'start_time': location.start_time.isoformat(),
                'latitude': location.latitude,
                'longitude': location.longitude,
                'max_attendees': location.max_attendees,        # ✅ add this back
                'male_attendees': location._count_by_gender(GenderEnum.male),
                'female_attendees': location._count_by_gender(GenderEnum.female),
                'max_male_attendees': location.max_male_attendees,
                'max_female_attendees': location.max_female_attendees,
                'total_price': float(location.total_price) if location.total_price else None,
                'currency': location.currency
            }
        }), 200
    else:
        return jsonify({'checked_in': False}), 200


@lru_cache(maxsize=1)
def get_s3_client():
    """Get or create S3 client (reused across requests)"""
    return boto3.client(
        's3',
        region_name=os.environ.get('DO_SPACE_REGION'),
        endpoint_url=f"https://{os.environ.get('DO_SPACE_REGION')}.digitaloceanspaces.com",
        aws_access_key_id=os.environ.get('DO_ACCESS_KEY'),
        aws_secret_access_key=os.environ.get('DO_SECRET_KEY')
    )


# CREATE A GROUP -> START
@app.route('/groups', methods=['POST'])
def create_group():

    current_user = get_current_user_from_token()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()

    name = data.get("name")
    description = data.get("description")
    gender_restriction_str = data.get("gender_restriction", "Everyone")

    if not name:
        return jsonify({"error": "Group name is required"}), 400

    # Validate and convert to GenderRestriction enum
    valid_values = {r.value: r for r in GenderRestriction}
    if gender_restriction_str not in valid_values:
        return jsonify({"error": f"gender_restriction must be one of {list(valid_values.keys())}"}), 400
    gender_restriction = valid_values[gender_restriction_str]

    if Groups.query.filter_by(name=name).first():
        return jsonify({"error": "Group name already exists"}), 409

    try:
        group = Groups(
            name=name,
            description=description,
            gender_restriction=gender_restriction,
            creator_id=current_user.id
        )

        # Creator automatically becomes member
        group.members.append(current_user)

        db.session.add(group)
        db.session.commit()

        return jsonify({
            "status": "group_created",
            "group": {
                "id": group.id,
                "name": group.name,
                "description": group.description,
                "image_url": group.image_url,
                "creator_id": group.creator_id,
                "gender_restriction": group.gender_restriction.value,  # ✅ serialize to string
                "members_count": group.members_count,
                "created_at": group.created_at.isoformat()
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": "Failed to create group"}), 500 


@app.route('/upload_group_image', methods=['POST'])
def upload_group_image():

    user = get_current_user_from_token()
    if not user:
        return jsonify({'message': 'Unauthorized'}), 401

    try:
        # --------------------------
        # Validate group_id
        # --------------------------
        group_id = request.form.get("group_id")

        if not group_id:
            return jsonify({"error": "group_id is required"}), 400

        try:
            group_id = int(group_id)
        except ValueError:
            return jsonify({"error": "Invalid group_id"}), 400

        # --------------------------
        # Verify ownership
        # --------------------------
        group = Groups.query.filter_by(
            id=group_id,
            creator_id=user.id
        ).first()

        if not group:
            return jsonify({
                "error": "Group not found or unauthorized"
            }), 404

        # --------------------------
        # Validate file
        # --------------------------
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400

        file = request.files['image']

        if not file or not allowed_file(file.filename):
            return jsonify({
                "error": "Invalid image format. Allowed: PNG, JPG, JPEG, GIF, WebP"
            }), 400

        # File size validation
        is_valid, error_msg = validate_image_size(file)
        if not is_valid:
            return jsonify({"error": error_msg}), 413

        # --------------------------
        # Process image
        # Force WebP for consistency
        # --------------------------
        try:
            processed_image, _ = resize_image_if_needed(file)

            image_format = "webp"
            content_type = "image/webp"

        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        # --------------------------
        # Deterministic path (1 image per group)
        # --------------------------
        object_key = f"group_images/group_{group_id}/main.webp"

        # --------------------------
        # Upload to DigitalOcean Spaces
        # --------------------------
        s3 = boto3.client(
            's3',
            region_name=os.environ.get('DO_SPACE_REGION'),
            endpoint_url=f"https://{os.environ.get('DO_SPACE_REGION')}.digitaloceanspaces.com",
            aws_access_key_id=os.environ.get('DO_ACCESS_KEY'),
            aws_secret_access_key=os.environ.get('DO_SECRET_KEY')
        )

        s3.put_object(
            Bucket=os.environ.get('DO_SPACE_NAME'),
            Key=object_key,
            Body=processed_image,
            ACL='public-read',
            ContentType=content_type,
            CacheControl='max-age=3600'  # 1 hour cache
        )

        image_url = f"{os.environ.get('DO_SPACE_URL')}/{object_key}"

        # --------------------------
        # Save to database
        # --------------------------
        group.image_url = image_url
        db.session.commit()

        return jsonify({
            "message": "Group image uploaded successfully",
            "group_id": group.id,
            "image_url": image_url,
            "format": image_format
        }), 201

    except Exception as e:
        db.session.rollback()
        import traceback
        print(traceback.format_exc())

        return jsonify({
            "error": "Upload failed"
        }), 500


@app.route('/groups', methods=['GET'])
def get_all_groups():
    current_user = get_current_user_from_token()
    user_id = current_user.id if current_user else None

    try:
        groups = Groups.query.order_by(Groups.created_at.desc()).all()
        results = []

        for group in groups:

            results.append({
                    "id": group.id,
                    "name": group.name,
                    "description": group.description,
                    "image_url": group.image_url,
                    "creator": {
                        "id": group.creator.id,
                        "email": group.creator.email
                    } if group.creator else None,  # ✅ handle deleted creator
                    "members_count": group.members_count,
                    "is_member": user_id in [u.id for u in group.members],
                    "gender_restriction": group.gender_restriction.value if group.gender_restriction else None,  # ✅ serialize enum
                    "created_at": group.created_at.isoformat()
            })

        return jsonify(results), 200

    except Exception as e:
        logger.error("Fatal error in GET /groups", exc_info=True)
        return jsonify({"error": "internal_server_error"}), 500



@app.route('/groups/<int:group_id>/join', methods=['POST'])
def join_group(group_id):
    current_user = get_current_user_from_token()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    group = db.session.get(Groups, group_id)
    if not group:
        return jsonify({"error": "Group not found"}), 404

    if current_user in group.members:
        return jsonify({"error": "User already a member"}), 400

    try:
        group.members.append(current_user)
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
    current_user = get_current_user_from_token()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    group = db.session.get(Groups, group_id)
    if not group:
        return jsonify({"error": "Group not found"}), 404

    if current_user not in group.members:
        return jsonify({"error": "User is not a member of this group"}), 400

    if group.creator_id == current_user.id:
        return jsonify({"error": "Group creator cannot leave their own group"}), 400

    try:
        group.members.remove(current_user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "status": "left",
        "group_id": group.id,
        "members_count": group.members_count
    }), 200


# Fetches matches and all related information about users
@app.route('/matches_at_location/<int:location_id>', methods=['GET'])
def get_user_matches_for_location(location_id):
    try:
        user = get_current_user_from_token()
        if not user:
            return jsonify({'message': 'Unauthorized'}), 401

        user_id = user.id

        # ✅ Fetch the location so we can access current_round
        location = EventLocation.query.filter_by(id=location_id).first()
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

        preferences = (MatchDecision.query
                       .filter(
                            or_(MatchDecision.user_id == user_id, MatchDecision.preferred_user_id == user_id)
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
                    image_url = user_image.imageString

                
            other_user_data = UserProfile.query.filter_by(user_auth_id=matched_user_id).first()
            other_user_preferences = UserPreferences.query.filter_by(user_id=matched_user_id).all()

            result.append({
                'preferred_user_id': matched_user_id,  # ✅ renamed from 'user_id' for frontend clarity
                'email': other_user_data.email,
                'first_name': other_user_data.first_name,
                'last_name': other_user_data.last_name,
                'date_of_birth': other_user_data.date_of_birth,
                'bio': other_user_data.bio if other_user_data else None,
                'gender': other_user_data.gender,
                'phone_number': other_user_data.phone_number,
                'looking_for': other_user_preferences.looking_for,
                'open_for': other_user_preferences.open_for,
                'hobbies': other_user_preferences.hobbies if other_user_preferences else [],
                'preferences': other_user_preferences if other_user_preferences else [],
                'image_url': image_url,
                'status': match.status,
                'location': match.location_id,
                'match_id': match.id,  # ← rename from 'match' to 'match_id'
                'current_server_time': get_unix_timestamp(datetime.now(timezone.utc)),
                'visible_after': match.visible_after,
                'round_number': match.round_number,  # ✅ from Doc 1
            })

        if len(result) == 0:
            return jsonify({'message': 'No matches left for this event'}), 400

        return jsonify({'matches': result})

    except Exception as e:
        print(f"Error in get_user_matches: {str(e)}")
        return jsonify({'matches': []})
    

@app.route('/preference', methods=['POST'])
def set_preference():
    try:
        auth_user = get_current_user_from_token()
        if not auth_user:
            return jsonify({'error': 'Unauthorized'}), 401

        data = request.get_json(silent=True)
        if not data:
            return jsonify({'error': 'Invalid or missing JSON body'}), 400

        preferred_user_auth_id = data.get('preferred_user_id')
        match_id = data.get('match_id')
        preference = data.get('preference')

        if not preferred_user_auth_id or not match_id or not preference:
            return jsonify({'error': 'Missing required fields'}), 400
        if preference not in ['like', 'reject', 'save_later']:
            return jsonify({'error': 'Invalid preference type'}), 400

        match = Match.query.get(match_id)
        if not match:
            return jsonify({'error': 'Match not found'}), 404

        existing_pref = MatchDecision.query.filter_by(
            user_id=auth_user.id,
            preferred_user_id=preferred_user_auth_id,
            match_id=match_id
        ).first()

        if existing_pref:
            if existing_pref.preference == preference:
                return jsonify({'message': f'Preference already set to "{preference}"', 'match_id': match_id}), 200
            existing_pref.preference = preference
            existing_pref.timestamp = datetime.now(timezone.utc)
        else:
            db.session.add(MatchDecision(
                user_id=auth_user.id,
                preferred_user_id=preferred_user_auth_id,
                match_id=match_id,
                preference=preference
            ))

        db.session.commit()

        update_match_consent_status(auth_user.id, preferred_user_auth_id, match_id)

        match = Match.query.get(match_id)
        if match and match.location_id:
            check_and_trigger_next_round(match.location_id)

        return jsonify({'message': f'Preference "{preference}" saved', 'match_id': match_id}), 200

    except Exception as e:
        print(f"❌ Error in set_preference: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal Server Error'}), 500


# This endpoint is for the Matches & Messages screen where users can see all their matches (pending, matched, decide) and message accepted matches. 
# It fetches all matches for the logged-in user and includes detailed info about the matched users, their preferences, and whether the message button should be shown.
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
            other_user_preferences = UserPreferences.query.filter_by(user_profile_id=other_user_data.id).first()

            user_pref = UserPreferences.query.filter_by(
                user_id=user.id, preferred_user_id=other_user_id
            ).first()

            other_pref = UserPreferences.query.filter_by(
                user_id=other_user_id, preferred_user_id=user.id
            ).first()

            if match.consent == 'active':
                display_status = 'matched'
                show_message_button = True
            elif match.consent == 'deleted':
                display_status = 'deleted'
                show_message_button = False
            else:  # consent == 'pending'
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
                    image_url = user_image.imageString

            result.append({
                # Match info
                'match_id': match.id,
                'status': display_status,
                'consent': match.consent,
                'show_message_button': show_message_button,
                'match_date': match.match_date.isoformat() if match.match_date else None,
                'location_id': match.location_id,

                # UserProfile
                'preferred_user_id': other_user_id,  # ✅ renamed from 'user_id'
                'first_name': other_user_data.first_name,
                'last_name': other_user_data.last_name,
                'email': other_user.email,
                'date_of_birth': other_user_data.date_of_birth,
                'gender': other_user_data.gender,
                'phone_number': other_user_data.phone_number,
                
                'bio': other_user_data.bio if other_user_data else None,
                'hobbies': other_user_preferences.hobbies if other_user_preferences else [],
                'preferences': other_user_preferences.preferences if other_user_preferences else [],
                'looking_for': other_user_data.looking_for,
                'open_for': other_user_data.open_for,
                # Image
                'image_url': image_url
            })

        return jsonify({'matches': result}), 200

    except Exception as e:
        print(f"Error in get_user_matches: {str(e)}")
        return jsonify({'error': 'Internal Server Error'}), 500


# This is for when users are in matchesAndMessage Screen and can Accept or Reject a user that they were earlier matched with!
@app.route('/update_match_status', methods=['POST'])
def update_match_status():
    try:
        data = request.get_json()
        match_id = data.get('match_id')
        decision = data.get('decision')  # 'accept' or 'reject'

        # ✅ Auth from token, same as set_preference
        user = get_current_user_from_token()
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401

        if not match_id or not decision:
            return jsonify({'error': 'Missing required fields'}), 400
        if decision not in ['accept', 'reject']:
            return jsonify({'error': 'Invalid decision'}), 400

        match = Match.query.get(match_id)
        if not match:
            return jsonify({'error': 'Match not found'}), 404

        if match.user1_id != user.id and match.user2_id != user.id:
            return jsonify({'error': 'User not authorized for this match'}), 403

        other_user_id = match.user2_id if match.user1_id == user.id else match.user1_id
        location_id = match.location_id

        pref = MatchDecision.query.filter_by(
            user_id=user.id,
            preferred_user_id=other_user_id,
            match_id=match_id
        ).first()

        new_preference = 'like' if decision == 'accept' else 'reject'

        if pref:
            if pref.preference in ['like', 'reject']:
                return jsonify({'error': 'Preference cannot be changed once set to like or reject'}), 403
            pref.preference = new_preference
            pref.timestamp = datetime.now(timezone.utc)
        else:
            pref = MatchDecision(
                user_id=user.id,
                preferred_user_id=other_user_id,
                match_id=match_id,
                preference=new_preference
            )
            db.session.add(pref)

        db.session.commit()

        update_match_consent_status(user.id, other_user_id, match_id)

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


@app.route('/send_message', methods=['POST'])
def send_message():
    try:
        # --- Sender comes from token, not form ---
        sender = get_current_user_from_token()
        if not sender:
            return jsonify({'error': 'Unauthorized'}), 401

        # --- Get form data ---
        receiver_id = request.form.get('receiver_id', type=int)  # use ID, not email
        message = request.form.get('message')
        reply_to_id = request.form.get('reply_to_id', type=int)
        image_file = request.files.get('image_url')

        if not receiver_id:
            return jsonify({'error': 'receiver_id is required'}), 400

        if not message and not image_file:
            return jsonify({'error': 'Message or image is required'}), 400

        # --- Verify receiver exists ---
        receiver = User.query.get(receiver_id)
        if not receiver:
            return jsonify({'error': 'Receiver not found'}), 404

        # --- Handle file upload ---
        image_url = None
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            unique_filename = f"users_chatscreen/{uuid.uuid4().hex}_{filename}"

            s3 = boto3.client(
                's3',
                region_name=os.environ.get('DO_SPACE_REGION'),
                endpoint_url=f"https://{os.environ.get('DO_SPACE_REGION')}.digitaloceanspaces.com",
                aws_access_key_id=os.environ.get('DO_ACCESS_KEY'),
                aws_secret_access_key=os.environ.get('DO_SECRET_KEY')
            )
            s3.put_object(
                Bucket=os.environ.get('DO_SPACE_NAME'),
                Key=unique_filename,
                Body=image_file,
                ACL='public-read',
                ContentType=image_file.content_type
            )
            image_url = f"{os.environ.get('DO_SPACE_URL')}/{unique_filename}"

        elif image_file:
            return jsonify({'error': 'Invalid file type'}), 400

        # --- Handle reply ---
        reply_obj = None
        if reply_to_id:
            original_msg = ChatMessage.query.get(reply_to_id)
            if original_msg:
                reply_obj = {
                    'id': original_msg.id,
                    'message': original_msg.message,
                    'sender_id': original_msg.sender_id
                }

        # --- Save message ---
        new_message = ChatMessage(
            sender_id=sender.id,
            receiver_id=receiver.id,
            message=message,
            image_url=image_url,
            reply_to_id=reply_to_id
        )
        db.session.add(new_message)
        db.session.commit()

        # --- Emit to room keyed by user_id (not email) ---
        socketio.emit('receive_message', {
            'id': new_message.id,
            'sender_id': sender.id,
            'receiver_id': receiver.id,
            'message': message,
            'image_url': image_url,
            'reply_to_id': reply_to_id,
            'reply_to': reply_obj,
            'timestamp': new_message.timestamp.isoformat()
        }, room=str(receiver.id))  # room is now user_id as string

        return jsonify({
            'status': 'Message sent',
            'id': new_message.id,
            'image_url': image_url,
            'reply_to_id': reply_to_id,
            'reply_to': reply_obj
        }), 200

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@socketio.on('connect')
def handle_connect(auth):
    """Validate token on connection and join user's own room."""
    token = auth.get('token') if auth else None

    if not token:
        disconnect()
        return

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        user_id = payload.get('user_id')
        user = User.query.get(user_id)

        if not user:
            disconnect()
            return

        # Join a room named by user_id so others can emit to them
        join_room(str(user_id))

    except jwt.ExpiredSignatureError:
        disconnect()
    except jwt.InvalidTokenError:
        disconnect()


@socketio.on('send_message')
def handle_message(data):
    # --- Resolve sender from token (set during connect) ---
    token = data.get('token')  # or pass once at connect and store in session
    if not token:
        emit('error', {'error': 'Unauthorized'})
        return

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        sender = User.query.get(payload.get('user_id'))
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        emit('error', {'error': 'Invalid or expired token'})
        return

    if not sender:
        emit('error', {'error': 'Sender not found'})
        return

    # --- Receiver by ID, not email ---
    receiver_id = data.get('receiver_id')
    receiver = User.query.get(receiver_id)
    if not receiver:
        emit('error', {'error': 'Receiver not found'})
        return

    message = data.get('message')
    image_url = data.get('image_url')
    reply_to_id = data.get('reply_to_id')

    if not message and not image_url:
        emit('error', {'error': 'Message or image is required'})
        return

    # --- Handle reply ---
    reply_obj = None
    if reply_to_id:
        original_msg = ChatMessage.query.get(reply_to_id)
        if original_msg:
            reply_obj = {
                'id': original_msg.id,
                'message': original_msg.message,
                'sender_id': original_msg.sender_id  # ID instead of email
            }

    # --- Save to DB ---
    new_message = ChatMessage(
        sender_id=sender.id,
        receiver_id=receiver.id,
        message=message,
        image_url=image_url,
        reply_to_id=reply_to_id
    )
    db.session.add(new_message)
    db.session.commit()

    payload_out = {
        'id': new_message.id,
        'sender_id': sender.id,
        'receiver_id': receiver.id,
        'message': message,
        'image_url': image_url,
        'reply_to_id': reply_to_id,
        'reply_to': reply_obj,
        'timestamp': new_message.timestamp.isoformat()
    }

    # --- Emit to receiver's room (keyed by user_id) ---
    emit('receive_message', payload_out, room=str(receiver.id))

    # --- Also emit back to sender so their UI updates ---
    emit('receive_message', payload_out, room=str(sender.id))


@socketio.on('join')
def on_join(data):
    token = data.get('token')
    if not token:
        emit('error', {'error': 'Unauthorized'})
        return

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        user = User.query.get(payload.get('user_id'))
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        emit('error', {'error': 'Invalid or expired token'})
        return

    if not user:
        emit('error', {'error': 'User not found'})
        return

    room = str(user.id)
    join_room(room)
    logger.info(f'User {user.id} has entered the room.')
    emit('status', {'msg': f'User {user.id} has entered the room.'}, room=room)


@app.route('/get_chats', methods=['GET'])
def get_chats():
    current_user = get_current_user_from_token()
    if not current_user:
        return jsonify({'error': 'Unauthorized'}), 401

    other_user_id = request.args.get('other_user_id', type=int)
    if not other_user_id:
        return jsonify({'error': 'Missing other_user_id'}), 400

    other_user = User.query.get(other_user_id)
    if not other_user:
        return jsonify({'error': 'User not found'}), 404

    messages = ChatMessage.query.filter(
        db.or_(
            db.and_(ChatMessage.sender_id == current_user.id, ChatMessage.receiver_id == other_user_id),
            db.and_(ChatMessage.sender_id == other_user_id, ChatMessage.receiver_id == current_user.id)
        )
    ).order_by(ChatMessage.timestamp).all()

    chat_history = []
    for msg in messages:
        reply_obj = None
        if msg.reply_to:
            # Resolve sender name for the replied-to message
            reply_sender_profile = msg.reply_to.sender.profile if msg.reply_to.sender else None
            reply_sender_name = (
                f"{reply_sender_profile.firstname} {reply_sender_profile.lastname}".strip()
                if reply_sender_profile else None
            )

            reply_obj = {
                'id': msg.reply_to.id,
                'message': msg.reply_to.message,
                'image_url': msg.reply_to.image_url,
                'sender_id': msg.reply_to.sender_id,
                'sender_name': reply_sender_name,  # ← added
            }

        # Resolve sender name for the current message
        sender_profile = msg.sender.profile if msg.sender else None
        sender_name = sender_profile.firstname if sender_profile else None

        chat_history.append({
            'id': msg.id,
            'sender_id': msg.sender_id,
            'sender_name': sender_name,            # ← added
            'receiver_id': msg.receiver_id,
            'is_mine': msg.sender_id == current_user.id,
            'message': msg.message,
            'image_url': msg.image_url,
            'reply_to_id': msg.reply_to_id,
            'reply_to': reply_obj,
            'timestamp': msg.timestamp.isoformat()
        })

    return jsonify(chat_history)


# CHAT FUNCTIONALITY -> End

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
"""
Empower & Elevate Leaders (EEL) — Database Models
Flask-SQLAlchemy models for PostgreSQL.

Design principles:
- Content (pillars, modules, lessons, quizzes) lives in the DB, not in code,
  so admins can add/edit curriculum without touching the frontend.
- Progress is tracked at three granularities: lesson, module, and pillar
  (via certificates), so the dashboard can show fine-grained % complete.
- Quiz answers are stored per-attempt so learners can retake quizzes and
  admins can see quiz performance analytics.
"""

from datetime import datetime
import enum
import uuid

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


def gen_uuid():
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class UserRole(enum.Enum):
    LEARNER = "learner"
    ADMIN = "admin"


class LessonContentType(enum.Enum):
    READING = "reading"
    VIDEO = "video"
    SCENARIO = "scenario"
    DISCUSSION = "discussion"


class ProgressStatus(enum.Enum):
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class QuestionType(enum.Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    REFLECTION = "reflection"  # free-text, ungraded


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.LEARNER)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    enrollments = db.relationship("Enrollment", back_populates="user", cascade="all, delete-orphan")
    module_progress = db.relationship("ModuleProgress", back_populates="user", cascade="all, delete-orphan")
    lesson_progress = db.relationship("LessonProgress", back_populates="user", cascade="all, delete-orphan")
    quiz_attempts = db.relationship("QuizAttempt", back_populates="user", cascade="all, delete-orphan")
    certificates = db.relationship("Certificate", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN


# ---------------------------------------------------------------------------
# Curriculum structure: Pillar -> Module -> Lesson
#                                       -> Quiz -> Question -> Choice
# ---------------------------------------------------------------------------

class Pillar(db.Model):
    """A learning track: LEAD, ETHICS, GLOBAL, etc."""
    __tablename__ = "pillars"

    id = db.Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    slug = db.Column(db.String(50), unique=True, nullable=False)  # 'lead', 'ethics', 'global'
    name = db.Column(db.String(120), nullable=False)              # 'Leadership'
    description = db.Column(db.Text)
    order = db.Column(db.Integer, nullable=False, default=0)
    is_published = db.Column(db.Boolean, default=False)

    modules = db.relationship(
        "Module", back_populates="pillar",
        order_by="Module.order", cascade="all, delete-orphan"
    )
    enrollments = db.relationship("Enrollment", back_populates="pillar")
    certificates = db.relationship("Certificate", back_populates="pillar")


class Module(db.Model):
    __tablename__ = "modules"

    id = db.Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    pillar_id = db.Column(UUID(as_uuid=False), db.ForeignKey("pillars.id"), nullable=False)
    slug = db.Column(db.String(80), nullable=False)
    title = db.Column(db.String(200), nullable=False)   # 'Understanding Leadership'
    description = db.Column(db.Text)
    order = db.Column(db.Integer, nullable=False, default=0)
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pillar = db.relationship("Pillar", back_populates="modules")
    lessons = db.relationship(
        "Lesson", back_populates="module",
        order_by="Lesson.order", cascade="all, delete-orphan"
    )
    quizzes = db.relationship("Quiz", back_populates="module", cascade="all, delete-orphan")
    progress_records = db.relationship("ModuleProgress", back_populates="module")

    __table_args__ = (
        db.UniqueConstraint("pillar_id", "slug", name="uq_module_pillar_slug"),
    )


class Lesson(db.Model):
    __tablename__ = "lessons"

    id = db.Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    module_id = db.Column(UUID(as_uuid=False), db.ForeignKey("modules.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content_type = db.Column(db.Enum(LessonContentType), nullable=False, default=LessonContentType.READING)
    content = db.Column(db.Text)          # markdown/html body, or a scenario prompt
    video_url = db.Column(db.String(500))  # nullable, used when content_type == VIDEO
    order = db.Column(db.Integer, nullable=False, default=0)

    module = db.relationship("Module", back_populates="lessons")
    progress_records = db.relationship("LessonProgress", back_populates="lesson")


class Quiz(db.Model):
    __tablename__ = "quizzes"

    id = db.Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    module_id = db.Column(UUID(as_uuid=False), db.ForeignKey("modules.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    passing_score = db.Column(db.Integer, default=70)  # percentage required to mark module complete

    module = db.relationship("Module", back_populates="quizzes")
    questions = db.relationship(
        "Question", back_populates="quiz",
        order_by="Question.order", cascade="all, delete-orphan"
    )
    attempts = db.relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan")


class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    quiz_id = db.Column(UUID(as_uuid=False), db.ForeignKey("quizzes.id"), nullable=False)
    prompt = db.Column(db.Text, nullable=False)  # e.g. "You are leading a student organization..."
    question_type = db.Column(db.Enum(QuestionType), nullable=False, default=QuestionType.MULTIPLE_CHOICE)
    order = db.Column(db.Integer, nullable=False, default=0)

    quiz = db.relationship("Quiz", back_populates="questions")
    choices = db.relationship(
        "Choice", back_populates="question",
        order_by="Choice.order", cascade="all, delete-orphan"
    )


class Choice(db.Model):
    __tablename__ = "choices"

    id = db.Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    question_id = db.Column(UUID(as_uuid=False), db.ForeignKey("questions.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)          # 'Investigate fairly and apply the same standard...'
    is_correct = db.Column(db.Boolean, default=False)
    explanation = db.Column(db.Text)                   # shown after answering, why it's right/wrong
    order = db.Column(db.Integer, nullable=False, default=0)

    question = db.relationship("Question", back_populates="choices")


# ---------------------------------------------------------------------------
# Enrollment & Progress tracking
# ---------------------------------------------------------------------------

class Enrollment(db.Model):
    """A learner opting into a pillar (learning track)."""
    __tablename__ = "enrollments"

    id = db.Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = db.Column(UUID(as_uuid=False), db.ForeignKey("users.id"), nullable=False)
    pillar_id = db.Column(UUID(as_uuid=False), db.ForeignKey("pillars.id"), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="enrollments")
    pillar = db.relationship("Pillar", back_populates="enrollments")

    __table_args__ = (
        db.UniqueConstraint("user_id", "pillar_id", name="uq_enrollment_user_pillar"),
    )


class ModuleProgress(db.Model):
    __tablename__ = "module_progress"

    id = db.Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = db.Column(UUID(as_uuid=False), db.ForeignKey("users.id"), nullable=False)
    module_id = db.Column(UUID(as_uuid=False), db.ForeignKey("modules.id"), nullable=False)
    status = db.Column(db.Enum(ProgressStatus), nullable=False, default=ProgressStatus.LOCKED)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    user = db.relationship("User", back_populates="module_progress")
    module = db.relationship("Module", back_populates="progress_records")

    __table_args__ = (
        db.UniqueConstraint("user_id", "module_id", name="uq_progress_user_module"),
    )


class LessonProgress(db.Model):
    __tablename__ = "lesson_progress"

    id = db.Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = db.Column(UUID(as_uuid=False), db.ForeignKey("users.id"), nullable=False)
    lesson_id = db.Column(UUID(as_uuid=False), db.ForeignKey("lessons.id"), nullable=False)
    completed_at = db.Column(db.DateTime)

    user = db.relationship("User", back_populates="lesson_progress")
    lesson = db.relationship("Lesson", back_populates="progress_records")

    __table_args__ = (
        db.UniqueConstraint("user_id", "lesson_id", name="uq_progress_user_lesson"),
    )


class QuizAttempt(db.Model):
    __tablename__ = "quiz_attempts"

    id = db.Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = db.Column(UUID(as_uuid=False), db.ForeignKey("users.id"), nullable=False)
    quiz_id = db.Column(UUID(as_uuid=False), db.ForeignKey("quizzes.id"), nullable=False)
    score = db.Column(db.Integer)  # percentage, 0-100
    passed = db.Column(db.Boolean, default=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    user = db.relationship("User", back_populates="quiz_attempts")
    quiz = db.relationship("Quiz", back_populates="attempts")
    answers = db.relationship("QuizAnswer", back_populates="attempt", cascade="all, delete-orphan")


class QuizAnswer(db.Model):
    __tablename__ = "quiz_answers"

    id = db.Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    attempt_id = db.Column(UUID(as_uuid=False), db.ForeignKey("quiz_attempts.id"), nullable=False)
    question_id = db.Column(UUID(as_uuid=False), db.ForeignKey("questions.id"), nullable=False)
    choice_id = db.Column(UUID(as_uuid=False), db.ForeignKey("choices.id"))  # null for reflection questions
    is_correct = db.Column(db.Boolean)

    attempt = db.relationship("QuizAttempt", back_populates="answers")
    question = db.relationship("Question")
    choice = db.relationship("Choice")


# ---------------------------------------------------------------------------
# Certificates
# ---------------------------------------------------------------------------

class Certificate(db.Model):
    """Issued when a learner completes every module in a pillar."""
    __tablename__ = "certificates"

    id = db.Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = db.Column(UUID(as_uuid=False), db.ForeignKey("users.id"), nullable=False)
    pillar_id = db.Column(UUID(as_uuid=False), db.ForeignKey("pillars.id"), nullable=False)
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    certificate_url = db.Column(db.String(500))  # link to generated PDF, if you generate one

    user = db.relationship("User", back_populates="certificates")
    pillar = db.relationship("Pillar", back_populates="certificates")

    __table_args__ = (
        db.UniqueConstraint("user_id", "pillar_id", name="uq_certificate_user_pillar"),
    )

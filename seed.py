"""
Seed script for EEL — populates the three pillars, a couple of modules/lessons,
and the "Difficult Decision" scenario quiz from the original plan.

Run with:  python seed.py
Assumes app.py exposes `create_app()` and models.py exposes `db`.
"""

from app import create_app
from models import (
    db, Pillar, Module, Lesson, Quiz, Question, Choice,
    LessonContentType, QuestionType,
)

app = create_app()

with app.app_context():
    # --- Pillars -----------------------------------------------------------
    lead = Pillar(slug="lead", name="Leadership", order=1, is_published=True)
    ethics = Pillar(slug="ethics", name="Ethical Leadership", order=2, is_published=True)
    global_ = Pillar(slug="global", name="Global Citizenship", order=3, is_published=True)
    db.session.add_all([lead, ethics, global_])
    db.session.flush()  # assigns IDs without committing yet

    # --- Leadership Foundations module --------------------------------------
    foundations = Module(
        pillar_id=lead.id,
        slug="leadership-foundations",
        title="Leadership Foundations",
        order=1,
        is_published=True,
    )
    db.session.add(foundations)
    db.session.flush()

    lessons = [
        Lesson(module_id=foundations.id, title="Understanding Leadership",
               content_type=LessonContentType.READING, order=1,
               content="What leadership means and why it matters..."),
        Lesson(module_id=foundations.id, title="Self-Awareness",
               content_type=LessonContentType.READING, order=2,
               content="Reflecting on your own strengths, blind spots, and values..."),
        Lesson(module_id=foundations.id, title="Communication",
               content_type=LessonContentType.VIDEO, order=3,
               video_url="https://example.com/videos/communication"),
        Lesson(module_id=foundations.id, title="Decision Making",
               content_type=LessonContentType.SCENARIO, order=4,
               content="Apply what you've learned to a real leadership dilemma."),
    ]
    db.session.add_all(lessons)
    db.session.flush()

    # --- Quiz: "The Difficult Decision" scenario -----------------------------
    quiz = Quiz(module_id=foundations.id, title="Leadership Foundations Assessment", passing_score=70)
    db.session.add(quiz)
    db.session.flush()

    question = Question(
        quiz_id=quiz.id,
        question_type=QuestionType.MULTIPLE_CHOICE,
        order=1,
        prompt=(
            "You are leading a student organization. A close friend has violated "
            "one of the organization's rules. What would you do?"
        ),
    )
    db.session.add(question)
    db.session.flush()

    choices = [
        Choice(question_id=question.id, order=1,
               text="Ignore it because they are your friend",
               is_correct=False,
               explanation="Ignoring the violation undermines fairness and erodes trust in your leadership."),
        Choice(question_id=question.id, order=2,
               text="Punish them immediately",
               is_correct=False,
               explanation="Acting without investigating risks an unfair or disproportionate response."),
        Choice(question_id=question.id, order=3,
               text="Investigate fairly and apply the same standard used for everyone",
               is_correct=True,
               explanation=(
                   "This reflects ethical leadership: consistent standards, due process, "
                   "and accountability regardless of personal relationships."
               )),
        Choice(question_id=question.id, order=4,
               text="Ask another leader to handle it",
               is_correct=False,
               explanation="Deflecting the decision avoids the responsibility that comes with your role."),
    ]
    db.session.add_all(choices)

    db.session.commit()
    print("Seed complete: 3 pillars, 1 module, 4 lessons, 1 quiz with 4 choices.")

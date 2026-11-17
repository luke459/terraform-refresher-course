from runner.api.content import Content
from runner.api.exams import ExamService
from runner.api.models import Answer, CreateExam
import pytest


def test_deadline_survives_reload_and_answers_lock(db, settings):
    now = [1000.0]
    exams = ExamService(db, Content(settings.root), now=lambda: now[0])
    exam = exams.create(CreateExam(mode="mock"))
    assert exam["deadline"] == 4600
    assert all("correct" not in q and "rationale" not in q for q in exam["questions"])
    restored = ExamService(db, Content(settings.root), now=lambda: now[0])
    assert restored.get(exam["id"])["deadline"] == 4600
    now[0] = 4601
    finished = restored.get(exam["id"])
    assert finished["submitted"] and finished["score"] == 0
    with pytest.raises(ValueError, match="ended"):
        restored.answer(exam["id"], Answer(question_id=exam["questions"][0]["id"], selected=["a"]))


def test_multiple_answer_requires_exact_set(db, settings):
    exams = ExamService(db, Content(settings.root))
    exam = exams.create(CreateExam(mode="practice", domain_id="01"))
    multi = next(q for q in exam["questions"] if q["type"] == "multiple")
    correct=Content(settings.root).questions()[multi['id']].correct
    result = exams.answer(exam["id"], Answer(question_id=multi["id"], selected=correct[:1]))
    assert result["correct"] is False
    result = exams.answer(exam["id"], Answer(question_id=multi["id"], selected=list(reversed(correct))))
    assert result["correct"] is True
    assert result["rationale"]


def test_mock_answers_remain_hidden_in_snapshot_and_content_updates(db,settings,monkeypatch):
    content=Content(settings.root)
    exams=ExamService(db,content)
    exam=exams.create(CreateExam(mode='mock'))
    assert 'snapshot' not in exam
    first=exam['questions'][0]['id']
    original=content.questions()[first].correct
    monkeypatch.setattr(content,'questions',lambda:{})
    restored=exams.get(exam['id'])
    assert restored['questions'][0]['id']==first
    assert 'correct' not in restored['questions'][0]
    exams.answer(exam['id'],Answer(question_id=first,selected=original))
    submitted=exams.submit(exam['id'])
    assert submitted['score']>0


def test_configured_short_mock_keeps_domains_and_persisted_length(db,settings):
    content=Content(settings.root)
    exams=ExamService(db,content)
    full=exams.create(CreateExam(mode='mock',mock_set='B'))
    short=exams.create(CreateExam(mode='mock',mock_set='B',question_count=20))
    assert len(short['questions'])==20
    assert {q['domain_id'] for q in short['questions']}=={f'{n:02}' for n in range(1,9)}
    assert set(short['question_ids'])<=set(full['question_ids'])
    restored=ExamService(db,content).get(short['id'])
    assert restored['question_ids']==short['question_ids'] and restored['deadline']==short['deadline']


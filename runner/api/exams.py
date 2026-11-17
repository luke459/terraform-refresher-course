import json
import random
import time
import uuid
from .models import Question


class ExamService:
    def __init__(self, db, content, now=time.time):
        self.db, self.content, self.now = db, content, now

    def create(self, request):
        bank = self.content.questions()
        if request.mode == "mock":
            blueprint = json.loads((self.content.root / "exam-bank" / "mock-blueprint.json").read_text())
            ids = blueprint["sets"][request.mock_set]
            if request.question_count and request.question_count<len(ids):
                # Short practice mocks draw only from the chosen disjoint set.
                # Keep every domain represented when the requested length allows it.
                rng=random.SystemRandom()
                by_domain={domain:[qid for qid in ids if bank[qid].domain_id==domain] for domain in sorted({bank[qid].domain_id for qid in ids})}
                selected=[rng.choice(group) for group in by_domain.values()] if request.question_count>=len(by_domain) else []
                selected += rng.sample([qid for qid in ids if qid not in selected],request.question_count-len(selected))
                rng.shuffle(selected)
                ids=selected
            duration = 3600
        else:
            ids = [q.id for q in bank.values() if not request.domain_id or q.domain_id == request.domain_id]
            random.SystemRandom().shuffle(ids)
            if not request.domain_id:
                ids = ids[:20]
            duration = None
        if not ids:
            raise ValueError("No questions available")
        exam_id = uuid.uuid4().hex
        now = self.now()
        snapshot = {qid:bank[qid].model_dump() for qid in ids}
        self.db.execute("INSERT INTO exams(id,mode,created,deadline,question_ids,snapshot) VALUES (?,?,?,?,?,?)",
            (exam_id, request.mode, now, now + duration if duration else None, json.dumps(ids),json.dumps(snapshot)))
        return self.get(exam_id)

    def row(self, exam_id):
        row = self.db.one("SELECT * FROM exams WHERE id=?", (exam_id,))
        if not row:
            raise ValueError("Exam session not found")
        return row

    def get(self, exam_id):
        row = self.row(exam_id)
        if row["deadline"] and self.now() >= row["deadline"] and not row["submitted"]:
            return self.submit(exam_id)
        bank = self.bank(row)
        questions = []
        for qid in json.loads(row["question_ids"]):
            item = bank[qid].model_dump()
            if not row["submitted"]:
                item.pop("correct")
                item.pop("rationale")
            questions.append(item)
        public = {key:value for key,value in row.items() if key != 'snapshot'}
        return {**public, "question_ids": json.loads(row["question_ids"]), "answers": json.loads(row["answers"]),
                "questions": questions, "server_time": self.now()}

    def bank(self,row):
        snapshot=json.loads(row.get('snapshot') or '{}')
        return {qid:Question.model_validate(question) for qid,question in snapshot.items()} if snapshot else self.content.questions()

    def answer(self, exam_id, answer):
        row = self.row(exam_id)
        if row["submitted"] or (row["deadline"] and self.now() >= row["deadline"]):
            if not row["submitted"]:
                self.submit(exam_id)
            raise ValueError("This exam has ended; answers are locked")
        if answer.question_id not in json.loads(row["question_ids"]):
            raise ValueError("Question is not part of this exam")
        question = self.bank(row)[answer.question_id]
        if not set(answer.selected) <= set(question.choices) or len(set(answer.selected)) != len(answer.selected):
            raise ValueError("Unknown or duplicate answer choice")
        if question.type != "multiple" and len(answer.selected) > 1:
            raise ValueError("Choose a single answer")
        with self.db.connection() as conn:
            conn.execute('BEGIN IMMEDIATE')
            latest=dict(conn.execute('SELECT * FROM exams WHERE id=?',(exam_id,)).fetchone())
            if latest['submitted'] or (latest['deadline'] and self.now()>=latest['deadline']):
                raise ValueError('This exam has ended; answers are locked')
            answers=json.loads(latest['answers'])
            answers[answer.question_id]={'selected':answer.selected,'flagged':answer.flagged}
            conn.execute('UPDATE exams SET answers=? WHERE id=?',(json.dumps(answers),exam_id))
        result = {"saved": True}
        if row["mode"] == "practice":
            result.update({"correct": set(answer.selected) == set(question.correct), "rationale": question.rationale,
                           "answer": question.correct})
        return result

    def submit(self, exam_id):
        self.row(exam_id)
        with self.db.connection() as conn:
            conn.execute('BEGIN IMMEDIATE')
            row=dict(conn.execute('SELECT * FROM exams WHERE id=?',(exam_id,)).fetchone())
            if not row['submitted']:
                bank=self.bank(row)
                ids=json.loads(row['question_ids']);answers=json.loads(row['answers'])
                score=100*sum(set(answers.get(qid,{}).get('selected',[]))==set(bank[qid].correct) for qid in ids)/len(ids)
                conn.execute('UPDATE exams SET submitted=?,score=? WHERE id=?',(self.now(),round(score,1),exam_id))
        return self.get(exam_id)

    def checkpoint(self, domain_id, answer):
        question = self.content.checkpoints(domain_id).get(answer.question_id)
        if not question or not set(answer.selected) <= set(question.choices):
            raise ValueError("Unknown checkpoint or answer choice")
        correct = set(answer.selected) == set(question.correct)
        self.db.execute("INSERT OR REPLACE INTO checkpoints VALUES (?,?,?,?,?)",
            (domain_id, answer.question_id, json.dumps(answer.selected), int(correct), self.now()))
        return {"correct": correct, "answer": question.correct, "rationale": question.rationale}

    def mastery(self, domain_id):
        attempts, distinct = [], set()
        for row in self.db.all("SELECT * FROM exams WHERE submitted IS NOT NULL AND mode='practice' ORDER BY submitted DESC"):
            bank=self.bank(row)
            ids = [qid for qid in json.loads(row["question_ids"]) if bank[qid].domain_id == domain_id]
            if not ids:
                continue
            answers = json.loads(row["answers"])
            distinct.update(qid for qid in ids if answers.get(qid, {}).get("selected"))
            score = 100 * sum(set(answers.get(qid, {}).get("selected", [])) == set(bank[qid].correct) for qid in ids) / len(ids)
            attempts.append(round(score, 1))
            if len(attempts) == 2:
                break
        enough = len(attempts) == 2 and len(distinct) >= 5
        return {"mastered": enough and min(attempts) >= 80, "sufficient_evidence": enough,
                "recent_scores": attempts, "distinct_questions": len(distinct)}


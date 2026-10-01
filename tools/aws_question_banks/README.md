# AWS chapter question-bank contract

Each `part_XX.json` is written by an author agent and reviewed by a different
agent. The files contain original practice questions, not recalled live exam
items, exam dumps, or copied commercial question-bank content.

## JSON shape

```json
{
  "part": 0,
  "author_agent": "P00-A",
  "chapters": [
    {
      "chapter": 1,
      "questions": [
        {
          "id": "ch001-q01",
          "intent": 1,
          "level": "SAA",
          "kind": "single",
          "tested": "short knowledge-point label",
          "prompt": "self-contained scenario and explicit decision request",
          "choices": ["A content", "B content", "C content", "D content"],
          "answers": [0],
          "explanations": [
            "Why A is correct or wrong.",
            "Why B is correct or wrong.",
            "Why C is correct or wrong.",
            "Why D is correct or wrong."
          ],
          "task_keys": ["SAA-2.1"],
          "source_ids": ["aws-saa-guide", "aws-service-doc"],
          "inspiration_ids": ["community-study-guide"]
        }
      ]
    }
  ],
  "sources": [
    {
      "id": "aws-service-doc",
      "title": "Exact source title",
      "url": "https://docs.aws.amazon.com/...",
      "kind": "official",
      "usage": "Facts and service behavior."
    },
    {
      "id": "community-study-guide",
      "title": "Exact public article or author-created practice resource",
      "url": "https://example.com/...",
      "kind": "community",
      "usage": "Topic frequency or distractor pattern only; no wording copied."
    }
  ]
}
```

## Author acceptance criteria

- Exactly 10 questions for every chapter in the part.
- Question IDs use `chNNN-qNN`; every chapter contains intents `1` through `10`
  exactly once, matching `tools/aws_exam_audits/part_XX.md`.
- Replace the old five-question template; do not reuse its prompt or choices.
- At least 7 single-answer and at least 2 two-answer questions per chapter.
- Single-answer questions have 4 choices and one answer index.
- Two-answer questions have 5 choices, two answer indexes, and `kind: "multi"`.
- Correct-answer positions vary; no chapter may place more than 4 answers in
  the same letter position.
- Every prompt is a self-contained scenario with enough constraints for one
  defensible answer set.
- Every choice receives a substantive explanation. Explain the violated
  constraint or the condition under which a distractor would become correct.
- Every factual statement is supported by at least one official AWS source.
- Public community sources may calibrate topic selection and plausible traps.
  Do not copy or lightly paraphrase their question text or answer structure.
- Do not use ExamTopics, recalled live exam items, braindumps, leaked questions,
  or sources advertising "actual exam questions".
- Keep SAA-C03 and SAP-C02 mappings explicit. Mark newer SAP-C03-only or
  emerging material as enrichment rather than scored SAP-C02 coverage.

## Review contract

A reviewer who did not author the part writes
`tools/aws_question_reviews/part_XX.md` and checks:

- unique defensible answer set;
- current AWS behavior and exam-version scope;
- realistic distractors;
- no old-book or cross-question duplication;
- source provenance and no dump-like source;
- required question count and intent coverage;
- wording clarity for a reader with no AWS background.

Reviewers do not silently edit the bank. They report question IDs and required
changes so a separate revision agent can make bounded corrections.

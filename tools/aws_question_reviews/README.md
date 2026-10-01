# Independent question-bank review contract

Each `part_XX.md` is written by a reviewer who did not author
`tools/aws_question_banks/part_XX.json`.

The reviewer must inspect all questions and report:

- question IDs with ambiguous or multiple defensible answer sets;
- outdated or unsupported AWS behavior;
- exam-version/scope mistakes;
- implausible distractors or repeated wording;
- incomplete explanations;
- incorrect official/community source labels;
- accidental similarity to the old five-question template or another bank.

Reviewers do not silently rewrite an author's JSON. They finish with one of:

- `PASS`: no required changes;
- `REVISE`: a numbered list of question IDs and exact required corrections.

After revisions, a different verification pass records `VERIFIED` in the same
report. Publication requires all 12 reports to end in `PASS` or `VERIFIED`.

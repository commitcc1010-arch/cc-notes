"""Compact topic factory with deterministic exam/source mappings."""
from __future__ import annotations

from aws_architect_model import T, Topic


_TASK_ROWS = """
1 SAA-2.1,SAA-2.2,SAP-2.4
2 SAA-2.2,SAA-3.4,SAP-1.1,SAP-1.3,SAP-2.4
3 SAA-3.2,SAA-4.2,SAP-2.5,SAP-2.6,SAP-4.4
4 SAA-3.4,SAA-4.4,SAP-1.1,SAP-2.5
5 SAA-1.2,SAA-3.4,SAP-1.1,SAP-2.3,SAP-2.5
6 SAA-3.1,SAA-4.1,SAP-2.5,SAP-2.6
7 SAA-3.3,SAA-4.3,SAP-2.5,SAP-2.6,SAP-4.3
8 SAA-2.2,SAP-1.3,SAP-2.4,SAP-3.4
9 SAA-2.2,SAP-2.2,SAP-2.4
10 SAA-1.1,SAA-1.2,SAA-1.3,SAP-1.2,SAP-2.3
11 SAA-3.4,SAA-4.4,SAP-1.1
12 SAA-2.2,SAA-3.4,SAP-1.1,SAP-1.3
13 SAA-1.2,SAA-3.4,SAA-4.4,SAP-1.1,SAP-2.3,SAP-2.6
14 SAA-1.2,SAP-1.2,SAP-2.3,SAP-3.2
15 SAA-2.1,SAA-3.4,SAA-4.4,SAP-1.1,SAP-2.5,SAP-2.6
16 SAA-2.2,SAA-3.4,SAP-1.1,SAP-1.3,SAP-2.4
17 SAA-1.2,SAA-3.4,SAA-4.4,SAP-1.1,SAP-2.5,SAP-2.6
18 SAA-2.1,SAA-2.2,SAA-3.4,SAP-1.1,SAP-2.4,SAP-2.5
19 SAA-3.4,SAA-4.4,SAP-1.1,SAP-2.2,SAP-2.5
20 SAA-1.2,SAA-3.4,SAP-1.1,SAP-1.2,SAP-1.4,SAP-2.3
21 SAA-1.1,SAP-1.2,SAP-2.3,SAP-3.2
22 SAA-1.1,SAP-1.2,SAP-2.3,SAP-3.2
23 SAA-1.1,SAP-1.2,SAP-1.4,SAP-2.3
24 SAA-1.1,SAP-1.2,SAP-1.4
25 SAA-1.1,SAP-1.2,SAP-1.4,SAP-3.2
26 SAA-1.1,SAP-1.2,SAP-1.4,SAP-2.3
27 SAA-1.3,SAP-1.2,SAP-2.3,SAP-3.2
28 SAA-1.2,SAA-1.3,SAP-1.2,SAP-2.3,SAP-3.2
29 SAA-1.2,SAP-1.2,SAP-2.3,SAP-3.2
30 SAA-1.2,SAP-1.2,SAP-3.2
31 SAA-1.3,SAA-4.1,SAP-1.2,SAP-2.2,SAP-2.3,SAP-3.2,SAP-4.1
32 SAA-3.2,SAA-4.2,SAP-2.5,SAP-2.6
33 SAA-2.2,SAA-3.1,SAA-4.1,SAP-2.4,SAP-2.5,SAP-2.6
34 SAA-2.1,SAA-2.2,SAA-3.2,SAA-4.2,SAP-2.4,SAP-2.5,SAP-2.6,SAP-3.3
35 SAA-2.1,SAA-2.2,SAA-3.2,SAP-2.4,SAP-2.5,SAP-3.4
36 SAA-2.1,SAA-3.2,SAA-4.2,SAP-2.5,SAP-2.6,SAP-3.3,SAP-4.4
37 SAA-1.2,SAA-2.1,SAA-3.2,SAA-4.2,SAP-2.3,SAP-2.5,SAP-2.6
38 SAA-2.1,SAA-2.2,SAA-3.2,SAA-4.2,SAP-2.1,SAP-2.4,SAP-2.5,SAP-2.6,SAP-4.3,SAP-4.4
39 SAA-2.1,SAA-3.2,SAA-4.2,SAP-2.5,SAP-2.6,SAP-3.3
40 SAA-2.1,SAA-3.2,SAA-4.2,SAP-2.1,SAP-2.5,SAP-2.6,SAP-4.4
41 SAA-1.3,SAA-3.1,SAA-4.1,SAP-2.3,SAP-2.5,SAP-2.6
42 SAA-3.1,SAA-4.1,SAP-2.5,SAP-2.6,SAP-3.5
43 SAA-3.1,SAA-4.1,SAP-2.5,SAP-2.6
44 SAA-3.1,SAA-3.5,SAA-4.1,SAA-4.4,SAP-2.5,SAP-2.6,SAP-4.2
45 SAA-2.2,SAA-3.3,SAA-4.3,SAP-2.4,SAP-2.5,SAP-2.6,SAP-3.3
46 SAA-2.2,SAA-3.3,SAA-4.3,SAP-1.3,SAP-2.2,SAP-2.4,SAP-2.5,SAP-2.6,SAP-3.3
47 SAA-2.1,SAA-3.3,SAA-4.3,SAP-2.4,SAP-2.5,SAP-2.6,SAP-3.3
48 SAA-2.1,SAA-3.3,SAA-4.3,SAP-2.5,SAP-2.6,SAP-3.3
49 SAA-1.3,SAA-3.3,SAA-3.5,SAA-4.3,SAP-2.3,SAP-2.5,SAP-2.6,SAP-4.4
50 SAA-2.1,SAA-3.5,SAA-4.3,SAP-2.4,SAP-2.5,SAP-2.6,SAP-3.3,SAP-4.4
51 SAA-3.3,SAA-4.3,SAP-2.5,SAP-2.6,SAP-4.3,SAP-4.4
52 SAA-2.1,SAA-2.2,SAP-2.4,SAP-3.1,SAP-3.4
53 SAA-2.1,SAA-2.2,SAA-3.5,SAP-2.4,SAP-4.4
54 SAA-2.1,SAA-3.5,SAP-2.4,SAP-2.5,SAP-3.3
55 SAA-2.1,SAA-2.2,SAP-2.1,SAP-2.4,SAP-3.1,SAP-4.4
56 SAA-2.1,SAA-2.2,SAP-2.4,SAP-3.4
57 SAA-2.1,SAA-2.2,SAP-2.4,SAP-3.4,SAP-4.4
58 SAA-2.1,SAA-2.2,SAP-2.4,SAP-3.4,SAP-4.3,SAP-4.4
59 SAA-2.1,SAA-2.2,SAA-3.2,SAP-2.4,SAP-2.5,SAP-3.3,SAP-3.4
60 SAA-2.1,SAA-2.2,SAA-3.2,SAP-2.4,SAP-2.5,SAP-4.3,SAP-4.4
61 SAA-2.2,SAP-1.3,SAP-2.2,SAP-2.4,SAP-3.4
62 SAA-2.2,SAA-4.2,SAA-4.3,SAP-1.3,SAP-2.2,SAP-2.4,SAP-2.6
63 SAA-2.2,SAP-1.3,SAP-2.2,SAP-2.4
64 SAA-2.1,SAA-2.2,SAA-3.2,SAA-3.3,SAA-4.2,SAA-4.3,SAP-2.4,SAP-2.5,SAP-2.6,SAP-3.3
65 SAA-2.2,SAA-3.2,SAP-2.4,SAP-2.5,SAP-3.3,SAP-3.4
66 SAA-2.2,SAP-3.1,SAP-3.3,SAP-3.4
67 SAA-3.2,SAP-3.1,SAP-3.3
68 SAA-4.2,SAP-1.5,SAP-2.6,SAP-3.5
69 SAA-4.2,SAP-1.5,SAP-2.6,SAP-3.3,SAP-3.5
70 SAA-4.1,SAA-4.3,SAP-1.5,SAP-2.6,SAP-3.5
71 SAA-4.4,SAP-1.1,SAP-1.5,SAP-2.6,SAP-3.5
72 SAA-1.2,SAA-2.2,SAP-2.1,SAP-3.1,SAP-3.2
73 SAA-1.2,SAA-2.2,SAP-2.1,SAP-3.1,SAP-3.2,SAP-3.4
74 SAA-2.2,SAP-2.1,SAP-2.4,SAP-3.4
75 SAA-1.2,SAP-2.1,SAP-3.1,SAP-3.2
76 SAA-1.2,SAA-2.2,SAP-3.1,SAP-3.2,SAP-3.4
77 SAA-1.3,SAA-2.2,SAP-2.2,SAP-3.1,SAP-3.4
78 SAA-2.2,SAP-3.1,SAP-3.2,SAP-3.3,SAP-3.4,SAP-3.5
79 SAP-1.4,SAP-1.5,SAP-3.1
80 SAP-1.1,SAP-1.2,SAP-1.4
81 SAP-1.2,SAP-1.4,SAP-3.1,SAP-3.2
82 SAP-1.2,SAP-1.4,SAP-2.3,SAP-3.2
83 SAP-1.1,SAP-1.3,SAP-2.2,SAP-2.4,SAP-2.5,SAP-3.4
84 SAP-1.2,SAP-1.3,SAP-1.4,SAP-2.2,SAP-3.2,SAP-3.4
85 SAP-1.5,SAP-2.6,SAP-3.5
86 SAP-4.1
87 SAP-4.2
88 SAP-4.1,SAP-4.2
89 SAP-4.3,SAP-4.4
90 SAP-3.1,SAP-3.2,SAP-3.3,SAP-3.4,SAP-3.5,SAP-4.3,SAP-4.4
91 SAP-2.3,SAP-2.5,SAP-2.6,SAP-4.4
92 SAP-1.2,SAP-2.3,SAP-3.2,SAP-4.4
93 SAP-1.2,SAP-2.3,SAP-3.2,SAP-4.4
94 SAP-1.2,SAP-1.4,SAP-2.3,SAP-3.2,SAP-4.4
95 SAP-2.1,SAP-2.3,SAP-3.1,SAP-4.4
96 SAP-2.4,SAP-2.5,SAP-2.6,SAP-3.1,SAP-3.2,SAP-3.3,SAP-3.4,SAP-3.5
97 SAA-1.2,SAA-2.1,SAA-2.2,SAA-3.3,SAA-3.4,SAA-4.4,SAP-1.1,SAP-1.3,SAP-2.4,SAP-2.5,SAP-2.6
98 SAA-1.1,SAA-1.2,SAA-1.3,SAA-2.1,SAA-3.2,SAA-4.2,SAP-1.4,SAP-2.3,SAP-2.5,SAP-2.6,SAP-4.4
99 SAA-2.1,SAA-2.2,SAA-3.1,SAA-3.5,SAA-4.1,SAA-4.4,SAP-2.4,SAP-2.5,SAP-2.6,SAP-3.3
100 SAA-1.1,SAA-1.2,SAA-1.3,SAP-1.2,SAP-1.4,SAP-2.3,SAP-3.2
101 SAA-3.4,SAA-4.4,SAP-1.1,SAP-4.1,SAP-4.2,SAP-4.3
102 SAA-1.3,SAA-2.1,SAA-3.3,SAA-3.5,SAA-4.3,SAP-2.3,SAP-2.5,SAP-2.6,SAP-4.4
103 SAA-2.2,SAP-1.3,SAP-2.2,SAP-2.4,SAP-3.4
104 SAP-1.2,SAP-2.3,SAP-2.4,SAP-2.5,SAP-2.6,SAP-3.1,SAP-3.2,SAP-4.4
105 SAA-2.1,SAA-3.2,SAA-4.2,SAP-2.5,SAP-2.6,SAP-4.4
106 SAA-2.1,SAA-2.2,SAP-2.4,SAP-2.5,SAP-4.3,SAP-4.4
107 SAA-2.2,SAP-1.3,SAP-2.4,SAP-3.4
108 SAA-2.2,SAP-1.3,SAP-2.4,SAP-3.4,SAP-4.3
109 SAA-2.1,SAA-2.2,SAA-3.2,SAP-2.4,SAP-2.5,SAP-3.3,SAP-3.4
110 SAA-2.1,SAA-3.3,SAP-2.4,SAP-2.5,SAP-3.3,SAP-3.4
111 SAA-1.2,SAA-2.2,SAP-1.2,SAP-2.3,SAP-2.4,SAP-3.2,SAP-3.4
112 SAA-1.1,SAA-1.2,SAA-1.3,SAP-1.2,SAP-2.3,SAP-3.2
113 SAA-2.2,SAP-3.1,SAP-3.3,SAP-3.4
114 SAA-2.2,SAP-1.3,SAP-2.2,SAP-2.4
115 SAA-4.1,SAA-4.2,SAA-4.3,SAA-4.4,SAP-1.5,SAP-2.6,SAP-3.5
116 SAP-4.1,SAP-4.2,SAP-4.3,SAP-4.4
"""


TASKS_BY_CHAPTER = {
    int(number): tuple(tasks.split(","))
    for row in _TASK_ROWS.strip().splitlines()
    for number, tasks in (row.split(maxsplit=1),)
}


def _tasks(number: int) -> tuple[str, ...]:
    return TASKS_BY_CHAPTER[number]


def _sources(number: int) -> tuple[str, ...]:
    community = ("community-saa", "community-traps", "community-sap", "community-sap-notes")[number % 4]
    if number == 12:
        return (
            "saa-d2",
            "saa-d3",
            "sap-d1",
            "network",
            "vpc-route-tables",
            "vpc-public-private-example",
            "vpc-cli-example",
            community,
        )
    if number <= 10:
        return ("saa-guide", "sap-guide", "well-architected", "jayendra-index", community)
    if number <= 20:
        return ("saa-d3", "sap-d1", "network", community)
    if number <= 31:
        extras = ("iam-policy-elements", "jayendra-iam") if 21 <= number <= 26 else ()
        return ("saa-d1", "sap-d1", "iam", "security", *extras, community)
    if number <= 40:
        return ("saa-d2", "saa-d3", "sap-d2", "compute", community)
    if number <= 51:
        extras = ("s3-policy-examples", "jayendra-s3") if 41 <= number <= 42 else ()
        return ("saa-d3", "saa-d4", "sap-d2", "database", *extras, community)
    if number <= 60:
        return ("saa-d2", "sap-d2", "integration", community)
    if number <= 71:
        return ("saa-d2", "saa-d4", "sap-d3", "reliability", "cost", community)
    if number <= 78:
        return ("sap-d2", "sap-d3", "operations", community)
    if number <= 90:
        return ("sap-guide", "sap-d1", "sap-d3", "sap-d4", "migration", community)
    if number <= 96:
        return ("sap-guide", "sap-d2", "bedrock", community)
    return (
        "saa-guide",
        "sap-guide",
        "well-architected",
        "integration",
        "jayendra-patterns",
        community,
    )


def topic(
    number: int,
    title: str,
    problem: str,
    decision: str,
    alternative: str,
    failure: str,
    pattern: str,
    scenario: str,
    services: str,
    level: str = "SAA → SAP",
) -> Topic:
    return T(
        number,
        title,
        problem,
        decision,
        alternative,
        failure,
        pattern,
        scenario,
        tuple(value.strip() for value in services.split("|") if value.strip()),
        _tasks(number),
        _sources(number),
        level,
    )

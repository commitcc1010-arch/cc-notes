---
title: Python Interview Toolbox
tags:
  - coding-interview
  - python
  - cheat-sheet
status: complete
updated: 2026-09-30
---

# Python Interview Toolbox

[[00 - Book Index|回到目錄]]

## 常用 imports

```python
from collections import Counter, defaultdict, deque
from functools import lru_cache
from heapq import heappush, heappop, heapify
from bisect import bisect_left, bisect_right
from math import gcd, inf
```

## Hashing

```python
freq = Counter(nums)
groups = defaultdict(list)
seen = set()
```

## Queue / Deque

```python
q = deque([start])
x = q.popleft()
q.append(next_state)

# Monotonic deque
while q and values[q[-1]] <= values[i]:
    q.pop()
q.append(i)
```

## Heap

```python
heap = []
heappush(heap, (priority, item))
priority, item = heappop(heap)

# Max heap
heappush(heap, -value)
largest = -heappop(heap)
```

## Binary Search

```python
lo, hi = 0, len(nums)  # first index satisfying condition
while lo < hi:
    mid = (lo + hi) // 2
    if condition(mid):
        hi = mid
    else:
        lo = mid + 1
return lo
```

## Memoization

```python
@lru_cache(None)
def dp(state):
    if base_case:
        return base_value
    return best(dp(next_state) for next_state in transitions)
```

## 常見陷阱

- `[[0] * n] * m` 會讓所有 row 指向同一個 list。
- `heapq` 是 min heap。
- `sort()` 回傳 `None`。
- `dict` key 必須 hashable。
- 遞迴深度很深時，優先改 iterative。
- 不要用 `pop(0)` 當 queue；它是 $O(n)$。
- `/` 是浮點除法，整數使用 `//`。

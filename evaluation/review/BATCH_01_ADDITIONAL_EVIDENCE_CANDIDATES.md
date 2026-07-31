# Batch 01 additional evidence candidates

## Mục đích

Hai câu q-005 và q-011 có decision `needs_more_evidence`. Re-running deterministic
embedding locator với wording không đổi trả lại cùng ranking; vì vậy artifact này
ghi source expansion theo các segment liền kề để reviewer kiểm đúng evidence, thay
vì gọi lại cùng query và coi đó là candidate mới.

Các đoạn dưới đây là candidate, không phải ground truth hay canonical evidence.

## mit60001-q-005 — base case

```text
Question: According to the course, why does a recursive function require a base case?
Video: WPSeyjX1-4s — 6. Recursion and Dictionaries
Source segment range: 105–116
Time range: 294.720–325.870
Status: candidate_requires_human_source_review
```

```text
In recursion, this is OK.
Our definition of a procedure can in its body call itself,
so long as I have what I call a base case,
a way of stopping that unwinding of the problems,
when I get to something I can solve directly.
And so what we're going to do is avoid infinite recursion
by ensuring that we have at least one or more base
cases that are easy to solve.
And then the basic idea is I just want to solve the same
problem on some simpler input with the idea of using that
solution to solve the larger problem.
```

## mit60001-q-011 — recursion và iteration

Hai range cùng dùng bài toán nhân số nguyên; chúng tạo evidence so sánh theo hai
cách giải khác nhau. Reviewer cần chấp nhận cả hai range nếu muốn dùng cho question
hiện tại.

```text
Question: How does the course compare recursion and iteration for solving problems?
Video: WPSeyjX1-4s — 6. Recursion and Dictionaries
Range A segments: 159–169
Range A time: 431.170–463.610
Status: candidate_requires_human_source_review
```

```text
Going to call it mult_iter, takes in two arguments a and b,
and I'm going to capture exactly that process.
I set up result internally as a little variable to accumulate things.
There is the iteration: as long as b is greater than 0,
add a to result, store it away, reduce b by 1,
and keep doing that until b is equal to 0, then return the result.
```

```text
Question: How does the course compare recursion and iteration for solving problems?
Video: WPSeyjX1-4s — 6. Recursion and Dictionaries
Range B segments: 181–200
Range B time: 500.420–564.430
Status: candidate_requires_human_source_review
```

```text
I've taken one problem and reduced it to a simpler version of the same problem,
plus some things I know how to do. I keep doing that until I get down to something
I can solve directly, a base case. If b is 1, the answer is a; otherwise solve the
same problem with a smaller version and add it to a. This is a recursive definition
that reduces a problem to a simpler version of the same problem.
```

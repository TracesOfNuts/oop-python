# Notebook sources

The notebooks in `notebooks/` are built from the `.txt` files in this folder.
Do not edit the notebooks by hand to change the course.
Edit the `.txt` file here, then rebuild:

```bash
python tools/build.py verify 04     # rebuild and test notebook 04 only
python tools/build.py               # rebuild and test everything
```

The build never overwrites a notebook that the student has already written in.
Use `--force` if you really want to overwrite it.

## File format

Each file is a list of blocks.
A block starts with a line that begins with `@@`.
Everything until the next `@@` line belongs to that block.
Files are named `NN_Title_Words.txt`, and `NN` is used to number the exercises (`4.1`, `4.2`, ...).

### Plain cells

```text
@@ md
Any Markdown text.

@@ code
print("A normal example cell")

@@ code raises=ValueError
int("abc")          # an example that is meant to fail, to show the error message

@@ code inputs=Amy|25
name = input("Name: ")   # when the verifier runs this cell, input() returns "Amy" then "25"
```

### Coding exercise

```text
@@ exercise Short title
What the student must do (Markdown).
@@ starter
# code the student starts with
@@ check
assert answer == 5, "❌ answer should be 5"
@@ hint
Optional hint (Markdown).
@@ solution
answer = 5
```

- `starter` and `solution` are required. `check` and `hint` are optional, but almost every exercise should have a check.
- The build wraps the check in a `try` block and adds a final `print("✅ Correct! Well done.")`.
  A failed `assert` prints its message as one line, instead of a long red error, and "Run All" keeps going.
- Do not use triple-quoted strings in a check, because the build indents the check code.
- Write each `assert` message so it tells the student what is wrong, and start it with `❌`.
- The verifier runs the solution and requires the check to pass.
- It also runs the empty starter and requires the check to FAIL, so a check must never pass on the starter.
- Add `inputs=...` on `@@ solution` if the code calls `input()`.

### Predict the output

```text
@@ predict Short title
Optional intro text.
@@ run
x = 3
print(x * 2)
@@ output
6
@@ explain
Why it prints that.
```

- For code that fails, write `@@ run raises=TypeError`. Keep `@@ output` only if something is printed before the error.
- The verifier runs the code and checks that the real output matches `@@ output` exactly.

### Written answer (theory)

```text
@@ write Short title
The question.
@@ hint
Optional.
@@ answer
The model answer.
```

## Style guide for authors

The student has very weak foundations.
She struggled with the first lesson on functions.
Every notebook must be written for her.

### Language

- Simple English, short sentences, one idea at a time.
- Put each full sentence on its own line in Markdown.
- Never use the em dash character. Use a plain dash `-`.
- Explain every new word the first time you use it, for example "argument: the value you pass in".
- Use everyday examples (bubble tea, a cash card, a phone book) before abstract ones.
- Show the real error message for common mistakes, and explain how to read it.

### Structure of each notebook

1. A title, "What you will learn", and "Why this matters for the exam".
2. Small sections. Each section is: explain, then a runnable example, then 2 to 5 exercises.
3. Exercises go from easy to hard:
   fill in one blank, then change working code, then write from scratch, then exam style.
4. Mix in "predict the output" exercises. Code reading is part of every exam paper.
5. End with a summary ("Key points"), a list of common mistakes, and an exam-style exercise.
6. Aim for 18 to 30 exercises per notebook.

### Code conventions (match the ICT162 course and exam)

- Methods and variables use camelCase, like the course: `topUp`, `addContact`, `searchContact`, `totalFees`.
- Classes use CapitalWords: `CashCard`, `PhoneBook`.
- Private attributes use two underscores (`self.__balance`).
  Protected ones use one underscore (`self._balance`), and class constants look like `_MAX_ITEMS`.
- Use f-strings for formatting, for example `f"${price:.2f}"`.
  Also show `.format()` once in the OOP notebooks, because exam code sometimes uses it.
- Use `@property` and `@name.setter`, never `getX()` / `setX()` methods unless the exam style needs it.
- Keep examples short. No lambdas, comprehensions, file I/O, recursion, or sets, because the exam does not need them.

### Checks

- Checks test values, not printed text, when possible.
  Ask the student to `return` a value or store it in a variable.
- To test printed text, capture it inside the check cell:

```python
import io, contextlib
buffer = io.StringIO()
with contextlib.redirect_stdout(buffer):
    showReceipt("Tea", 2.5)
assert buffer.getvalue() == "Tea costs $2.50\n", f"❌ Your function printed {buffer.getvalue()!r}"
```

- Check cells must be self-contained.
  Do not rely on helper modules, so the notebook also works when copied somewhere else.
- tkinter checks must not open a window that blocks.
  Inside the check, replace `tk.Tk.mainloop` with a function that does nothing, build the app,
  simulate the user, and destroy the window at the end.

### Emoji markers (use only these, and use them the same way everywhere)

| Marker | Meaning |
| --- | --- |
| 🏋️ | coding exercise (added by the build) |
| 🔮 | predict the output (added by the build) |
| ✍️ | written answer (added by the build) |
| 💡 | tip or hint |
| ⚠️ | common mistake |
| 🎯 | how this appears in the exam |
| 📝 | key points summary |

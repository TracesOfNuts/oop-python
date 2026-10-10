# ICT162 Object Oriented Programming - Exam Preparation Course

A hands-on Python course in Jupyter notebooks.
It takes a student from the very basics (variables, printing) to the full ICT162 exam (classes, inheritance, exceptions and tkinter GUIs).
Every notebook is full of small exercises that check themselves.

## For the student: how to start

### 1. Install the tools (one time only)

1. Install Python 3 from [python.org](https://www.python.org/downloads/).
   On Windows, tick **"Add python.exe to PATH"** on the first screen of the installer.
2. Open a terminal in this folder.
   On Windows: open the folder in File Explorer, click the address bar, type `cmd` and press Enter.
3. Install Jupyter:

   ```bash
   python -m pip install notebook
   ```

### 2. Open the course

In the same terminal, run:

```bash
python -m notebook notebooks
```

Your browser opens.
Click **00_Start_Here.ipynb** and follow it.

💡 You can also open the notebooks in **VS Code** with the Jupyter extension.

⚠️ Notebook **13 (GUI with tkinter)** opens real windows, so it must run on your own computer.
It does not work in Google Colab.

### 3. How to work through the course

- Do the notebooks **in order**, from 00 to 15.
- In each exercise, replace the `...` with your answer, run the cell, then run the **✅ CHECK** cell under it.
- Try for a few minutes before you open the **💡 Hint**, and again before the **👀 Solution**.
- For **🔮 Predict** exercises, write your guess before you run the code.
  The exam has many "what does this print?" questions.
- Your answers are saved in the notebook. Save often with **Ctrl + S**.

## The course

| Notebook | Topic | Why it is in the exam |
| --- | --- | --- |
| 00 | Start here | How notebooks and the exercises work, how to read errors |
| 01 | Variables and printing | f-strings like `f"${price:.2f}"` appear in every `__str__` |
| 02 | Functions | Methods are functions inside a class |
| 03 | Decisions (`if`) | Every method that checks a rule |
| 04 | Lists and loops | Searching, adding, removing and totalling objects |
| 05 | Dictionaries | Class dictionaries such as fees by type |
| 06 | Classes and objects | "Write the class" is in every paper |
| 07 | Encapsulation and properties | `__private` attributes, `@property`, setters |
| 08 | Class variables and class methods | `_MAX_ITEMS`, running ids, `@classmethod`, overloading |
| 09 | Composition and collections | "has a" relationships, PhoneBook style classes |
| 10 | Inheritance | `super()`, overriding by replacement or refinement |
| 11 | Abstract classes and polymorphism | `ABC`, `@abstractmethod`, theory answers |
| 12 | Exceptions | Custom exceptions, `raise`, `try` / `except` |
| 13 | GUI with tkinter | About 20 marks in every paper |
| 14 | Exam drills | "Error or output?" questions and theory sentences |
| 15 | Mock exam | A full 2 hour practice paper with a marking guide |

`MEMORY_AID_SHEET.md` is a model of the one A4 double-sided sheet that the exam allows.
Read it, then write your own version by hand. Writing it is part of the revision.

### What is left out, and why

The course only teaches what the exam tests (Seminars 1 to 5 and the past papers from 2023 to 2025).
These Python topics are skipped because they never appear: file reading and writing, list comprehensions, `lambda`, recursion, sets, static methods, multiple inheritance, and the `pack` / `place` layouts beyond a short mention.
`for` loops are **not** skipped.
Every paper asks you to search, count or total a list of objects, and that needs a loop.
`while` loops get only a short section, because they appear only in menu questions.

## For the tutor

### Folders

| Folder | What is in it |
| --- | --- |
| `notebooks/` | The student notebooks. The student writes in these. |
| `solutions/` | The same notebooks with every answer filled in and run, so you can see the expected output. |
| `source/` | The plain-text sources the notebooks are built from. Edit these to change the course. |
| `tools/build.py` | Builds `notebooks/` from `source/` and tests every exercise. |

### Changing the course

Edit a file in `source/` (the format is explained in `source/README.md`), then run:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt     # macOS/Linux: .venv/bin/python
.venv/Scripts/python tools/build.py                         # build and test everything
.venv/Scripts/python tools/build.py verify 07               # build and test notebook 07 only
```

The test runs every solution and checks that:

- every solution passes its check, and every check fails on the empty starter code,
- every "predict the output" answer matches what Python really prints,
- every example that is meant to fail raises the stated error.

The build never overwrites a notebook that the student has already written in.
Add `--force` to overwrite it anyway.
Add `--no-solutions` to build the student notebooks without the 👀 Solution sections.

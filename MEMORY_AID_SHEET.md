# ICT162 Memory Aid Sheet (model)

The exam allows ONE A4 sheet, both sides, handwritten or typed.
This is a model.
Copy it by hand and change it to suit you: writing it is revision.

## Side 1 - Classes

### Class with private attributes, property, setter, `__str__`

```python
class Item:
    _TAX = 0.09                          # class variable: Item._TAX or type(self)._TAX
    _nextId = 1                          # running id

    def __init__(self, name, price=10):  # default parameter = "overloading"
        self.__id = Item._nextId
        Item._nextId += 1                # do not forget to increment
        self.__name = name
        self.__price = price

    @property
    def price(self):                     # use: item.price   (no brackets)
        return self.__price

    @price.setter
    def price(self, newPrice):           # use: item.price = 5
        if newPrice > 0:
            self.__price = newPrice

    def __str__(self):
        return f"Id: {self.__id} Name: {self.__name} Price: ${self.__price:.2f}"
```

### Class method on a class dictionary

```python
class Plan:
    _FEES = {"A": 10, "B": 20}

    @classmethod
    def updateFees(cls, key, fees):      # cls, never self
        cls._FEES[key] = fees            # adds if new, updates if old

    @classmethod
    def getFees(cls, key):
        return cls._FEES.get(key)        # None if missing
```

### Collection class (composition, "has a")

```python
class PhoneBook:
    _MAX = 3

    def __init__(self, owner):
        self.__owner = owner
        self.__contacts = []                       # new list for each object

    def searchContact(self, name):
        for c in self.__contacts:
            if c.name.lower() == name.lower():     # case insensitive
                return c
        return None

    def addContact(self, contact):
        if len(self.__contacts) + 1 > PhoneBook._MAX:
            raise PhoneBookException("Phone book is full")
        if self.searchContact(contact.name) is not None:
            raise PhoneBookException("Duplicate name")
        self.__contacts.append(contact)

    def removeContact(self, name):
        c = self.searchContact(name)
        if c is None:
            return False
        self.__contacts.remove(c)
        return True

    def __str__(self):
        result = f"Owner: {self.__owner}"
        for c in self.__contacts:
            result += "\n" + str(c)
        return result
```

### Error or output? (quick table)

| Code | Result |
| --- | --- |
| `Shape()` when `Shape` is abstract | `TypeError` |
| subclass misses one abstract method, then create it | `TypeError` |
| subclass inherits the method from its parent | fine |
| `obj.price = 5` with no setter | `AttributeError` |
| `obj.price()` (property called) | `TypeError: 'float' object is not callable` |
| `obj.__name` outside the class | `AttributeError` (name mangling) |
| `obj.__name = "x"` outside the class | no error, makes a NEW attribute |
| `self._X = 5` | instance copy only; `Cls._X = 5` changes it for all |
| method defined twice | the last one wins |
| child forgets `super().__init__()` | parent attributes missing: `AttributeError` |
| child uses parent's `self.__x` | `AttributeError`: use the property |

## Side 2 - Inheritance, exceptions, GUI, theory

### Abstract class and subclass

```python
from abc import ABC, abstractmethod

class Shape(ABC):
    def __init__(self, name):
        self._name = name

    @abstractmethod
    def area(self):
        pass

    def __str__(self):
        return f"{self._name} area: {self.area():.2f}"

class Square(Shape):
    def __init__(self, name, side):
        super().__init__(name)                     # parent's data first
        self._side = side

    def area(self):                                # must implement every abstract method
        return self._side ** 2

    def __str__(self):                             # refinement: calls super()
        return super().__str__() + f" side: {self._side}"
```

### Custom exception

```python
class ShopException(Exception):
    pass

raise ShopException("Shop is full")               # inside a method, after a check

try:                                               # in main / the caller
    shop.add(item)
except ShopException as e:                         # specific exceptions before Exception
    print(e)
else:
    print("Added")                                 # only if no exception
finally:
    print("Always runs")                           # even after return
```

"Do not handle the exception here" = no `try` in that method.

### tkinter skeleton and callback

```python
import tkinter as tk
from tkinter import scrolledtext

class MyGUI:
    def __init__(self):
        self.__win = tk.Tk()
        self.__win.title("Converter")
        tk.Label(self.__win, text="Value:").grid(row=0, column=0, sticky=tk.W)
        self.__entry = tk.Entry(self.__win, width=10)
        self.__entry.grid(row=0, column=1, padx=5, pady=5)
        tk.Button(self.__win, text="Go", command=self.go).grid(row=1, column=0, columnspan=2)
        self.__out = scrolledtext.ScrolledText(self.__win, width=30, height=4)
        self.__out.grid(row=2, column=0, columnspan=2)
        self.__out.config(state=tk.DISABLED)
        self.__win.mainloop()

    def go(self):                       # with .bind('<Button-1>', self.go): def go(self, evt)
        self.__out.config(state=tk.NORMAL)
        self.__out.delete("1.0", tk.END)
        text = self.__entry.get().strip()
        if text == "":
            self.__out.insert(tk.END, "Please enter a value")
        else:
            try:
                value = float(text)
                if value <= 0:
                    self.__out.insert(tk.END, "Value must be positive")
                else:
                    self.__out.insert(tk.END, f"Result: {value * 2:.1f}")
            except ValueError:
                self.__out.insert(tk.END, "Value must be numeric")
        self.__out.config(state=tk.DISABLED)
```

Listbox: `lb.bind("<<ListboxSelect>>", self.onSelect)`, then `index = lb.curselection()[0]`.
Radiobutton: `self.__choice = tk.IntVar()`, `tk.Radiobutton(win, text="A", variable=self.__choice, value=1)`, read with `self.__choice.get()`.
Disable a button: `btn.config(state=tk.DISABLED)`.

### Theory sentences

- **Encapsulation**: data and the methods that use it are kept together in a class, and the data is hidden (private) so it can only be changed through methods.
- **Abstraction**: show only what an object does (its methods), hide how it does it.
- **Inheritance ("is a")**: a subclass reuses the attributes and methods of its superclass, e.g. a Manager is an Employee.
- **Composition ("has a")**: an object contains another object and uses its methods, e.g. a Customer has a CashCard.
- **Polymorphism**: the same method call behaves differently depending on the object's class. In `for s in shapes: print(s.area())`, `s.area()` runs the Circle or the Rectangle version.
- **Overriding by replacement**: the subclass method does not call the parent's version.
- **Overriding by refinement**: the subclass method calls `super().method()` and then adds more.
- **Overloading in Python**: not supported directly (a second definition replaces the first), so use default parameters, e.g. `def add(self, x, y, z=None)`.
- **Abstract class**: cannot be instantiated; it forces subclasses to implement its abstract methods.
- **Class variable**: one shared copy for all objects (a limit, a rate, a running id).

### Mark savers

Use class variables, not numbers.
Follow the order of checks in the question.
Copy message text and output format exactly (`$` and 2 decimals).
`len(list) + 1 > MAX` for "this addition results in more than".
`.lower()` for case insensitive.
`self` in every method, `cls` in class methods.
GUI: `float()` the `.get()` text, `NORMAL` before writing, `DISABLED` after.

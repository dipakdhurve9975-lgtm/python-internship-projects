# Python from the beginning

Use Python 3.11 or later. Save one example in `hello.py`, open PowerShell in that folder and run `python hello.py`. Try examples one at a time. A line beginning with `#` is a comment. Spaces at the start of a line matter in Python.

These are study examples connected to the apps. The actual 12-week diary was not attached, so no exact weekly syllabus or attendance is claimed. Use `DIARY_MAPPING.md` to add verified diary headings later.

## Print and variables

`print()` shows a value. A variable is a name for a value. `=` assigns a value; `==` compares values.

```python
name = "Ada"
score = 10
print("Hello", name)
print("Score:", score)
```

MathDuel has variables for scores. SunDrop has a variable for the selected folder.

## Four common types

```python
age = 20          # int: whole number
seconds = 2.5     # float: decimal number
title = "My file" # str: text
correct = True    # bool: True or False
print(type(age), type(seconds), type(title), type(correct))
```

The game answer is an integer. Elapsed time is a float. A nickname is a string. Whether an answer is correct is a boolean.

## Input and conversion

`input()` always returns text. Convert text to a number with `int()` or `float()`.

```python
name = input("Your name: ")
age = int(input("Your age as a whole number: "))
print(name, "will be", age + 1, "next year")
```

Entering `hello` as an age causes an error. Later we will catch that error.

## Operators

```python
a, b = 12, 3
print(a + b, a - b, a * b, a / b)
print(a // b)  # whole-number division
print(a % b)   # remainder
print(b ** 2)  # square
print(a > b, a == b, a != b)
print(a > 0 and b > 0)
```

`/` produces a float. `//` produces a whole-number quotient for integers. The generator creates exact division questions by multiplying two integers first.

## Decisions with if and else

```python
answer = 7
if answer == 7:
    print("Correct")
else:
    print("Try the next question")
```

Only one branch runs. Four spaces mark the statements inside each branch.

## For and while loops

```python
for number in range(1, 4):
    print("Round", number)

count = 3
while count > 0:
    print(count)
    count -= 1
```

`range(1, 4)` includes 1, 2 and 3. A `while` loop repeats while its condition is true. The server has a background loop that checks deadlines. It sleeps briefly between checks.

## List, tuple, set and dictionary

```python
players = ["Ada", "Alan"]     # list: ordered, can change
players.append("Solo")
size = (390, 844)              # tuple: ordered, cannot change items
unique = {"Ada", "Ada", "Alan"} # set: unique values
player = {"name": "Ada", "score": 10} # dict: key and value
print(players[0], size[1], sorted(unique), player["score"])
```

Rooms contain a list of players. The server uses dictionaries to find rooms by code and submissions by player index.

## Functions

```python
def add_points(score, points):
    return score + points

print(add_points(10, 5))
```

Functions take inputs and can return outputs. MathDuel's `question()` returns question text and its integer answer. Small functions are easier to test.

## Strings

```python
title = "  My recording  "
print(title.strip())
print(title.upper())
print("recording" in title)
print(f"File: {title.strip()}")
```

SunDrop removes dangerous filename characters. A filename is not the same as a URL. A URL can also contain private query parameters, so the history does not store URLs.

## Files and JSON

Run this in a practice folder; it writes a small new file.

```python
from pathlib import Path
import json

path = Path("practice_history.json")
path.write_text(json.dumps({"score": 10}), encoding="utf-8")
record = json.loads(path.read_text(encoding="utf-8"))
print(record["score"])
```

`Path` helps work with filenames. JSON stores simple lists, dictionaries, strings, numbers and booleans. SunDrop writes a temporary file first, then replaces the history file to reduce partial-write damage.

## Try and except

```python
try:
    answer = int(input("Enter a whole number: "))
    print(answer * 2)
except ValueError:
    print("That was not a whole number")
```

A clear error message lets the user retry. Do not hide every error without explaining what failed. SunDrop converts network and extraction errors into useful messages.

## Imports

```python
import math
from pathlib import Path
print(math.isqrt(81))
print(Path.cwd())
```

Imports let us use existing code. `math` and `pathlib` come with Python. Flask, yt-dlp and CustomTkinter must be installed. A virtual environment keeps project packages separate.

## Classes and objects

```python
class Player:
    def __init__(self, name):
        self.name = name
        self.score = 0

    def reward(self, points):
        self.score += points

player = Player("Ada")
player.reward(10)
print(player.name, player.score)
```

A class is a description; an object is one instance of it. `self` refers to that object. SunDrop's window is a class. The game uses dataclasses to hold players and rooms.

## Comprehensions

```python
squares = [number ** 2 for number in range(1, 5)]
print(squares)
connected = [name for name in ["Ada", "", "Alan"] if name]
print(connected)
```

A comprehension is a short way to build a collection. Use a normal loop when that is easier to understand.

## Flask routes

After installing Flask, save this as `route_demo.py`:

```python
from flask import Flask
app = Flask(__name__)

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False)
```

Run `python route_demo.py` and open `http://127.0.0.1:5050/health`. A route connects a URL path to a function. Our main game route serves HTML, while `/health` returns JSON.

## Socket.IO events

HTTP routes handle ordinary requests. Socket.IO keeps an event connection so the server can send a question to both players. This tiny server receives a `hello` event from a Socket.IO client:

```python
from flask import Flask
from flask_socketio import SocketIO, emit
app = Flask(__name__)
sio = SocketIO(app, async_mode="threading")

@sio.on("hello")
def hello(data):
    emit("greeting", {"message": "Hello from Python"})

if __name__ == "__main__":
    sio.run(app, host="127.0.0.1", port=5051, debug=False)
```

Running this starts the event server; it has no HTML page. MathDuel includes a full client. Its browser emits `create`, `join`, `start` and `answer`; Python emits `identity`, `state` and `problem`. Socket.IO can use WebSocket or fall back to HTTP polling. It is not identical to a raw WebSocket connection.

## SQLite and safe queries

```python
import sqlite3
with sqlite3.connect(":memory:") as db:
    db.execute("CREATE TABLE scores (name TEXT, points INTEGER)")
    db.execute("INSERT INTO scores VALUES (?, ?)", ("Ada", 10))
    print(db.execute("SELECT points FROM scores WHERE name = ?", ("Ada",)).fetchone())
```

The `?` marks a parameter. Values are passed separately instead of being pasted into SQL. MathDuel stores completed matches in a SQLite file. The example above uses memory, so it leaves no file.

## GUI, workers and queues

The UI is the part the user sees. The backend performs rules, storage and downloads. A slow download on the GUI thread would freeze buttons. SunDrop uses a worker thread and a queue. Tk's `after()` reads that queue and updates widgets on the main thread. Cancellation asks the worker to stop at a progress hook; it does not forcefully kill the thread.

## Tests

```python
def add(a, b):
    return a + b

def test_add():
    assert add(2, 3) == 5
```

Save this as `test_example.py` and run `python -m pytest test_example.py`. A passing test checks a specific behavior; it does not prove that every possible website or device works.

## Git

Git records versions of files. A commit is a saved change. GitHub hosts repositories online, but Git works locally too.

```powershell
git init
git add .
git status
git commit -m "First working demonstration"
```

Check `git status` before committing. Do not commit a virtual environment, secrets or personal histories. Pushing uploads commits to a remote repository; only do that when you choose to publish.

## Main project files

| File | What it does |
|---|---|
| `mathduel-lan/app.py` | Flask routes, Socket.IO events, IP candidates, rate limits and the timer worker. |
| `mathduel-lan/engine.py` | Generates questions; checks answers, scores, room phases and database records. |
| `mathduel-lan/templates/index.html` | Gives the browser its page structure and labels. |
| `mathduel-lan/static/style.css` | Colors, spacing, mascot, desktop and mobile layouts. |
| `mathduel-lan/static/game.js` | Displays server state and sends player actions; it does not score. |
| `sundrop/app.py` | Desktop widgets, folder picker, appearance and queue processing. |
| `sundrop/core.py` | URL validation, safe names, format inspection, downloading and JSON history. |
| `sundrop/artwork.py` | Reuses thumbnails, makes fallback covers and verifies MP3 tags on a copy. |
| `sundrop/player.py` | Plays local supported audio, pauses it, changes volume and opens files safely. |
| `docs/make_sample.py` | Creates original audio for safe tests. |
| Both `tests/` folders | Automated checks of rules, validation, storage and integration. |

Start by changing a caption or color. Next add a small function and a test. Change one thing at a time, run the app, and explain the result in your own words.

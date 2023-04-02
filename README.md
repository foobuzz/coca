# coca

A Python lib to help you update the lines you have already printed to stdout.

```python
with coca.LinesSession() as session:
    line1 = session.line("Hello World!")
    line2 = session.line("Everything is Awesome")

    for i in range(10):
        time.sleep(0.3)
        line1.update(["🎉🎉🎉🎉🎉🎉", "Hello World!"][i%2])
        time.sleep(0.3)
        line2.update(["💖💖💖💖💖💖", "Everything is Awesome"][i%2])
```

![basic example](docs/screens/hello_world.gif)

**Note:** Coca uses ANSI escape codes to do what it does, and will therefore only work on compatible terminals.


## Installation

```
pip install coca
```

## Usage

In order to use coca you must instanciate a `LinesSession`.

```python
session = coca.LinesSession()
```
Everytime you want to write a line at the end of stdout, use the `line` method on the session, which returns a `Line` object.

```python
some_line = session.line("Download in progress...")
```

Everytime you want to update the text of the line, you can use the `update` method on the `Line`:

```python
some_line.update("Download finished!")
```

While your session is active, all your interactions with stdout must be done either through `LinesSession.line` or `Line.update`.

Although adding a new line with `line` will always print the line at the end of everything that has already been printed, whenever you update a line, the terminal's cursor will be put one carriage return after the updated line, which can be anywhere in the printed lines depending on which line you updated. To put the cursor one carriage return after the _last_ line of the session, so that you may resume regular interaction with stdout without altering already printed lines, you can call the `end` method on the session:

```python
session.end()
```

`LinesSession` can also be used as a context manager, in which case the `end` method will automatically be called upon exiting the context.

```python
with coca.LinesSession() as session:
    some_line = session.line("Download in progress...")
    # doing important stuff
    some_line.update("Download finished!")
```

**Limitation:** Updating a line that has scrolled out of the terminal's display area will not work and result in undefined behavior. See [Design considerations](docs/design_considerations.md#lines-off-display-area).


### String formatting

`.format`-style string formatting can be used with keyword arguments on the `line` method. The point being, you can update formatting keys individually later:

```python
with coca.LinesSession() as session:
    some_line = session.line("Progress: [{percent:.2f}%] {bar}>", percent=0, bar='')

    for i in range(41):
        time.sleep(0.2)
        some_line.update(percent=i/40*100, bar='='*i) 
```

![progress example](docs/screens/progress.gif)


### Multithreading

The lines created on a single session can safely be dispatched accross multiple threads.

```python
def run_counting(line):
    for i in range(101):
        line.update(count=i)
        time.sleep(random.uniform(0, 0.2))

threads = []

with coca.LinesSession() as session:
    for thread_number in range(10):
        line = session.line(
            "[Thread {thread}]: {count}",
            thread=thread_number, count=0,
        )
        t = threading.Thread(target=run_counting, kwargs={'line': line})
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
```

![threads example](docs/screens/threads.gif)


## Line wrapping

Coca is aware of the current terminal size, and will appropriately handle line wrapping:

```python
with coca.LinesSession() as session:
    line1 = session.line("Hello!")
    line2 = session.line("This is the second line.")

    time.sleep(2)

    line1.update(
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor "
        "incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis "
        "nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. "
        "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore "
        "eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt "
        "in culpa qui officia deserunt mollit anim id est laborum. "
    )

    time.sleep(2)

    line1.update("Hello!")
```

![line-wrapping example](docs/screens/wrap.gif)

**Limitations:**
 - The line-wrapping calculation is naive and will only work when one Unicode character in the string is equal to one unit of width in the terminal. Literal newlines, ANSI escape codes for colors and such, emojis, and non-latin characters, won't do well with line-wrapping. See [Design considerations](docs/design_considerations.md#line-wrapping).
 - The terminal size is assumed to the same accross the life of a single session.

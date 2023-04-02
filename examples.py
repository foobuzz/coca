import queue
import random
import threading
import string
import time

import sys; sys.path.append('src')
import coca


def simple_example():
    session = coca.LinesSession()

    line = session.line("Hello World!")

    for i in range(10):
        time.sleep(0.5)
        line.update(["Hello World!", "Everything is Awesome!"][i%2])


def two_lines_example():
    with coca.LinesSession() as session:
        line1 = session.line("Hello World!")
        line2 = session.line("Everything is Awesome")

        for i in range(10):
            time.sleep(0.2)
            line1.update(["Hello World!", "🎉🎉🎉🎉🎉🎉"][i%2])
            time.sleep(0.2)
            line2.update(["Everything is Awesome", "💖💖💖💖💖💖"][i%2])


def progress_example():
    with coca.LinesSession() as session:
        some_line = session.line("Progress: [{percent:.2f}%] {bar}>", percent=0, bar='')

        for i in range(41):
            time.sleep(0.2)
            some_line.update(percent=i/40*100, bar='='*i)


def threads_example():

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


def multiline_example():
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


if __name__ == '__main__':
    simple_example()
    two_lines_example()
    progress_example()
    threads_example()
    multiline_example()

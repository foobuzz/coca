import math
import shutil
import sys
import threading
from dataclasses import dataclass
from typing import Optional


# Welcome to the realm of race conditions and offset-by-one errors where
# printing cannot be used to debug. Good luck.


class LinesSession:

    """
    Abstraction over the section of stdout that will be handled by coca. Use
    the `line` method to write a line to stdout, and call the `end` method
    when you are done (or use the session as a context manager). Do not
    manually write to stdout while the session is active. The session and
    associated Line instances can safely be shared between threads (allegedly).
    """

    def __init__(self):
        # Number of physical lines on the terminal.
        # Starts at 1 because we assume the program starts with its own line
        # (which is the case on my machine™).
        self.lines_counter = 1

        # A dictionary of Line objects IDs to a _LineEntry object.
        self.lines_index = {}
        self.last_line_entry = None

        # The current physical position of the cursor on the terminal.
        # Line 0 is the first line of the program's stdout.
        self.current_line = 0

        self.printing_lock = threading.Lock()

        self.available_width = shutil.get_terminal_size()[0]

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.end()

    def line(self, template: str, **kwargs) -> 'Line':
        """
        Write a new line to the end of this session's stdout and return a Line
        instance allowing you to dynamically update the line later.

        The `template` string can use curly braces to define variables using
        the semantics of the `str.format` method, in which case the values
        should be given as keyword arguments. The point of passing values
        separately is that you will be able to update them individually when
        updating the line with `Line.update`.
        """
        with self.printing_lock:
            line_obj = Line(self, template, **kwargs)
            text = line_obj.text()
            nb_physical_lines = self._compute_nb_physical_lines(text)

            line_entry = _LineEntry(
                line_obj=line_obj,
                text=text,
                line_number=self.lines_counter - 1,
                nb_physical_lines=nb_physical_lines,
                next_line_entry=None,
            )
            self.lines_index[id(line_obj)] = line_entry
            if self.last_line_entry is not None:
                self.last_line_entry.next_line_entry = line_entry
            self.last_line_entry = line_entry

            # It seems that writing a line that is too big to fit into the
            # current available vertical space will make it shift upwards for
            # some reason. For this reason we "reserve" the vertical space
            # we're gonna need by printing some empty lines at the end.
            self._extend(nb_physical_lines - 1)
            self._print_at_line(text, line_entry.line_number)

        return line_obj

    def print_line(self, line_obj: 'Line') -> None:
        """
        Given a Line object assumed to be associated with the session, update
        stdout with the current text rendering of the Line.
        """
        with self.printing_lock:
            line_entry = self.lines_index[id(line_obj)]
            text = line_obj.text()
            line_entry.text = text

            old_nb_physical_lines = line_entry.nb_physical_lines
            new_nb_physical_lines = self._compute_nb_physical_lines(text)

            if old_nb_physical_lines < new_nb_physical_lines:
                size_diff = new_nb_physical_lines - old_nb_physical_lines
                self._extend(size_diff)

            self._print_at_line(text, line_entry.line_number)

            if old_nb_physical_lines != new_nb_physical_lines:
                line_entry.nb_physical_lines = new_nb_physical_lines

                # The new text has fewer or more physical lines than the existing
                # one, we must rewrite all the following lines which will be shifted
                # either up or down.
                current_line_entry = line_entry.next_line_entry
                current_line_number = line_entry.line_number + new_nb_physical_lines
                while current_line_entry is not None:
                    current_line_entry.line_number = current_line_number
                    self._print_at_line(
                        current_line_entry.text,
                        current_line_number,
                    )
                    current_line_number += current_line_entry.nb_physical_lines
                    current_line_entry = current_line_entry.next_line_entry

            if new_nb_physical_lines < old_nb_physical_lines:
                # Lines have been shifted up, this means that there is a
                # remnent of previous lines prints at the end of stdout, which
                # we need to clear up.
                self._truncate()

    def end(self) -> None:
        """
        Put the cursor at the end this session stdout.
        """
        self._set_cursor_to_line_number(self.lines_counter - 1)

    def _compute_nb_physical_lines(self, text: str) -> int:
        return max(1, math.ceil(len(text) / self.available_width))

    def _print_at_line(self, text: str, line_number: int) -> None:
        """
        Print `text` at the given physical `line_number`.
        """
        size = self._compute_nb_physical_lines(text)

        # Erase the current content of the physical lines, if any
        for position in range(line_number, line_number + size):
            self._set_cursor_to_line_number(position)
            print("\033[2K", end='')

        # Print the new content
        self._set_cursor_to_line_number(line_number)
        print(text)

        self.current_line = line_number + size
        self.lines_counter = max(self.lines_counter, self.current_line + 1)

    def _set_cursor_to_line_number(self, line_number: int):
        # ANSI Escape codes are used to move the cursor
        # (https://gist.github.com/fnky/458719343aabd01cfb17a3a4f7296797)
        diff = line_number - self.current_line
        if diff == 0:
            # Only go at the beginning of the current line
            print('\033[0G', end='')
        else:
            print(f"\033[{abs(diff)}{'E' if diff > 0 else 'F'}", end='')
        sys.stdout.flush()
        self.current_line = line_number

    def _extend(self, size):
        """
        Extend the number of lines of the current session by `size` lines, by
        printing enough empty lines at the end of what is already printed.
        """
        for line_number in range(
            self.lines_counter - 1, self.lines_counter + size
        ):
            self._print_at_line('', line_number)

    def _truncate(self):
        """
        Remove everything starting from the current cursor position, and restore
        the cursor to its position at the moment this method is called.
        """
        original_cursor_position = self.current_line
        size_truncation = self.lines_counter - self.current_line - 1
        for line_number in range(self.current_line, self.lines_counter - 1):
            self._print_at_line('', line_number)
        self._set_cursor_to_line_number(original_cursor_position)
        self.lines_counter -= size_truncation


class Line:

    """
    A handle over a line of text associated with a LineSession. Do not instanciate
    this class manually, use the `LinesSession.line` factory method.
    """

    def __init__(self, session: LinesSession, template: str, **kwargs):
        self.session = session
        self.template = template
        self.kwargs = kwargs

    def text(self) -> str:
        """
        Return the current text rendering of this line.
        """
        if not self.kwargs:
            return self.template
        return self.template.format(**self.kwargs)

    def update(self, template: Optional[str] = None, **kwargs) -> None:
        """
        Update the content of this line on stdout. The entire string can be
        changed by updating the `template`, or individual formatting values
        can be updated with keyword arguments.
        """
        if template is not None:
            self.template = template
            self.kwargs = {}
        self.kwargs.update(kwargs)
        self.session.print_line(self)


@dataclass
class _LineEntry:

    """
    Internal linked list of all the Line objects known by the session,
    additionally containing the physical properties of the line in the terminal
    (position, size, and the text itself).
    """
    line_obj: Line
    # On the LineEntry keeping its current text in spite of the text being available
    # through Line.text():
    # The current thread might need to rewrite lines to shift them up or down,
    # and if another thread, in the meantime, has the Line's components
    # updated, then the .text() method will return something different. This
    # can lead to nasty race conditions if not handled properly. It's just
    # simpler that any shifting will shift the current printed text.
    text: str
    line_number: int
    nb_physical_lines: int
    next_line_entry: Optional['_LineEntry']

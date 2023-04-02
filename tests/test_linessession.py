"""
This tests the printing primitives of LinesSession.

For higher level testing, just run `python examples.py` and see if it looks
good. We could run it in a subprocess and compare stdout to an expected
result, but that would be very flaky to implementation changes as the
resulting strings of ANSI escape codes have no guaranty of being "canonical"
for the behavior they achieve.
"""

import re

import pytest

import coca


def _sum_jumps(print_calls, ansi_codes_only=False):
    """
    From a list of mock calls to the print function, return the net result
    of cursor moves. A negative number means "up" and a positive one "down".
    """
    net = 0
    for _, args, kwargs in print_calls:
        text = args[0]

        if not ansi_codes_only:
            net += text.count('\n')
            net += kwargs.get('end', '\n').count('\n')

        if match := re.match('\033\[([0-9]+)(E|F)', text):
            diff, direction = match.groups()
            net += int(diff) * (-1 if direction == 'F' else 1)

    return net


def _text_index(print_calls, text):
    """
    From a list of mock calls to the print function, return the index of the
    given printed `text`, or None if no such text is found.
    """
    for i, (_, pos_args, _) in enumerate(print_calls):
        if pos_args[0] == text:
            return i
    return None


def _count_text(print_calls, text):
    """
    From a list of mock calls to the print function, return the number of times
    `text` has been printed.
    """
    count = 0
    for _, pos_args, _ in print_calls:
        if pos_args[0] == text:
            count += 1
    return count


@pytest.mark.parametrize('line_to_print_to, expected_net_jump', [
    (7, 0),
    (8, 1),
    (2, -5),
])
def test_print_at_line(mocker, line_to_print_to, expected_net_jump):
    session = coca.LinesSession()
    session.lines_counter = 10
    session.current_line = 7
    session.available_width = 80

    print_mock = mocker.patch('coca.print')

    session._print_at_line("hello world", line_to_print_to)

    print_calls = print_mock.mock_calls
    erased_code_index = _text_index(print_calls, '\033[2K')
    hello_index = _text_index(print_calls, "hello world")

    assert _sum_jumps(print_calls, ansi_codes_only=True) == expected_net_jump
    assert erased_code_index is not None
    assert hello_index is not None
    assert erased_code_index < hello_index

    assert session.current_line == line_to_print_to + 1
    assert session.lines_counter == 10


def test_print_multiple_lines_at_line(mocker):
    session = coca.LinesSession()
    session.lines_counter = 10
    session.current_line = 2
    session.available_width = 80

    mocker.patch('coca.print')

    session._print_at_line('a'*150, 2)

    assert session.lines_counter == 10
    assert session.current_line == 4


def test_truncate(mocker):
    session = coca.LinesSession()
    session.lines_counter = 10
    session.current_line = 7
    session.available_width = 80

    print_mock = mocker.patch('coca.print')

    session._truncate()

    print_calls = print_mock.mock_calls

    # We removed 2 lines (last line is always empty)
    assert _count_text(print_calls, '\033[2K') == 2
    # The cursor did not move
    assert _sum_jumps(print_calls) == 0

    assert session.current_line == 7
    assert session.lines_counter == 8

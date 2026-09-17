"""
The screen-reading half of scripts/tv_remote_test.py.

That script is what finally says whether the gate's remote works on real hardware, so it has
to be able to tell "a button is focused" from "nothing is focused" -- the second being the
original bug. A parser that never returns None would report PASS on a TV nobody can use,
which is worse than not testing at all.
"""

import pathlib
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

from tv_remote_test import focused_label, on_screen, texts  # noqa: E402


def dump(*nodes: str) -> ET.Element:
    return ET.fromstring(f"<hierarchy>{''.join(nodes)}</hierarchy>")


NODE_GATE = '<node text="Two switches to turn on" bounds="[0,0][100,40]"/>'
NODE_TURN_ON = '<node text="Turn on" focused="true" bounds="[600,100][760,160]"/>'
NODE_TURN_ON_BLUR = '<node text="Turn on" focused="false" bounds="[600,100][760,160]"/>'
NODE_CHANGE = '<node text="Change" focused="true" bounds="[600,200][760,260]"/>'


def test_reads_the_focused_button():
    assert focused_label(dump(NODE_GATE, NODE_TURN_ON, NODE_CHANGE.replace('"true"', '"false"'))) == "Turn on"


def test_nothing_focused_is_reported_as_nothing():
    # The bug itself. If this ever returns a label, the script reports a working remote on a
    # TV whose remote is dead.
    assert focused_label(dump(NODE_GATE, NODE_TURN_ON_BLUR)) is None


def test_unlabelled_focus_still_distinguishes_rows():
    # Compose puts focus on the clickable node, which may carry no text of its own; two rows
    # must still be told apart or "Down moved the highlight" cannot be checked.
    a = focused_label(dump('<node focused="true" bounds="[600,100][760,160]"/>'))
    b = focused_label(dump('<node focused="true" bounds="[600,200][760,260]"/>'))
    assert a is not None and b is not None and a != b


def test_finds_the_gate_and_the_pin_prompt():
    assert on_screen(dump(NODE_GATE), "Two switches to turn on")
    assert on_screen(dump('<node text="Maintenance access"/>'), "maintenance access")
    assert not on_screen(dump(NODE_GATE), "Maintenance access")


def test_texts_skips_empty_nodes():
    assert texts(dump(NODE_GATE, '<node text=""/>', NODE_TURN_ON)) == [
        "Two switches to turn on",
        "Turn on",
    ]

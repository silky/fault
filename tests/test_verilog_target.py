import tempfile
import magma as m
import fault
from bit_vector import BitVector
import common
import random
from fault.actions import Poke, Expect, Eval, Step, Print, Peek
from fault.random import random_bv
import copy
import os.path
import pytest


def pytest_generate_tests(metafunc):
    if "target" in metafunc.fixturenames:
        targets = [fault.verilator_target.VerilatorTarget]
        if os.getenv(TRAVIS, False):
            targets.append(fault.system_verilog_target.SystemVerilogTarget)
        metafunc.parametrize("target", targets)


def run(circ, actions, target, flags=[]):
    with tempfile.TemporaryDirectory() as tempdir:
        m.compile(f"{tempdir}/{circ.name}", circ,
                  output="coreir-verilog")
        if target == fault.verilator_target.VerilatorTarget:
            target = target(
                circ, directory=f"{tempdir}/",
                flags=flags, skip_compile=True)
        else:
            target = target(
                circ, directory=f"{tempdir}/",
                skip_compile=True)
        target.run(actions)


def test_target_basic(target):
    """
    Test basic workflow with a simple circuit.
    """
    circ = common.TestBasicCircuit
    actions = (Poke(circ.I, 0), Eval(), Expect(circ.O, 0))
    run(circ, actions, target)


def test_target_peek(target):
    circ = common.TestPeekCircuit
    actions = []
    for i in range(3):
        x = random_bv(3)
        actions.append(Poke(circ.I, x))
        actions.append(Eval())
        actions.append(Expect(circ.O0, Peek(circ.O1)))
    run(circ, actions, target)


def test_target_nested_arrays_by_element(target):
    circ = common.TestNestedArraysCircuit
    expected = [random.randint(0, (1 << 4) - 1) for i in range(3)]
    actions = []
    for i, val in enumerate(expected):
        actions.append(Poke(circ.I[i], val))
    actions.append(Eval())
    for i, val in enumerate(expected):
        actions.append(Expect(circ.O[i], val))
    run(circ, actions, target)


def test_target_nested_arrays_bulk(target):
    circ = common.TestNestedArraysCircuit
    expected = [random.randint(0, (1 << 4) - 1) for i in range(3)]
    actions = []
    actions.append(Poke(circ.I, expected))
    actions.append(Eval())
    actions.append(Expect(circ.O, expected))
    run(circ, actions, target)


def test_target_double_nested_arrays_bulk(target):
    circ = common.TestDoubleNestedArraysCircuit
    expected = [[random.randint(0, (1 << 4) - 1) for i in range(3)]
                for _ in range(2)]
    actions = []
    actions.append(Poke(circ.I, expected))
    actions.append(Eval())
    actions.append(Expect(circ.O, expected))
    run(circ, actions, target)


def test_target_clock(capfd, target):
    circ = common.TestBasicClkCircuit
    actions = [
        Poke(circ.I, 0),
        Print(circ.I),
        Expect(circ.O, 0),
        Poke(circ.CLK, 0),
        Print(circ.O),
        Step(circ.CLK, 1),
        Poke(circ.I, BitVector(1, 1)),
        Eval(),
        Print(circ.O),
    ]
    run(circ, actions, target, flags=["-Wno-lint"])
    out, err = capfd.readouterr()
    lines = out.splitlines()

    if target == fault.verilator_target.VerilatorTarget:
        assert lines[-3] == "BasicClkCircuit.I = 0", out
        assert lines[-2] == "BasicClkCircuit.O = 0", out
        assert lines[-1] == "BasicClkCircuit.O = 1", out
    else:
        assert lines[-6] == "BasicClkCircuit.I = 0", out
        assert lines[-5] == "BasicClkCircuit.O = 0", out
        assert lines[-4] == "BasicClkCircuit.O = 1", out


def test_print_nested_arrays(capfd, target):
    circ = common.TestNestedArraysCircuit
    actions = [
        Poke(circ.I, [BitVector(i, 4) for i in range(3)]),
        Print(circ.I),
        Eval(),
        Expect(circ.O, [BitVector(i, 4) for i in range(3)]),
        Print(circ.O),
        Poke(circ.I, [BitVector(4 - i, 4) for i in range(3)]),
        Eval(),
        Print(circ.O),
    ]
    run(circ, actions, target, flags=["-Wno-lint"])
    out, err = capfd.readouterr()
    if target == fault.verilator_target.VerilatorTarget:
        actual = "\n".join(out.splitlines()[-9:])
    else:
        actual = "\n".join(out.splitlines()[-9 - 3: -3])
    assert actual == """\
NestedArraysCircuit.I[0] = 0
NestedArraysCircuit.I[1] = 1
NestedArraysCircuit.I[2] = 2
NestedArraysCircuit.O[0] = 0
NestedArraysCircuit.O[1] = 1
NestedArraysCircuit.O[2] = 2
NestedArraysCircuit.O[0] = 4
NestedArraysCircuit.O[1] = 3
NestedArraysCircuit.O[2] = 2""", out


def test_print_double_nested_arrays(capfd, target):
    circ = common.TestDoubleNestedArraysCircuit
    actions = [
        Poke(circ.I, [[BitVector(i + j * 3, 4) for i in range(3)]
                      for j in range(2)]),
        Print(circ.I),
        Eval(),
        Expect(circ.O, [[BitVector(i + j * 3, 4) for i in range(3)]
                        for j in range(2)]),
        Print(circ.O),
        Poke(circ.I, [[BitVector(i + (j + 1) * 3, 4) for i in range(3)]
                      for j in range(2)]),
        Eval(),
        Print(circ.O),
    ]
    run(circ, actions, target, flags=["-Wno-lint"])
    out, err = capfd.readouterr()
    print(out)
    if target == fault.verilator_target.VerilatorTarget:
        actual = "\n".join(out.splitlines()[-18:])
    else:
        actual = "\n".join(out.splitlines()[-18 - 3: -3])
    assert actual == """\
DoubleNestedArraysCircuit.I[0][0] = 0
DoubleNestedArraysCircuit.I[0][1] = 1
DoubleNestedArraysCircuit.I[0][2] = 2
DoubleNestedArraysCircuit.I[1][0] = 3
DoubleNestedArraysCircuit.I[1][1] = 4
DoubleNestedArraysCircuit.I[1][2] = 5
DoubleNestedArraysCircuit.O[0][0] = 0
DoubleNestedArraysCircuit.O[0][1] = 1
DoubleNestedArraysCircuit.O[0][2] = 2
DoubleNestedArraysCircuit.O[1][0] = 3
DoubleNestedArraysCircuit.O[1][1] = 4
DoubleNestedArraysCircuit.O[1][2] = 5
DoubleNestedArraysCircuit.O[0][0] = 3
DoubleNestedArraysCircuit.O[0][1] = 4
DoubleNestedArraysCircuit.O[0][2] = 5
DoubleNestedArraysCircuit.O[1][0] = 6
DoubleNestedArraysCircuit.O[1][1] = 7
DoubleNestedArraysCircuit.O[1][2] = 8\
""", out


def test_target_tuple(target):
    circ = common.TestTupleCircuit
    actions = [
        Poke(circ.I.a, 5),
        Poke(circ.I.b, 11),
        Eval(),
        Expect(circ.O.a, 5),
        Expect(circ.O.b, 11),
    ]
    run(circ, actions, target)


# @pytest.mark.parametrize("width", range(1, 33))
# Select random subset of range to speed up test, TODO: Maybe actually make
# this random
@pytest.mark.parametrize("width", [1, 4, 5, 7, 8, 11, 13, 16, 19, 22, 24, 27,
                                   31, 32])
def test_target_sint_sign_extend(width, target):
    circ = common.define_simple_circuit(
        m.SInt(width), f"test_target_sint_sign_extend_{width}")
    actions = [
        Poke(circ.I, -2),
        Eval(),
        Expect(circ.O, -2),
    ]
    run(circ, actions, target)

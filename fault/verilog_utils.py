import magma as m


def verilog_name(name):
    if isinstance(name, m.ref.DefnRef):
        return str(name)
    if isinstance(name, m.ref.ArrayRef):
        array_name = verilog_name(name.array.name)
        if issubclass(name.array.T, m.Digital):
            return f"{array_name}[{name.index}]"
        return f"{array_name}_{name.index}"
    if isinstance(name, m.ref.TupleRef):
        tuple_name = verilog_name(name.tuple.name)
        index = name.index
        try:
            int(index)
            # python/coreir don't allow pure integer names
            index = f"_{index}"
        except ValueError:
            pass
        return f"{tuple_name}_{index}"
    raise NotImplementedError(name, type(name))


def verilator_name(name):
    if isinstance(name, m.ref.ArrayRef) and issubclass(name.array.T, m.Digital):
        # Setting a specific bit is done using bit twiddling, so we return the
        # full array see https://github.com/leonardt/fault/pull/194 for more
        # info
        name = verilog_name(name.array.name)
    else:
        name = verilog_name(name)
    # pg 21 of verilator 4.018 manual
    # To avoid conicts with Verilator's internal symbols, any double
    # underscore are replaced with ___05F (5F is the hex code of an underscore.)
    return name.replace("__", "___05F")

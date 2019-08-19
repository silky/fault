import os
from pathlib import Path
from .system_verilog_target import SystemVerilogTarget


class VerilogAMSTarget(SystemVerilogTarget):
    def __init__(self, circuit, simulator='ncsim', directory='build/',
                 model_paths=None, stop_time=1, vsup=1.0, rout=1, flags=None,
                 ext_srcs=None, use_spice=None, use_input_wires=True,
                 ext_model_file=True, bus_delim='<>', **kwargs):
        """
        simulator: Name of the simulator to be used for simulation.
        model_paths: paths to SPICE/Spectre files used in the simulation
        stop_time: simulation time passed to the analog solver.  must be
        longer than the mixed-signal simulation duration, or simulation will
        end before encountering $finish.
        vsup: supply voltage assumed for D/A and A/D conversions
        rout: output resistance assumed for D/A conversions
        flags: Additional flags to be passed to the simulator.  Certain
        additional flags will be tacked onto this before passing to the
        SystemVerilogTarget.
        ext_srcs: Additional source files to be compiled when building this
        simulation.
        use_spice: List of names of modules that should use a spice model
        rather than a verilog model.  Not always required, but sometimes
        needed when instantiating a spice module directly in SystemVerilog
        code.
        use_input_wires: If True, drive DUT inputs through wires that are
        in turn assigned to a reg.  This helps with proper discipline
        resolution for Verilog-AMS simulation.
        ext_model_file: If True, don't include the assumed model name in the
        list of Verilog sources.  The assumption is that the user has already
        taken care of this via ext_srcs.
        bus_delim: '<>', '[]', or '_' indicating bus styles "a<3>", "b[2]",
        c_1.
        """

        # save settings
        self.stop_time = stop_time
        self.vsup = vsup
        self.rout = rout
        self.use_spice = use_spice if use_spice is not None else []
        self.bus_delim = bus_delim

        # save file names that will be written
        self.amscf = 'amscf.scs'
        self.vamsf = f'{circuit.name}.vams'

        # update simulator argument
        assert simulator == 'ncsim', 'Only the ncsim simulator is allowed at this time.'  # noqa

        # update flags argument
        flags = flags if flags is not None else []
        model_paths = model_paths if model_paths is not None else []
        for path in model_paths:
            flags += ['-modelpath', f'{path}']

        # update ext_srcs
        ext_srcs = ext_srcs if ext_srcs is not None else []
        ext_srcs += [self.amscf]
        if hasattr(circuit, 'vams_code'):
            ext_srcs += [self.vamsf]

        # call the superconstructor
        super().__init__(circuit=circuit, simulator=simulator, flags=flags,
                         ext_srcs=ext_srcs, directory=directory,
                         use_input_wires=use_input_wires,
                         ext_model_file=ext_model_file, **kwargs)

    def run(self, *args, **kwargs):
        # write the AMS control file
        self.write_amscf()

        # write the VAMS wrapper (if needed)
        if hasattr(self.circuit, 'vams_code'):
            self.write_vamsf()

        # then call the super constructor
        super().run(*args, **kwargs)

    def gen_amscf(self, tab='    ', nl='\n'):
        # specify which modules instantiated in SystemVerilog code
        # should use SPICE models
        amsd_lines = ''
        for model in self.use_spice:
            amsd_lines += f'{tab}config cell={model} use=spice{nl}'
            amsd_lines += f'{tab}portmap subckt={model} autobus=yes busdelim="{self.bus_delim}"{nl}'  # noqa

        # return text content of the AMS control file
        return f'''
tranSweep tran stop={self.stop_time}s
amsd {{
    ie vsup={self.vsup} rout={self.rout}
{amsd_lines}
}}'''

    def write_amscf(self):
        with open(self.directory / Path(self.amscf), 'w') as f:
            f.write(self.gen_amscf())

    def write_vamsf(self):
        with open(self.directory / Path(self.vamsf), 'w') as f:
            f.write(self.circuit.vams_code)

# General imports
from pathlib import Path
import os
import sys

# cocotb imports
import cocotb
from cocotb.triggers import ClockCycles, Edge, FallingEdge, ReadOnly, RisingEdge
from cocotb.runner import get_runner
from cocotb.clock import Clock
from cocotb_bus.drivers import BusDriver
from cocotb_bus.monitors import BusMonitor
import numpy as np

SAMPLES_TO_TEST = 10000


async def reset(clk, reset_wire, num_cycles, active_val):
    reset_wire.value = active_val
    await ClockCycles(clk, num_cycles)
    reset_wire.value = 1 - active_val


class DUTMonitor(BusMonitor):
    """
    monitors axi streaming bus
    """

    def __init__(self, dut, name, clk, callback=None):
        self._signals = ["mag_sq_out", "mag_sq_valid_out"]
        BusMonitor.__init__(self, dut, name, clk, callback=callback)
        self.clock = clk
        self.transactions = 0
        self.mag_sq_out = []

    async def _monitor_recv(self):
        """
        Monitor receiver
        """
        falling_edge = FallingEdge(self.clock)
        read_only = ReadOnly()
        while True:
            await falling_edge
            await read_only  # readonly (the postline)
            self.transactions += 1
            valid = self.bus.mag_sq_valid_out.value
            mag_sq = self.bus.mag_sq_out.value
            if valid:
                self.mag_sq_out.append(mag_sq)
                self._recv((mag_sq))


class DUTDriver(BusDriver):
    def __init__(self, dut, name, clk):
        self._signals = ["i_in", "q_in", "iq_valid_in"]
        BusDriver.__init__(self, dut, name, clk)
        self.clock = clk
        self.bus.i_in.value = 0
        self.bus.q_in.value = 0
        self.bus.iq_valid_in.value = 0

    async def _driver_send(self, values, sync=True):
        for value in values:
            await RisingEdge(self.clock)
            self.bus.i_in.value = int(value[0])
            self.bus.q_in.value = int(value[1])
            self.bus.iq_valid_in.value = 1
        await RisingEdge(self.clock)
        self.bus.iq_valid_in.value = 0


@cocotb.test
async def test_complex_to_mag_sq(dut):
    """
    Ensures that the complex_to_mag_sq module is working correctly.
    """
    ind = DUTDriver(dut, "", dut.clk_in)
    outm = DUTMonitor(dut, "", dut.clk_in)
    # Setup the module
    cocotb.start_soon(Clock(dut.clk_in, 10, units="ns").start())
    await reset(dut.clk_in, dut.rst_in, 2, 1)
    # Generate random pairs of I and Q values
    iq_values = np.random.randint(-(2**15), 2**15, (SAMPLES_TO_TEST, 2))
    squared_mags = np.sum(iq_values**2, axis=1)
    # Send the I and Q values to the module
    ind.append(iq_values)
    # Wait for the module to process the data
    await ClockCycles(dut.clk_in, 100)
    # Check the output
    differences = [
        x for x in zip(outm.mag_sq_out, squared_mags.tolist()) if x[0] != x[1]
    ]
    assert not differences, f"{len(differences)} differences found: {differences}"


def complex_to_mag_sq_runner():
    """Simulate the downsampler using the Python runner."""
    sim = os.getenv("SIM", "icarus")
    proj_path = Path(__file__).resolve().parent.parent
    sys.path.append(str(proj_path / "sim" / "model"))
    sources = [
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/complex_to_mag_sq.sv",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/complex_multiply.sv",
    ]
    build_test_args = ["-Wall"]  # ,"COCOTB_RESOLVE_X=ZEROS"]
    parameters = {}
    sys.path.append(str(proj_path / "sim"))
    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="complex_to_mag_sq",
        always=True,
        build_args=build_test_args,
        parameters=parameters,
        timescale=("1ns", "1ps"),
        waves=True,
    )
    run_test_args = []
    runner.test(
        hdl_toplevel="complex_to_mag_sq",
        test_module="test_complex_to_mag_sq",
        test_args=run_test_args,
        waves=True,
    )


if __name__ == "__main__":
    complex_to_mag_sq_runner()

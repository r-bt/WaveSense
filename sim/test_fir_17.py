# General imports
import os
import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import random

# cocotb imports
import cocotb
from cocotb.triggers import ClockCycles, Edge, FallingEdge, ReadOnly
from cocotb.runner import get_runner
from cocotb.clock import Clock
from cocotb_bus.drivers import BusDriver
from cocotb_bus.monitors import BusMonitor


class AXISMonitor(BusMonitor):
    """
    monitors axi streaming bus
    """

    def __init__(self, dut, name, clk, callback=None):
        self._signals = ["axis_data_tvalid", "axis_data_tready", "axis_data_tdata"]
        BusMonitor.__init__(self, dut, name, clk, callback=callback)
        self.clock = clk
        self.transactions = 0
        self.data = []

    async def _monitor_recv(self):
        """
        Monitor receiver
        """
        falling_edge = FallingEdge(self.clock)
        read_only = ReadOnly()
        while True:
            await falling_edge
            await read_only  # readonly (the postline)
            valid = self.bus.axis_data_tvalid.value
            ready = self.bus.axis_data_tready.value
            data = self.bus.axis_data_tdata.value
            if valid and ready:
                self.transactions += 1
                self.data.append(data.signed_integer)
                self._recv(data)


class AXISDriver(BusDriver):
    def __init__(self, dut, name, clk):
        self._signals = ["axis_data_tvalid", "axis_data_tready", "axis_data_tdata"]
        BusDriver.__init__(self, dut, name, clk)
        self.clock = clk
        self.bus.axis_data_tdata.value = 0
        self.bus.axis_data_tvalid.value = 0

    async def _driver_send(self, value, sync=True):
        if value["type"] == "single":
            await FallingEdge(self.clock)
            self.bus.axis_data_tdata.value = value["contents"]["data"]
            self.bus.axis_data_tvalid.value = 1
            await ReadOnly()
            while not self.bus.axis_data_tready.value:
                await Edge(self.clock)
                await ReadOnly()
        else:
            for val in value["contents"]["data"]:
                await FallingEdge(self.clock)
                self.bus.axis_data_tdata.value = int(val)
                self.bus.axis_data_tvalid.value = 1
                await ReadOnly()
                while not self.bus.axis_data_tready.value:
                    await Edge(self.clock)
                    await ReadOnly()
        await FallingEdge(self.clock)
        self.bus.axis_data_tvalid.value = 0


async def set_ready(dut, ready_val):
    await FallingEdge(dut.aclk)
    dut.m_axis_data_tready.value = ready_val


async def reset(clk, reset_wire, num_cycles, active_val):
    reset_wire.value = active_val
    await ClockCycles(clk, num_cycles)
    reset_wire.value = 1 - active_val


@cocotb.test
async def test_with_generated_data(dut):
    """
    Generates a sine wave with high and low frequencies and sends it to the DUT.
    """
    # Initialize the monitors
    inm = AXISMonitor(dut, "s", dut.aclk)
    outm = AXISMonitor(dut, "m", dut.aclk)
    ind = AXISDriver(dut, "s", dut.aclk)
    # Setup the DUT
    cocotb.start_soon(Clock(dut.aclk, 10, units="ns").start())
    await set_ready(dut, 1)
    await reset(dut.aclk, dut.aresetn, 2, 0)
    # Generate the data
    fs = 100e6
    f0 = 15e6
    f1 = 7e6
    n_samples = 128
    t = np.arange(n_samples) / fs
    wave = np.sin(2 * np.pi * f0 * t) + np.sin(2 * np.pi * f1 * t)
    # Scale to be 16 bit
    wave = (2**8 - 1) * wave
    # Send the data to the filter
    ind.append({"type": "burst", "contents": {"data": wave}})
    # Wait for the data to be processed
    await ClockCycles(dut.aclk, 1000)
    # Plot the output
    ax, fig = plt.subplots(ncols=1, nrows=2)
    fig[0].plot(wave)
    fig[1].plot(outm.data)
    plt.show()


@cocotb.test
async def test_with_sample_data(dut):
    """
    Extends the sample data
    """
    # Initialize the monitors
    inm = AXISMonitor(dut, "s", dut.aclk)
    outm = AXISMonitor(dut, "m", dut.aclk)
    ind = AXISDriver(dut, "s", dut.aclk)
    # Setup the DUT
    cocotb.start_soon(Clock(dut.aclk, 10, units="ns").start())
    await set_ready(dut, 1)
    await reset(dut.aclk, dut.aresetn, 2, 0)
    # Load the lts data
    cwd = os.path.dirname(os.path.abspath(__file__))
    samples_path = os.path.join(cwd, "samples.dat")
    signal = np.fromfile(samples_path, dtype=np.int16)[:1000]
    real_data = signal[::2]
    # Extend each element 10 times
    wave = np.repeat(real_data, 10)
    # Send the data to the filter
    ind.append({"type": "burst", "contents": {"data": wave}})
    # Wait for the data to be processed
    await ClockCycles(dut.aclk, 5000)
    # # Plot the output
    ax, fig = plt.subplots(ncols=1, nrows=4)
    fig[0].plot(real_data)
    fig[1].plot(wave)
    fig[2].plot(outm.data)
    fig[3].plot(outm.data[::10])
    plt.show()


def sync_short_runner():
    """Simulate the downsampler using the Python runner."""
    sim = os.getenv("SIM", "icarus")
    proj_path = Path(__file__).resolve().parent.parent
    sys.path.append(str(proj_path / "sim" / "model"))
    sources = [
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/fir_17.sv",
    ]
    build_test_args = ["-Wall"]  # ,"COCOTB_RESOLVE_X=ZEROS"]
    parameters = {"C_S_AXIS_TDATA_WIDTH": 32, "C_M_AXIS_TDATA_WIDTH": 32}
    sys.path.append(str(proj_path / "sim"))
    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="fir_17",
        always=True,
        build_args=build_test_args,
        parameters=parameters,
        timescale=("1ns", "1ps"),
        waves=True,
    )
    run_test_args = []
    runner.test(
        hdl_toplevel="fir_17",
        test_module="test_fir_17",
        test_args=run_test_args,
        waves=True,
    )


if __name__ == "__main__":
    sync_short_runner()

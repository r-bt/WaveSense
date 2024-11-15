# General imports
import os
import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

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
        self._signals = ['axis_tvalid', 'axis_tready',
                         'i_axis_tdata', 'q_axis_tdata']
        BusMonitor.__init__(self, dut, name, clk, callback=callback)
        self.clock = clk
        self.transactions = 0
        self.data_i = []
        self.data_q = []

    async def _monitor_recv(self):
        """
        Monitor receiver
        """
        falling_edge = FallingEdge(self.clock)
        read_only = ReadOnly()
        while True:
            await falling_edge
            await read_only  # readonly (the postline)
            valid = self.bus.axis_tvalid.value
            ready = self.bus.axis_tready.value
            i = self.bus.i_axis_tdata.value
            q = self.bus.q_axis_tdata.value
            if valid and ready:
                self.transactions += 1
                if int(i) > 2**31:
                    self.data_i.append(i - 2**32)
                else:
                    self.data_i.append(int(i))
                if int(q) > 2**31:
                    self.data_q.append(q - 2**32)
                else:
                    self.data_q.append(int(q))
                self._recv((i, q))


class AXISDriver(BusDriver):
    def __init__(self, dut, name, clk):
        self._signals = ['axis_tvalid', 'axis_tready',
                         'i_axis_tdata', 'q_axis_tdata']
        BusDriver.__init__(self, dut, name, clk)
        self.clock = clk
        self.bus.i_axis_tdata.value = 0
        self.bus.q_axis_tdata.value = 0
        self.bus.axis_tvalid.value = 0

    async def _driver_send(self, value, sync=True):
        if value['type'] == 'single':
            await FallingEdge(self.clock)
            self.bus.i_axis_tdata.value, self.bus.q_axis_tdata.value = value['contents']['data']
            self.bus.axis_tvalid.value = 1
            await ReadOnly()
            while not self.bus.axis_tready.value:
                await Edge(self.clock)
                await ReadOnly()
        else:
            for i, q in value['contents']['data']:
                await FallingEdge(self.clock)
                self.bus.i_axis_tdata.value = int(i)
                self.bus.q_axis_tdata.value = int(q)
                self.bus.axis_tvalid.value = 1
                await ReadOnly()
                while not self.bus.axis_tready.value:
                    await Edge(self.clock)
                    await ReadOnly()
        await FallingEdge(self.clock)
        self.bus.axis_tvalid.value = 0


async def set_ready(dut, ready_val):
    await FallingEdge(dut.clk_in)
    dut.xcorr_axis_tready.value = ready_val


async def reset(clk, reset_wire, num_cycles, active_val):
    reset_wire.value = active_val
    await ClockCycles(clk, num_cycles)
    reset_wire.value = 1 - active_val


@cocotb.test()
async def test_lts_xcorr(dut):
    inm = AXISMonitor(dut, 'signal', dut.clk_in)
    outm = AXISMonitor(dut, 'xcorr', dut.clk_in)
    ind = AXISDriver(dut, 'signal', dut.clk_in)
    # Setup the DUT
    cocotb.start_soon(Clock(dut.clk_in, 10, units="ns").start())
    await set_ready(dut, 1)
    await reset(dut.clk_in, dut.rst_in, 2, 1)
    # Feed in some real data
    cwd = os.path.dirname(os.path.abspath(__file__))
    samples_path = os.path.join(cwd, "samples.dat")
    signal = np.fromfile(samples_path, dtype=np.int16)[:1000]
    i = signal[::2]
    q = signal[1::2]
    # Drive the DUT
    await ClockCycles(dut.clk_in, 1)
    ind.append({'type': 'burst', 'contents': {'data': zip(i, q)}})
    # Test back-pressure
    await ClockCycles(dut.clk_in, 200)
    await set_ready(dut, 0)
    await ClockCycles(dut.clk_in, 100)
    await set_ready(dut, 1)
    await ClockCycles(dut.clk_in, 15)
    await set_ready(dut, 0)
    await ClockCycles(dut.clk_in, 49)
    await set_ready(dut, 1)
    await ClockCycles(dut.clk_in, 300)
    # Check that the data is what we expect
    assert inm.transactions == 500, 'Sent the wrong number of samples!'
    assert outm.transactions == 469, 'Received the wrong number of samples!'
    # Check that xcorr worked
    xcorr_mag = np.abs(np.array(outm.data_i) + 1j * np.array(outm.data_q))
    # plt.plot(xcorr_mag, '-o')
    # plt.show()
    peak1, peak2 = np.argpartition(xcorr_mag, -2)[-2:]
    assert 63 <= abs(peak1 - peak2) <= 65, 'Peaks are not 64 samples apart!'


def lts_xcorr_runner():
    """Simulate the LTS cross-correlater using the Python runner."""
    sim = os.getenv("SIM", "icarus")
    proj_path = Path(__file__).resolve().parent.parent
    sys.path.append(str(proj_path / "sim" / "model"))
    sources = [
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/lts_xcorr.sv",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/complex_multiply.sv"
    ]
    build_test_args = ["-Wall"]  # ,"COCOTB_RESOLVE_X=ZEROS"]
    parameters = {}
    sys.path.append(str(proj_path / "sim"))
    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="lts_xcorr",
        always=True,
        build_args=build_test_args,
        parameters=parameters,
        timescale=("1ns", "1ps"),
        waves=True,
    )
    run_test_args = []
    runner.test(
        hdl_toplevel="lts_xcorr",
        test_module="test_lts_xcorr",
        test_args=run_test_args,
        waves=True,
    )


if __name__ == "__main__":
    lts_xcorr_runner()

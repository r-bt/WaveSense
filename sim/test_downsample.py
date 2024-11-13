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
        self._signals = ['axis_tvalid', 'axis_tready', 'axis_tdata']
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
            valid = self.bus.axis_tvalid.value
            ready = self.bus.axis_tready.value
            data = self.bus.axis_tdata.value
            if valid and ready:
                self.transactions += 1
                if int(data) > 2**31:
                    self.data.append(data - 2**32)
                else:
                    self.data.append(int(data))
                self._recv(data)


class AXISDriver(BusDriver):
    def __init__(self, dut, name, clk):
        self._signals = ['axis_tvalid', 'axis_tready', 'axis_tdata']
        BusDriver.__init__(self, dut, name, clk)
        self.clock = clk
        self.bus.axis_tdata.value = 0
        self.bus.axis_tvalid.value = 0

    async def _driver_send(self, value, sync=True):
        if value['type'] == 'single':
            await FallingEdge(self.clock)
            self.bus.axis_tdata.value = value['contents']['data']
            self.bus.axis_tvalid.value = 1
            await ReadOnly()
            while not self.bus.axis_tready.value:
                await Edge(self.clock)
                await ReadOnly()
        else:
            for val in value['contents']['data']:
                await FallingEdge(self.clock)
                self.bus.axis_tdata.value = int(val)
                self.bus.axis_tvalid.value = 1
                await ReadOnly()
                while not self.bus.axis_tready.value:
                    await Edge(self.clock)
                    await ReadOnly()
        await FallingEdge(self.clock)
        self.bus.axis_tvalid.value = 0


async def set_ready(dut, ready_val):
    await FallingEdge(dut.s00_axis_aclk)
    dut.m00_axis_tready.value = ready_val


async def reset(clk, reset_wire, num_cycles, active_val):
    reset_wire.value = active_val
    await ClockCycles(clk, num_cycles)
    reset_wire.value = 1 - active_val


@cocotb.test()
async def test_downsample_sinusoid(dut):
    inm = AXISMonitor(dut, 's00', dut.s00_axis_aclk)
    outm = AXISMonitor(dut, 'm00', dut.s00_axis_aclk)
    ind = AXISDriver(dut, 's00', dut.s00_axis_aclk)
    # Setup the DUT
    cocotb.start_soon(Clock(dut.s00_axis_aclk, 10, units="ns").start())
    await set_ready(dut, 1)
    await reset(dut.s00_axis_aclk, dut.s00_axis_aresetn, 2, 0)
    # Generate the data
    f_in = 122.88
    f_out = 20
    n_samples = 10000
    filter_len = 17
    data_in = (2**16 * (np.sin(np.arange(n_samples) * np.pi / f_in)
                        - np.sin(np.arange(n_samples) * 3 * np.pi / f_in) / 9
                        + np.sin(np.arange(n_samples) * 4 * np.pi / f_in) / 25
                        + np.sin(np.arange(n_samples) * 41 * np.pi / f_in)
                        + np.sin(np.arange(n_samples) * 39 * np.pi / f_in))).astype(int)
    # Drive the DUT
    await ClockCycles(dut.s00_axis_aclk, 1)
    ind.append({'type': 'burst', 'contents': {'data': data_in}})
    # Flush the FIR filter
    ind.append({'type': 'burst', 'contents': {'data': np.zeros(filter_len)}})
    # Test back-pressure
    await ClockCycles(dut.s00_axis_aclk, n_samples // 3)
    await set_ready(dut, 0)
    await ClockCycles(dut.s00_axis_aclk, 100)
    await set_ready(dut, 1)
    await ClockCycles(dut.s00_axis_aclk, 15)
    await set_ready(dut, 0)
    await ClockCycles(dut.s00_axis_aclk, 49)
    await set_ready(dut, 1)
    await ClockCycles(dut.s00_axis_aclk, 2 * n_samples // 3 + 50)
    # Check that the data is what we expect
    assert inm.transactions == n_samples + \
        filter_len, 'Sent the wrong number of samples!'
    assert outm.transactions == int(
        n_samples * f_out / f_in), 'Received the wrong number of samples!'
    # Check that downsampling worked
    fft_in = np.abs(np.fft.rfft(inm.data)) / inm.transactions / 2 / np.pi
    fft_out = np.abs(np.fft.rfft(outm.data)) / outm.transactions / 2 / np.pi
    # plt.plot(fft_in)
    # plt.plot(fft_out / 150)
    # plt.show()
    assert np.isclose(fft_in[:len(fft_out)], fft_out / 150,
                      atol=200, rtol=0.2).all(), 'FFT does not match!'


def downsample_runner():
    """Simulate the downsampler using the Python runner."""
    sim = os.getenv("SIM", "icarus")
    proj_path = Path(__file__).resolve().parent.parent
    sys.path.append(str(proj_path / "sim" / "model"))
    sources = [
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/downsample.sv",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/fir_17.sv"
    ]
    build_test_args = ["-Wall"]  # ,"COCOTB_RESOLVE_X=ZEROS"]
    parameters = {
        'SAMPLE_RATE_IN': 122880,
        'SAMPLE_RATE_OUT': 20000
    }
    sys.path.append(str(proj_path / "sim"))
    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="downsample",
        always=True,
        build_args=build_test_args,
        parameters=parameters,
        timescale=("1ns", "1ps"),
        waves=True,
    )
    run_test_args = []
    runner.test(
        hdl_toplevel="downsample",
        test_module="test_downsample",
        test_args=run_test_args,
        waves=True,
    )


if __name__ == "__main__":
    downsample_runner()

# General imports
import os
import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

from fft_helpers import generate_sample_data, plot_results

# cocotb imports
import cocotb
from cocotb.triggers import ClockCycles, Edge, FallingEdge, ReadOnly, RisingEdge
from cocotb.runner import get_runner
from cocotb.clock import Clock
from cocotb_bus.drivers import BusDriver
from cocotb_bus.monitors import BusMonitor


class AXISMonitor(BusMonitor):
    """
    monitors axi streaming bus
    """

    def __init__(self, dut, name, clk, callback=None):
        self._signals = [
            "axis_tlast",
            "axis_tvalid",
            "axis_tready",
            "re_axis_tdata",
            "im_axis_tdata",
        ]
        BusMonitor.__init__(self, dut, name, clk, callback=callback)
        self.clock = clk
        self.transactions = 0
        self.data = [[]]

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
            last = self.bus.axis_tlast.value
            re_data = self.bus.re_axis_tdata.value
            im_data = self.bus.im_axis_tdata.value
            if valid and ready:
                self.data[-1].append((re_data.integer, im_data.integer))
                self._recv((re_data, im_data))

                if last:
                    self.transactions += 1
                    self.data.append([])


class AXISDriver(BusDriver):
    def __init__(self, dut, name, clk):
        self._signals = [
            "axis_tlast",
            "axis_tvalid",
            "axis_tready",
            "re_axis_tdata",
            "im_axis_tdata",
        ]
        BusDriver.__init__(self, dut, name, clk)
        self.clock = clk
        self.bus.re_axis_tdata.value = 0
        self.bus.im_axis_tdata.value = 0
        self.bus.axis_tvalid.value = 0

    async def _driver_send(self, value, sync=True):
        if value["type"] == "single":
            await FallingEdge(self.clock)
            self.bus.re_axis_tdata.value = int(value["contents"]["data"]) >> 16
            self.bus.im_axis_tdata.value = int(value["contents"]["data"]) & 0xFFFF
            self.bus.axis_tvalid.value = 1
            await ReadOnly()
            while not self.bus.axis_tready.value:
                await Edge(self.clock)
                await ReadOnly()
        else:
            sent = 0
            for val in value["contents"]["data"]:
                sent += 1
                await FallingEdge(self.clock)
                self.bus.re_axis_tdata.value = int(val) >> 16
                self.bus.im_axis_tdata.value = int(val) & 0xFFFF
                self.bus.axis_tvalid.value = 1
                self.bus.axis_tlast.value = sent == 64
                await RisingEdge(self.clock)
                await ReadOnly()
                while not self.bus.axis_tready.value:
                    await RisingEdge(self.clock)
                    await ReadOnly()
                if sent == 64:
                    sent = 0
        await FallingEdge(self.clock)
        self.bus.axis_tlast.value = 0
        self.bus.axis_tvalid.value = 0


async def set_ready(dut, ready_val):
    await FallingEdge(dut.clk_in)
    dut.fft_axis_tready.value = ready_val


async def reset(clk, reset_wire, num_cycles, active_val):
    reset_wire.value = active_val
    await ClockCycles(clk, num_cycles)
    reset_wire.value = 1 - active_val


@cocotb.test()
async def test_lot_of_data(dut):
    """
    Send the same sequence 10 times and make sure the output is the same despite randomly applying back pressure.
    """
    # Setup some parameters
    n_samples = 64
    fs = 200
    f0 = 60
    f1 = 45
    transactions = 100
    # Setup monitors and driver
    inm = AXISMonitor(dut, "sample", dut.clk_in)
    outm = AXISMonitor(dut, "fft", dut.clk_in)
    ind = AXISDriver(dut, "sample", dut.clk_in)
    # Setup the DUT
    cocotb.start_soon(Clock(dut.clk_in, 10, units="ns").start())
    await reset(dut.clk_in, dut.rst_in, 2, 1)
    await set_ready(dut, 1)
    # Generate some freq data
    waveform = generate_sample_data(fs, f0, f1, n_samples)
    # Pass the samples to the DUT
    ind.append({"type": "burst", "contents": {"data": np.tile(waveform, transactions)}})
    # Apply back pressure randomly while sending in the data
    while outm.transactions != (transactions - 3):
        await set_ready(dut, np.random.randint(2))
    plot_results(outm.data[0], n_samples, fs)


def axis_fft_runner():
    """Simulate the downsampler using the Python runner."""
    sim = os.getenv("SIM", "icarus")
    proj_path = Path(__file__).resolve().parent.parent
    sys.path.append(str(proj_path / "sim" / "model"))
    sources = [
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/axis_fft.sv",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/bram_fifo.sv",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/pipeline.sv",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/src/fft-core/fftmain.v",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/src/fft-core/bimpy.v",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/src/fft-core/bitreverse.v",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/src/fft-core/butterfly.v",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/src/fft-core/convround.v",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/src/fft-core/fftstage.v",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/src/fft-core/hwbfly.v",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/src/fft-core/laststage.v",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/src/fft-core/longbimpy.v",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/src/fft-core/qtrstage.v",
    ]
    build_test_args = ["-Wall"]  # ,"COCOTB_RESOLVE_X=ZEROS"]
    parameters = {}
    sys.path.append(str(proj_path / "sim"))
    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="axis_fft",
        always=True,
        build_args=build_test_args,
        parameters=parameters,
        timescale=("1ns", "1ps"),
        waves=True,
    )
    run_test_args = []
    runner.test(
        hdl_toplevel="axis_fft",
        test_module="test_axis_fft",
        test_args=run_test_args,
        waves=True,
    )


if __name__ == "__main__":
    axis_fft_runner()

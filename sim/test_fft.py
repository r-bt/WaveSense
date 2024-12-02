# General imports
import os
import sys
from pathlib import Path
from matplotlib import pyplot as plt
import numpy as np
import pdb

from fft_helpers import generate_sample_data, plot_results, plot_waveform

# cocotb imports
import cocotb
from cocotb.triggers import ClockCycles, Edge, FallingEdge, ReadOnly, RisingEdge
from cocotb.runner import get_runner
from cocotb.clock import Clock
from cocotb_bus.drivers import BusDriver
from cocotb_bus.monitors import BusMonitor


class FFTMonitor(BusMonitor):
    """
    monitors axi streaming bus
    """

    def __init__(self, dut, clk, count, callback=None):
        self._signals = ["o_result", "o_sync"]
        BusMonitor.__init__(self, dut, None, clk, callback=callback)
        self.clock = clk
        self.count = count
        self.to_collect = count
        self.values = []

    async def _monitor_recv(self):
        """
        Monitor receiver
        """
        falling_edge = FallingEdge(self.clock)
        read_only = ReadOnly()
        while True:
            await falling_edge
            await read_only  # readonly (the postline)
            if self.bus.o_sync.value:
                self.values.append([])
                self.count = 0

            if self.count != self.to_collect:
                self.count += 1
                self.values[-1].append(self.bus.o_result.value)


class FFTDriver(BusDriver):
    def __init__(self, dut, clk):
        self._signals = ["i_ce", "i_sample"]
        BusDriver.__init__(self, dut, None, clk)
        self.clock = clk
        self.bus.i_ce.value = 0
        self.bus.i_sample.value = 0

    async def _driver_send(self, values, sync=True):
        for value in values:
            await RisingEdge(self.clock)
            self.bus.i_sample.value = int(value)
            self.bus.i_ce.value = 1
        await RisingEdge(self.clock)
        self.bus.i_sample.value = 0
        # self.bus.i_ce.value = 0


@cocotb.test
async def test_with_mock_data(dut):
    """
    Sends a mock waveform to the FFT module and compares to FFT from python
    """
    # Setup some parameters
    n_samples = 64
    fs = 200
    f0 = 60
    f1 = 45
    # # Setup the monitors and drivers
    inm = FFTMonitor(dut, dut.i_clk, n_samples)
    ind = FFTDriver(dut, dut.i_clk)
    # Start the clock
    cocotb.start_soon(Clock(dut.i_clk, 10, units="ns").start())
    # # Reset the module
    dut.i_reset.value = 1
    await ClockCycles(dut.i_clk, 5)
    dut.i_reset.value = 0
    # Generate some freq data
    waveform = generate_sample_data(fs, f0, f1, n_samples)
    plot_waveform(waveform, n_samples, fs)
    # Pass the samples to the DUT
    ind.append(waveform)
    # Wait some clock cycles
    await ClockCycles(dut.i_clk, 10000)
    # Show the first collection of fft bins
    vals = [
        (value.integer >> 16 & 0xFFFF, value.integer & 0xFFFF)
        for value in inm.values[0]
    ]
    plot_results(vals, n_samples, fs)
    print(inm.values[0])


def sync_short_runner():
    """Simulate the ZipCPU FFT module"""
    sim = os.getenv("SIM", "icarus")
    proj_path = Path(__file__).resolve().parent.parent
    sys.path.append(str(proj_path / "sim" / "model"))
    sources = [
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
        hdl_toplevel="fftmain",
        always=True,
        build_args=build_test_args,
        parameters=parameters,
        timescale=("1ns", "1ps"),
        waves=True,
    )
    run_test_args = []
    runner.test(
        hdl_toplevel="fftmain",
        test_module="test_fft",
        test_args=run_test_args,
        waves=True,
    )


if __name__ == "__main__":
    sync_short_runner()

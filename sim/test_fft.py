# General imports
import os
import sys
from pathlib import Path
from matplotlib import pyplot as plt
import numpy as np
import pdb

# cocotb imports
import cocotb
from cocotb.triggers import ClockCycles, Edge, FallingEdge, ReadOnly, RisingEdge
from cocotb.runner import get_runner
from cocotb.clock import Clock
from cocotb_bus.drivers import BusDriver
from cocotb_bus.monitors import BusMonitor


def get_results_fft(values):
    magnitudes = []

    # Extract real and imaginary parts
    for value in values:
        real_part = (value.integer >> 16) & 0xFFFF
        imag_part = value.integer & 0xFFFF

        if real_part > 2**15:
            real_part -= 2**16
        if imag_part > 2**15:
            imag_part -= 2**16

        real_part = np.int32(real_part)
        imag_part = np.int32(imag_part)

        magnitudes.append(np.sqrt(real_part**2 + imag_part**2))

    return magnitudes


def plot_results(values, num_samples, fs):

    magnitudes = get_results_fft(values)

    freqs = np.fft.fftfreq(num_samples, 1 / fs)

    # Plot the FFT
    plt.figure(figsize=(10, 6))
    plt.plot(
        freqs[: num_samples // 2],
        magnitudes[: num_samples // 2],
        label="FFT",
        color="b",
    )
    plt.title("FFT of the Signal")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Magnitude")
    plt.legend()
    plt.grid(True)
    plt.show()


def plot_waveform(complex_samples, num_samples, fs):
    # Extract real part
    real_part = (complex_samples >> 16) & 0xFFFF  # Shift and mask to get the real part
    real_part = np.int16(real_part)

    # Plot the real part (time domain)
    plt.figure(figsize=(10, 6))
    plt.subplot(2, 1, 1)
    plt.plot(real_part, label="Wave", color="b", alpha=0.7)
    plt.title("Generated Sine Wave - Time Domain")
    plt.xlabel("Sample Index")
    plt.ylabel("Amplitude")
    plt.legend()
    plt.grid(True)

    # Compute the FFT of the real part (frequency domain)
    fft_result = np.fft.fft(real_part)
    fft_freq = np.fft.fftfreq(num_samples, 1 / fs)

    # Plot the magnitude of the FFT (frequency domain)
    plt.subplot(2, 1, 2)
    plt.plot(
        fft_freq[: num_samples // 2],
        np.abs(fft_result)[: num_samples // 2],
        label="FFT",
        color="r",
    )
    plt.title("FFT of the Signal - Frequency Domain")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Magnitude")
    plt.legend()
    plt.grid(True)

    # Show the plots
    plt.tight_layout()
    plt.show()


def generate_sample_data(fs: int, f0: int, f1: int, num_samples: int):
    """
    Generate complex waveform data for FFT: the first 16 bits for the real part,
    the second 16 bits for the imaginary part, each represented as a 32-bit complex number.
    """
    # Time vector
    t = np.arange(num_samples) / fs

    # Generate the real and imaginary parts as sine waves
    real_part = np.sin(2 * np.pi * f0 * t) + np.sin(2 * np.pi * f1 * t)

    real_part /= 2

    # Scale the real part to 16-bit integer rang
    real_int = np.int16(np.round(real_part * (2**15 - 1)))

    # Combine the real and imaginary parts into a single 32-bit complex sample array
    complex_samples = np.uint32(real_int) << 16

    return complex_samples


class FFTMonitor(BusMonitor):
    """
    monitors axi streaming bus
    """

    def __init__(self, dut, clk, callback=None):
        self._signals = ["o_result", "o_sync"]
        BusMonitor.__init__(self, dut, None, clk, callback=callback)
        self.clock = clk
        self.count = 64
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

            if self.count != 64:
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
    inm = FFTMonitor(dut, dut.i_clk)
    ind = FFTDriver(dut, dut.i_clk)
    # Start the clock
    cocotb.start_soon(Clock(dut.i_clk, 10, units="ns").start())
    # # Reset the module
    dut.i_reset.value = 1
    await ClockCycles(dut.i_clk, 5)
    dut.i_reset.value = 0
    # Generate some freq data
    waveform = generate_sample_data(fs, f0, f1, n_samples)
    # Pass the samples to the DUT
    ind.append(waveform)
    # Wait some clock cycles
    await ClockCycles(dut.i_clk, 10000)
    # Show the first collection of fft bins
    plot_results(inm.values[0], n_samples, fs)


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
    includes = [
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/src/fft-core/cmem_8.hex",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/src/fft-core/cmem_16.hex",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/src/fft-core/cmem_32.hex",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/src/fft-core/cmem_64.hex",
    ]
    build_test_args = ["-Wall"]  # ,"COCOTB_RESOLVE_X=ZEROS"]
    parameters = {}
    sys.path.append(str(proj_path / "sim"))
    runner = get_runner(sim)
    runner.build(
        sources=sources,
        includes=includes,
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

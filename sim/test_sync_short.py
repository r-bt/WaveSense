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

# Load in the samples
current_dir = os.path.dirname(os.path.abspath(__file__))
samples_path = os.path.join(current_dir, "samples.dat")


wave = np.fromfile(samples_path, dtype=np.int16)

i_q_pairs = wave.reshape(-1, 2)
combined_values = (i_q_pairs[:, 0].astype(np.int32) << 16) | (
    i_q_pairs[:, 1].astype(np.uint16)
)

samples = [complex(i, q) for i, q in zip(wave[::2], wave[1::2])]


async def reset(clk, reset_wire, num_cycles, active_val):
    reset_wire.value = active_val
    await ClockCycles(clk, num_cycles)
    reset_wire.value = 1 - active_val


def plot_results():
    fig, ax = plt.subplots(nrows=2, ncols=1, sharex=True)
    ax[0].plot([s.real for s in samples[:500]], "-bo")
    ax[1].plot(
        [
            abs(
                sum(
                    [
                        samples[i + j] * samples[i + j + 16].conjugate()
                        for j in range(0, 48)
                    ]
                )
            )
            / sum([abs(samples[i + j]) ** 2 for j in range(0, 48)])
            for i in range(0, 500)
        ],
        "-ro",
    )
    plt.show()


class SyncMonitor(BusMonitor):
    """
    monitors axi streaming bus
    """

    def __init__(self, dut, name, clk, callback=None):
        self._signals = ["sample_in", "sample_in_valid", "short_preamble_detected"]
        BusMonitor.__init__(self, dut, name, clk, callback=callback)
        self.clock = clk
        self.transactions = 0
        self.short_preamble_detected = []

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
            short_preamble_detected = self.bus.short_preamble_detected.value
            self.short_preamble_detected.append(short_preamble_detected)
            self._recv((short_preamble_detected))


class SyncDriver(BusDriver):
    def __init__(self, dut, name, clk):
        self._signals = ["rst_in", "sample_in", "sample_in_valid"]
        BusDriver.__init__(self, dut, name, clk)
        self.clock = clk
        self.bus.sample_in.value = 0
        self.bus.sample_in_valid.value = 0

    async def _driver_send(self, values, sync=True):
        for value in values:
            await RisingEdge(self.clock)
            self.bus.sample_in.value = int(value)
            self.bus.sample_in_valid.value = 1
        await RisingEdge(self.clock)
        self.bus.sample_in_valid.value = 0


# @cocotb.test
# async def test_with_mock_data(dut):
#     """
#     Sends 10 repeating sequence of I [-7, 8] and Q = 5 to the sync_short module
#     """
#     outm = SyncMonitor(dut, "", dut.clk_in)
#     ind = SyncDriver(dut, "", dut.clk_in)
#     # Setup the module
#     cocotb.start_soon(Clock(dut.clk_in, 10, units="ns").start())
#     await reset(dut.clk_in, dut.rst_in, 2, 1)

#     # Define the range for I values
#     mock_i_values = np.arange(-7, 9)  # -7 to 8 inclusive
#     mock_q_values = np.full_like(mock_i_values, 5)  # Q values are all 5

#     # Combine I and Q into pairs
#     mock_i_q_pairs = np.column_stack((mock_i_values, mock_q_values))

#     # Repeat the pairs 10 times
#     mock_i_q_pairs = np.tile(mock_i_q_pairs, (10, 1))

#     # Combine the values into 32 bit values
#     values = (mock_i_q_pairs[:, 0].astype(np.uint32) << 16) | (
#         mock_i_q_pairs[:, 1].astype(np.uint16)
#     )

#     await ind._driver_send(values)
#     await ClockCycles(dut.clk_in, 1000)


@cocotb.test
async def test_sync_short(dut):
    """
    Sends samples.dat to the sync_short module
    """
    outm = SyncMonitor(dut, "", dut.clk_in)
    ind = SyncDriver(dut, "", dut.clk_in)
    # Setup the module
    cocotb.start_soon(Clock(dut.clk_in, 10, units="ns").start())
    await reset(dut.clk_in, dut.rst_in, 2, 1)
    # Send the samples
    await ind._driver_send(combined_values)
    await ClockCycles(dut.clk_in, 1000)


def sync_short_runner():
    """Simulate the downsampler using the Python runner."""
    sim = os.getenv("SIM", "icarus")
    proj_path = Path(__file__).resolve().parent.parent
    sys.path.append(str(proj_path / "sim" / "model"))
    sources = [
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/sync_short.sv",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/complex_to_mag_sq.sv",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/complex_to_mag.sv",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/moving_avg.sv",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/delay_sample.sv",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/complex_multiply.sv",
    ]
    build_test_args = ["-Wall"]  # ,"COCOTB_RESOLVE_X=ZEROS"]
    parameters = {}
    sys.path.append(str(proj_path / "sim"))
    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="sync_short",
        always=True,
        build_args=build_test_args,
        parameters=parameters,
        timescale=("1ns", "1ps"),
        waves=True,
    )
    run_test_args = []
    runner.test(
        hdl_toplevel="sync_short",
        test_module="test_sync_short",
        test_args=run_test_args,
        waves=True,
    )


if __name__ == "__main__":
    sync_short_runner()

# General imports
import os
import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import random

# cocotb imports
import cocotb
from cocotb.binary import BinaryValue, BinaryRepresentation
from cocotb.triggers import ClockCycles, Edge, FallingEdge, ReadOnly
from cocotb.runner import get_runner
from cocotb.clock import Clock
from cocotb_bus.drivers import BusDriver
from cocotb_bus.monitors import BusMonitor
from test_utils import upsample_data, DESIRED_SAMPLE_RATE, DATA_SAMPLE_RATE


class AXISMonitor(BusMonitor):
    """
    monitors axi streaming bus
    """

    def __init__(self, dut, name, clk, callback=None):
        if name == "signal":
            self._signals = ["axis_tvalid", "axis_tready", "axis_tdata"]
        else:
            self._signals = ["axis_tvalid", "axis_tready", "axis_tlast", "axis_tdata"]
        BusMonitor.__init__(self, dut, name, clk, callback=callback)
        self.clock = clk
        self.transactions = 0
        self.data_i = [[]]
        self.data_q = [[]]

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
            if "axis_tlast" in self._signals:
                last = self.bus.axis_tlast.value
            else:
                last = None
            if valid and ready:
                q = int(data) >> 16
                i = int(data) & 0xFFFF
                self.transactions += 1
                if i > 2**15:
                    i -= 2**16
                self.data_i[-1].append(i)
                if q > 2**15:
                    q -= 2**16
                self.data_q[-1].append(q)
                # Start a new frame upon receiving a tlast
                if last:
                    self.data_i.append([])
                    self.data_q.append([])
                self._recv((data, last))


class AXISDriver(BusDriver):
    def __init__(self, dut, name, clk, send_invalid):
        self._signals = ["axis_tvalid", "axis_tready", "axis_tdata"]
        BusDriver.__init__(self, dut, name, clk)
        self.clock = clk
        self.bus.axis_tdata.value = 0
        self.bus.axis_tvalid.value = 0
        if send_invalid:
            self.wait_cycles_range = (0, 3)
        else:
            self.wait_cycles_range = (0, 0)

    async def _driver_send(self, value, sync=True):
        if value["type"] == "single":
            await FallingEdge(self.clock)
            i, q = value["contents"]["data"]
            self.bus.axis_tdata.value = int(
                (np.int32(q) << 16) | (np.int32(i) & 0xFFFF)
            )
            self.bus.axis_tvalid.value = 1
            await ReadOnly()
            while not self.bus.axis_tready.value:
                await Edge(self.clock)
                await ReadOnly()
        else:
            for q, i in value["contents"]["data"]:
                await FallingEdge(self.clock)
                self.bus.axis_tdata.value = int(
                    (np.int32(q) << 16) | (np.int32(i) & 0xFFFF)
                )
                self.bus.axis_tvalid.value = 1
                await ReadOnly()
                while not self.bus.axis_tready.value:
                    await Edge(self.clock)
                    await ReadOnly()
                wait_cycles = random.randint(*self.wait_cycles_range)
                if wait_cycles:
                    await FallingEdge(self.clock)
                    self.bus.axis_tdata.value = 0
                    self.bus.axis_tvalid.value = 0
                    await ClockCycles(self.clock, wait_cycles - 1)
        await FallingEdge(self.clock)
        self.bus.axis_tvalid.value = 0


async def set_ready(dut, ready_val):
    await FallingEdge(dut.clk_in)
    dut.csi_axis_tready.value = ready_val


async def reset(clk, reset_wire, num_cycles, active_val):
    reset_wire.value = active_val
    await ClockCycles(clk, num_cycles)
    reset_wire.value = 1 - active_val


# @cocotb.test()
# async def partial_filter_and_downsample_test(dut):
#     """
#     Extends the sample data
#     """
#     # Initialize the monitors
#     inm = AXISMonitor(dut, "signal", dut.clk_in)
#     outm = AXISMonitor(dut, "csi", dut.clk_in)
#     ind = AXISDriver(dut, "signal", dut.clk_in, False)
#     # Setup the DUT
#     cocotb.start_soon(Clock(dut.clk_in, 10, units="ns").start())
#     await reset(dut.clk_in, dut.rst_in, 2, 1)
#     await set_ready(dut, 1)
#     # Feed in some real data
#     cwd = os.path.dirname(os.path.abspath(__file__))
#     samples_path = os.path.join(cwd, "samples.dat")
#     signal = np.fromfile(samples_path, dtype=np.int16)[:1000]
#     i = upsample_data(signal[::2], DATA_SAMPLE_RATE, DESIRED_SAMPLE_RATE)
#     q = upsample_data(signal[1::2], DATA_SAMPLE_RATE, DESIRED_SAMPLE_RATE)
#     # Extend each element 10 times
#     # Send the data to the filter
#     ind.append({"type": "burst", "contents": {"data": zip(q, i)}})
#     # Wait for the data to be processed
#     await ClockCycles(dut.clk_in, 5000)
#     # Plot the output
#     ax, fig = plt.subplots(ncols=1, nrows=3)
#     fig[0].plot(signal[::2])
#     fig[1].plot(i)
#     # fig[1].plot(wave)
#     fig[2].plot(outm.data_i[0])
#     # fig[3].plot(outm.data[::10])
#     plt.show()


# @cocotb.test
# async def partial_lts_extractor_test(dut):
#     """
#     Extends the sample data
#     """
#     inm = AXISMonitor(dut, "signal", dut.clk_in)
#     outm = AXISMonitor(dut, "csi", dut.clk_in)
#     ind = AXISDriver(dut, "signal", dut.clk_in, False)
#     # Setup the DUT
#     cocotb.start_soon(Clock(dut.clk_in, 10, units="ns").start())
#     dut.sw_in.value = 4  # Threshold ~= 2000
#     await set_ready(dut, 1)
#     await reset(dut.clk_in, dut.rst_in, 2, 1)
#     # Feed in some real data
#     cwd = os.path.dirname(os.path.abspath(__file__))
#     samples_path = os.path.join(cwd, "samples.dat")
#     signal = np.fromfile(samples_path, dtype=np.int16)
#     i = signal[::2]
#     q = signal[1::2]
#     # Extend the data for the filter and downsample
#     i = upsample_data(i, DATA_SAMPLE_RATE, DESIRED_SAMPLE_RATE)
#     q = upsample_data(q, DATA_SAMPLE_RATE, DESIRED_SAMPLE_RATE)
#     # Drive the DUT
#     await ClockCycles(dut.clk_in, 1)
#     ind.append({"type": "burst", "contents": {"data": zip(q, i)}})
#     await ClockCycles(dut.clk_in, 200)
#     await set_ready(dut, 0)
#     await ClockCycles(dut.clk_in, 100)
#     await set_ready(dut, 1)
#     await ClockCycles(dut.clk_in, 115)
#     await set_ready(dut, 0)
#     await ClockCycles(dut.clk_in, 49)
#     await set_ready(dut, 1)
#     await ClockCycles(dut.clk_in, 217)
#     await set_ready(dut, 0)
#     await ClockCycles(dut.clk_in, 49)
#     await set_ready(dut, 1)
#     await ClockCycles(dut.clk_in, 12)
#     await set_ready(dut, 0)
#     await ClockCycles(dut.clk_in, 49)
#     await set_ready(dut, 1)
#     await ClockCycles(dut.clk_in, 140000)
#     # Check that we sent and received the correct amount of data
#     assert inm.transactions == len(i), "Sent the wrong number of samples!"
#     assert outm.transactions == 128 * 19, "Received the wrong number of samples!"
#     # Save the LTS data
#     lts_arr = np.array(
#         [np.array(outm.data_i[i]) + 1j * np.array(outm.data_q[i]) for i in range(30)]
#     )
#     np.save(os.path.join(cwd, "lts_arr_from_csi_extractor.npy"), lts_arr)
#     # Check (visually) that it worked
#     for i in range(19):
#         lts1 = np.array(outm.data_i[2 * i]) + 1j * np.array(outm.data_q[2 * i])
#         lts2 = np.array(outm.data_i[2 * i + 1]) + 1j * np.array(outm.data_q[2 * i + 1])
#         # Plot the FFTs as a visual check
#         plt.plot(np.fft.fft(lts1).real, "-o")
#         plt.plot(np.fft.fft(lts2).real, "-o")
#         plt.show()


@cocotb.test
async def partial_lts_extractor_test(dut):
    """
    Extends the sample data
    """
    inm = AXISMonitor(dut, "signal", dut.clk_in)
    outm = AXISMonitor(dut, "csi", dut.clk_in)
    ind = AXISDriver(dut, "signal", dut.clk_in, False)
    # Setup the DUT
    cocotb.start_soon(Clock(dut.clk_in, 10, units="ns").start())
    dut.sw_in.value = 4  # Threshold ~= 2000
    await set_ready(dut, 1)
    await reset(dut.clk_in, dut.rst_in, 2, 1)
    # Feed in some real data
    cwd = os.path.dirname(os.path.abspath(__file__))
    samples_path = os.path.join(cwd, "samples.dat")
    signal = np.fromfile(samples_path, dtype=np.int16)
    i = signal[::2]
    q = signal[1::2]
    # Extend the data for the filter and downsample
    i = upsample_data(i, DATA_SAMPLE_RATE, DESIRED_SAMPLE_RATE)
    q = upsample_data(q, DATA_SAMPLE_RATE, DESIRED_SAMPLE_RATE)
    # Drive the DUT
    await ClockCycles(dut.clk_in, 1)
    ind.append({"type": "burst", "contents": {"data": zip(q, i)}})
    ready_cycles = 0

    while ready_cycles < 140000:
        # Randomly set ready
        is_ready = random.randint(0, 1)
        # is_ready = 1
        await set_ready(dut, is_ready)
        ready_cycles += 1 if is_ready else 0
        await ClockCycles(dut.clk_in, 1)

    # await ClockCycles(dut.clk_in, 200)
    # await set_ready(dut, 0)
    # await ClockCycles(dut.clk_in, 100)
    # await set_ready(dut, 1)
    # await ClockCycles(dut.clk_in, 115)
    # await set_ready(dut, 0)
    # await ClockCycles(dut.clk_in, 49)
    # await set_ready(dut, 1)
    # await ClockCycles(dut.clk_in, 217)
    # await set_ready(dut, 0)
    # await ClockCycles(dut.clk_in, 49)
    # await set_ready(dut, 1)
    # await ClockCycles(dut.clk_in, 12)
    # await set_ready(dut, 0)
    # await ClockCycles(dut.clk_in, 49)
    # await set_ready(dut, 1)
    # await ClockCycles(dut.clk_in, 70000)
    # await ClockCycles(dut.clk_in, 200)
    # await set_ready(dut, 0)
    # await ClockCycles(dut.clk_in, 100)
    # await set_ready(dut, 1)
    # await ClockCycles(dut.clk_in, 115)
    # await set_ready(dut, 0)
    # await ClockCycles(dut.clk_in, 49)
    # await set_ready(dut, 1)
    # await ClockCycles(dut.clk_in, 217)
    # await set_ready(dut, 0)
    # await ClockCycles(dut.clk_in, 49)
    # await set_ready(dut, 1)
    # await ClockCycles(dut.clk_in, 12)
    # await set_ready(dut, 0)
    # await ClockCycles(dut.clk_in, 49)
    # await set_ready(dut, 1)
    # await ClockCycles(dut.clk_in, 70000)
    # Check that we sent and received the correct amount of data
    assert inm.transactions == len(i), "Sent the wrong number of samples!"
    # Check we received the correct number of samples
    assert outm.transactions == 52 * 19, "Received the wrong number of samples!"
    # Plot the data
    for i in range(19):
        plt.plot(outm.data_i[i], "-o")
        plt.plot(outm.data_q[i], "-o")
        # Include legend
        plt.legend(["Real", "Imaginary"])
        plt.show()
    # assert outm.transactions == 128 * 19, "Received the wrong number of samples!"
    # # Save the LTS data
    # lts_arr = np.array(
    #     [np.array(outm.data_i[i]) + 1j * np.array(outm.data_q[i]) for i in range(30)]
    # )
    # np.save(os.path.join(cwd, "lts_arr_from_csi_extractor.npy"), lts_arr)
    # # Check (visually) that it worked
    # for i in range(19):
    #     lts1 = np.array(outm.data_i[2 * i]) + 1j * np.array(outm.data_q[2 * i])
    #     lts2 = np.array(outm.data_i[2 * i + 1]) + 1j * np.array(outm.data_q[2 * i + 1])
    #     # Plot the FFTs as a visual check
    #     plt.plot(np.fft.fft(lts1).real, "-o")
    #     plt.plot(np.fft.fft(lts2).real, "-o")
    #     plt.show()


def sync_short_runner():
    """Simulate the downsampler using the Python runner."""
    sim = os.getenv("SIM", "icarus")
    proj_path = Path(__file__).resolve().parent.parent
    sys.path.append(str(proj_path / "sim" / "model"))
    sources = [
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/csi_extractor.sv",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/fir_17.sv",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/downsample.sv",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/sync_short.sv",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/power_trigger.sv",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/sync_long.sv",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/bram_fifo.sv",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/complex_multiply.sv",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/complex_to_mag.sv",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/complex_to_mag_sq.sv",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/delay_sample.sv",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/lts_xcorr.sv",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/moving_avg.sv",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/pipeline.sv",
        proj_path
        / "WaveSense/ip_repo/csi_extractor_1_0/hdl/xilinx_true_dual_port_read_first_2_clock_ram.v",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/lts_extractor.sv",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/block_fft.sv",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/axis_fft.sv",
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
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/equalizer.sv",
    ]
    build_test_args = ["-Wall"]  # ,"COCOTB_RESOLVE_X=ZEROS"]
    parameters = {}
    sys.path.append(str(proj_path / "sim"))
    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="csi_extractor_sv",
        always=True,
        build_args=build_test_args,
        parameters=parameters,
        timescale=("1ns", "1ps"),
        waves=True,
    )
    run_test_args = []
    runner.test(
        hdl_toplevel="csi_extractor_sv",
        test_module="test_csi_extractor",
        test_args=run_test_args,
        waves=True,
    )


if __name__ == "__main__":
    sync_short_runner()

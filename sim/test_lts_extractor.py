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
        if name == 'signal':
            self._signals = ['axis_tvalid', 'axis_tready', 'axis_tdata']
        else:
            self._signals = ['axis_tvalid', 'axis_tready', 'axis_tlast', 'axis_tdata']
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
            if 'axis_tlast' in self._signals:
                last = self.bus.axis_tlast.value
            else:
                last = None
            if valid and ready:
                i = int(data) >> 16
                q = int(data) & 0xFFFF
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
        self._signals = ['axis_tvalid', 'axis_tready', 'axis_tdata']
        BusDriver.__init__(self, dut, name, clk)
        self.clock = clk
        self.bus.axis_tdata.value = 0
        self.bus.axis_tvalid.value = 0
        if send_invalid:
            self.wait_cycles_range = (0, 3)
        else:
            self.wait_cycles_range = (0, 0)

    async def _driver_send(self, value, sync=True):
        if value['type'] == 'single':
            await FallingEdge(self.clock)
            i, q = value['contents']['data']
            self.bus.axis_tdata.value = int((np.int32(i) << 16) | (np.int32(q) & 0xFFFF))
            self.bus.axis_tvalid.value = 1
            await ReadOnly()
            while not self.bus.axis_tready.value:
                await Edge(self.clock)
                await ReadOnly()
        else:
            for i, q in value['contents']['data']:
                await FallingEdge(self.clock)
                self.bus.axis_tdata.value = int((np.int32(i) << 16) | (np.int32(q) & 0xFFFF))
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
    dut.lts_axis_tready.value = ready_val


async def reset(clk, reset_wire, num_cycles, active_val):
    reset_wire.value = active_val
    await ClockCycles(clk, num_cycles)
    reset_wire.value = 1 - active_val


@cocotb.test()
async def test_lts_extractor_with_invalid(dut):
    inm = AXISMonitor(dut, 'signal', dut.clk_in)
    outm = AXISMonitor(dut, 'lts', dut.clk_in)
    ind = AXISDriver(dut, 'signal', dut.clk_in, True)
    # Setup the DUT
    cocotb.start_soon(Clock(dut.clk_in, 10, units="ns").start())
    await set_ready(dut, 1)
    await reset(dut.clk_in, dut.rst_in, 2, 1)
    # Feed in some real data
    cwd = os.path.dirname(os.path.abspath(__file__))
    samples_path = os.path.join(cwd, "samples.dat")
    signal = np.fromfile(samples_path, dtype=np.int16)
    i = signal[::2]
    q = signal[1::2]
    # Drive the DUT
    await ClockCycles(dut.clk_in, 1)
    ind.append({'type': 'burst', 'contents': {'data': zip(i, q)}})
    await ClockCycles(dut.clk_in, 200)
    await set_ready(dut, 0)
    await ClockCycles(dut.clk_in, 100)
    await set_ready(dut, 1)
    await ClockCycles(dut.clk_in, 115)
    await set_ready(dut, 0)
    await ClockCycles(dut.clk_in, 49)
    await set_ready(dut, 1)
    await ClockCycles(dut.clk_in, 217)
    await set_ready(dut, 0)
    await ClockCycles(dut.clk_in, 49)
    await set_ready(dut, 1)
    await ClockCycles(dut.clk_in, 12)
    await set_ready(dut, 0)
    await ClockCycles(dut.clk_in, 49)
    await set_ready(dut, 1)
    await ClockCycles(dut.clk_in, 50000)
    # Check that the data is what we expect
    assert inm.transactions == len(i), 'Sent the wrong number of samples!'
    assert outm.transactions == 128 * 15, 'Received the wrong number of samples!'
    # Check (visually) that it worked
    # for i in range(15):
    #     lts1 = np.array(outm.data_i[2 * i]) + 1j * np.array(outm.data_q[0])
    #     lts2 = np.array(outm.data_i[2 * i + 1]) + 1j * np.array(outm.data_q[1])
    #     # Plot the FFTs as a visual check
    #     plt.plot(np.fft.fft(lts1).real, '-o')
    #     plt.plot(np.fft.fft(lts2).real, '-o')
    #     plt.show()


@cocotb.test()
async def test_lts_extractor_no_invalid(dut):
    inm = AXISMonitor(dut, 'signal', dut.clk_in)
    outm = AXISMonitor(dut, 'lts', dut.clk_in)
    ind = AXISDriver(dut, 'signal', dut.clk_in, False)
    # Setup the DUT
    cocotb.start_soon(Clock(dut.clk_in, 10, units="ns").start())
    await set_ready(dut, 1)
    await reset(dut.clk_in, dut.rst_in, 2, 1)
    # Feed in some real data
    cwd = os.path.dirname(os.path.abspath(__file__))
    samples_path = os.path.join(cwd, "samples.dat")
    signal = np.fromfile(samples_path, dtype=np.int16)
    i = signal[::2]
    q = signal[1::2]
    # Drive the DUT
    await ClockCycles(dut.clk_in, 1)
    ind.append({'type': 'burst', 'contents': {'data': zip(i, q)}})
    await ClockCycles(dut.clk_in, 200)
    await set_ready(dut, 0)
    await ClockCycles(dut.clk_in, 100)
    await set_ready(dut, 1)
    await ClockCycles(dut.clk_in, 115)
    await set_ready(dut, 0)
    await ClockCycles(dut.clk_in, 49)
    await set_ready(dut, 1)
    await ClockCycles(dut.clk_in, 217)
    await set_ready(dut, 0)
    await ClockCycles(dut.clk_in, 49)
    await set_ready(dut, 1)
    await ClockCycles(dut.clk_in, 12)
    await set_ready(dut, 0)
    await ClockCycles(dut.clk_in, 49)
    await set_ready(dut, 1)
    await ClockCycles(dut.clk_in, 40000)
    # Check that the data is what we expect
    assert inm.transactions == len(i), 'Sent the wrong number of samples!'
    assert outm.transactions == 128 * 15, 'Received the wrong number of samples!'
    # Check (visually) that it worked
    # for i in range(15):
    #     lts1 = np.array(outm.data_i[2 * i]) + 1j * np.array(outm.data_q[0])
    #     lts2 = np.array(outm.data_i[2 * i + 1]) + 1j * np.array(outm.data_q[1])
    #     # Plot the FFTs as a visual check
    #     plt.plot(np.fft.fft(lts1).real, '-o')
    #     plt.plot(np.fft.fft(lts2).real, '-o')
    #     plt.show()


def lts_extractor_runner():
    """Simulate the LTS extractor using the Python runner."""
    sim = os.getenv("SIM", "icarus")
    proj_path = Path(__file__).resolve().parent.parent
    hdl_path = proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl"
    sys.path.append(str(proj_path / "sim" / "model"))
    sources = [
        hdl_path / "lts_extractor.sv",
        hdl_path / "power_trigger.sv",
        hdl_path / "sync_short.sv",
        hdl_path / "complex_to_mag_sq.sv",
        hdl_path / "delay_sample.sv",
        hdl_path / "moving_avg.sv",
        hdl_path / "sync_long.sv",
        hdl_path / "pipeline.sv",
        hdl_path / "complex_to_mag.sv",
        hdl_path / "lts_xcorr.sv",
        hdl_path / "complex_multiply.sv",
        hdl_path / "xilinx_true_dual_port_read_first_2_clock_ram.v",
        hdl_path / "bram_fifo.sv",
    ]
    build_test_args = ["-Wall"]  # ,"COCOTB_RESOLVE_X=ZEROS"]
    parameters = {}
    sys.path.append(str(proj_path / "sim"))
    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="lts_extractor",
        always=True,
        build_args=build_test_args,
        parameters=parameters,
        timescale=("1ns", "1ps"),
        waves=True,
    )
    run_test_args = []
    runner.test(
        hdl_toplevel="lts_extractor",
        test_module="test_lts_extractor",
        test_args=run_test_args,
        waves=True,
    )


if __name__ == "__main__":
    lts_extractor_runner()

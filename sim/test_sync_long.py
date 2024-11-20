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
            self._signals = ['axis_tvalid', 'axis_tready',
                             'i_axis_tdata', 'q_axis_tdata']
        else:
            self._signals = ['axis_tvalid', 'axis_tready', 'axis_tlast',
                             'i_axis_tdata', 'q_axis_tdata']
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
            i = self.bus.i_axis_tdata.value
            q = self.bus.q_axis_tdata.value
            if 'axis_tlast' in self._signals:
                last = self.bus.axis_tlast.value
            else:
                last = None
            if valid and ready:
                self.transactions += 1
                if int(i) > 2**15:
                    self.data_i[-1].append(i - 2**16)
                else:
                    self.data_i[-1].append(int(i))
                if int(q) > 2**15:
                    self.data_q[-1].append(q - 2**16)
                else:
                    self.data_q[-1].append(int(q))
                # Start a new frame upon receiving a tlast
                if last:
                    self.data_i.append([])
                    self.data_q.append([])
                self._recv((i, q, last))


class AXISDriver(BusDriver):
    def __init__(self, dut, name, clk, send_invalid):
        self._signals = ['axis_tvalid', 'axis_tready',
                         'i_axis_tdata', 'q_axis_tdata']
        BusDriver.__init__(self, dut, name, clk)
        self.clock = clk
        self.bus.i_axis_tdata.value = 0
        self.bus.q_axis_tdata.value = 0
        self.bus.axis_tvalid.value = 0
        if send_invalid:
            self.wait_cycles_range = (0, 3)
        else:
            self.wait_cycles_range = (0, 0)

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
                wait_cycles = random.randint(*self.wait_cycles_range)
                if wait_cycles:
                    await FallingEdge(self.clock)
                    self.bus.i_axis_tdata.value = 0
                    self.bus.q_axis_tdata.value = 0
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
async def test_sync_long_with_invalid(dut):
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
    signal = np.fromfile(samples_path, dtype=np.int16)[:1000]
    i = signal[::2]
    q = signal[1::2]
    # Drive the DUT
    await ClockCycles(dut.clk_in, 1)
    ind.append({'type': 'burst', 'contents': {'data': zip(i[160:], q[160:])}})
    await ClockCycles(dut.clk_in, 100)
    await set_ready(dut, 0)
    await ClockCycles(dut.clk_in, 100)
    await set_ready(dut, 1)
    await ClockCycles(dut.clk_in, 15)
    await set_ready(dut, 0)
    await ClockCycles(dut.clk_in, 49)
    await set_ready(dut, 1)
    await ClockCycles(dut.clk_in, 17)
    await set_ready(dut, 0)
    await ClockCycles(dut.clk_in, 49)
    await set_ready(dut, 1)
    await ClockCycles(dut.clk_in, 12)
    await set_ready(dut, 0)
    await ClockCycles(dut.clk_in, 49)
    await set_ready(dut, 1)
    await ClockCycles(dut.clk_in, 500)
    # Check that the data is what we expect
    assert inm.transactions == 340, 'Sent the wrong number of samples!'
    assert outm.transactions == 128, 'Received the wrong number of samples!'
    # Check that it worked
    ref_lts_loc = 171
    lts1 = np.array(outm.data_i[0]) + 1j * np.array(outm.data_q[0])
    assert (lts1 == i[ref_lts_loc+32:ref_lts_loc+96] +
            1j * q[ref_lts_loc+32:ref_lts_loc+96]).all()
    lts2 = np.array(outm.data_i[1]) + 1j * np.array(outm.data_q[1])
    assert (lts2 == i[ref_lts_loc+96:ref_lts_loc+160] +
            1j * q[ref_lts_loc+96:ref_lts_loc+160]).all()
    # Plot the FFTs as a visual check
    # plt.plot(np.fft.fft(lts1).real, '-o')
    # plt.plot(np.fft.fft(lts2).real, '-o')
    # plt.show()


@cocotb.test()
async def test_sync_long_no_invalid(dut):
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
    signal = np.fromfile(samples_path, dtype=np.int16)[:1000]
    i = signal[::2]
    q = signal[1::2]
    # Drive the DUT
    await ClockCycles(dut.clk_in, 1)
    ind.append({'type': 'burst', 'contents': {'data': zip(i[160:], q[160:])}})
    # Test back-pressure
    await ClockCycles(dut.clk_in, 100)
    await set_ready(dut, 0)
    await ClockCycles(dut.clk_in, 100)
    await set_ready(dut, 1)
    await ClockCycles(dut.clk_in, 15)
    await set_ready(dut, 0)
    await ClockCycles(dut.clk_in, 49)
    await set_ready(dut, 1)
    await ClockCycles(dut.clk_in, 17)
    await set_ready(dut, 0)
    await ClockCycles(dut.clk_in, 49)
    await set_ready(dut, 1)
    await ClockCycles(dut.clk_in, 12)
    await set_ready(dut, 0)
    await ClockCycles(dut.clk_in, 49)
    await set_ready(dut, 1)
    await ClockCycles(dut.clk_in, 500)
    # Check that the data is what we expect
    assert inm.transactions == 340, 'Sent the wrong number of samples!'
    assert len(outm.data_i) == 3 and outm.transactions == 128, 'Received the wrong number of samples!'
    # Check that it worked
    ref_lts_loc = 171
    lts1 = np.array(outm.data_i[0]) + 1j * np.array(outm.data_q[0])
    assert (lts1 == i[ref_lts_loc+32:ref_lts_loc+96] +
            1j * q[ref_lts_loc+32:ref_lts_loc+96]).all()
    lts2 = np.array(outm.data_i[1]) + 1j * np.array(outm.data_q[1])
    assert (lts2 == i[ref_lts_loc+96:ref_lts_loc+160] +
            1j * q[ref_lts_loc+96:ref_lts_loc+160]).all()
    # Plot the FFTs as a visual check
    # plt.plot(np.fft.fft(lts1).real, '-o')
    # plt.plot(np.fft.fft(lts2).real, '-o')
    # plt.show()


def sync_long_runner():
    """Simulate the LTS cross-correlater using the Python runner."""
    sim = os.getenv("SIM", "icarus")
    proj_path = Path(__file__).resolve().parent.parent
    hdl_path = proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl"
    sys.path.append(str(proj_path / "sim" / "model"))
    sources = [
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
        hdl_toplevel="sync_long",
        always=True,
        build_args=build_test_args,
        parameters=parameters,
        timescale=("1ns", "1ps"),
        waves=True,
    )
    run_test_args = []
    runner.test(
        hdl_toplevel="sync_long",
        test_module="test_sync_long",
        test_args=run_test_args,
        waves=True,
    )


if __name__ == "__main__":
    sync_long_runner()

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
        self._signals = [
            "axis_tvalid",
            "axis_tready",
            "axis_tlast",
            "re_axis_tdata",
            "im_axis_tdata",
        ]
        BusMonitor.__init__(self, dut, name, clk, callback=callback)
        self.clock = clk
        self.transactions = 0
        self.data_re = []
        self.data_im = []

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
            re = self.bus.re_axis_tdata.value
            im = self.bus.im_axis_tdata.value
            if valid and ready:
                self.transactions += 1
                if int(re) > 2**15:
                    self.data_re.append(re - 2**16)
                else:
                    self.data_re.append(int(re))
                if int(im) > 2**15:
                    self.data_im.append(im - 2**16)
                else:
                    self.data_im.append(int(im))
                # Start a new frame upon receiving a tlast
                self._recv((re, im))


class AXISDriver(BusDriver):
    def __init__(self, dut, name, clk, send_invalid):
        self._signals = [
            "axis_tvalid",
            "axis_tready",
            "axis_tlast",
            "re_axis_tdata",
            "im_axis_tdata",
        ]
        BusDriver.__init__(self, dut, name, clk)
        self.clock = clk
        self.bus.re_axis_tdata.value = 0
        self.bus.im_axis_tdata.value = 0
        self.bus.axis_tvalid.value = 0
        if send_invalid:
            self.wait_cycles_range = (0, 3)
        else:
            self.wait_cycles_range = (0, 0)

    async def _driver_send(self, value, sync=True):
        if value["type"] == "single":
            await FallingEdge(self.clock)
            self.bus.re_axis_tdata.value, self.bus.im_axis_tdata.value = value[
                "contents"
            ]["data"]
            self.bus.axis_tlast.value = value["contents"]["last"]
            self.bus.axis_tvalid.value = 1
            await ReadOnly()
            while not self.bus.axis_tready.value:
                await Edge(self.clock)
                await ReadOnly()
        else:
            for idx, val in enumerate(value["contents"]["data"]):
                re, im = val
                await FallingEdge(self.clock)
                self.bus.re_axis_tdata.value = int(re)
                self.bus.im_axis_tdata.value = int(im)
                self.bus.axis_tlast.value = int(
                    idx == len(value["contents"]["data"]) - 1
                )
                self.bus.axis_tvalid.value = 1
                await ReadOnly()
                while not self.bus.axis_tready.value:
                    await Edge(self.clock)
                    await ReadOnly()
                wait_cycles = random.randint(*self.wait_cycles_range)
                if wait_cycles:
                    await FallingEdge(self.clock)
                    self.bus.re_axis_tdata.value = 0
                    self.bus.im_axis_tdata.value = 0
                    self.bus.axis_tlast.value = 0
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
async def test_sync_long_with_invalid(dut):
    inm = AXISMonitor(dut, "fft", dut.clk_in)
    outm = AXISMonitor(dut, "csi", dut.clk_in)
    ind = AXISDriver(dut, "fft", dut.clk_in, True)
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
    ref_lts_loc = 171
    lts1 = (
        i[ref_lts_loc + 32 : ref_lts_loc + 96]
        + 1j * q[ref_lts_loc + 32 : ref_lts_loc + 96]
    )
    fft1 = np.fft.fft(lts1) / len(lts1) / 2 / np.pi
    lts2 = (
        i[ref_lts_loc + 96 : ref_lts_loc + 160]
        + 1j * q[ref_lts_loc + 96 : ref_lts_loc + 160]
    )
    fft2 = np.fft.fft(lts2) / len(lts2) / 2 / np.pi
    lts_ref = np.loadtxt(os.path.join(cwd, "lts.txt")).view(complex)
    fft_ref = np.fft.fft(lts_ref)
    # Drive the DUT
    await ClockCycles(dut.clk_in, 1)
    ind.append({"type": "burst", "contents": {"data": list(zip(fft1.real, fft1.imag))}})
    ind.append({"type": "burst", "contents": {"data": list(zip(fft2.real, fft2.imag))}})
    await ClockCycles(dut.clk_in, 60)
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
    await ClockCycles(dut.clk_in, 350)
    # Check that the data is what we expect
    assert inm.transactions == 128, "Sent the wrong number of samples!"
    assert outm.transactions == 52, "Received the wrong number of samples!"
    # Check that it worked
    h = np.array(outm.data_re) + 1j * np.array(outm.data_im)
    h_expanded = np.concat(([np.inf], h[:26], [np.inf] * 11, h[26:]))
    # plt.plot((fft1 / h_expanded).real, '-o')
    # plt.plot((fft2 / h_expanded).real, '-o')
    # plt.plot(fft_ref.real, '-o')
    # plt.show()
    assert np.isclose((fft1 / h_expanded).real, fft_ref.real, atol=0.05).all()
    assert np.isclose((fft2 / h_expanded).real, fft_ref.real, atol=0.05).all()


@cocotb.test()
async def test_sync_long_no_invalid(dut):
    inm = AXISMonitor(dut, "fft", dut.clk_in)
    outm = AXISMonitor(dut, "csi", dut.clk_in)
    ind = AXISDriver(dut, "fft", dut.clk_in, False)
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
    ref_lts_loc = 171
    lts1 = (
        i[ref_lts_loc + 32 : ref_lts_loc + 96]
        + 1j * q[ref_lts_loc + 32 : ref_lts_loc + 96]
    )
    fft1 = np.fft.fft(lts1) / len(lts1) / 2 / np.pi
    lts2 = (
        i[ref_lts_loc + 96 : ref_lts_loc + 160]
        + 1j * q[ref_lts_loc + 96 : ref_lts_loc + 160]
    )
    fft2 = np.fft.fft(lts2) / len(lts2) / 2 / np.pi
    lts_ref = np.loadtxt(os.path.join(cwd, "lts.txt")).view(complex)
    fft_ref = np.fft.fft(lts_ref)
    # Drive the DUT
    await ClockCycles(dut.clk_in, 1)
    ind.append({"type": "burst", "contents": {"data": list(zip(fft1.real, fft1.imag))}})
    ind.append({"type": "burst", "contents": {"data": list(zip(fft2.real, fft2.imag))}})
    await ClockCycles(dut.clk_in, 20)
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
    await ClockCycles(dut.clk_in, 150)
    # Check that the data is what we expect
    assert inm.transactions == 128, "Sent the wrong number of samples!"
    assert outm.transactions == 52, "Received the wrong number of samples!"
    # Check that it worked
    h = np.array(outm.data_re) + 1j * np.array(outm.data_im)
    h_expanded = np.concat(([np.inf], h[:26], [np.inf] * 11, h[26:]))
    plt.plot((fft1 / h_expanded).real, "-o")
    plt.plot((fft2 / h_expanded).real, "-o")
    plt.plot(fft_ref.real, "-o")
    plt.show()
    assert np.isclose((fft1 / h_expanded).real, fft_ref.real, atol=0.05).all()
    assert np.isclose((fft2 / h_expanded).real, fft_ref.real, atol=0.05).all()


def equalizer_runner():
    """Simulate the equalizer (CSI extractor) using the Python runner."""
    sim = os.getenv("SIM", "icarus")
    proj_path = Path(__file__).resolve().parent.parent
    hdl_path = proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl"
    sys.path.append(str(proj_path / "sim" / "model"))
    sources = [
        hdl_path / "equalizer.sv",
        hdl_path / "pipeline.sv",
        hdl_path / "xilinx_true_dual_port_read_first_2_clock_ram.v",
        hdl_path / "bram_fifo.sv",
    ]
    build_test_args = ["-Wall"]  # ,"COCOTB_RESOLVE_X=ZEROS"]
    parameters = {}
    sys.path.append(str(proj_path / "sim"))
    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="equalizer",
        always=True,
        build_args=build_test_args,
        parameters=parameters,
        timescale=("1ns", "1ps"),
        waves=True,
    )
    run_test_args = []
    runner.test(
        hdl_toplevel="equalizer",
        test_module="test_equalizer",
        test_args=run_test_args,
        waves=True,
    )


if __name__ == "__main__":
    equalizer_runner()

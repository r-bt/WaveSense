# General imports
import os
import sys
from pathlib import Path

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
        self._signals = ["axis_tvalid", "axis_tready", "axis_tdata"]
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
        self._signals = ["axis_tvalid", "axis_tready", "axis_tdata"]
        BusDriver.__init__(self, dut, name, clk)
        self.clock = clk
        self.bus.axis_tdata.value = 0
        self.bus.axis_tvalid.value = 0

    async def _driver_send(self, value, sync=True):
        if value["type"] == "single":
            await FallingEdge(self.clock)
            self.bus.axis_tdata.value = value["contents"]["data"]
            self.bus.axis_tvalid.value = 1
            await ReadOnly()
            while not self.bus.axis_tready.value:
                await Edge(self.clock)
                await ReadOnly()
        else:
            for val in value["contents"]["data"]:
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
async def test_delay(dut):
    """
    Delay a sample by a fixed number of samples
    """
    inm = AXISMonitor(dut, "s00", dut.s00_axis_aclk)
    outm = AXISMonitor(dut, "m00", dut.s00_axis_aclk)
    ind = AXISDriver(dut, "s00", dut.s00_axis_aclk)
    # Setup the DUT
    cocotb.start_soon(Clock(dut.s00_axis_aclk, 10, units="ns").start())
    await set_ready(dut, 1)
    await reset(dut.s00_axis_aclk, dut.s00_axis_aresetn, 2, 0)
    # Generate the data
    repetitions = 5
    samples = list(range(16)) * repetitions
    n_samples = len(samples)

    # Drive the DUT
    await ClockCycles(dut.s00_axis_aclk, 1)
    ind.append({"type": "burst", "contents": {"data": samples}})
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
    assert inm.transactions == n_samples, "Sent the wrong number of samples!"
    assert outm.transactions == int(
        n_samples - 16
    ), "Received the wrong number of samples!"
    # Check that the data matches
    for i in range(n_samples - 16):
        assert outm.data[i] == samples[i + 16], "Data mismatch!"


def downsample_runner():
    """Simulate the downsampler using the Python runner."""
    sim = os.getenv("SIM", "icarus")
    proj_path = Path(__file__).resolve().parent.parent
    sys.path.append(str(proj_path / "sim" / "model"))
    sources = [
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/delay.sv",
    ]
    build_test_args = ["-Wall"]  # ,"COCOTB_RESOLVE_X=ZEROS"]
    parameters = {}
    sys.path.append(str(proj_path / "sim"))
    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="delay",
        always=True,
        build_args=build_test_args,
        parameters=parameters,
        timescale=("1ns", "1ps"),
        waves=True,
    )
    run_test_args = []
    runner.test(
        hdl_toplevel="delay",
        test_module="test_delay",
        test_args=run_test_args,
        waves=True,
    )


if __name__ == "__main__":
    downsample_runner()

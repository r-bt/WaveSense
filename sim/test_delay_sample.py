# General imports
import os
import sys
from pathlib import Path

# cocotb imports
import cocotb
from cocotb.triggers import ClockCycles, Edge, FallingEdge, ReadOnly, RisingEdge
from cocotb.runner import get_runner
from cocotb.clock import Clock


async def reset(clk, reset_wire, num_cycles, active_val):
    reset_wire.value = active_val
    await ClockCycles(clk, num_cycles)
    reset_wire.value = 1 - active_val


@cocotb.test
async def test_delay_sample(dut):
    """
    Ensures that the complex_to_mag_sq module is working correctly.
    """
    # Setup the module
    cocotb.start_soon(Clock(dut.clk_in, 10, units="ns").start())
    await reset(dut.clk_in, dut.rst_in, 2, 1)
    # Feed in some real data
    data_in = [1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 22, 24, 26, 28, 30, 34, 36, 38, 40]
    dut.data_in_valid.value = 1
    for i in data_in:
        dut.data_in.value = i
        await RisingEdge(dut.clk_in)
    dut.data_in_valid.value = 0
    await ClockCycles(dut.clk_in, 10)


def delay_sample_runner():
    """Simulate the downsampler using the Python runner."""
    sim = os.getenv("SIM", "icarus")
    proj_path = Path(__file__).resolve().parent.parent
    sys.path.append(str(proj_path / "sim" / "model"))
    sources = [proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/delay_sample.sv"]
    build_test_args = ["-Wall"]  # ,"COCOTB_RESOLVE_X=ZEROS"]
    parameters = {}
    sys.path.append(str(proj_path / "sim"))
    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="delay_sample",
        always=True,
        build_args=build_test_args,
        parameters=parameters,
        timescale=("1ns", "1ps"),
        waves=True,
    )
    run_test_args = []
    runner.test(
        hdl_toplevel="delay_sample",
        test_module="test_delay_sample",
        test_args=run_test_args,
        waves=True,
    )


if __name__ == "__main__":
    delay_sample_runner()

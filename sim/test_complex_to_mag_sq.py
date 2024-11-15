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
async def test_complex_to_mag_sq(dut):
    """
    Ensures that the complex_to_mag_sq module is working correctly.
    """
    # Setup the module
    cocotb.start_soon(Clock(dut.clk_in, 10, units="ns").start())
    await reset(dut.clk_in, dut.rst_in, 2, 1)
    # Feed in some real data
    await RisingEdge(dut.clk_in)
    dut.i_in.value = 5
    dut.q_in.value = 5
    dut.iq_valid_in.value = 1
    await ClockCycles(dut.clk_in, 1)
    dut.iq_valid_in.value = 0
    await ClockCycles(dut.clk_in, 1)
    await FallingEdge(dut.clk_in)
    assert dut.mag_sq_valid_out.value == 1
    assert dut.mag_sq_out.value == 50


def complex_to_mag_sq_runner():
    """Simulate the downsampler using the Python runner."""
    sim = os.getenv("SIM", "icarus")
    proj_path = Path(__file__).resolve().parent.parent
    sys.path.append(str(proj_path / "sim" / "model"))
    sources = [
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/complex_to_mag_sq.sv",
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/complex_multiply.sv",
    ]
    build_test_args = ["-Wall"]  # ,"COCOTB_RESOLVE_X=ZEROS"]
    parameters = {}
    sys.path.append(str(proj_path / "sim"))
    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="complex_to_mag_sq",
        always=True,
        build_args=build_test_args,
        parameters=parameters,
        timescale=("1ns", "1ps"),
        waves=True,
    )
    run_test_args = []
    runner.test(
        hdl_toplevel="complex_to_mag_sq",
        test_module="test_complex_to_mag_sq",
        test_args=run_test_args,
        waves=True,
    )


if __name__ == "__main__":
    complex_to_mag_sq_runner()

# General imports
import os
import sys
from pathlib import Path
import random
import logging
import numpy as np

# cocotb imports
import cocotb
from cocotb.triggers import RisingEdge, ClockCycles, FallingEdge, ReadOnly
from cocotb.runner import get_runner
from cocotb.clock import Clock
from cocotb.handle import SimHandleBase

# Get current directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# Samples path
samples_path = os.path.join(current_dir, "samples.dat")


async def reset(clk, rst, cycles, value: int):
    """
    Reset the DUT
    """
    rst.value = value
    for _ in range(cycles + 1):
        print(_)
        await RisingEdge(clk)
    rst.value = 1 - value


@cocotb.test()
async def sample_data_test(dut):
    """
    Passes sample data from OpenOFDM to the power_trigger module
    """
    # Setup the DUT
    cocotb.start_soon(Clock(dut.clk_in, 10, units="ns").start())
    await reset(dut.clk_in, dut.rst_in, 1, 1)
    # Read the samples
    wave = np.fromfile(samples_path, dtype=np.uint16)
    n_samples = len(wave) // 2
    # Get the real and imaginary parts
    imag = wave[::2]
    real = wave[1::2]
    # Combine the values into 32 bit values
    values = []
    for i in range(n_samples):
        values.append((imag[i].astype(np.uint32) << 16) | real[i].astype(np.uint32))
    # Send the values to the DUT
    dut.signal_valid_in.value = 1
    dut.power_thresh_in.value = 100
    for i in range(n_samples):
        dut.signal_data_in.value = int(values[i])
        await RisingEdge(dut.clk_in)
    dut.signal_valid_in.value = 0


"""the code below should largely remain unchanged in structure, though the specific files and things
specified should get updated for different simulations.
"""


def power_trigger_runner():
    """Simulate the power trigger using the Python runner."""
    sim = os.getenv("SIM", "icarus")
    proj_path = Path(__file__).resolve().parent.parent
    sys.path.append(str(proj_path / "sim" / "model"))
    sources = [
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl/power_trigger.sv",
    ]  # grow/modify this as needed.
    includes = [
        proj_path / "WaveSense/ip_repo/csi_extractor_1_0/hdl",
    ]
    build_test_args = ["-Wall"]  # ,"COCOTB_RESOLVE_X=ZEROS"]
    parameters = {}
    sys.path.append(str(proj_path / "sim"))
    runner = get_runner(sim)
    runner.build(
        sources=sources,
        includes=includes,
        hdl_toplevel="power_trigger",
        always=True,
        build_args=build_test_args,
        parameters=parameters,
        timescale=("1ns", "1ps"),
        waves=True,
    )
    run_test_args = []
    runner.test(
        hdl_toplevel="power_trigger",
        test_module="test_power_trigger",
        test_args=run_test_args,
        waves=True,
    )


if __name__ == "__main__":
    power_trigger_runner()

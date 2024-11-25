// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// Copyright 2022-2024 Advanced Micro Devices, Inc. All Rights Reserved.
// --------------------------------------------------------------------------------
// Tool Version: Vivado v.2024.1 (lin64) Build 5076996 Wed May 22 18:36:09 MDT 2024
// Date        : Mon Nov 25 10:21:00 2024
// Host        : eecs-digital-26 running 64-bit Ubuntu 24.04.1 LTS
// Command     : write_verilog -force -mode synth_stub
//               /home/andiqu/WaveSense/WaveSense/ip_repo/csi_extractor_1_0/src/fir_compiler_0/fir_compiler_0_stub.v
// Design      : fir_compiler_0
// Purpose     : Stub declaration of top-level module interface
// Device      : xczu48dr-ffvg1517-2-e
// --------------------------------------------------------------------------------

// This empty module with port declaration file causes synthesis tools to infer a black box for IP.
// The synthesis directives are for Synopsys Synplify support to prevent IO buffer insertion.
// Please paste the declaration into a Verilog source file or add the file as an additional source.
(* x_core_info = "fir_compiler_v7_2_22,Vivado 2024.1" *)
module fir_compiler_0(aresetn, aclk, s_axis_data_tvalid, 
  s_axis_data_tready, s_axis_data_tdata, m_axis_data_tvalid, m_axis_data_tready, 
  m_axis_data_tdata)
/* synthesis syn_black_box black_box_pad_pin="aresetn,s_axis_data_tvalid,s_axis_data_tready,s_axis_data_tdata[31:0],m_axis_data_tvalid,m_axis_data_tready,m_axis_data_tdata[31:0]" */
/* synthesis syn_force_seq_prim="aclk" */;
  input aresetn;
  input aclk /* synthesis syn_isclock = 1 */;
  input s_axis_data_tvalid;
  output s_axis_data_tready;
  input [31:0]s_axis_data_tdata;
  output m_axis_data_tvalid;
  input m_axis_data_tready;
  output [31:0]m_axis_data_tdata;
endmodule

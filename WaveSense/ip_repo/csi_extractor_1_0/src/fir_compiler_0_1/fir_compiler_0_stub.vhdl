-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- Copyright 2022-2024 Advanced Micro Devices, Inc. All Rights Reserved.
-- --------------------------------------------------------------------------------
-- Tool Version: Vivado v.2024.1 (lin64) Build 5076996 Wed May 22 18:36:09 MDT 2024
-- Date        : Sun Nov 24 15:04:17 2024
-- Host        : eecs-digital-26 running 64-bit Ubuntu 24.04.1 LTS
-- Command     : write_vhdl -force -mode synth_stub
--               /home/andiqu/WaveSense/WaveSense/ip_repo/csi_extractor_1_0/src/fir_compiler_0_1/fir_compiler_0_stub.vhdl
-- Design      : fir_compiler_0
-- Purpose     : Stub declaration of top-level module interface
-- Device      : xczu48dr-ffvg1517-2-e
-- --------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity fir_compiler_0 is
  Port ( 
    aresetn : in STD_LOGIC;
    aclk : in STD_LOGIC;
    s_axis_data_tvalid : in STD_LOGIC;
    s_axis_data_tready : out STD_LOGIC;
    s_axis_data_tdata : in STD_LOGIC_VECTOR ( 31 downto 0 );
    m_axis_data_tvalid : out STD_LOGIC;
    m_axis_data_tready : in STD_LOGIC;
    m_axis_data_tdata : out STD_LOGIC_VECTOR ( 31 downto 0 )
  );

end fir_compiler_0;

architecture stub of fir_compiler_0 is
attribute syn_black_box : boolean;
attribute black_box_pad_pin : string;
attribute syn_black_box of stub : architecture is true;
attribute black_box_pad_pin of stub : architecture is "aresetn,aclk,s_axis_data_tvalid,s_axis_data_tready,s_axis_data_tdata[31:0],m_axis_data_tvalid,m_axis_data_tready,m_axis_data_tdata[31:0]";
attribute x_core_info : string;
attribute x_core_info of stub : architecture is "fir_compiler_v7_2_22,Vivado 2024.1";
begin
end;

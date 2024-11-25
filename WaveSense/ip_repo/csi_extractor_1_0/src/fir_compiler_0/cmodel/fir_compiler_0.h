
//------------------------------------------------------------------------------
// (c) Copyright 2023 Advanced Micro Devices. All rights reserved.
//
// This file contains confidential and proprietary information
// of AMD, Inc. and is protected under U.S. and
// international copyright and other intellectual property
// laws.
//
// DISCLAIMER
// This disclaimer is not a license and does not grant any
// rights to the materials distributed herewith. Except as
// otherwise provided in a valid license issued to you by
// AMD, and to the maximum extent permitted by applicable
// law: (1) THESE MATERIALS ARE MADE AVAILABLE "AS IS" AND
// WITH ALL FAULTS, AND AMD HEREBY DISCLAIMS ALL WARRANTIES
// AND CONDITIONS, EXPRESS, IMPLIED, OR STATUTORY, INCLUDING
// BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY, NON-
// INFRINGEMENT, OR FITNESS FOR ANY PARTICULAR PURPOSE; and
// (2) AMD shall not be liable (whether in contract or tort,
// including negligence, or under any other theory of
// liability) for any loss or damage of any kind or nature
// related to, arising under or in connection with these
// materials, including for any direct, or any indirect,
// special, incidental, or consequential loss or damage
// (including loss of data, profits, goodwill, or any type of
// loss or damage suffered as a result of any action brought
// by a third party) even if such damage or loss was
// reasonably foreseeable or AMD had been advised of the
// possibility of the same.
//
// CRITICAL APPLICATIONS
// AMD products are not designed or intended to be fail-
// safe, or for use in any application requiring fail-safe
// performance, such as life-support or safety devices or
// systems, Class III medical devices, nuclear facilities,
// applications related to the deployment of airbags, or any
// other applications that could lead to death, personal
// injury, or severe property or environmental damage
// (individually and collectively, "Critical
// Applications"). Customer assumes the sole risk and
// liability of any use of AMD products in Critical
// Applications, subject only to applicable laws and
// regulations governing limitations on product liability.
//
// THIS COPYRIGHT NOTICE AND DISCLAIMER MUST BE RETAINED AS
// PART OF THIS FILE AT ALL TIMES.
//------------------------------------------------------------------------------ 
//
// C Model configuration for the "fir_compiler_0" instance.
//
//------------------------------------------------------------------------------
//
// coefficients: -0.0002080117075788305,-0.0019319507649830719,-0.002937226519262469,-0.004326588065160176,-0.0051672711371284095,-0.005019062101378063,-0.0035767154568100883,-0.0009281389796082299,0.0023613478501919097,0.005333457126111164,0.006894723337460544,0.006201433140789667,0.0030451586612048804,-0.0019177758270619257,-0.0072150249072798845,-0.010929236567170339,-0.011322347741609937,-0.007527322543332624,-0.000059006652998551963,0.009080774115522161,0.01682367147890624,0.019932611525077207,0.016144159097537646,0.005196571505860679,-0.010627719591396084,-0.026706632143446568,-0.03708100855416565,-0.03604658800009165,-0.01990565599852336,0.011647146706817872,0.054963682407976895,0.10295065140251855,0.14658475775497948,0.17706169207906836,0.1879970473607177,0.17706169207906836,0.14658475775497948,0.10295065140251855,0.054963682407976895,0.011647146706817872,-0.01990565599852336,-0.03604658800009165,-0.03708100855416565,-0.026706632143446568,-0.010627719591396084,0.005196571505860679,0.016144159097537646,0.019932611525077207,0.01682367147890624,0.009080774115522161,-0.000059006652998551963,-0.007527322543332624,-0.011322347741609937,-0.010929236567170339,-0.0072150249072798845,-0.0019177758270619257,0.0030451586612048804,0.006201433140789667,0.006894723337460544,0.005333457126111164,0.0023613478501919097,-0.0009281389796082299,-0.0035767154568100883,-0.005019062101378063,-0.0051672711371284095,-0.004326588065160176,-0.002937226519262469,-0.0019319507649830719,-0.0002080117075788305
// chanpats: 173
// name: fir_compiler_0
// filter_type: 0
// rate_change: 0
// interp_rate: 1
// decim_rate: 1
// zero_pack_factor: 1
// coeff_padding: 0
// num_coeffs: 69
// coeff_sets: 1
// reloadable: 0
// is_halfband: 0
// quantization: 1
// coeff_width: 16
// coeff_fract_width: 16
// chan_seq: 0
// num_channels: 1
// num_paths: 2
// data_width: 16
// data_fract_width: 0
// output_rounding_mode: 1
// output_width: 16
// output_fract_width: 0
// config_method: 0

const double fir_compiler_0_coefficients[69] = {-0.0002080117075788305,-0.0019319507649830719,-0.002937226519262469,-0.004326588065160176,-0.0051672711371284095,-0.005019062101378063,-0.0035767154568100883,-0.0009281389796082299,0.0023613478501919097,0.005333457126111164,0.006894723337460544,0.006201433140789667,0.0030451586612048804,-0.0019177758270619257,-0.0072150249072798845,-0.010929236567170339,-0.011322347741609937,-0.007527322543332624,-0.000059006652998551963,0.009080774115522161,0.01682367147890624,0.019932611525077207,0.016144159097537646,0.005196571505860679,-0.010627719591396084,-0.026706632143446568,-0.03708100855416565,-0.03604658800009165,-0.01990565599852336,0.011647146706817872,0.054963682407976895,0.10295065140251855,0.14658475775497948,0.17706169207906836,0.1879970473607177,0.17706169207906836,0.14658475775497948,0.10295065140251855,0.054963682407976895,0.011647146706817872,-0.01990565599852336,-0.03604658800009165,-0.03708100855416565,-0.026706632143446568,-0.010627719591396084,0.005196571505860679,0.016144159097537646,0.019932611525077207,0.01682367147890624,0.009080774115522161,-0.000059006652998551963,-0.007527322543332624,-0.011322347741609937,-0.010929236567170339,-0.0072150249072798845,-0.0019177758270619257,0.0030451586612048804,0.006201433140789667,0.006894723337460544,0.005333457126111164,0.0023613478501919097,-0.0009281389796082299,-0.0035767154568100883,-0.005019062101378063,-0.0051672711371284095,-0.004326588065160176,-0.002937226519262469,-0.0019319507649830719,-0.0002080117075788305};

const xip_fir_v7_2_pattern fir_compiler_0_chanpats[1] = {P_BASIC};

static xip_fir_v7_2_config gen_fir_compiler_0_config() {
  xip_fir_v7_2_config config;
  config.name                = "fir_compiler_0";
  config.filter_type         = 0;
  config.rate_change         = XIP_FIR_INTEGER_RATE;
  config.interp_rate         = 1;
  config.decim_rate          = 1;
  config.zero_pack_factor    = 1;
  config.coeff               = &fir_compiler_0_coefficients[0];
  config.coeff_padding       = 0;
  config.num_coeffs          = 69;
  config.coeff_sets          = 1;
  config.reloadable          = 0;
  config.is_halfband         = 0;
  config.quantization        = XIP_FIR_QUANTIZED_ONLY;
  config.coeff_width         = 16;
  config.coeff_fract_width   = 16;
  config.chan_seq            = XIP_FIR_BASIC_CHAN_SEQ;
  config.num_channels        = 1;
  config.init_pattern        = fir_compiler_0_chanpats[0];
  config.num_paths           = 2;
  config.data_width          = 16;
  config.data_fract_width    = 0;
  config.output_rounding_mode= XIP_FIR_TRUNCATE_LSBS;
  config.output_width        = 16;
  config.output_fract_width  = 0,
  config.config_method       = XIP_FIR_CONFIG_SINGLE;
  return config;
}

const xip_fir_v7_2_config fir_compiler_0_config = gen_fir_compiler_0_config();


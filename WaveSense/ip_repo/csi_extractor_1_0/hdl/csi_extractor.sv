`timescale 1ns / 1ps
`default_nettype none

/*
 * Module `csi_extractor`
 *
 * Top-level module that extracts CSI from an 802.11 OFDM signal.
 */
module csi_extractor_sv (
    input wire clk_in,
    input wire rst_in,

    input wire signal_axis_tvalid,
    input wire [31:0] signal_axis_tdata,
    output logic signal_axis_tready,

    output logic csi_axis_tvalid, csi_axis_tlast,
    output logic [31:0] csi_axis_tdata,
    input wire csi_axis_tready,

    // For debugging
    input wire [3:0] sw_in,
    output logic [3:0] led_out
);

    logic signed [15:0] signal_i_data;
    assign signal_i_data = $signed(signal_axis_tdata[15:0]);

    logic signed [15:0] signal_q_data;
    assign signal_q_data = $signed(signal_axis_tdata[31:16]); 

    // // Stage 0: Downsample 122.88 MSPS -> 20 MSPS
    logic filter_axis_tready;
    
    logic I_signal_axis_tready;
    logic I_filter_axis_tvalid;
    logic signed [31:0] I_filter_axis_tdata;
    fir_17 #(
        .C_S_AXIS_TDATA_WIDTH(16),
        .C_M_AXIS_TDATA_WIDTH(27) // From bitgrowth output is 16+6 + log2(17) = 27 bits
    ) I_fir_inst (
        .aclk(clk_in),
        .aresetn(~rst_in),

        .s_axis_data_tvalid(signal_axis_tvalid),
        .s_axis_data_tdata(signal_i_data),
        .s_axis_data_tready(I_signal_axis_tready),

        .m_axis_data_tvalid(I_filter_axis_tvalid),
        .m_axis_data_tdata(I_filter_axis_tdata),
        .m_axis_data_tready(filter_axis_tready)
    );

    logic Q_signal_axis_tready;
    logic Q_filter_axis_tvalid;
    logic signed [31:0] Q_filter_axis_tdata;
    fir_17  #(
        .C_S_AXIS_TDATA_WIDTH(32),
        .C_M_AXIS_TDATA_WIDTH(32)
    ) Q_fir_inst (
        .aclk(clk_in),
        .aresetn(~rst_in),

        .s_axis_data_tvalid(signal_axis_tvalid),
        .s_axis_data_tdata(signal_q_data),
        .s_axis_data_tready(Q_signal_axis_tready),

        .m_axis_data_tvalid(Q_filter_axis_tvalid),
        .m_axis_data_tdata(Q_filter_axis_tdata),
        .m_axis_data_tready(filter_axis_tready)
    );

    assign signal_axis_tready = Q_signal_axis_tready;

    logic downsample_axis_tvalid, downsample_axis_tready;
    logic [31:0] downsample_axis_tdata;
    downsample downsample_inst (
        .s00_axis_aclk(clk_in),
        .s00_axis_aresetn(~rst_in),
        .s00_axis_tvalid(I_filter_axis_tvalid && Q_filter_axis_tvalid),
        .s00_axis_tdata({Q_filter_axis_tdata[26:11], I_filter_axis_tdata[26:11]}),
        .s00_axis_tready(filter_axis_tready),

        .m00_axis_aclk(clk_in),
        .m00_axis_aresetn(~rst_in),
        .m00_axis_tready(downsample_axis_tready),
        .m00_axis_tvalid(downsample_axis_tvalid),
        .m00_axis_tdata(downsample_axis_tdata)
    );

    // Stages 1-3: Extract LTS
    logic lts_axis_tvalid, lts_axis_tlast, lts_axis_tready;
    logic [15:0] lts_i_axis_tdata, lts_q_axis_tdata;
    lts_extractor lts_extractor_inst (
        .clk_in(clk_in),
        .rst_in(rst_in),

        .signal_axis_tvalid(downsample_axis_tvalid),
        .signal_axis_tdata(downsample_axis_tdata),
        .signal_axis_tready(downsample_axis_tready),

        .lts_axis_tvalid(lts_axis_tvalid),
        .lts_axis_tlast(lts_axis_tlast),
        .lts_axis_tdata({lts_q_axis_tdata, lts_i_axis_tdata}),
        .lts_axis_tready(lts_axis_tready),

        .sw_in(sw_in),
        .led_out(led_out)
    );

    // Stage 4: FFT of the LTS
    logic fft_axis_tvalid, fft_axis_tlast;
    logic [31:0] fft_axis_tdata;
    logic fft_axis_tready;
    block_fft fft_inst (
        .clk_in(clk_in),
        .rst_in(rst_in),

        .sample_axis_tvalid(lts_axis_tvalid),
        .sample_axis_tlast(lts_axis_tlast),
        .sample_re_axis_tdata(lts_i_axis_tdata),
        .sample_im_axis_tdata(lts_q_axis_tdata),
        .sample_axis_tready(lts_axis_tready),

        .fft_axis_tvalid(fft_axis_tvalid),
        .fft_axis_tlast(fft_axis_tlast),
        .fft_re_axis_tdata(fft_axis_tdata[15:0]),
        .fft_im_axis_tdata(fft_axis_tdata[31:16]),
        .fft_axis_tready(fft_axis_tready)
    );

    // Stage 5: Equalizer
    logic [15:0] csi_re_axis_tdata, csi_im_axis_tdata;
    assign csi_axis_tdata = {csi_re_axis_tdata, csi_im_axis_tdata};
    equalizer equalizer_inst (
        .clk_in(clk_in),
        .rst_in(rst_in),

        .fft_axis_tvalid(fft_axis_tvalid),
        .fft_axis_tlast(fft_axis_tlast),
        .fft_re_axis_tdata(fft_axis_tdata[15:0]),
        .fft_im_axis_tdata(fft_axis_tdata[31:16]),
        .fft_axis_tready(fft_axis_tready),

        .csi_axis_tvalid(csi_axis_tvalid),
        .csi_axis_tlast(csi_axis_tlast),
        .csi_re_axis_tdata(csi_re_axis_tdata),
        .csi_im_axis_tdata(csi_im_axis_tdata),
        .csi_axis_tready(csi_axis_tready)
    );

endmodule

`default_nettype wire

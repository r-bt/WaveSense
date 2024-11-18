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
    output logic [3:0] led_out,
    output logic downsample_valid_out,
    output logic [31:0] downsample_data_out
);

    typedef enum {
        WAIT_POWER_TRIGGER,
        SYNC_SHORT,
        SYNC_LONG
    } state_t;
    state_t state;

    // Stage 0: Downsample 122.88 MSPS -> 20 MSPS
    logic downsample_valid, downsample_ready;
    logic [31:0] downsample_data;
    downsample downsample_inst (
        .s00_axis_aclk(clk_in),
        .s00_axis_aresetn(~rst_in),
        .s00_axis_tvalid(signal_axis_tvalid),
        .s00_axis_tdata(signal_axis_tdata),
        .s00_axis_tready(signal_axis_tready),

        .m00_axis_aclk(clk_in),
        .m00_axis_aresetn(~rst_in),
        .m00_axis_tready(downsample_ready),
        .m00_axis_tvalid(downsample_valid),
        .m00_axis_tdata(downsample_data)
    );
    // For debugging
    assign downsample_valid_out = downsample_valid && state != WAIT_POWER_TRIGGER;
    assign downsample_data_out = downsample_data;

    // Stage 1: Power trigger
    logic power_trigger;
    power_trigger #(
        .POWER_THRESH(2000)
    ) power_trigger_inst (
        .clk_in(clk_in),
        .rst_in(rst_in),

        .signal_data_in(downsample_data),
        .signal_valid_in(downsample_valid),

        .trigger_out(power_trigger)
    );

    // Stage 2: Detect the short preamble
    logic sync_short_rst;
    logic short_preamble_detected;
    sync_short sync_short_inst (
        .clk_in(clk_in),
        .rst_in(rst_in || sync_short_rst),

        .sample_in(downsample_data),
        .sample_in_valid(downsample_valid && (state == SYNC_SHORT)),

        .short_preamble_detected(short_preamble_detected)
    );

    // Stage 3: Detect the long preamble
    logic sync_long_rst;
    logic [15:0] sample_cnt;
    logic lts_axis_tvalid, lts_axis_tlast;
    logic [15:0] lts_i_axis_tdata, lts_q_axis_tdata;
    logic lts_axis_tready;
    sync_long sync_long_inst (
        .clk_in(clk_in),
        .rst_in(rst_in || sync_long_rst),

        .signal_axis_tvalid(downsample_valid && (state == SYNC_LONG)),
        .signal_i_axis_tdata(downsample_data[31:16]),
        .signal_q_axis_tdata(downsample_data[15:0]),
        .signal_axis_tready(downsample_ready),

        .lts_axis_tvalid(lts_axis_tvalid),
        .lts_axis_tlast(lts_axis_tlast),
        .lts_i_axis_tdata(lts_i_axis_tdata),
        .lts_q_axis_tdata(lts_q_axis_tdata),
        .lts_axis_tready(lts_axis_tready)
    );

    // Stage 4: FFT of the LTS
    logic fft_axis_tvalid, fft_axis_tlast;
    logic [31:0] fft_axis_tdata;
    logic fft_axis_tready;
    xfft_0 xfft_0_inst (
        .aclk(clk_in),
        .aresetn(~rst_in),

        .s_axis_data_tvalid(lts_axis_tvalid),
        .s_axis_data_tlast(lts_axis_tlast),
        .s_axis_data_tdata({lts_q_axis_tdata, lts_i_axis_tdata}),
        .s_axis_data_tready(lts_axis_tready),

        .m_axis_data_tvalid(fft_axis_tvalid),
        .m_axis_data_tlast(fft_axis_tlast),
        .m_axis_data_tdata(fft_axis_tdata),
        .m_axis_data_tready(fft_axis_tready)
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

    // Assign LEDs different meanings based on switches
    always_comb begin
        case (sw_in)
            4'b0000: begin
                led_out = {
                    power_trigger,
                    short_preamble_detected,
                    lts_axis_tvalid,
                    csi_axis_tvalid
                };
            end
            4'b0001: begin
                led_out = {
                    power_trigger,
                    downsample_valid,
                    fft_axis_tvalid,
                    fft_axis_tlast
                };
            end
            4'b0010: begin
                led_out = {
                    1'b0,
                    state == WAIT_POWER_TRIGGER,
                    state == SYNC_SHORT,
                    state == SYNC_LONG
                };
            end
            4'b0100: begin
                led_out = {
                    signal_axis_tready,
                    csi_axis_tready,
                    downsample_ready,
                    lts_axis_tready
                };
            end
            default: begin
                led_out = sample_cnt[3:0];
            end
        endcase
    end


    // State machine for control flow
    always_ff @(posedge clk_in) begin
        if (rst_in) begin
            state <= WAIT_POWER_TRIGGER;
            sync_short_rst <= 0;
            sync_long_rst <= 0;
            sample_cnt <= 0;
        end else begin
            case (state)
                WAIT_POWER_TRIGGER: begin
                    if (power_trigger) begin
                        sync_short_rst <= 1;
                        state <= SYNC_SHORT;
                    end
                end

                SYNC_SHORT: begin
                    sync_short_rst <= 0;
                    // Transition back to idle if power level drops
                    if (~power_trigger) begin
                        state <= WAIT_POWER_TRIGGER;
                    end

                    if (short_preamble_detected) begin
                        sync_long_rst <= 1;
                        sample_cnt <= 0;
                        state <= SYNC_LONG;
                    end
                end

                SYNC_LONG: begin
                    sync_long_rst <= 0;

                    if (downsample_valid) begin
                        sample_cnt <= sample_cnt + 1;
                    end

                    if (sample_cnt > 320 || ~power_trigger
                        || csi_axis_tlast) begin
                            state <= WAIT_POWER_TRIGGER;
                    end
                end
            endcase
        end
    end
endmodule

`default_nettype wire

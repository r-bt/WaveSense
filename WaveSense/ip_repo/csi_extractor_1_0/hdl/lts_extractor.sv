`timescale 1ns / 1ps
`default_nettype none

/*
 * Module `lts_extractor`
 *
 * Finds and outputs the two LTS sequences.
 */
module lts_extractor (
    input wire clk_in,
    input wire rst_in,

    input wire signal_axis_tvalid,
    input wire [31:0] signal_axis_tdata,
    output logic signal_axis_tready,

    output logic lts_axis_tvalid, lts_axis_tlast,
    output logic [31:0] lts_axis_tdata,
    input wire lts_axis_tready,

    input wire [3:0] sw_in,
    output logic [3:0] led_out
);

    typedef enum {
        WAIT_POWER_TRIGGER,
        SYNC_SHORT,
        SYNC_LONG
    } state_t;
    state_t state;

    // Stage 1: Power trigger
    logic power_trigger;
    power_trigger power_trigger_inst (
        .clk_in(clk_in),
        .rst_in(rst_in),
        .power_thresh_in(50 + (sw_in << 5)),

        .signal_data_in(signal_axis_tdata),
        .signal_valid_in(signal_axis_tvalid),

        .trigger_out(power_trigger)
    );

    // Stage 2: Detect the short preamble
    logic sync_short_rst;
    logic short_preamble_detected;
    sync_short sync_short_inst (
        .clk_in(clk_in),
        .rst_in(rst_in || sync_short_rst),

        .sample_in(signal_axis_tdata),
        .sample_in_valid(signal_axis_tvalid && (state == SYNC_SHORT)),

        .short_preamble_detected(short_preamble_detected)
    );

    // Stage 3: Detect the long preamble
    logic sync_long_rst;
    logic [15:0] sample_cnt;
    logic [15:0] lts_i_axis_tdata, lts_q_axis_tdata;
    sync_long sync_long_inst (
        .clk_in(clk_in),
        .rst_in(rst_in || sync_long_rst),

        .signal_axis_tvalid(signal_axis_tvalid && (state == SYNC_LONG)),
        .signal_i_axis_tdata(signal_axis_tdata[31:16]),
        .signal_q_axis_tdata(signal_axis_tdata[15:0]),
        .signal_axis_tready(signal_axis_tready),

        .lts_axis_tvalid(lts_axis_tvalid),
        .lts_axis_tlast(lts_axis_tlast),
        .lts_i_axis_tdata(lts_i_axis_tdata),
        .lts_q_axis_tdata(lts_q_axis_tdata),
        .lts_axis_tready(lts_axis_tready)
    );
    assign lts_axis_tdata = {lts_i_axis_tdata, lts_q_axis_tdata};

    // Visualize the state using the LEDs
    assign led_out = {
        state == lts_axis_tvalid,
        state == WAIT_POWER_TRIGGER,
        state == SYNC_SHORT,
        state == SYNC_LONG
    };

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

                    if (signal_axis_tvalid) begin
                        sample_cnt <= sample_cnt + 1;
                    end

                    if (sample_cnt > 320 || ~power_trigger || lts_axis_tlast) begin
                            state <= WAIT_POWER_TRIGGER;
                    end
                end
            endcase
        end
    end
endmodule

`default_nettype wire

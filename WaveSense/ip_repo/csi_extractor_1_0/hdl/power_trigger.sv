`timescale 1ns / 1ps
`default_nettype none

module power_trigger #(
    parameter integer POWER_THRESH = 1000,
    parameter integer POWER_WIN_LEN = 80,
    parameter integer SKIP_SAMPLE = 0
) (
    input wire clk_in,
    input wire rst_in,

    input wire [31:0] signal_data_in,
    input wire signal_valid_in,

    output logic trigger_out
);

    typedef enum {SKIP, IDLE, PACKET} state_t;
    state_t state;

    logic [15:0] sample_cnt;
    logic [15:0] abs_i;
    assign abs_i = signal_data_in[31] ? (~signal_data_in[31:16]) + 1
                                      : signal_data_in[31:16];

    always_ff @(posedge clk_in) begin
        if (rst_in) begin
            sample_cnt <= 0;
            trigger_out <= 0;
            state <= SKIP;
        end else if (signal_valid_in) begin
            case (state)
                SKIP: begin
                    if (sample_cnt < SKIP_SAMPLE) begin
                        sample_cnt <= sample_cnt + 1;
                    end else begin
                        sample_cnt <= 0;
                        state <= IDLE;
                    end
                end

                IDLE: begin
                    if (abs_i >= POWER_THRESH) begin
                        trigger_out <= 1;
                        state <= PACKET;
                    end
                end

                PACKET: begin
                    if (abs_i < POWER_THRESH) begin
                        if (sample_cnt < POWER_WIN_LEN) begin
                            sample_cnt <= sample_cnt + 1;
                        end else begin
                            trigger_out <= 0;
                            sample_cnt <= 0;
                            state <= IDLE;
                        end
                    end else begin
                        sample_cnt <= 0;
                    end
                end
            endcase
        end
    end

endmodule

`default_nettype wire

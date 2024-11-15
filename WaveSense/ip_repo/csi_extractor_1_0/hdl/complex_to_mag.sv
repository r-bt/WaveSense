`timescale 1ns / 1ps
`default_nettype none

/*
 * Module `complex_to_mag`
 *
 * Converts complex numbers to magnitude.
 *
 * TODO: Make this AXI maybe?
 */
module complex_to_mag #(
    parameter integer DATA_WIDTH = 32
) (
    input wire  clk_in, rst_in,
    input wire signed [DATA_WIDTH-1 : 0] i_in, q_in,
    input wire  iq_valid_in,
    output logic [DATA_WIDTH-1 : 0] mag_out,
    output logic  mag_valid_out
);

    logic [DATA_WIDTH-1 : 0] abs_i, abs_q;
    logic [DATA_WIDTH-1 : 0] min, max;

    always_comb begin
        abs_i = i_in[DATA_WIDTH-1] ? (~i_in + 1) : i_in;
        abs_q = q_in[DATA_WIDTH-1] ? (~q_in + 1) : q_in;
        min = abs_i < abs_q ? abs_i : abs_q;
        max = abs_i > abs_q ? abs_i : abs_q;
    end

    always_ff @(posedge clk_in) begin
        if (rst_in) begin
            mag_out <= 0;
            mag_valid_out <= 0;
        end else begin
            mag_out <= max + (min >> 2);
            mag_valid_out <= iq_valid_in;
        end
    end

endmodule

`default_nettype wire

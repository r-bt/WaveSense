`timescale 1ns / 1ps
`default_nettype none

/*
 * Module `complex_multiply`
 *
 * A module that multiplies two complex numbers.
 */
module complex_multiply #(
    parameter integer DATA_WIDTH = 16
) (
    input wire clk_in,

    input wire signed [DATA_WIDTH-1:0] i0_in, q0_in, i1_in, q1_in,
    input wire valid_in,
    output logic signed [2*DATA_WIDTH-1:0] i_out, q_out,
    output logic valid_out
);

    always_ff @(posedge clk_in) begin
        if (valid_in) begin
            i_out <= i0_in * i1_in - q0_in * q1_in;
            q_out <= i0_in * q1_in + q0_in * i1_in;
            valid_out <= 1;
        end else begin
            valid_out <= 0;
        end
    end

endmodule

`default_nettype wire

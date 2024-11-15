`timescale 1ns / 1ps
`default_nettype none

/*
 * Module `complex_to_mag_sq`
 *
 * Calcualtes the squared magnitude of a complex number.
 *
 * TODO: Make this AXI maybe?
 */
module complex_to_mag_sq #(
    parameter integer DATA_WIDTH = 16
) (
    input wire  clk_in, rst_in,

    input wire signed [DATA_WIDTH-1 : 0] i_in, q_in,
    input wire iq_valid_in,

    output logic [2*DATA_WIDTH-1 : 0] mag_sq_out,
    output logic  mag_sq_valid_out
);

    logic valid_in;
    logic [DATA_WIDTH-1 : 0] input_i, input_q;
    logic [DATA_WIDTH-1 : 0] input_q_neg; 

    complex_multiply mult_in (
      .clk_in(clk_in),

      .i0_in(input_i), .q0_in(input_q),
      .i1_in(input_i), .q1_in(input_q_neg),
      .valid_in(valid_in),

      .i_out(mag_sq_out), .q_out(),
      .valid_out(mag_sq_valid_out)
    );

    always_ff @(posedge clk_in) begin
        if (rst_in) begin
            input_i <= 0;
            input_q <= 0;
            input_q_neg <= 0;
            valid_in <= 0;
        end else begin
            input_i <= i_in;
            input_q <= q_in;
            input_q_neg <= ~q_in + 1;
            valid_in <= iq_valid_in;
        end
    end

endmodule

`default_nettype wire

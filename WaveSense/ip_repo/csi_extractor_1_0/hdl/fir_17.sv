`timescale 1ns / 1ps
`default_nettype none

/*
 * Module `fir_17`
 *
 * 17-tap FIR filter to low-pass below 10 MHz, assuming Fs = 122.88 MHz.
 */
module fir_17 #(
    parameter integer C_S00_AXIS_TDATA_WIDTH  = 32,
    parameter integer C_M00_AXIS_TDATA_WIDTH  = 32
) (
    // Ports of Axi Slave Bus Interface S00_AXIS
    input wire  s00_axis_aclk, s00_axis_aresetn,
    input wire  s00_axis_tvalid,
    input wire signed [C_S00_AXIS_TDATA_WIDTH-1 : 0] s00_axis_tdata,
    output logic  s00_axis_tready,
 
    // Ports of Axi Master Bus Interface M00_AXIS
    input wire  m00_axis_aclk, m00_axis_aresetn,
    input wire  m00_axis_tready,
    output logic  m00_axis_tvalid,
    output logic [C_M00_AXIS_TDATA_WIDTH-1 : 0] m00_axis_tdata
);
 
    // localparam NUM_COEFFS = 25;
    localparam NUM_COEFFS = 17;
    logic signed [7:0] coeffs [NUM_COEFFS-1 : 0];
    //initializing values
    // TODO: Handle overflow correctly
    initial begin
        // coeffs[0] = 1;
        // coeffs[1] = 1;
        // coeffs[2] = 1;
        // coeffs[3] = 0;
        // coeffs[4] = -2;
        // coeffs[5] = -4;
        // coeffs[6] = -5;
        // coeffs[7] = -3;
        // coeffs[8] = 3;
        // coeffs[9] = 11;
        // coeffs[10] = 19;
        // coeffs[11] = 26;
        // coeffs[12] = 29;
        // coeffs[13] = 26;
        // coeffs[14] = 19;
        // coeffs[15] = 11;
        // coeffs[16] = 3;
        // coeffs[17] = -3;
        // coeffs[18] = 5;
        // coeffs[19] = -4;
        // coeffs[20] = -2;
        // coeffs[21] = 0;
        // coeffs[22] = 1;
        // coeffs[23] = 1;
        // coeffs[24] = 1;
        coeffs[0] = -1;
        coeffs[1] = -2;
        coeffs[2] = -2;
        coeffs[3] = 0;
        coeffs[4] = 6;
        coeffs[5] = 13;
        coeffs[6] = 21;
        coeffs[7] = 27;
        coeffs[8] = 29;
        coeffs[9] = 27;
        coeffs[10] = 21;
        coeffs[11] = 13;
        coeffs[12] = 6;
        coeffs[13] = 0;
        coeffs[14] = -2;
        coeffs[15] = -2;
        coeffs[16] = -1;
        for(int i=0; i<NUM_COEFFS; i++)begin
            y_reg[i] = 0;
        end
    end

    logic signed [C_M00_AXIS_TDATA_WIDTH-1:0] y_reg [NUM_COEFFS-1:0];
    assign m00_axis_tdata = y_reg[0];
    logic [NUM_COEFFS-1:0] valid_reg;
    assign m00_axis_tvalid = valid_reg[0];
    assign s00_axis_tready = m00_axis_tready || ~valid_reg[0];

    always_ff @(posedge s00_axis_aclk) begin
        if (~s00_axis_aresetn) begin
            for (int i = 0; i < NUM_COEFFS; i++) begin
                y_reg[i] <= 0;
                valid_reg[i] <= 0;
            end
        end else if (s00_axis_tvalid && (m00_axis_tready || ~valid_reg[0])) begin
            for (int i = 0; i < NUM_COEFFS - 1; i++) begin
                y_reg[i] <= y_reg[i + 1] + s00_axis_tdata * coeffs[i];
                valid_reg[i] <= valid_reg[i + 1];
            end
            y_reg[NUM_COEFFS - 1] <= s00_axis_tdata * coeffs[NUM_COEFFS - 1];
            valid_reg[NUM_COEFFS - 1] <= s00_axis_tvalid;
        end else if (m00_axis_tready) begin
            valid_reg[0] <= 0;
        end
    end
 
endmodule

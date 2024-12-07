`timescale 1ns / 1ps
`default_nettype none

/*
 * Module `fir_17`
 *
 * 17-tap FIR filter to low-pass below 10 MHz, assuming Fs = 122.88 MHz.
 */
module fir_17 #(
    parameter integer C_S_AXIS_TDATA_WIDTH  = 16,
    parameter integer C_M_AXIS_TDATA_WIDTH  = 16
) (
    input wire aclk,
    input wire aresetn,

    // Ports of Axi Slave Bus Interface s_AXIS
    input wire  s_axis_data_tvalid,
    input wire signed [C_S_AXIS_TDATA_WIDTH-1 : 0] s_axis_data_tdata,
    output logic  s_axis_data_tready,

    // Ports of Axi Master Bus Interface m_AXIS
    input wire  m_axis_data_tready,
    output logic  m_axis_data_tvalid,
    output logic signed [C_M_AXIS_TDATA_WIDTH-1 : 0] m_axis_data_tdata
);

    // localparam NUM_COEFFS = 25;
    localparam NUM_COEFFS = 17;
    logic signed [5:0] coeffs [NUM_COEFFS-1 : 0];
    //initializing values
    // TODO: Handle overflow correctly
    initial begin
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

    logic signed [C_M_AXIS_TDATA_WIDTH-1:0] y_reg [NUM_COEFFS-1:0];
    assign m_axis_data_tdata = y_reg[0];
    logic [NUM_COEFFS-1:0] valid_reg;
    assign m_axis_data_tvalid = valid_reg[0];
    assign s_axis_data_tready = m_axis_data_tready || ~valid_reg[0];

    always_ff @(posedge aclk) begin
        if (~aresetn) begin
            for (int i = 0; i < NUM_COEFFS; i++) begin
                y_reg[i] <= 0;
                valid_reg[i] <= 0;
            end
        end else if (s_axis_data_tvalid && (m_axis_data_tready || ~valid_reg[0])) begin
            for (int i = 0; i < NUM_COEFFS - 1; i++) begin
                y_reg[i] <= y_reg[i + 1] + s_axis_data_tdata * coeffs[i];
                valid_reg[i] <= valid_reg[i + 1];
            end
            y_reg[NUM_COEFFS - 1] <= s_axis_data_tdata * coeffs[NUM_COEFFS - 1];
            valid_reg[NUM_COEFFS - 1] <= s_axis_data_tvalid;
        end else if (m_axis_data_tready) begin
            valid_reg[0] <= 0;
        end
    end

endmodule

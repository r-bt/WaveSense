`timescale 1ns / 1ps
`default_nettype none

/*
 * Module `downsample`
 *
 * Downsamples from a high (122.88 MSPS) sampling rate to a lower
 * (20 MSPS) rate to make CSI extraction easier.
 *
 * Super simple for now: zero-order hold (no interpolation).
 */
module downsample #(
    parameter integer SAMPLE_RATE_IN = 122_880,
    parameter integer SAMPLE_RATE_OUT = 20_000,
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

    // Step 1: Filter out high-frequency components of high-frequency input
    logic filtered_valid, filtered_ready;
    logic [C_S00_AXIS_TDATA_WIDTH-1:0] filtered_data;
    fir_17 fir_17_inst (
        .s00_axis_aclk(s00_axis_aclk),
        .s00_axis_aresetn(s00_axis_aresetn),
        .s00_axis_tvalid(s00_axis_tvalid),
        .s00_axis_tdata(s00_axis_tdata),
        .s00_axis_tready(s00_axis_tready),

        .m00_axis_aclk(m00_axis_aclk),
        .m00_axis_aresetn(m00_axis_aresetn),
        .m00_axis_tvalid(filtered_valid),
        .m00_axis_tdata(filtered_data),
        .m00_axis_tready(filtered_ready)
    );

    // Step 2: Downsample
    logic [$clog2(SAMPLE_RATE_IN):0] counter;
    assign filtered_ready = m00_axis_tready || ~m00_axis_tvalid;
    always_ff @(posedge s00_axis_aclk) begin
        if (~s00_axis_aresetn) begin
            counter <= 0;
            m00_axis_tvalid <= 0;
        end else if (filtered_valid && filtered_ready) begin
            if (counter + SAMPLE_RATE_OUT >= SAMPLE_RATE_IN) begin
                counter <= counter + SAMPLE_RATE_OUT - SAMPLE_RATE_IN;
                m00_axis_tvalid <= 1;
                m00_axis_tdata <= filtered_data;
            end else begin
                counter <= counter + SAMPLE_RATE_OUT;
                if (m00_axis_tready) begin
                    m00_axis_tvalid <= 0;
                end
            end
        end else if (m00_axis_tready) begin
            m00_axis_tvalid <= 0;
        end
    end

endmodule

`default_nettype wire
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
    parameter integer SAMPLE_RATE_OUT = 20_000
) (
    // Ports of Axi Slave Bus Interface S00_AXIS
    input wire s00_axis_aclk, s00_axis_aresetn,
    input wire s00_axis_tvalid,
    input wire [31:0] s00_axis_tdata,
    output logic s00_axis_tready,

    // Ports of Axi Master Bus Interface M00_AXIS
    input wire m00_axis_aclk, m00_axis_aresetn,
    input wire m00_axis_tready,
    output logic m00_axis_tvalid,
    output logic [31:0] m00_axis_tdata
);
    // Step 2: Downsample
    logic [$clog2(SAMPLE_RATE_IN):0] counter;
    assign s00_axis_tready = m00_axis_tready || ~m00_axis_tvalid;
    always_ff @(posedge s00_axis_aclk) begin
        if (~s00_axis_aresetn) begin
            counter <= 0;
            m00_axis_tvalid <= 0;
        end else if (s00_axis_tvalid && s00_axis_tready) begin
            if (counter + SAMPLE_RATE_OUT >= SAMPLE_RATE_IN) begin
                counter <= counter + SAMPLE_RATE_OUT - SAMPLE_RATE_IN;
                m00_axis_tvalid <= 1;
                m00_axis_tdata <= s00_axis_tdata;
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

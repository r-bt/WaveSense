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
    parameter integer DATA_WIDTH = 32
) (
    input wire clk_in,
    input wire rst_in,

    input wire signal_axis_tvalid,
    input wire [DATA_WIDTH-1:0] signal_axis_tdata,
    output logic signal_axis_tready,

    input wire downsample_axis_tready,
    output logic downsample_axis_tvalid,
    output logic [DATA_WIDTH-1:0] downsample_axis_tdata
);

    logic [$clog2(SAMPLE_RATE_IN):0] counter;
    assign signal_axis_tready = downsample_axis_tready || ~downsample_axis_tvalid;
    always_ff @(posedge clk_in) begin
        if (rst_in) begin
            counter <= 0;
            downsample_axis_tvalid <= 0;
        end else if (signal_axis_tvalid && signal_axis_tready) begin
            if (counter + SAMPLE_RATE_OUT >= SAMPLE_RATE_IN) begin
                counter <= counter + SAMPLE_RATE_OUT - SAMPLE_RATE_IN;
                downsample_axis_tvalid <= 1;
                downsample_axis_tdata <= signal_axis_tdata;
            end else begin
                if (signal_axis_tready) begin
                    counter <= counter + SAMPLE_RATE_OUT;
                end
                if (downsample_axis_tready) begin
                    downsample_axis_tvalid <= 0;
                end
            end
        end else if (downsample_axis_tready) begin
            downsample_axis_tvalid <= 0;
        end
    end

endmodule

`default_nettype wire

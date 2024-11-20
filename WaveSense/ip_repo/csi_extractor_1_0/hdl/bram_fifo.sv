`timescale 1ns / 1ps
`default_nettype none

/*
 * Module `bram_fifo`
 *
 * A small FIFO with a fixed depth to deal with BRAM latency.
 */
module bram_fifo #(
    parameter integer DEPTH=4,
    parameter integer WIDTH=33
) (
    input wire clk_in,
    input wire rst_in,

    input wire s_axis_tvalid,
    input wire [WIDTH-1:0] s_axis_tdata,

    output logic m_axis_tvalid,
    output logic [WIDTH-1:0] m_axis_tdata,
    input wire m_axis_tready
);

    logic [DEPTH-1:0] valid_buf;
    logic [WIDTH-1:0] data_buf [DEPTH-1:0];

    assign m_axis_tvalid = valid_buf[0];
    assign m_axis_tdata = data_buf[0];

    always_ff @(posedge clk_in) begin
        if (rst_in) begin
            for (int i = 0; i < DEPTH; i++) begin
                valid_buf[i] <= 0;
                data_buf[i] <= 0;
            end
        end else begin
            if (m_axis_tready) begin
                for (int i = 1; i < DEPTH; i++) begin
                    // Ingest new data when possible
                    if (s_axis_tvalid && (valid_buf[i - 1] || i == 1) && ~valid_buf[i]) begin
                        valid_buf[i - 1] <= 1;
                        data_buf[i - 1] <= s_axis_tdata;
                    end else begin
                        valid_buf[i - 1] <= valid_buf[i];
                        data_buf[i - 1] <= data_buf[i];
                    end
                end
                // Worst case, add to the very last register
                if (s_axis_tvalid && valid_buf[DEPTH - 1]) begin
                    valid_buf[DEPTH - 1] <= 1;
                    data_buf[DEPTH - 1] <= s_axis_tdata;
                end else begin
                    valid_buf[DEPTH - 1] <= 0;
                    data_buf[DEPTH - 1] <= 0;
                end
            end else if (s_axis_tvalid && ~valid_buf[DEPTH - 1]) begin
                // Ingest new data when possible
                for (int i = 1; i < DEPTH; i++) begin
                    if (valid_buf[i - 1] && ~valid_buf[i]) begin
                        valid_buf[i] <= 1;
                        data_buf[i] <= s_axis_tdata;
                    end
                end
                // Best case, add to the very first register
                if (~valid_buf[0]) begin
                    valid_buf[0] <= 1;
                    data_buf[0] <= s_axis_tdata;
                end
            end
        end
    end

endmodule

`default_nettype wire

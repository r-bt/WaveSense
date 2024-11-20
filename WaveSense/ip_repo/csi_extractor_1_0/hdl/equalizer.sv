`timescale 1ns / 1ps
`default_nettype none

/*
 * Module `equalizer`
 *
 * Given the FFTs of the two LTS sequences, computes the channel
 * frequency response and returns that as the CSI.
 */
module equalizer (
    input wire clk_in,
    input wire rst_in,
    // Input signal: FFT of the two LTS sequences (length 64 each)
    input wire fft_axis_tvalid, fft_axis_tlast,
    input wire signed [15:0] fft_re_axis_tdata, fft_im_axis_tdata,
    output logic fft_axis_tready,
    // Output signal: The channel frequency response
    output logic csi_axis_tvalid, csi_axis_tlast,
    output logic signed [15:0] csi_re_axis_tdata, csi_im_axis_tdata,
    input wire csi_axis_tready
);

    // Masks for deciding whether H[i] is positive, negative, or zero
    localparam POS_MASK = 64'b0100_1101_0100_0001_1001_0101_1110_0000_0000_0011_0011_0101_1111_1001_1010_1111;
    localparam NEG_MASK = 64'b0011_0010_1011_1110_0110_1010_0000_0000_0000_0000_1100_1010_0000_0110_0101_0000;

    localparam FFT_LEN = 64;

    // Iteration counters
    logic [$clog2(FFT_LEN)-1:0] k_cnt;
    logic lts_idx;

    // Cache the first FFT
    logic signed [15:0] fft_re_cached, fft_im_cached;
    xilinx_true_dual_port_read_first_2_clock_ram #(
        .RAM_WIDTH(32),
        .RAM_DEPTH(FFT_LEN),
        .RAM_PERFORMANCE("HIGH_PERFORMANCE")
    ) fft_cache (
        // Port A: Write all received samples into buffer
        .addra(k_cnt),
        .dina({fft_re_axis_tdata, fft_im_axis_tdata}),
        .clka(clk_in),
        .wea(~lts_idx),
        .ena(1'b1),
        .rsta(rst_in),
        .regcea(1'b0),
        .douta(),
        // Port B: Read the LTS in the output stage
        .addrb(k_cnt),
        .dinb(0),
        .clkb(clk_in),
        .web(1'b0),
        .enb(1'b1),
        .rstb(rst_in),
        .regceb(1'b1),
        .doutb({fft_re_cached, fft_im_cached})
    );

    // Pipeline for waiting for BRAM
    logic valid_piped, tlast_piped, pos_piped, neg_piped;
    logic signed [15:0] fft_re_piped, fft_im_piped;
    pipeline #(
        .WIDTH(36),
        .DEPTH(2)
    ) fft_pipe (
        .clk_in(clk_in),
        .rst_in(rst_in),
        .val_in({fft_axis_tvalid && fft_axis_tready && lts_idx,
                 POS_MASK[FFT_LEN-k_cnt-1], NEG_MASK[FFT_LEN-k_cnt-1],
                 fft_axis_tlast, fft_re_axis_tdata, fft_im_axis_tdata}),
        .val_out({valid_piped, pos_piped, neg_piped,
                  tlast_piped, fft_re_piped, fft_im_piped})
    );

    // FIFO for dealing with AXI tready
    logic valid_fifo, pos_fifo, neg_fifo, tlast_fifo;
    logic signed [15:0] fft1_re_fifo, fft2_re_fifo;
    logic signed [15:0] fft1_im_fifo, fft2_im_fifo;
    bram_fifo #(
        .WIDTH(67)
    ) bram_fifo_inst (
        .clk_in(clk_in),
        .rst_in(rst_in),
        .s_axis_tvalid(valid_piped),
        .s_axis_tdata({pos_piped, neg_piped, tlast_piped,
                       fft_re_piped, fft_im_piped,
                       fft_re_cached, fft_im_cached}),
        .m_axis_tvalid(valid_fifo),
        .m_axis_tdata({pos_fifo, neg_fifo, tlast_fifo,
                       fft1_re_fifo, fft1_im_fifo,
                       fft2_re_fifo, fft2_im_fifo}),
        .m_axis_tready(fft_axis_tready)
    );

    assign fft_axis_tready = csi_axis_tready || ~csi_axis_tvalid;

    always_ff @(posedge clk_in) begin
        if (rst_in) begin
            csi_axis_tvalid <= 0;
            csi_axis_tlast <= 0;
            csi_re_axis_tdata <= 0;
            csi_im_axis_tdata <= 0;
            k_cnt <= 0;
            lts_idx <= 0;
        end else begin
            if (fft_axis_tready) begin
                if (fft_axis_tvalid) begin
                    if (k_cnt == FFT_LEN - 1) begin
                        k_cnt <= 0;
                        lts_idx <= ~lts_idx;
                    end else begin
                        k_cnt <= k_cnt + 1;
                    end
                end

                csi_axis_tlast <= tlast_fifo;
                if (pos_fifo) begin
                    csi_axis_tvalid <= valid_fifo;
                    csi_re_axis_tdata <= (fft1_re_fifo>>>1) + (fft2_re_fifo>>>1);
                    csi_im_axis_tdata <= (fft1_im_fifo>>>1) + (fft2_im_fifo>>>1);
                end else if (neg_fifo) begin
                    csi_axis_tvalid <= valid_fifo;
                    csi_re_axis_tdata <= ((-fft1_re_fifo)>>>1) + ((-fft2_re_fifo)>>>1);
                    csi_im_axis_tdata <= ((-fft1_im_fifo)>>>1) + ((-fft2_im_fifo)>>>1);
                end else begin
                    csi_axis_tvalid <= 0;
                end
            end
        end
    end

endmodule

`default_nettype wire

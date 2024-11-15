`timescale 1ns / 1ps
`default_nettype none

/*
 * Module `sync_long`
 *
 * Uses the LTS to align OFDM symbols, and returns the FFT
 * of the last 64 samples in each symbol. Assumes Fs = 20 MSPS.
 *
 * Specifically:
 * (1) Computes the cross-correlation between the received LTS
 *     and the known LTS sequence.
 * (2) Detects peaks in the cross-correlation (there should be
 *     exactly two peaks).
 * (3) Checks that the peaks are 64±1 samples apart.
 * (4) After detecting the second peak, outputs the entire
 *     (cached) LTS sequence to a downstream module.
 *
 * (A downstream module will handle the FFT.)
 */
module sync_long #(
    parameter integer NUM_STS_TAIL = 32,
    parameter integer INPUT_BUF_LEN = 256
) (
    input wire clk_in,
    input wire rst_in,
    // Input signal: 20 MSPS I/Q samples of the WiFi signal
    input wire signal_axis_tvalid,
    input wire signed [15:0] signal_i_axis_tdata, signal_q_axis_tdata,
    output logic signal_axis_tready,
    // Output signal: The two LTS sequences
    output logic lts_axis_tvalid, lts_axis_tlast,
    output logic signed [15:0] lts_i_axis_tdata, lts_q_axis_tdata,
    input wire lts_axis_tready
);

    localparam LTS_WIN_LEN = 64;
    localparam XCORR_WIN_LEN = 32;

    typedef enum {
        WAIT_FOR_RESET,
        SKIP_STS_TAIL,
        XCORR_PEAK1,
        XCORR_PEAK2,
        OUTPUT
    } state_t;
    state_t state;

    // General-purpose counter
    logic [$clog2(INPUT_BUF_LEN)-1:0] stage_cnt;

    // BRAM I/O addresses
    logic [$clog2(INPUT_BUF_LEN)-1:0] signal_waddr, lts_raddr;
    logic lts_valid, lts_last;

    xilinx_true_dual_port_read_first_2_clock_ram #(
        .RAM_WIDTH(32),
        .RAM_DEPTH(INPUT_BUF_LEN),
        .RAM_PERFORMANCE("HIGH_PERFORMANCE")
    ) input_buf (
        // Port A: Write all received samples into buffer
        .addra(signal_waddr),
        .dina({signal_i_axis_tdata, signal_q_axis_tdata}),
        .clka(clk_in),
        .wea(signal_axis_tvalid),
        .ena(1'b1),
        .rsta(rst_in),
        .regcea(1'b0),
        .douta(),
        // Port B: Read the LTS in the output stage
        .addrb(lts_raddr),
        .dinb(0),
        .clkb(clk_in),
        .web(1'b0),
        .enb(1'b1),
        .rstb(rst_in),
        .regceb(1'b1),
        .doutb({lts_i_axis_tdata, lts_q_axis_tdata})
    );
    pipeline #(
        .WIDTH(2),
        .DEPTH(2)
    ) valid_last_pipe (
        .clk_in(clk_in),
        .rst_in(rst_in),
        .val_in({lts_valid, lts_last}),
        .val_out({lts_axis_tvalid, lts_axis_tlast})
    );

    // Cross-correlation control/data signals
    logic [$clog2(INPUT_BUF_LEN)-1:0] xcorr_cnt;
    logic xcorr_iq_valid, xcorr_mag_valid;
    logic [31:0] xcorr_i, xcorr_q;
    logic [31:0] xcorr_mag, xcorr_mag_max;
    
    lts_xcorr lts_xcorr_inst (
        .clk_in(clk_in),
        .rst_in(rst_in),
        .signal_axis_tvalid(signal_axis_tvalid),
        .signal_i_axis_tdata(signal_i_axis_tdata),
        .signal_q_axis_tdata(signal_q_axis_tdata),
        .signal_axis_tready(signal_axis_tready),
        .xcorr_axis_tvalid(xcorr_iq_valid),
        .xcorr_i_axis_tdata(xcorr_i),
        .xcorr_q_axis_tdata(xcorr_q),
        // There should never be any backpressure in the xcorr stages
        .xcorr_axis_tready(1'b1)
    );
    complex_to_mag #(.DATA_WIDTH(32)) complex_to_mag_inst (
        .clk_in(clk_in),
        .rst_in(rst_in),
        .i_in(xcorr_i),
        .q_in(xcorr_q),
        .iq_valid_in(xcorr_iq_valid),
        .mag_out(xcorr_mag),
        .mag_valid_out(xcorr_mag_valid)
    );

    // Peak detection signals
    logic [$clog2(INPUT_BUF_LEN)-1:0] peak1_addr, peak2_addr, gap;
    assign gap = peak2_addr - peak1_addr;

    always_ff @(posedge clk_in) begin
        if (rst_in) begin
            state <= SKIP_STS_TAIL;
            stage_cnt <= 0;
            signal_waddr <= 0;
            lts_raddr <= 0;
            xcorr_cnt <= 0;
            xcorr_mag_max <= 0;
            lts_valid <= 0;
            lts_last <= 0;
        end else begin
            // Always write to the BRAM when valid
            // TODO: Deal with overflow here
            if (signal_axis_tvalid && signal_waddr != INPUT_BUF_LEN - 1) begin
                signal_waddr <= signal_waddr + 1;
            end
            if (xcorr_mag_valid) begin
                xcorr_cnt <= xcorr_cnt + 1;
            end

            case (state)
                // Do nothing while waiting for the next packet
                WAIT_FOR_RESET: begin
                end
                // Skip the (32-sample) tail of the STS
                SKIP_STS_TAIL: begin
                    if (signal_axis_tvalid) begin
                        if (stage_cnt == NUM_STS_TAIL - 1) begin
                            stage_cnt <= 0;
                            state <= XCORR_PEAK1;
                        end else begin
                            stage_cnt <= stage_cnt + 1;
                        end
                    end
                end
                // Find peaks in the cross-correlation
                XCORR_PEAK1: begin
                    if (xcorr_mag_valid) begin
                        // Check for peaks
                        if (xcorr_mag > xcorr_mag_max) begin
                            xcorr_mag_max <= xcorr_mag;
                            peak1_addr <= xcorr_cnt;
                        end
                        // Transition to next state after the first LTS
                        if (stage_cnt == LTS_WIN_LEN - 1) begin
                            stage_cnt <= 0;
                            xcorr_mag_max <= 0;
                            state <= XCORR_PEAK2;
                        end else begin
                            stage_cnt <= stage_cnt + 1;
                        end
                    end
                end
                XCORR_PEAK2: begin
                    if (xcorr_mag_valid) begin
                        // Check for peaks
                        if (xcorr_mag > xcorr_mag_max) begin
                            xcorr_mag_max <= xcorr_mag;
                            peak2_addr <= xcorr_cnt;
                        end
                        // Transition to next state after the first LTS
                        if (stage_cnt == LTS_WIN_LEN - 1) begin
                            if (gap > 62 && gap < 66) begin
                                // LTS detected!
                                stage_cnt <= 0;
                                lts_raddr <= peak1_addr - XCORR_WIN_LEN + 32;
                                lts_valid <= 1;
                                state <= OUTPUT;
                            end else begin
                                // Uh-oh spaghetti-o! Something went wrong!
                                // Wait for the next packet and try again!
                                state <= WAIT_FOR_RESET;
                            end
                        end else begin
                            stage_cnt <= stage_cnt + 1;
                        end
                    end
                end
                // Output the LTS sequence
                // TODO: Deal with the ready signal in here
                OUTPUT: begin
                    if (stage_cnt == 2 * LTS_WIN_LEN - 1) begin
                        state <= WAIT_FOR_RESET;
                        lts_valid <= 0;
                        lts_last <= 0;
                    end else begin
                        stage_cnt <= stage_cnt + 1;
                        lts_raddr <= lts_raddr + 1;
                        // Output two tlast pulses
                        lts_last <= (stage_cnt == LTS_WIN_LEN - 2 ||
                                     stage_cnt == 2 * LTS_WIN_LEN - 2);
                    end
                end
            endcase
        end
    end

endmodule

`default_nettype wire

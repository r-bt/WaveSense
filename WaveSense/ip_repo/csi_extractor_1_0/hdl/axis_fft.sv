/**

Wrapper for ZipCPU FFT core to talk over AXIS

**/

module axis_fft (
    input wire clk_in,
    input wire rst_in,

    input wire sample_axis_tvalid, sample_axis_tlast,
    input wire signed [15:0] sample_re_axis_tdata, sample_im_axis_tdata,
    output logic sample_axis_tready,
   
    output logic fft_axis_tvalid, fft_axis_tlast,
    output logic signed [15:0] fft_re_axis_tdata, fft_im_axis_tdata,
    input wire fft_axis_tready
);

    // Register the output ready signal

    always_ff @(posedge clk_in) begin
        sample_axis_tready <= fft_axis_tready | ~fft_axis_tvalid;
    end

    // Create the FFT core

    logic o_sync;
    logic [31:0] o_result;

    fftmain fft_inst (
        .i_clk(clk_in),
        .i_reset(rst_in),

        .i_sample({sample_re_axis_tdata, sample_im_axis_tdata}),
        .i_ce(sample_axis_tvalid && sample_axis_tready),

        .o_result(o_result),
        .o_sync(o_sync)
    );

    // Convert output to AXIS

    logic [5:0] samples_remaining;

    logic [15:0] re_data;
    logic [15:0] im_data;
    logic data_valid;
    logic data_last;

    always_ff @(posedge clk_in) begin
        if (rst_in) begin
            samples_remaining <= 0;

            re_data <= 0;
            im_data <= 0;
            data_valid <= 0;
            data_last <= 0;
        end else begin
            if (sample_axis_tvalid && sample_axis_tready) begin
                data_valid <= 1;
                re_data <= o_result[31:16];
                im_data <= o_result[15:0];
                data_last <= 0; // Single cycle high

                if (o_sync) begin
                    samples_remaining <= 63;
                end else if (samples_remaining > 0) begin
                    data_last <= samples_remaining == 1;
                    samples_remaining <= samples_remaining - 1;
                end else if (samples_remaining == 0) begin
                    data_valid <= 0;
                end
            end else begin
                data_valid <= 0;
            end
        end
    end

    // Skid buffer for the output to deal with the ready signal

    bram_fifo #(
        .WIDTH(33),
        .DEPTH(3)
    ) output_buffer_inst (
        .clk_in(clk_in),
        .rst_in(rst_in),

        .s_axis_tvalid(data_valid),
        .s_axis_tdata({re_data, im_data, data_last}),

        .m_axis_tvalid(fft_axis_tvalid),
        .m_axis_tdata({fft_re_axis_tdata, fft_im_axis_tdata, fft_axis_tlast}),
        .m_axis_tready(fft_axis_tready || ~fft_axis_tvalid)
    );

endmodule;
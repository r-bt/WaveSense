/**

Convert Pipelined FFT to Block FFT

**/

module block_fft (
    input wire clk_in,
    input wire rst_in,

    input wire sample_axis_tvalid, sample_axis_tlast,
    input wire signed [15:0] sample_re_axis_tdata, sample_im_axis_tdata,
    output logic sample_axis_tready,
   
    output logic fft_axis_tvalid, fft_axis_tlast,
    output logic signed [15:0] fft_re_axis_tdata, fft_im_axis_tdata,
    input wire fft_axis_tready
);

    typedef enum {RECEIVING, EXTENDING, RESETTING} state_t;
    state_t state;

    // AXIS FFT already registers the output ready signal
    assign sample_axis_tready = (state != EXTENDING) && fft_ready;

    // FFT input data

    logic signed [15:0] re_data;
    logic signed [15:0] im_data;
    logic data_valid;
    logic data_last;

    assign re_data = state == RECEIVING ? sample_re_axis_tdata : 0;
    assign im_data = state == RECEIVING ? sample_im_axis_tdata : 0;
    assign data_valid = state == EXTENDING || (state == RECEIVING && sample_axis_tvalid);
    assign data_last = (state == RECEIVING && sample_axis_tlast);

    // Convert the pipelined FFT to a block FFT
    
    logic prev_was_last;
    logic [2:0] sequences;

    always_ff @(posedge clk_in) begin
        if (rst_in) begin
            state <= RECEIVING;

            prev_was_last <= 0;

            sequences <= 0;
        end else begin
            case (state)
                RECEIVING: begin
                    if (fft_ready) begin
                        prev_was_last <= 0; // Single cycle high
                        if (data_valid) begin
                            if (data_last) begin
                                prev_was_last <= 1;
                                sequences <= sequences + 1;
                            end
                        end else begin
                            if (prev_was_last) begin
                                state <= EXTENDING;
                            end
                        end
                    end
                end
                EXTENDING: begin
                    if (fft_ready && data_last) begin
                        sequences <= sequences - 1;
                        if (sequences == 1) begin
                            state <= RESETTING;
                        end
                    end
                end
                RESETTING: begin
                    state <= RECEIVING;
                end
            endcase
        end
    end

    // Create AXIS FFT

    logic fft_ready;
    logic fft_valid;

    axis_fft axis_fft_inst (
        .clk_in(clk_in),
        .rst_in(rst_in || (state == RESETTING)),

        .sample_axis_tvalid(data_valid),
        .sample_axis_tlast(data_last),
        .sample_re_axis_tdata(re_data),
        .sample_im_axis_tdata(im_data),
        .sample_axis_tready(fft_ready),

        .fft_axis_tvalid(fft_valid),
        .fft_axis_tlast(fft_axis_tlast),
        .fft_re_axis_tdata(fft_re_axis_tdata),
        .fft_im_axis_tdata(fft_im_axis_tdata),
        .fft_axis_tready(fft_axis_tready)
    );

    assign fft_axis_tvalid = fft_valid && (state != RESETTING);

endmodule
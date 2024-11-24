`timescale 1ns / 1ps
`default_nettype none

module sync_short(
  input wire clk_in,
  input wire rst_in,

  input wire [31:0] sample_in,
  input wire sample_in_valid,

  output logic short_preamble_detected
);

    localparam DELAY_SHIFT = 4;
    localparam WINDOW_SHIFT = 4;

    // Minimum number of samples that have to exceed plateau threshold to claim a short preamble
    localparam MIN_PLATEAU = 100;

    localparam MIN_POS = MIN_PLATEAU >> 2;
    localparam MIN_NEG = MIN_PLATEAU >> 2;

    /**
    * Calculate the average squared magnitude of the input samples.
    */

    logic [31:0] mag_sq;
    logic mag_sq_valid;

    complex_to_mag_sq mag_sq_inst (
        .clk_in(clk_in),
        .rst_in(rst_in),

        .i_in(sample_in[31:16]),
        .q_in(sample_in[15:0]),
        .iq_valid_in(sample_in_valid),

        .mag_sq_out(mag_sq),
        .mag_sq_valid_out(mag_sq_valid)
    );

    logic [31:0] mag_sq_avg;
    logic mag_sq_avg_valid;

    moving_avg #(
        .DATA_WIDTH(32), 
        .WINDOW_SHIFT(WINDOW_SHIFT)
    ) mag_sq_avg_inst (
        .clk_in(clk_in),
        .rst_in(rst_in),

        .data_in(mag_sq),
        .data_in_valid(mag_sq_valid),

        .data_out(mag_sq_avg),
        .data_out_valid(mag_sq_avg_valid)
    );

    /**
    * Calculate S[i] * conj(S[i+16])
    */

    logic [31:0] sample_delayed;
    logic sample_delayed_valid;

    delay_sample #(.DATA_WIDTH(32), .DELAY_SHIFT(DELAY_SHIFT)) sample_delayed_inst (
        .clk_in(clk_in),
        .rst_in(rst_in),

        .data_in(sample_in),
        .data_in_valid(sample_in_valid),

        .data_out(sample_delayed),
        .data_out_valid(sample_delayed_valid)
    );

    logic [31:0] sample_delayed_conj;
    logic sample_delayed_conj_valid;

    logic [31:0] sample_in_prev;
    logic sample_in_valid_prev;

    always_ff @(posedge clk_in) begin
        if (rst_in) begin
            sample_delayed_conj <= 0;
            sample_delayed_conj_valid <= 0;
            sample_in_valid_prev <= 0;
        end else begin
            sample_delayed_conj_valid <= sample_delayed_valid;

            sample_delayed_conj[31:16] <= sample_delayed[31:16];
            sample_delayed_conj[15:0] <= ~sample_delayed[15:0] + 1;

            if (sample_in_valid) begin
                sample_in_prev <= sample_in;
            end
            sample_in_valid_prev <= sample_in_valid;
        end
    end

    logic [63:0] prod;
    logic prod_valid;

    complex_multiply delay_prod_inst (
        .clk_in(clk_in),

        .i0_in(sample_in_prev[31:16]),
        .q0_in(sample_in_prev[15:0]),
        .i1_in(sample_delayed_conj[31:16]),
        .q1_in(sample_delayed_conj[15:0]),
        .valid_in(sample_in_valid_prev),

        .i_out(prod[63:32]),
        .q_out(prod[31:0]),
        .valid_out(prod_valid)
    );

    /**
    * Calculate the average magnitude of the delayed prod
    */

    logic [63:0] prod_avg;
    logic prod_avg_valid;

    moving_avg #(.DATA_WIDTH(32), .WINDOW_SHIFT(WINDOW_SHIFT)) delay_prod_avg_i_inst (
        .clk_in(clk_in),
        .rst_in(rst_in),

        .data_in(prod[63:32]),
        .data_in_valid(prod_valid),

        .data_out(prod_avg[63:32]),
        .data_out_valid(prod_avg_valid)
    );

    moving_avg #(.DATA_WIDTH(32), .WINDOW_SHIFT(WINDOW_SHIFT)) delay_prod_avg_q_inst (
        .clk_in(clk_in),
        .rst_in(rst_in),

        .data_in(prod[31:0]),
        .data_in_valid(prod_valid),

        .data_out(prod_avg[31:0])
    );

    logic [31:0] delay_prod_avg_mag;
    logic delay_prod_avg_valid;

    complex_to_mag #(.DATA_WIDTH(32)) delay_prod_avg_mag_inst (
        .clk_in(clk_in),
        .rst_in(rst_in),

        .i_in(prod_avg[63:32]),
        .q_in(prod_avg[31:0]),
        .iq_valid_in(prod_avg_valid),

        .mag_out(delay_prod_avg_mag),
        .mag_valid_out(delay_prod_avg_valid)
    );

    /**
    * Check number of consecutive samples with correleation larger than 0.75. 
    * Also check if incoming singal has both positive and negative samples to elimiate false positives
    */

    logic [31:0] pos_count;
    logic has_pos;

    logic [31:0] neg_count;
    logic has_neg;

    logic [31:0] prod_thres;
    logic [31:0] plateau_count;


    always_ff @(posedge clk_in) begin
        if (rst_in) begin
            pos_count <= 0;
            has_pos <= 0;

            neg_count <= 0;
            has_neg <= 0;

            prod_thres <= 0;

            plateau_count <= 0;

            short_preamble_detected <= 0;
        end else begin
            has_pos <= pos_count > MIN_POS;
            has_neg <= neg_count > MIN_NEG;

            // prod_thres = 0.75 * mag_sq_avg
            prod_thres <= {1'b0, mag_sq_avg[31:1]} + {2'b0, mag_sq_avg[31:2]};

            if (delay_prod_avg_valid) begin
                if (delay_prod_avg_mag > prod_thres) begin
                    if (sample_in_prev[31] == 1) begin  // TODO: This is wrong
                        neg_count <= neg_count + 1;
                    end else begin
                        pos_count <= pos_count + 1;
                    end

                    if (plateau_count > MIN_PLATEAU) begin
                        plateau_count <= 0;
                        pos_count <= 0;
                        neg_count <= 0;
                        short_preamble_detected <= has_pos && has_neg;
                    end else begin
                        plateau_count <= plateau_count + 1;
                        short_preamble_detected <= 0;
                    end
                end else begin
                    plateau_count <= 0;
                    pos_count <= 0;
                    neg_count <= 0;
                    short_preamble_detected <= 0;
                end
            end else begin
                short_preamble_detected <= 0;
            end
        end
    end

endmodule

`default_nettype wire

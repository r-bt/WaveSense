`timescale 1ns / 1ps
`default_nettype none

/*
 * Module `lts_xcorr`
 *
 * Computes the cross-correlation between the received LTS and the known LTS.
 * Kind of like a FIR filter, but with complex multiplication and in reverse order.
 */
module lts_xcorr (
    input wire clk_in,
    input wire rst_in,

    input wire signal_axis_tvalid,
    input wire signed [15:0] signal_i_axis_tdata, signal_q_axis_tdata,
    output logic signal_axis_tready,

    output logic xcorr_axis_tvalid,
    output logic signed [31:0] xcorr_i_axis_tdata, xcorr_q_axis_tdata,
    input wire xcorr_axis_tready
);
 
    localparam integer NUM_COEFFS = 32;
    localparam integer CMPLX_MULT_STAGES = 1;

    logic signed [15:0] coeffs_i [NUM_COEFFS-1 : 0];
    logic signed [15:0] coeffs_q [NUM_COEFFS-1 : 0];
    //initializing values (complex conjugate of the known LTF)
    initial begin
        {coeffs_i[0], coeffs_q[0]} <=   { 16'd156, 16'd0};
        {coeffs_i[1], coeffs_q[1]} <=   {-16'd5,   16'd120};
        {coeffs_i[2], coeffs_q[2]} <=   { 16'd40,  16'd111};
        {coeffs_i[3], coeffs_q[3]} <=   { 16'd97, -16'd83};
        {coeffs_i[4], coeffs_q[4]} <=   { 16'd21, -16'd28};
        {coeffs_i[5], coeffs_q[5]} <=   { 16'd60,  16'd88};
        {coeffs_i[6], coeffs_q[6]} <=   {-16'd115, 16'd55};
        {coeffs_i[7], coeffs_q[7]} <=   {-16'd38,  16'd106};
        {coeffs_i[8], coeffs_q[8]} <=   { 16'd98,  16'd26};
        {coeffs_i[9], coeffs_q[9]} <=   { 16'd53, -16'd4};
        {coeffs_i[10], coeffs_q[10]} <= { 16'd1,   16'd115};
        {coeffs_i[11], coeffs_q[11]} <= {-16'd137, 16'd47};
        {coeffs_i[12], coeffs_q[12]} <= { 16'd24,  16'd59};
        {coeffs_i[13], coeffs_q[13]} <= { 16'd59,  16'd15};
        {coeffs_i[14], coeffs_q[14]} <= {-16'd22, -16'd161};
        {coeffs_i[15], coeffs_q[15]} <= { 16'd119, 16'd4};
        {coeffs_i[16], coeffs_q[16]} <= { 16'd62,  16'd62};
        {coeffs_i[17], coeffs_q[17]} <= { 16'd37, -16'd98};
        {coeffs_i[18], coeffs_q[18]} <= {-16'd57, -16'd39};
        {coeffs_i[19], coeffs_q[19]} <= {-16'd131,-16'd65};
        {coeffs_i[20], coeffs_q[20]} <= { 16'd82, -16'd92};
        {coeffs_i[21], coeffs_q[21]} <= { 16'd70, -16'd14};
        {coeffs_i[22], coeffs_q[22]} <= {-16'd60, -16'd81};
        {coeffs_i[23], coeffs_q[23]} <= {-16'd56,  16'd22};
        {coeffs_i[24], coeffs_q[24]} <= {-16'd35,  16'd151};
        {coeffs_i[25], coeffs_q[25]} <= {-16'd122, 16'd17};
        {coeffs_i[26], coeffs_q[26]} <= {-16'd127, 16'd21};
        {coeffs_i[27], coeffs_q[27]} <= { 16'd75,  16'd74};
        {coeffs_i[28], coeffs_q[28]} <= {-16'd3,  -16'd54};
        {coeffs_i[29], coeffs_q[29]} <= {-16'd92, -16'd115};
        {coeffs_i[30], coeffs_q[30]} <= { 16'd92, -16'd106};
        {coeffs_i[31], coeffs_q[31]} <= { 16'd12, -16'd98};
        for (int i = 0; i < NUM_COEFFS; i++) begin
            i_sum_reg[i] = 0;
            q_sum_reg[i] = 0;
        end
    end

    logic signed [31:0] i_mult_reg [NUM_COEFFS-1:0];
    logic signed [31:0] q_mult_reg [NUM_COEFFS-1:0];
    logic signed [31:0] i_sum_reg [NUM_COEFFS-1:0];
    logic signed [31:0] q_sum_reg [NUM_COEFFS-1:0];
    logic [CMPLX_MULT_STAGES-1:0] valid_in_reg;
    logic [NUM_COEFFS-1:0] valid_out_reg;

    assign xcorr_axis_tvalid = valid_out_reg[NUM_COEFFS-1];
    assign xcorr_i_axis_tdata = i_sum_reg[NUM_COEFFS-1];
    assign xcorr_q_axis_tdata = q_sum_reg[NUM_COEFFS-1];
    assign signal_axis_tready = xcorr_axis_tready ||
                                ~(&valid_out_reg[NUM_COEFFS-1:NUM_COEFFS-CMPLX_MULT_STAGES-1]);

    genvar mult_idx;
    generate
        for (mult_idx = 0; mult_idx < NUM_COEFFS; mult_idx++) begin : cmplx_mult
            complex_multiply #(
                .DATA_WIDTH(16)
            ) mult_inst (
                .clk_in(clk_in),
                .i0_in(signal_i_axis_tdata),
                .q0_in(signal_q_axis_tdata),
                .i1_in(coeffs_i[mult_idx]),
                .q1_in(coeffs_q[mult_idx]),
                .i_out(i_mult_reg[mult_idx]),
                .q_out(q_mult_reg[mult_idx])
            );
        end
    endgenerate

    always_ff @(posedge clk_in) begin
        if (rst_in) begin
            for (int i = 0; i < NUM_COEFFS; i++) begin
                i_sum_reg[i] <= 0;
                q_sum_reg[i] <= 0;
                valid_out_reg[i] <= 0;
            end
            for (int i = 0; i < CMPLX_MULT_STAGES; i++) begin
                valid_in_reg[i] <= 0;
            end
        end else begin
            // Stage 1: Complex multiply
            for (int i = 1; i < CMPLX_MULT_STAGES; i++) begin
                valid_in_reg[i] <= valid_out_reg[i - 1];
            end
            valid_in_reg[0] <= signal_axis_tvalid;
            // Stage 2: Sum it together
            if (valid_in_reg[CMPLX_MULT_STAGES-1] && signal_axis_tready) begin
                for (int i = 1; i < NUM_COEFFS; i++) begin
                    i_sum_reg[i] <= i_mult_reg[i] + i_sum_reg[i - 1];
                    q_sum_reg[i] <= q_mult_reg[i] + q_sum_reg[i - 1];
                    valid_out_reg[i] <= valid_out_reg[i - 1];
                end
                i_sum_reg[0] <= i_mult_reg[0];
                q_sum_reg[0] <= q_mult_reg[0];
                valid_out_reg[0] <= 1;
            end else if (xcorr_axis_tready) begin
                valid_out_reg[NUM_COEFFS-1] <= 0;
            end
        end
    end

endmodule

`default_nettype wire

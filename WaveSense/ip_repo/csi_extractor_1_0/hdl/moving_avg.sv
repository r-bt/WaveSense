module moving_avg 
#(
    parameter DATA_WIDTH = 32,
    parameter WINDOW_SHIFT = 4
) (
    input wire clk_in,
    input wire rst_in,

    input wire signed [DATA_WIDTH - 1 : 0] data_in,
    input wire data_in_valid,

    output logic signed [DATA_WIDTH - 1 : 0] data_out,
    output logic data_out_valid
);

    localparam WINDOW_SIZE = 1 << WINDOW_SHIFT;
    localparam SUM_WIDTH = DATA_WIDTH + WINDOW_SHIFT;

    logic signed [SUM_WIDTH - 1 : 0] running_sum;

    logic [WINDOW_SHIFT - 1 : 0] addr;
    logic is_full;

    logic signed [DATA_WIDTH - 1 : 0] buffer [WINDOW_SIZE - 1 : 0];

    always_ff @(posedge clk_in) begin
        if (rst_in) begin
            addr <= 0;
            running_sum <= 0;
            is_full <= 0;
            data_out_valid <= 0;

            for (int i = 0; i < (1 << WINDOW_SHIFT); i++) begin
                buffer[i] <= 0;
            end
        end else if (data_in_valid) begin
            addr <= addr + 1;
            buffer[addr] <= data_in;

            if (addr == WINDOW_SIZE - 1) begin
                is_full <= 1;
                data_out_valid <= 1;
            end else begin
                data_out_valid <= is_full;
            end

            if (is_full) begin
                running_sum <= running_sum + data_in - buffer[addr];
            end else begin
                running_sum <= running_sum + data_in;
            end
            
        end else begin
            data_out_valid <= 0;
        end
    end

    assign data_out = running_sum >> WINDOW_SHIFT;

endmodule
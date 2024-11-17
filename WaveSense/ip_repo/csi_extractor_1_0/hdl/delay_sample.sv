/**
DELAY module 

Only supports 2^n delay
**/

module delay_sample #(
  parameter DATA_WIDTH = 32,
  parameter DELAY_SHIFT = 4
) (
  input wire clk_in,
  input wire rst_in,

  input wire [DATA_WIDTH-1:0] data_in,
  input wire data_in_valid,

  output logic [DATA_WIDTH-1:0] data_out,
  output logic data_out_valid
);

  localparam DELAY_SIZE = 1 << DELAY_SHIFT;

  logic [DELAY_SHIFT-1:0] addr;
  logic is_full;

  logic [DATA_WIDTH-1:0] buffer [DELAY_SIZE-1:0];

  always_ff @(posedge clk_in) begin
    if (rst_in) begin
      addr <= 0;
      is_full <= 0;
      data_out_valid <= 0;

      // CocoTB gives a warning if try to use DELAY_SIZE in the for loop
      for (int i = 0; i < (1 << DELAY_SHIFT); i++) begin
        buffer[i] <= 0;
      end
    end else if (data_in_valid) begin
      addr <= addr + 1;
      buffer[addr] <= data_in;

      if (addr == DELAY_SIZE - 1) begin
        is_full <= 1;
        data_out_valid <= 1;
      end else begin
        data_out_valid <= is_full;
      end
    end else begin
      data_out_valid <= 0;
    end
  end

  assign data_out = buffer[addr];

endmodule
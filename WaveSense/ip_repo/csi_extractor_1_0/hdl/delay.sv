/**
DELAY module 

Note, to delay SAMPLES cycles we store SAMPLES + 1 samples in the buffer.
**/

module delay #(
  parameter integer SAMPLES=16,
  parameter integer C_S00_AXIS_TDATA_WIDTH  = 32
) (
  // Ports of Axi Slave Bus Interface S00_AXIS
  input wire  s00_axis_aclk, s00_axis_aresetn,
  input wire  s00_axis_tvalid,
  input wire  [C_S00_AXIS_TDATA_WIDTH-1 : 0] s00_axis_tdata,
  output logic  s00_axis_tready,

  // Ports of Axi Master Bus Interface M00_AXIS
  input wire  m00_axis_tready,
  output logic  m00_axis_tvalid,
  output logic [C_S00_AXIS_TDATA_WIDTH-1 : 0] m00_axis_tdata
);

  logic [31:0] sample_in_buffer [SAMPLES:0];
  logic [$clog2(SAMPLES): 0] count;

  always_ff @(posedge s00_axis_aclk) begin
    if (~s00_axis_aresetn) begin
      count <= 0;
      for (int i = 0; i < SAMPLES; i++) begin
        sample_in_buffer[i] <= 0;
      end
    end else if (s00_axis_tready) begin
      m00_axis_tvalid <= 0; // Single cycle high
      if (s00_axis_tvalid) begin
        // Wait until at least SAMPLES samples are received before valid output
        if (count != SAMPLES) begin
          count <= count + 1;
        end else begin
          m00_axis_tvalid <= 1;
        end
        // Cycle through the buffer
        for (int i = 0; i < SAMPLES + 1; i++) begin
          if (i == 0) begin
            sample_in_buffer[i] <= s00_axis_tdata;
          end else begin
            sample_in_buffer[i] <= sample_in_buffer[i-1];
          end
        end
      end
    end
  end

  assign m00_axis_tdata = sample_in_buffer[SAMPLES];
  assign s00_axis_tready = m00_axis_tready || ~m00_axis_tvalid;

endmodule
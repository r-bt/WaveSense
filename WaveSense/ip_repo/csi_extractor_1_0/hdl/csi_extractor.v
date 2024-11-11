
`timescale 1 ns / 1 ps

	module csi_extractor #
	(
		// Users to add parameters here

		// User parameters ends
		// Do not modify the parameters beyond this line


		// Parameters of Axi Slave Bus Interface S00_AXIS
		parameter integer C_S00_AXIS_TDATA_WIDTH	= 32,

		// Parameters of Axi Master Bus Interface M00_AXIS
		parameter integer C_M00_AXIS_TDATA_WIDTH	= 32,
		parameter integer C_M00_AXIS_START_COUNT	= 32
	)
	(
		// Users to add ports here
		
		output wire [3:0] trigger,

		// User ports ends
		// Do not modify the ports beyond this line


		// Ports of Axi Slave Bus Interface S00_AXIS
		input wire  s00_axis_aclk,
		input wire  s00_axis_aresetn,
		output wire  s00_axis_tready,
		input wire [C_S00_AXIS_TDATA_WIDTH-1 : 0] s00_axis_tdata,
		input wire [(C_S00_AXIS_TDATA_WIDTH/8)-1 : 0] s00_axis_tstrb,
		input wire  s00_axis_tlast,
		input wire  s00_axis_tvalid,

		// Ports of Axi Master Bus Interface M00_AXIS
		input wire  m00_axis_aclk,
		input wire  m00_axis_aresetn,
		output wire  m00_axis_tvalid,
		output wire [C_M00_AXIS_TDATA_WIDTH-1 : 0] m00_axis_tdata,
		output wire [(C_M00_AXIS_TDATA_WIDTH/8)-1 : 0] m00_axis_tstrb,
		output wire  m00_axis_tlast,
		input wire  m00_axis_tready
	);

	// Power trigger
	
	wire trigger_store;
	
	power_trigger power_trigger_inst (
        .clock(s00_axis_aclk),
        .enable(1'b1),
        .reset(!s00_axis_aresetn),

        .set_stb(0),
        .set_addr(0),
        .set_data(0),

        .sample_in(s00_axis_tdata),
        .sample_in_strobe(s00_axis_tvalid),

        .trigger(trigger_store)
    );
    
    assign trigger = {1'b1,1'b0,1'b0,trigger_store};
	
	// DMA related
	
	reg [C_M00_AXIS_TDATA_WIDTH-1 : 0] tdata;
	reg valid;
	reg [17:0] counter;
	
	always @(posedge m00_axis_aclk) begin
	   valid <= 0; // Only high for one cycle
	   if (!m00_axis_aresetn) begin
	       counter <= 0;
	       tdata <= 0;
	   end else if (s00_axis_tvalid) begin
	       tdata <= s00_axis_tdata;
	       valid <= 1;
	       counter <= counter + 1;
	   end
    end
    
    assign m00_axis_tdata = tdata;
    assign m00_axis_tvalid = valid;
    assign m00_axis_tlast = counter == 0;
    
    assign s00_axis_tready = m00_axis_tready;
	// User logic ends

	endmodule

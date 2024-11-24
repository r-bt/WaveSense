
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

		input wire [3:0] sw,
		input wire [3:0] btn,
		output wire [3:0] led,

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

	wire csi_axis_tlast;
	csi_extractor_sv csi_extractor_inst (
		.clk_in(s00_axis_aclk),
		.rst_in(~s00_axis_aresetn),

		.signal_axis_tvalid(s00_axis_tvalid && btn[0]),
		.signal_axis_tdata(s00_axis_tdata),
		.signal_axis_tready(s00_axis_tready),

		.csi_axis_tvalid(m00_axis_tvalid),
		.csi_axis_tlast(csi_axis_tlast),
		.csi_axis_tdata(m00_axis_tdata),
		.csi_axis_tready(m00_axis_tready),

		.sw_in(sw),
		.led_out(led)
	);

	// Generate a tlast signal
	reg [7:0] cnt;
	assign m00_axis_tstrb = 4'b1111;
	assign m00_axis_tlast = cnt == 8'hFF;
	always @(posedge s00_axis_aclk) begin
		if (~s00_axis_aresetn) begin
			cnt <= 0;
		end if (csi_axis_tlast) begin
			cnt <= cnt + 1;
		end
	end

endmodule

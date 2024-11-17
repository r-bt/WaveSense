
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

	// State machine 

	localparam S_WAIT_POWER_TRIGGER =   0;
	localparam S_SYNC_SHORT         =   1;
	localparam S_SYNC_LONG          =   2;

	reg [3:0] state;

	// Downsample

	wire downsample_valid;
	wire [C_S00_AXIS_TDATA_WIDTH - 1 : 0] downsampled_data;

	wire downsample_ready;
	
	downsample downsample_inst (
		.s00_axis_aclk(s00_axis_aclk),
		.s00_axis_aresetn(s00_axis_aresetn),
		.s00_axis_tvalid(s00_axis_tvalid),
		.s00_axis_tdata(s00_axis_tdata),
		.s00_axis_tready(s00_axis_tready),

		.m00_axis_tready(downsample_ready),
		.m00_axis_tvalid(downsample_valid),
		.m00_axis_tdata(downsampled_data)
	);

	// Power trigger
	
	wire power_trigger;
	
	power_trigger power_trigger_inst (
        .clock(s00_axis_aclk),
        .enable(1'b1),
        .reset(!s00_axis_aresetn),

        .set_stb(0),
        .set_addr(0),
        .set_data(0),

        .sample_in(downsampled_data),
        .sample_in_strobe(downsample_valid),

        .trigger(power_trigger)
    );

	// Sync Short

	reg sync_short_reset;
	wire sync_short_enabled = state == S_SYNC_SHORT;

	wire short_preamble_detected;

	sync_short sync_short_inst (
		.clk_in(s00_axis_aclk),
		.rst_in(!s00_axis_aresetn | sync_short_reset),

		.sample_in(downsampled_data),
		.sample_in_valid(downsample_valid && sync_short_enabled),

		.short_preamble_detected(short_preamble_detected)
	);

	// Sync Long

	reg sync_long_reset;
	reg sync_long_enable;
	reg [31:0] sample_count;

	wire lts_axis_tvalid, lts_axis_tlast;
	wire signed [15:0] lts_i_axis_tdata, lts_q_axis_tdata;
	wire lts_axis_tready;

	sync_long sync_long_inst (
		.clk_in(s00_axis_aclk),
		.rst_in(!s00_axis_aresetn | sync_long_reset),

		.signal_axis_tvalid(downsample_valid && sync_long_enable),
		.signal_i_axis_tdata(downsampled_data[31:16]),
		.signal_q_axis_tdata(downsampled_data[15:0]),
		.signal_axis_tready(downsample_ready),

		.lts_axis_tvalid(lts_axis_tvalid),
		.lts_axis_tlast(lts_axis_tlast),
		.lts_i_axis_tdata(lts_i_axis_tdata),
		.lts_q_axis_tdata(lts_q_axis_tdata),
		.lts_axis_tready(lts_axis_tready)
	);

	// FFT of LTS

	wire fft_axis_tvalid, fft_axis_tlast;
	wire [31:0] fft_axis_tdata;
	wire fft_axis_tready;

	xfft_0 xfft_0_inst (
		.aclk(s00_axis_aclk),
		.aresetn(s00_axis_aresetn),

		.s_axis_data_tvalid(lts_axis_tvalid),
		.s_axis_data_tlast(lts_axis_tlast),
		.s_axis_data_tdata({lts_i_axis_tdata, lts_q_axis_tdata}),
		.s_axis_data_tready(lts_axis_tready),

		.m_axis_data_tvalid(fft_axis_tvalid),
		.m_axis_data_tlast(fft_axis_tlast),
		.m_axis_data_tdata(fft_axis_tdata),
		.m_axis_data_tready(fft_axis_tready)
	);

	// Equalizer

	wire csi_axis_tvalid, csi_axis_tlast;
	wire signed [15:0] csi_re_axis_tdata, csi_im_axis_tdata;
	wire csi_axis_tready;

	equalizer equalizer_inst (
		.clk_in(s00_axis_aclk),
		.rst_in(!s00_axis_aresetn),

		.fft_axis_tvalid(fft_axis_tvalid),
		.fft_axis_tlast(fft_axis_tlast),
		.fft_re_axis_tdata(fft_axis_tdata[31:16]),
		.fft_im_axis_tdata(fft_axis_tdata[15:0]),
		.fft_axis_tready(fft_axis_tready),

		.csi_axis_tvalid(csi_axis_tvalid),
		.csi_axis_tlast(csi_axis_tlast),
		.csi_re_axis_tdata(csi_re_axis_tdata),
		.csi_im_axis_tdata(csi_im_axis_tdata),
		.csi_axis_tready(1)  // TODO: Make me AXI!
	);

	assign trigger = {power_trigger, short_preamble_detected, lts_axis_tlast, csi_axis_tlast};

	// State machine to control flow

	always @(posedge s00_axis_aclk) begin
		if (!s00_axis_aresetn) begin
			state <= S_WAIT_POWER_TRIGGER;

			sync_short_reset <= 0; 

			sync_long_reset <= 0;
			sync_long_enable <= 0;

			sample_count <= 0;
		end else begin
			case (state)

				S_WAIT_POWER_TRIGGER: begin
					sync_long_enable <= 0;

					if (power_trigger) begin
						sync_short_reset <= 1;
						state <= S_SYNC_SHORT;
					end
				end

				S_SYNC_SHORT: begin
					if (sync_short_reset) begin
						sync_short_reset <= 0;
					end

					if (~power_trigger) begin
                    // power level drops before finding STS
                    	state <= S_WAIT_POWER_TRIGGER;
                	end

					if (short_preamble_detected) begin
						sync_long_reset <= 1;
						sync_long_enable <= 1;

						sample_count <= 0;
						state <= S_SYNC_LONG;
                	end
				end

				S_SYNC_LONG: begin
					if (sync_long_reset) begin
                    	sync_long_reset <= 0;
               		end

					if (downsample_valid) begin
						sample_count <= sample_count + 1;
					end

					if (sample_count > 320) begin
						state <= S_WAIT_POWER_TRIGGER;
					end

					if (~power_trigger) begin
						state <= S_WAIT_POWER_TRIGGER;
					end

					if (lts_axis_tlast) begin
						state <= S_WAIT_POWER_TRIGGER;
					end
				end
			endcase
		end
	end
	
	// DMA related
	
	reg [C_M00_AXIS_TDATA_WIDTH-1 : 0] tdata;
	reg valid;
	reg [17:0] counter;
	
	always @(posedge m00_axis_aclk) begin
	   valid <= 0; // Only high for one cycle
	   if (!m00_axis_aresetn) begin
	       counter <= 0;
	       tdata <= 0;
	   end else if (downsample_valid) begin
	       tdata <= downsampled_data;
	       valid <= 1;
	       counter <= counter + 1;
	   end
    end
    
    assign m00_axis_tdata = tdata;
    assign m00_axis_tvalid = valid;
    assign m00_axis_tlast = counter == 0;
    
    // assign s00_axis_tready = m00_axis_tready;
	// User logic ends

	endmodule

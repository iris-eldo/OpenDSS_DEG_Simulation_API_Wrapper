V2.0;;;
8	ELEMENT		NODE	-511	-223	0	source_bus	-497	-223	-497	-223				
9	SYSTEM	1	MAIN_NODE	0	0	0		-497	-223	0	0	source_bus.1.0			
11	ELEMENT		NODE	-511	-5	0	upfc_input	-497	-5	-497	-5				
12	ELEMENT	Phases=1--	TRANSFORMER_YY	0	0	0	service50kva	-497	-223	-497	-5	source_bus.1.0	upfc_input.1		
13	ELEMENT		NODE	-222	-5	0	upfc_output	-208	-5	-208	-5				
15	ELEMENT		NODE	-8	-5	0	load_bus	6	-5	6	-5				
16	ELEMENT	Phases=1--	TRANSFORMER_YY	0	0	0	tupfcout	-208	-5	6	-5	upfc_output.1.0	load_bus.1.0		
19	ELEMENT	Phases=1--	UPFC	-497	-5	0	UPFC_0	-497	-5	-208	-5	upfc_input.1	upfc_output.1	Capacitor.	

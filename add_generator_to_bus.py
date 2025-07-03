import opendssdirect as dss
from simulation_core import OpenDSSCircuit # Import OpenDSSCircuit for type hinting

def add_generation_to_bus(circuit_object: OpenDSSCircuit, bus_name: str, kw: float, phases: int):
    """
    Adds or updates a generator on a specific bus in the active OpenDSS circuit,
    using different models for 1-ph and 3-ph.

    Args:
        circuit_object (OpenDSSCircuit): The active OpenDSSCircuit instance.
        bus_name (str): The name of the bus to add/update the generator on.
        kw (float): The active power (kW) of the generator.
        phases (int): The number of phases for the generator (1 or 3).
    """
    bus_name_lower = bus_name.lower()
    gen_name_only = f"Gen_{bus_name_lower}_{phases}ph"
    full_dss_name = f"Generator.{gen_name_only}"

    all_gen_names = [name.lower() for name in dss.Generators.AllNames()]

    # Determine model settings based on phase
    if phases == 3:
        model_string = "Model=1"  # Voltage-controlled model for 3-phase
        final_kw = kw
    else: # single-phase
        model_string = "Model=3 PF=1.0"  # Fixed-power model for 1-phase
        final_kw = kw * 2 # Apply the "half-power" fix, as per original logic

    if gen_name_only in all_gen_names:
        # If it exists, update its kW property
        print(f"Generator '{gen_name_only}' already exists. Updating its kW setpoint to {final_kw} kW.")
        dss.Text.Command(f"{full_dss_name}.kW={final_kw}")
    else:
        # If it does not exist, create it
        print(f"Adding new generator '{gen_name_only}' with {final_kw} kW...")
        dss.Circuit.SetActiveBus(bus_name_lower)
        base_kv = dss.Bus.kVBase()

        # Defensive check to prevent crash if bus has no voltage base
        if base_kv == 0:
            print(f"ERROR: Bus '{bus_name_lower}' has a base voltage of 0. Cannot add generator.")
            return

        # Determine connection string and kV based on phase
        if phases == 3:
            conn = ".1.2.3"
            final_kv_gen = base_kv
        else:
            # For single phase, assume the first node found on the bus
            # This might need refinement based on exact single-phase bus configurations
            nodes_on_bus = dss.Bus.Nodes()
            if not nodes_on_bus:
                print(f"ERROR: Bus '{bus_name_lower}' has no nodes. Cannot add single-phase generator.")
                return
            node = nodes_on_bus[0] # Use the first available node
            conn = f".{node}"
            final_kv_gen = base_kv / 1.732 # Line-to-neutral voltage for single phase

        dss.Text.Command(
            f'New {full_dss_name} '
            f'Bus1={bus_name_lower}{conn} phases={phases} '
            f'kV={final_kv_gen:.4f} '
            f'kW={final_kw} {model_string}'
        )
    print(f"Generator operation for bus '{bus_name}' completed.")
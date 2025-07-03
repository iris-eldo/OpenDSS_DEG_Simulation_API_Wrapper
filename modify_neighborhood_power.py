import opendssdirect as dss
from simulation_core import NEIGHBORHOOD_DATA, OpenDSSCircuit

def modify_loads_in_neighborhood(circuit_object: OpenDSSCircuit, neighborhood_id: int, factor: float):
    """
    Modifies the kW and kVAR of all loads within a specified neighborhood
    by a given factor.

    Args:
        circuit_object (OpenDSSCircuit): The active OpenDSSCircuit instance.
        neighborhood_id (int): The ID of the neighborhood whose loads are to be modified.
        factor (float): The multiplication factor for the load (e.g., 0.8 for 20% reduction).
    """
    buses_in_neighborhood = [bus.lower() for bus in NEIGHBORHOOD_DATA.get(neighborhood_id, [])]
    
    if not buses_in_neighborhood:
        print(f"No buses found for neighborhood ID {neighborhood_id} or neighborhood ID is invalid.")
        return
    
    if dss.Loads.Count() == 0:
        print("No loads found in the circuit to modify.")
        return

    dss.Loads.First()
    while True:
        bus_name = dss.CktElement.BusNames()[0].split('.')[0].lower()
        if bus_name in buses_in_neighborhood:
            current_kw = dss.Loads.kW()
            current_kvar = dss.Loads.kvar()
            dss.Loads.kW(current_kw * factor)
            dss.Loads.kvar(current_kvar * factor)
            # print(f"  Modified load on bus {bus_name}: kW from {current_kw:.2f} to {current_kw * factor:.2f}")
        
        if not dss.Loads.Next() > 0:
            break
    print(f"Loads in neighborhood {neighborhood_id} modified by factor {factor}.")
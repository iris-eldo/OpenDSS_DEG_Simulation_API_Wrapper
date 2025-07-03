import opendssdirect as dss
import pandas as pd

from IEEE_123_Bus_G_neighbourhoods import *

class OpenDSSCircuit:
    """A class to interact with a persistent OpenDSS circuit object."""

    def __init__(self, dss_file: str):
        self.dss_file = dss_file or r"Test_Systems\IEEE_123_Bus-G\Master.dss"
        # This dictionary now stores the "aesthetic" devices added to the circuit
        self.devices = {}
        self._initialize_dss()

    def _initialize_dss(self):
        """Initializes the DSS engine and compiles the circuit."""
        print("Initializing and compiling base circuit...")
        dss.Basic.ClearAll()
        dss.Text.Command(f'Compile "{self.dss_file}"')
        if dss.Circuit.NumBuses() == 0:
            raise FileNotFoundError(f"No buses found. Check DSS file: {self.dss_file}")

    def get_buses_with_loads(self) -> pd.DataFrame:
        """Gets all buses with voltage, load, generation, and device information attributed per-node."""
        bus_data = []
        all_bus_names = [b.lower() for b in dss.Circuit.AllBusNames()]
        for bus_name in all_bus_names:
            dss.Circuit.SetActiveBus(bus_name)
            nodes_on_bus = dss.Bus.Nodes()
            pu_voltages = dss.Bus.puVmagAngle()
            for i, node in enumerate(nodes_on_bus):
                if (2 * i + 1) < len(pu_voltages):
                    bus_data.append({'Bus': bus_name, 'Node': node, 'VMag_pu': pu_voltages[2*i], 'VAngle': pu_voltages[2*i+1]})
        buses_df = pd.DataFrame(bus_data)

        load_kw, load_kvar, gen_kw, gen_kvar = {}, {}, {}, {}
        
        # Aggregate load data from the simulation
        if dss.Loads.Count() > 0:
            dss.Loads.First()
            while True:
                bus_name_raw = dss.CktElement.BusNames()[0]
                bus_name = bus_name_raw.split('.')[0].lower()
                nodes, num_nodes = dss.CktElement.NodeOrder(), dss.CktElement.NumPhases()
                if num_nodes > 0:
                    kw_per_node, kvar_per_node = dss.Loads.kW() / num_nodes, dss.Loads.kvar() / num_nodes
                    for node in nodes:
                        key = (bus_name, node)
                        load_kw[key] = load_kw.get(key, 0) + kw_per_node
                        load_kvar[key] = load_kvar.get(key, 0) + kvar_per_node
                if not dss.Loads.Next() > 0: break
        
        # Aggregate generator data from the simulation
        if dss.Generators.Count() > 0:
            dss.Generators.First()
            while True:
                bus_name, nodes = dss.CktElement.BusNames()[0].split('.')[0].lower(), dss.CktElement.NodeOrder()
                num_nodes, powers = len(nodes), dss.CktElement.Powers()
                if num_nodes > 0 and len(powers) >= 2:
                    kw_per_node, kvar_per_node = -sum(powers[::2]) / num_nodes, -sum(powers[1::2]) / num_nodes
                    for node in nodes:
                        key = (bus_name, node)
                        gen_kw[key] = gen_kw.get(key, 0) + kw_per_node
                        gen_kvar[key] = gen_kvar.get(key, 0) + kvar_per_node
                if not dss.Generators.Next() > 0: break
        
        # Map aggregated data to the main DataFrame
        buses_df['Load_kW'] = buses_df.apply(lambda r: load_kw.get((r['Bus'], r['Node']), 0), axis=1)
        buses_df['Load_kVAR'] = buses_df.apply(lambda r: load_kvar.get((r['Bus'], r['Node']), 0), axis=1)
        buses_df['Gen_kW'] = buses_df.apply(lambda r: gen_kw.get((r['Bus'], r['Node']), 0), axis=1)
        buses_df['Gen_kVAR'] = buses_df.apply(lambda r: gen_kvar.get((r['Bus'], r['Node']), 0), axis=1)
        
        # Map the stored aesthetic devices to all nodes of the parent bus for reporting
        buses_df['Devices'] = buses_df.apply(lambda r: self.devices.get(r['Bus'], []), axis=1)
        return buses_df.fillna(0)

    def modify_loads_in_neighborhood(self, neighborhood_id: int, factor: float):
        """Modifies all loads within a specified neighborhood by a multiplication factor."""
        buses_in_neighborhood = [bus.lower() for bus in NEIGHBORHOOD_DATA.get(neighborhood_id, [])]
        if not buses_in_neighborhood or dss.Loads.Count() == 0: return
        dss.Loads.First()
        while True:
            bus_name = dss.CktElement.BusNames()[0].split('.')[0].lower()
            if bus_name in buses_in_neighborhood:
                dss.Loads.kW(dss.Loads.kW() * factor)
                dss.Loads.kvar(dss.Loads.kvar() * factor)
            if not dss.Loads.Next() > 0: break

    def add_generation_to_bus(self, bus_name: str, kw: float, phases: int):
        """Adds a new generator element to the simulation."""
        bus_name_lower, gen_name_only = bus_name.lower(), f"Gen_{bus_name.lower()}_{phases}ph"
        full_dss_name, model_string, final_kw = f"Generator.{gen_name_only}", ("Model=1", kw) if phases == 3 else ("Model=3 PF=1.0", kw * 2)
        if gen_name_only in [name.lower() for name in dss.Generators.AllNames()]:
            dss.Text.Command(f"{full_dss_name}.kW={final_kw}")
        else:
            dss.Circuit.SetActiveBus(bus_name_lower)
            base_kv = dss.Bus.kVBase()
            if base_kv == 0: return
            conn, final_kv = (".1.2.3", base_kv) if phases == 3 else (f".{dss.Bus.Nodes()[0]}", base_kv / 1.732)
            dss.Text.Command(f'New {full_dss_name} Bus1={bus_name_lower}{conn} phases={phases} kV={final_kv:.4f} kW={final_kw} {model_string}')

    def add_device_to_bus(self, bus_name: str, device_name: str, kw: float, phases: int):
        """
        Adds a device's power to the existing load(s) on the bus and stores the device for reporting.
        The device itself is not a separate OpenDSS element.
        """
        bus_name_lower = bus_name.lower()
        load_found_and_updated = False

        # Find the load(s) on the specified bus and add the new device power to them
        if dss.Loads.Count() > 0:
            dss.Loads.First()
            while True:
                current_bus_name = dss.CktElement.BusNames()[0].split('.')[0].lower()
                if current_bus_name == bus_name_lower:
                    original_kw = dss.Loads.kW()
                    dss.Loads.kW(original_kw + kw)
                    load_found_and_updated = True
                if not dss.Loads.Next() > 0: break
        
        if not load_found_and_updated:
            print(f"Warning: No existing load found on bus '{bus_name_lower}' to add power from device '{device_name}'.")

        # Store the device information for API reporting
        if bus_name_lower not in self.devices:
            self.devices[bus_name_lower] = []
        
        # Remove any existing device with the same name on the same bus to prevent duplicates
        self.devices[bus_name_lower] = [d for d in self.devices[bus_name_lower] if d.get('device_name') != device_name]
        
        # Add the new device info
        self.devices[bus_name_lower].append({'device_name': device_name, 'kw': kw})

    # --- NEW FUNCTION ---
    def disconnect_device_from_bus(self, bus_name: str, device_name: str) -> bool:
        """
        Disconnects a device by subtracting its power from the parent bus's load
        and removes it from the aesthetic device list. Returns True if successful.
        """
        bus_name_lower = bus_name.lower()
        device_name_lower = device_name.lower()

        # Check if the bus and the device exist in our records
        if bus_name_lower not in self.devices:
            print(f"Info: No devices registered on bus '{bus_name_lower}'. Nothing to disconnect.")
            return False

        device_to_remove = None
        for device in self.devices[bus_name_lower]:
            if device.get('device_name').lower() == device_name_lower:
                device_to_remove = device
                break

        if not device_to_remove:
            print(f"Info: Device '{device_name}' not found on bus '{bus_name_lower}'.")
            return False

        # Get the power of the device to be removed
        kw_to_subtract = device_to_remove.get('kw', 0)

        # Find the corresponding load(s) in OpenDSS and subtract the power
        load_found_and_updated = False
        if dss.Loads.Count() > 0:
            dss.Loads.First()
            while True:
                current_bus_name = dss.CktElement.BusNames()[0].split('.')[0].lower()
                if current_bus_name == bus_name_lower:
                    original_kw = dss.Loads.kW()
                    new_kw = max(0, original_kw - kw_to_subtract) # Ensure load doesn't go negative
                    dss.Loads.kW(new_kw)
                    load_found_and_updated = True
                if not dss.Loads.Next() > 0: break
        
        if not load_found_and_updated:
            print(f"Warning: No load element found for bus '{bus_name_lower}' in the simulation to update.")
        
        # Remove the device from our internal list
        self.devices[bus_name_lower] = [
            d for d in self.devices[bus_name_lower] if d.get('device_name').lower() != device_name_lower
        ]
        # If the bus has no more devices, remove the bus key from the dictionary
        if not self.devices[bus_name_lower]:
            del self.devices[bus_name_lower]
            
        print(f"Success: Device '{device_name}' ({kw_to_subtract} kW) disconnected from bus '{bus_name}'.")
        return True

    def solve_power_flow(self):
        """Solves the power flow for the current state of the circuit."""
        dss.Text.Command("Set MaxControlIter=100")
        dss.Solution.Solve()

    def get_power_flow_results(self) -> dict:
        """Returns key metrics from the latest power flow solution."""
        total_p, _ = dss.Circuit.TotalPower()
        return {
            'converged': dss.Solution.Converged(),
            'total_power_kW': total_p,
            'total_losses_kW': dss.Circuit.Losses()[0]/1000
        }

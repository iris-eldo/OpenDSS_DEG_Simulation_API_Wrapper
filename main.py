import opendssdirect as dss
import pandas as pd

from IEEE_123_Bus_G_neighbourhoods import *


class OpenDSSCircuit:
    """
    A class to interact with a persistent OpenDSS circuit object,
    with automated management of neighborhood transformer loading.
    """

    def __init__(self, dss_file: str):
        self.dss_file = dss_file or r"Test_Systems\IEEE_123_Bus-G\Master.dss"
        self.devices = {}
        self.bus_capacities = {}
        self.bus_transformers = {} 
        self.transformer_statuses = {} 
        self.load_original_bus_map = {} # NEW: Tracks the original bus for each load
        self._initialize_dss()

    def _initialize_dss(self):
        """Initializes the DSS engine, inventories capacities, then adds transformers and rewires."""
        print("Initializing and compiling base circuit...")
        dss.Basic.ClearAll()
        dss.Text.Command(f'Compile "{self.dss_file}"')
        if dss.Circuit.NumBuses() == 0:
            raise FileNotFoundError(f"No buses found. Check DSS file: {self.dss_file}")
        
        # --- REORDERED LOGIC ---
        # 1. Inventory the original circuit to get per-bus loads.
        self._inventory_capacities_and_map_loads()
        # 2. Modify the circuit for simulation by adding transformers and rewiring.
        self._add_neighborhood_transformers_and_rewire_loads()

    def _inventory_capacities_and_map_loads(self):
        """
        Scans all loads and generators on the original circuit to populate the
        internal capacity tracking and create a map of loads to their original buses.
        """
        print("Inventorying original bus capacities and mapping loads...")
        self.bus_capacities = {}
        self.load_original_bus_map = {}
        
        if dss.Loads.Count() > 0:
            dss.Loads.First()
            while True:
                load_name = dss.Loads.Name()
                bus_name = dss.CktElement.BusNames()[0].split('.')[0].lower()
                kw = dss.Loads.kW()

                # Store the original bus for this load
                self.load_original_bus_map[load_name.lower()] = bus_name

                # Attribute the capacity to its actual bus
                if bus_name not in self.bus_capacities: 
                    self.bus_capacities[bus_name] = {'load_kw': 0, 'gen_kw': 0}
                self.bus_capacities[bus_name]['load_kw'] += kw
                
                if not dss.Loads.Next() > 0: break
        
        if dss.Generators.Count() > 0:
            dss.Generators.First()
            while True:
                bus_name = dss.CktElement.BusNames()[0].split('.')[0].lower()
                kw = dss.Generators.kW()
                if bus_name not in self.bus_capacities: self.bus_capacities[bus_name] = {'load_kw': 0, 'gen_kw': 0}
                self.bus_capacities[bus_name]['gen_kw'] += kw
                if not dss.Generators.Next() > 0: break
        print("Initial bus capacities inventoried.")

    def _add_neighborhood_transformers_and_rewire_loads(self):
        """
        Adds transformers and rewires existing loads to be served by them.
        """
        print("Adding neighborhood transformers and rewiring loads...")
        
        for neighborhood_id, primary_bus_name in TRANSFORMER_DATA.items():
            transformer_name = f"xfmr_neigh_{neighborhood_id}"
            primary_bus = primary_bus_name.lower()
            secondary_bus = f"{primary_bus}_sec"
            
            buses_in_neighborhood = [b.lower() for b in NEIGHBORHOOD_DATA.get(neighborhood_id, [])]

            if primary_bus not in [b.lower() for b in dss.Circuit.AllBusNames()]:
                continue

            dss.Circuit.SetActiveBus(primary_bus)
            primary_kv = dss.Bus.kVBase()
            if primary_kv == 0: continue
            
            dss_command = (f"New Transformer.{transformer_name} Phases=1 XHL=5.6 windings=2 "
                           f"Buses=[{primary_bus}, {secondary_bus}] kVs=[{primary_kv:.4f}, 0.24] "
                           f"kVAs=[300, 300] Conns=[Wye, Wye]")
            dss.Text.Command(dss_command)
            
            if primary_bus not in self.bus_transformers: self.bus_transformers[primary_bus] = []
            self.bus_transformers[primary_bus].append(transformer_name)

            for load_name, original_bus in self.load_original_bus_map.items():
                if original_bus in buses_in_neighborhood:
                    #print(f"  -> Moving Load.{load_name} from bus '{original_bus}' to '{secondary_bus}'")
                    dss.Text.Command(f"edit Load.{load_name} Bus1={secondary_bus} kV=0.24")

        print(f"Transformer and rewiring setup complete.")
                
    def _check_transformer_overloads(self) -> list:
        """Checks all transformers for overloading and returns a list of overloaded ones."""
        overloaded_transformers = []
        if dss.Transformers.Count() == 0: return overloaded_transformers
        
        dss.Transformers.First()
        while True:
            name = dss.Transformers.Name()
            dss.Circuit.SetActiveElement(f"Transformer.{name}")
            rated_kva = dss.Transformers.kVA()
            powers = dss.CktElement.Powers()
            current_kva = (powers[0]**2 + powers[1]**2)**0.5
            
            if current_kva > rated_kva:
                overloaded_transformers.append({
                    "name": name, "rated_kVA": rated_kva,
                    "current_kVA": current_kva, "overload_kVA": current_kva - rated_kva
                })
            if not dss.Transformers.Next() > 0: break
        return overloaded_transformers

    def _get_neighborhood_from_transformer(self, transformer_name: str) -> int:
        """Finds the neighborhood ID associated with a given transformer name."""
        try:
            return int(transformer_name.split('_')[-1])
        except (ValueError, IndexError):
            return -1
            
    def _disable_regulators(self):
        """Disables all regulator controls in the circuit to aid convergence."""
        if dss.RegControls.Count() == 0: return
        
        print("Disabling regulator controls to ensure snapshot solution convergence...")
        dss.RegControls.First()
        while True:
            dss.Text.Command(f"edit RegControl.{dss.RegControls.Name()} enabled=no")
            if not dss.RegControls.Next() > 0: break
                
    def _update_transformer_statuses(self):
        """
        Scans all transformers and updates their status, loading, and rating.
        """
        self.transformer_statuses.clear()
        if dss.Transformers.Count() == 0: return

        dss.Transformers.First()
        while True:
            name = dss.Transformers.Name()
            dss.Circuit.SetActiveElement(f"Transformer.{name}")
            rated_kva = dss.Transformers.kVA()
            powers = dss.CktElement.Powers()
            current_kva = (powers[0]**2 + powers[1]**2)**0.5
            loading_percent = (current_kva / rated_kva) * 100 if rated_kva > 0 else 0
            self.transformer_statuses[name] = {
                "name": name, "rated_kVA": rated_kva, "current_kVA": round(current_kva, 2),
                "loading_percent": round(loading_percent, 2), "status": "Overloaded" if loading_percent > 100 else "OK"
            }
            if not dss.Transformers.Next() > 0: break

    def solve_and_manage_loading(self, max_iterations=10) -> dict:
        """
        CORE METHOD: Solves power flow and automatically manages transformer overloads.
        """
        management_log = []
        self._disable_regulators()
        
        for i in range(max_iterations):
            dss.Text.Command("Set Mode=Snap")
            dss.Solution.Solve()

            if not dss.Solution.Converged():
                management_log.append("FATAL: Power flow failed to converge.")
                self._update_transformer_statuses()
                return {"status": "ERROR", "management_log": management_log}

            overloads = self._check_transformer_overloads()
            self._update_transformer_statuses()

            if not overloads:
                status = "OK"
                if i > 0: management_log.append(f"System stabilized after {i} iteration(s).")
                return {"status": status, "management_log": management_log}

            status = "ALERT"
            management_log.append(f"Iteration {i+1}: Detected {len(overloads)} overloaded transformer(s). Taking corrective action.")
            
            for overloaded_xfmr in overloads:
                neighborhood_id = self._get_neighborhood_from_transformer(overloaded_xfmr['name'])
                if neighborhood_id == -1: continue
                reduction_factor = (overloaded_xfmr['rated_kVA'] * 0.98) / overloaded_xfmr['current_kVA']
                management_log.append(f"-> Action: Reducing load in neighborhood {neighborhood_id} by factor {reduction_factor:.3f}.")
                self.modify_loads_in_neighborhood(neighborhood_id, reduction_factor)
        
        management_log.append(f"Warning: System could not be stabilized after {max_iterations} iterations.")
        return {"status": "ALERT", "management_log": management_log}

    def modify_loads_in_neighborhood(self, neighborhood_id: int, factor: float):
        """
        Modifies all loads within a neighborhood by a direct multiplication factor.
        """
        buses_in_neighborhood = [b.lower() for b in NEIGHBORHOOD_DATA.get(neighborhood_id, [])]
        
        for load_name, original_bus in self.load_original_bus_map.items():
            if original_bus in buses_in_neighborhood:
                # Update the simulation
                dss.Loads.Name(load_name)
                original_load_kw = dss.Loads.kW()
                new_kw = original_load_kw * factor
                dss.Text.Command(f"edit Load.{load_name} kW={new_kw}")
                
                # Update internal capacity tracking
                if original_bus in self.bus_capacities:
                    self.bus_capacities[original_bus]['load_kw'] -= (original_load_kw - new_kw)

    def get_buses_with_loads(self) -> pd.DataFrame:
        """
        Gets all buses with voltage info, power info from the logical model, and connected elements.
        """
        bus_data = []
        all_bus_names = [b.lower() for b in dss.Circuit.AllBusNames() if "_sec" not in b.lower()]

        for bus_name in all_bus_names:
            dss.Circuit.SetActiveBus(bus_name)
            nodes_on_bus = dss.Bus.Nodes()
            pu_voltages = dss.Bus.puVmagAngle()
            
            # Use the logical capacity data inventoried at the start
            caps = self.bus_capacities.get(bus_name, {'load_kw': 0, 'gen_kw': 0})
            total_load_kw = caps['load_kw']
            total_gen_kw = caps['gen_kw']
            net_power_kw = total_gen_kw - total_load_kw
            
            if nodes_on_bus:
                bus_data.append({
                    'Bus': bus_name, 'VMag_pu': pu_voltages[0], 'VAngle': pu_voltages[1],
                    'Load_kW': total_load_kw, 'Gen_kW': total_gen_kw, 'Net_Power_kW': net_power_kw
                })
        
        if not bus_data: return pd.DataFrame()

        buses_df = pd.DataFrame(bus_data)
        device_map = {bus: self.devices.get(bus, []) for bus in all_bus_names}
        
        transformer_map = {}
        for bus in all_bus_names:
            names = self.bus_transformers.get(bus, [])
            transformer_map[bus] = [self.transformer_statuses.get(name) for name in names if self.transformer_statuses.get(name)]

        buses_df['Devices'] = buses_df['Bus'].map(device_map)
        buses_df['Transformers'] = buses_df['Bus'].map(transformer_map)
        
        buses_df['Transformers'] = buses_df['Transformers'].apply(lambda d: d if isinstance(d, list) else [])
        buses_df['Devices'] = buses_df['Devices'].apply(lambda d: d if isinstance(d, list) else [])
        
        return buses_df

    def add_device_to_bus(self, bus_name: str, device_name: str, kw: float, phases: int):
        """Adds a new load (device) to the correct transformer secondary bus."""
        primary_bus_lower = bus_name.lower()
        
        neighborhood_id = -1
        for nid, buses in NEIGHBORHOOD_DATA.items():
            if primary_bus_lower in [b.lower() for b in buses]:
                neighborhood_id = nid
                break
                
        if neighborhood_id == -1: return

        transformer_primary_bus = TRANSFORMER_DATA.get(neighborhood_id)
        if not transformer_primary_bus: return
        secondary_bus = f"{transformer_primary_bus.lower()}_sec"

        if primary_bus_lower not in self.bus_capacities:
            self.bus_capacities[primary_bus_lower] = {'load_kw': 0, 'gen_kw': 0}
        self.bus_capacities[primary_bus_lower]['load_kw'] += kw
        
        if primary_bus_lower not in self.devices: self.devices[primary_bus_lower] = []
        self.devices[primary_bus_lower].append({'device_name': device_name, 'kw': kw})

        new_load_name = f"dev_{device_name.replace(' ', '_')}"
        dss.Text.Command(f"New Load.{new_load_name} Bus1={secondary_bus} phases=1 conn=wye kV=0.24 kW={kw} model=1")
        self.load_original_bus_map[new_load_name.lower()] = primary_bus_lower

    def add_generation_to_bus(self, bus_name: str, kw: float, phases: int):
        """Adds a new generator to a primary bus."""
        bus_name_lower = bus_name.lower()
        gen_name = f"Gen_{bus_name_lower}_{len(dss.Generators.AllNames()) + 1}"
        dss.Circuit.SetActiveBus(bus_name_lower)
        base_kv = dss.Bus.kVBase()
        if base_kv == 0: return
        
        conn, final_kv = (".1.2.3", base_kv) if phases == 3 else (f".{dss.Bus.Nodes()[0]}", base_kv / 1.732)
        dss.Text.Command(f'New Generator.{gen_name} Bus1={bus_name_lower}{conn} phases={phases} kV={final_kv:.4f} kW={kw} PF=1.0')

        if bus_name_lower not in self.bus_capacities: self.bus_capacities[bus_name_lower] = {'load_kw': 0, 'gen_kw': 0}
        self.bus_capacities[bus_name_lower]['gen_kw'] += kw

    def get_power_flow_results(self) -> dict:
        total_p, _ = dss.Circuit.TotalPower()
        return {'converged': dss.Solution.Converged(), 'total_power_kW': total_p, 'total_losses_kW': dss.Circuit.Losses()[0]/1000}

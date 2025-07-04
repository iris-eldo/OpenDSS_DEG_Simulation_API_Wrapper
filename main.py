import opendssdirect as dss
import pandas as pd

from IEEE_123_Bus_G_neighbourhoods import *

# This factor makes generation curtailment more aggressive to stabilize the system faster.
AGGRESSION_FACTOR = 1.25

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
        self.load_original_bus_map = {}
        self.original_load_kws = {} 
        self.generator_states = {} # NEW: To track original and current generator capacities
        self._initialize_dss()

    def _initialize_dss(self):
        """Initializes the DSS engine, inventories capacities, then adds transformers and rewires."""
        print("Initializing and compiling base circuit...")
        dss.Basic.ClearAll()
        dss.Text.Command(f'Compile "{self.dss_file}"')
        if dss.Circuit.NumBuses() == 0:
            raise FileNotFoundError(f"No buses found. Check DSS file: {self.dss_file}")
        
        self._inventory_capacities_and_map_loads()
        self._add_neighborhood_transformers_and_rewire_loads()

    def _inventory_capacities_and_map_loads(self):
        """
        Scans all loads and generators on the original circuit to populate the
        internal capacity tracking and create a map of loads to their original buses.
        """
        print("Inventorying original bus capacities and mapping loads...")
        self.bus_capacities = {}
        self.load_original_bus_map = {}
        self.original_load_kws = {}
        self.generator_states = {}
        
        if dss.Loads.Count() > 0:
            dss.Loads.First()
            while True:
                load_name = dss.Loads.Name()
                bus_name = dss.CktElement.BusNames()[0].split('.')[0].lower()
                kw = dss.Loads.kW()

                self.load_original_bus_map[load_name.lower()] = bus_name
                self.original_load_kws[load_name.lower()] = kw

                if bus_name not in self.bus_capacities: 
                    self.bus_capacities[bus_name] = {'load_kw': 0, 'gen_kw': 0}
                self.bus_capacities[bus_name]['load_kw'] += kw
                
                if not dss.Loads.Next() > 0: break
        
        if dss.Generators.Count() > 0:
            dss.Generators.First()
            while True:
                gen_name = dss.Generators.Name()
                bus_name = dss.CktElement.BusNames()[0].split('.')[0].lower()
                kw = dss.Generators.kW()
                if bus_name not in self.bus_capacities: self.bus_capacities[bus_name] = {'load_kw': 0, 'gen_kw': 0}
                self.bus_capacities[bus_name]['gen_kw'] += kw
                
                self.generator_states[gen_name.lower()] = {
                    'original_kw': kw,
                    'bus_name': bus_name,
                }
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
                           f"kVAs=[120, 120] Conns=[Wye, Wye]")
            dss.Text.Command(dss_command)
            
            if primary_bus not in self.bus_transformers: self.bus_transformers[primary_bus] = []
            self.bus_transformers[primary_bus].append(transformer_name)

            for load_name, original_bus in self.load_original_bus_map.items():
                if original_bus in buses_in_neighborhood:
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

    def _restore_generation_to_meet_load(self) -> bool:
        """
        NEW: Checks if any curtailed generator can be ramped up to meet new local load.
        """
        action_taken = False
        for gen_name, state in self.generator_states.items():
            bus_name = state['bus_name']
            bus_load_kw = self.bus_capacities.get(bus_name, {}).get('load_kw', 0)
            
            dss.Generators.Name(gen_name)
            current_gen_kw = dss.Generators.kW()
            
            if bus_load_kw > current_gen_kw:
                original_kw = state['original_kw']
                new_target_kw = min(original_kw, bus_load_kw)
                
                # Only make a change if it's significant
                if new_target_kw > current_gen_kw + 0.01:
                    dss.Text.Command(f"edit Generator.{gen_name} kW={new_target_kw}")
                    # Update bus_capacities to reflect the change
                    self.bus_capacities[bus_name]['gen_kw'] += (new_target_kw - current_gen_kw)
                    action_taken = True
                    
        return action_taken

    def solve_and_manage_loading(self, max_iterations=50) -> dict:
        """
        CORE METHOD: Solves power flow and automatically manages transformer overloads
        by first curtailing generation, then reducing load if necessary.
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

            # Pre-step: Dynamically restore generation to meet any new local load.
            if self._restore_generation_to_meet_load():
                management_log.append(f"Iteration {i+1} (Pre-step): Restored generation to meet local load. Re-solving.")
                dss.Solution.Solve()
                if not dss.Solution.Converged():
                    management_log.append("FATAL: Power flow failed to converge after restoring generation.")
                    self._update_transformer_statuses()
                    return {"status": "ERROR", "management_log": management_log}

            overloads = self._check_transformer_overloads()
            self._update_transformer_statuses()

            if not overloads:
                status = "OK"
                management_log.append(f"System stabilized in {i+1} iteration(s).")
                return {"status": status, "management_log": management_log}

            management_log.append(f"Iteration {i+1}: Detected {len(overloads)} overloaded transformer(s).")
            
            # Step 1: Attempt to curtail generation first (aggressively).
            if self._curtail_generator_overloads(overloads, management_log):
                continue

            # Step 2: If no generation was curtailed, proceed to reduce load.
            self._reduce_load_overloads(overloads, management_log)
        
        management_log.append(f"Warning: System could not be stabilized within the {max_iterations} iteration limit.")
        return {"status": "ALERT", "management_log": management_log}

    def _curtail_generator_overloads(self, overloads: list, management_log: list) -> bool:
        """
        Scans ALL neighborhoods. If any are net-exporting, it curtails their generation
        to attempt to alleviate any detected overloads anywhere in the system.
        """
        management_log.append("-> STAGE 1: Checking all neighborhoods for any net-generation...")

        exporting_neighborhoods = {}
        total_system_net_export = 0
        for hood_id in NEIGHBORHOOD_DATA.keys():
            buses_in_hood = [b.lower() for b in NEIGHBORHOOD_DATA.get(hood_id, [])]
            total_load = sum(self.bus_capacities.get(b, {}).get('load_kw', 0) for b in buses_in_hood)
            total_gen = sum(self.bus_capacities.get(b, {}).get('gen_kw', 0) for b in buses_in_hood)
            net_power = total_gen - total_load
            if net_power > 0:
                exporting_neighborhoods[hood_id] = net_power
                total_system_net_export += net_power

        if not exporting_neighborhoods:
            management_log.append("-> No net-exporting neighborhoods found anywhere in the system.")
            return False

        total_overload_kw = sum(xfmr['current_kVA'] - (xfmr['rated_kVA'] * 0.98) for xfmr in overloads)
        
        management_log.append(f"-> Found {len(exporting_neighborhoods)} exporting neighborhood(s) with a total net export of {total_system_net_export:.2f} kW.")
        management_log.append(f"-> Total transformer overload to be corrected: {total_overload_kw:.2f} kW.")

        # Aggressively curtail generation to solve faster
        curtailment_kw = min(total_overload_kw * AGGRESSION_FACTOR, total_system_net_export)

        if curtailment_kw <= 0.01: # Don't act on trivial amounts
            return False

        management_log.append(f"--> Action: Curtailing a total of {curtailment_kw:.2f} kW from exporting neighborhoods.")

        for hood_id, net_export in exporting_neighborhoods.items():
            if total_system_net_export > 0:
                proportion_of_export = net_export / total_system_net_export
                reduction_for_this_hood = curtailment_kw * proportion_of_export
                
                if reduction_for_this_hood > 0:
                    management_log.append(f"---> Curtailing generation in neighborhood {hood_id} by {reduction_for_this_hood:.2f} kW.")
                    self._curtail_neighborhood_generation_by_amount(hood_id, reduction_for_this_hood)

        return True

    def _reduce_load_overloads(self, overloads: list, management_log: list):
        """
        Reduces load for overloaded transformers in net-importing neighborhoods.
        """
        management_log.append("-> STAGE 2: Proceeding with load reduction for importing neighborhoods.")
        for xfmr in overloads:
            neighborhood_id = self._get_neighborhood_from_transformer(xfmr['name'])
            if neighborhood_id == -1: continue
            overload_kw = xfmr['current_kVA'] - (xfmr['rated_kVA'] * 0.98)
            management_log.append(f"--> Action: Reducing load in importing neighborhood {neighborhood_id} by {overload_kw:.2f} kW.")
            self._reduce_neighborhood_load_by_amount(neighborhood_id, overload_kw)

    def _reduce_neighborhood_load_by_amount(self, neighborhood_id: int, reduction_kw: float):
        """Reduces the load on net-importing buses within a neighborhood by a specific total amount."""
        buses_in_neighborhood = [b.lower() for b in NEIGHBORHOOD_DATA.get(neighborhood_id, [])]
        
        importing_buses_in_hood = {}
        total_net_import = 0
        for bus_name in buses_in_neighborhood:
            bus_cap = self.bus_capacities.get(bus_name)
            if not bus_cap: continue
            
            net_power = bus_cap['gen_kw'] - bus_cap['load_kw']
            if net_power < 0:
                import_val = abs(net_power)
                total_net_import += import_val
                importing_buses_in_hood[bus_name] = import_val
        
        if total_net_import == 0: return

        for bus_name, net_import_on_bus in importing_buses_in_hood.items():
            proportion_of_import = net_import_on_bus / total_net_import
            kw_to_shed_from_bus = reduction_kw * proportion_of_import
            
            total_load_on_bus = self.bus_capacities[bus_name]['load_kw']
            if total_load_on_bus > 0:
                factor = 1 - (kw_to_shed_from_bus / total_load_on_bus)
                self.modify_loads_in_houses(bus_name, factor, is_auto_reduction=True)

    def _curtail_neighborhood_generation_by_amount(self, neighborhood_id: int, reduction_kw: float):
        """
        Reduces the generation on net-exporting buses within a neighborhood by a specific total amount.
        This version is driven by the central bus_capacities state.
        """
        buses_in_neighborhood = [b.lower() for b in NEIGHBORHOOD_DATA.get(neighborhood_id, [])]
        
        exporting_buses = {}
        total_net_export_in_hood = 0
        for bus_name in buses_in_neighborhood:
            caps = self.bus_capacities.get(bus_name)
            if not caps: continue
            net_power = caps['gen_kw'] - caps['load_kw']
            if net_power > 0:
                exporting_buses[bus_name] = net_power
                total_net_export_in_hood += net_power
                
        if total_net_export_in_hood == 0: return

        for bus_name, net_export_on_bus in exporting_buses.items():
            proportion = net_export_on_bus / total_net_export_in_hood
            kw_to_shed_from_this_bus = reduction_kw * proportion

            current_gen_on_bus = self.bus_capacities[bus_name]['gen_kw']
            load_on_bus = self.bus_capacities[bus_name]['load_kw']
            
            new_target_gen_for_bus = current_gen_on_bus - kw_to_shed_from_this_bus
            
            floor_gen_kw = load_on_bus # The absolute minimum generation required for this bus
            final_gen_kw_for_bus = max(floor_gen_kw, new_target_gen_for_bus)
            
            if current_gen_on_bus > 0:
                scaling_factor = final_gen_kw_for_bus / current_gen_on_bus if current_gen_on_bus > 0 else 0
                
                # Find all generators on this bus and scale them
                gens_on_this_bus = [gn for gn, gs in self.generator_states.items() if gs['bus_name'] == bus_name]
                for gen_name in gens_on_this_bus:
                    dss.Generators.Name(gen_name)
                    original_gen_kw = dss.Generators.kW()
                    dss.Text.Command(f"edit Generator.{gen_name} kW={original_gen_kw * scaling_factor}")

            self.bus_capacities[bus_name]['gen_kw'] = final_gen_kw_for_bus

    def modify_loads_in_neighborhood(self, neighborhood_id: int, factor: float):
        """Modifies loads in a neighborhood, only affecting the net load on each importing bus."""
        buses_in_neighborhood = [b.lower() for b in NEIGHBORHOOD_DATA.get(neighborhood_id, [])]
        for bus_name in buses_in_neighborhood:
            self.modify_loads_in_houses(bus_name, factor)

    def modify_loads_in_houses(self, house_bus_name: str, factor: float, is_auto_reduction: bool = False) -> dict:
        """Modifies the load on a single bus. If not an auto_reduction, it only affects the net load."""
        bus_name_lower = house_bus_name.lower()
        bus_cap = self.bus_capacities.get(bus_name_lower)
        if not bus_cap or bus_cap['load_kw'] == 0:
            return {"status": "info", "message": f"No load found for bus '{house_bus_name}'."}

        loads_on_this_bus = {ln: ob for ln, ob in self.load_original_bus_map.items() if ob == bus_name_lower}
        if not loads_on_this_bus:
            return {"status": "info", "message": f"No loads in simulation for bus '{house_bus_name}'."}

        total_load_on_bus = bus_cap['load_kw']
        reduction_amount = 0
        
        if is_auto_reduction:
            reduction_amount = total_load_on_bus * (1 - factor)
        else:
            total_gen_on_bus = bus_cap['gen_kw']
            if total_load_on_bus > total_gen_on_bus:
                net_import = total_load_on_bus - total_gen_on_bus
                reduction_amount = net_import * (1 - factor)
            else:
                return {"status": "no_change", "message": "Bus is not a net power importer."}

        if total_load_on_bus > 0 and reduction_amount > 0:
            for load_name in loads_on_this_bus.keys():
                dss.Loads.Name(load_name)
                original_kw = dss.Loads.kW()
                proportion = original_kw / total_load_on_bus
                new_kw = original_kw - (reduction_amount * proportion)
                dss.Text.Command(f"edit Load.{load_name} kW={new_kw}")
        
        self.bus_capacities[bus_name_lower]['load_kw'] -= reduction_amount
        return {"status": "success", "message": "Load modified."}

    def get_buses_with_loads(self) -> pd.DataFrame:
        """Gets all buses with voltage info, power info from the logical model, and connected elements."""
        bus_data = []
        all_bus_names = [b.lower() for b in dss.Circuit.AllBusNames() if "_sec" not in b.lower()]

        for bus_name in all_bus_names:
            dss.Circuit.SetActiveBus(bus_name)
            nodes_on_bus = dss.Bus.Nodes()
            pu_voltages = dss.Bus.puVmagAngle()
            
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
        
        neighborhood_id = next((nid for nid, buses in NEIGHBORHOOD_DATA.items() if primary_bus_lower in [b.lower() for b in buses]), None)
        if neighborhood_id is None: return

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
        
        new_load_name_lower = new_load_name.lower()
        self.load_original_bus_map[new_load_name_lower] = primary_bus_lower
        self.original_load_kws[new_load_name_lower] = kw

    def disconnect_device_from_bus(self, bus_name: str, device_name: str) -> bool:
        """Removes a device from the simulation and updates capacity tracking."""
        primary_bus_lower = bus_name.lower()
        
        device_list = self.devices.get(primary_bus_lower, [])
        device_to_remove = next((d for d in device_list if d.get('device_name') == device_name), None)
        if not device_to_remove: return False

        kw_to_subtract = device_to_remove.get('kw', 0)
        
        if primary_bus_lower in self.bus_capacities:
            self.bus_capacities[primary_bus_lower]['load_kw'] -= kw_to_subtract
        
        self.devices[primary_bus_lower] = [d for d in device_list if d.get('device_name') != device_name]

        load_name_to_remove = f"dev_{device_name.replace(' ', '_')}"
        dss.Loads.Name(load_name_to_remove)
        if dss.Loads.Name().lower() == load_name_to_remove:
            dss.Text.Command(f"disable Load.{load_name_to_remove}")
        
        load_name_to_remove_lower = load_name_to_remove.lower()
        if load_name_to_remove_lower in self.load_original_bus_map:
            del self.load_original_bus_map[load_name_to_remove_lower]
        if load_name_to_remove_lower in self.original_load_kws:
            del self.original_load_kws[load_name_to_remove_lower]
            
        return True

    def add_generation_to_bus(self, bus_name: str, kw: float, phases: int):
        """Adds a new generator and updates capacity tracking."""
        print(f"Adding {kw}kW generator to bus {bus_name}.")
        
        bus_name_lower = bus_name.lower()
        # Create a more unique generator name
        gen_name = f"Gen_{bus_name_lower.replace('.', '_')}_{kw:.0f}kW"
        dss.Circuit.SetActiveBus(bus_name_lower)
        base_kv = dss.Bus.kVBase()
        if base_kv == 0: return
        
        conn, final_kv = (".1.2.3", base_kv) if phases == 3 else (f".{dss.Bus.Nodes()[0]}", base_kv / 1.732)
        dss.Text.Command(f'New Generator.{gen_name} Bus1={bus_name_lower}{conn} phases={phases} kV={final_kv:.4f} kW={kw} PF=1.0')

        if bus_name_lower not in self.bus_capacities:
            self.bus_capacities[bus_name_lower] = {'load_kw': 0, 'gen_kw': 0}
        self.bus_capacities[bus_name_lower]['gen_kw'] += kw
        
        # Track the new generator's original state
        self.generator_states[gen_name.lower()] = {
            'original_kw': kw,
            'bus_name': bus_name_lower,
        }

    def get_power_flow_results(self) -> dict:
        total_p, _ = dss.Circuit.TotalPower()
        return {'converged': dss.Solution.Converged(), 'total_power_kW': total_p, 'total_losses_kW': dss.Circuit.Losses()[0]/1000}

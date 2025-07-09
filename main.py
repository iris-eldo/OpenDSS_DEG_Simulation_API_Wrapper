import opendssdirect as dss
import pandas as pd
import time
import random

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
        self.storage_devices = {}
        self.last_simulation_time = time.time()
        self.bus_capacities = {}
        self.bus_transformers = {}
        self.transformer_statuses = {}
        self.load_original_bus_map = {}
        self.original_load_kws = {}
        self.generator_states = {}
        self.bus_dfps = {} # Tracks bus-level subscriptions
        self.dfps = [] # Initializes the list to store DFP program definitions
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
                           f"kVAs=[300, 300] Conns=[Wye, Wye]")
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

    def _update_storage_devices_state(self):
        """Updates the energy levels of storage devices based on elapsed time using actual rates."""
        current_time = time.time()
        delta_t_seconds = current_time - self.last_simulation_time
        self.last_simulation_time = current_time
        delta_t_hours = delta_t_seconds / 3600.0

        if delta_t_hours == 0:
            return

        for name, device in self.storage_devices.items():
            if not device.get('active', True):
                continue

            if device['mode'] == 'load':
                energy_added = device['actual_charge_rate'] * delta_t_hours
                device['current_energy_kwh'] += energy_added

                if device['current_energy_kwh'] >= device['max_capacity_kwh']:
                    device['current_energy_kwh'] = device['max_capacity_kwh']
                    print(f"Storage device '{name}' is full. Stopping charge.")
                    
                    dss.Text.Command(f"edit Load.{device['opendss_load_name']} kW=0")
                    self.bus_capacities[device['bus_name']]['load_kw'] -= device['actual_charge_rate']
                    device['actual_charge_rate'] = 0
                    device['active'] = False

            elif device['mode'] == 'generator':
                energy_removed = device['actual_discharge_rate'] * delta_t_hours
                device['current_energy_kwh'] -= energy_removed
                
                if device['current_energy_kwh'] <= 0:
                    device['current_energy_kwh'] = 0
                    print(f"Storage device '{name}' fully discharged. Stopping discharge.")

                    dss.Text.Command(f"edit Generator.{device['opendss_gen_name']} kW=0")
                    self.bus_capacities[device['bus_name']]['gen_kw'] -= device['actual_discharge_rate']
                    device['actual_discharge_rate'] = 0
                    device['active'] = False

    def solve_and_manage_loading(self, max_iterations=50) -> dict:
        """
        CORE METHOD: Solves power flow and automatically manages transformer overloads
        by first curtailing generation, then reducing load if necessary.
        """
        self._update_storage_devices_state()
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
        """Reduces the load on net-importing buses within a neighborhood by a specific total amount, prioritizing storage."""
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
            
            if kw_to_shed_from_bus <= 0: continue
            
            remaining_shed = kw_to_shed_from_bus

            # --- Stage 1: Reduce load from charging storage devices first ---
            active_storage_loads = [
                device for device in self.storage_devices.values()
                if device['bus_name'] == bus_name and device['mode'] == 'load' and device.get('active', True)
            ]
            for device in active_storage_loads:
                if remaining_shed <= 0: break
                
                current_kw = device['actual_charge_rate']
                reduction = min(remaining_shed, current_kw)
                
                # Update the device's actual rate and the OpenDSS element
                device['actual_charge_rate'] -= reduction
                dss.Text.Command(f"edit Load.{device['opendss_load_name']} kW={device['actual_charge_rate']}")
                remaining_shed -= reduction

            # --- Stage 2: If more shedding is needed, reduce other loads ---
            if remaining_shed > 0:
                regular_loads = {
                    ln: self.original_load_kws[ln] for ln, ob in self.load_original_bus_map.items() 
                    if ob == bus_name and not ln.startswith('stor_load_')
                }
                total_regular_load_kw = sum(regular_loads.values())

                if total_regular_load_kw > 0:
                    for load_name in regular_loads.keys():
                        if remaining_shed <= 0: break
                        dss.Loads.Name(load_name)
                        current_kw = dss.Loads.kW()
                        proportion = current_kw / total_regular_load_kw
                        reduction = min(remaining_shed * proportion, current_kw)
                        dss.Text.Command(f"edit Load.{load_name} kW={current_kw - reduction}")
                        remaining_shed -= reduction

            # --- Stage 3: Update the master bus capacity tracking ---
            actual_shed_amount = kw_to_shed_from_bus - remaining_shed
            if actual_shed_amount > 0:
                self.bus_capacities[bus_name]['load_kw'] -= actual_shed_amount

    def _curtail_neighborhood_generation_by_amount(self, neighborhood_id: int, reduction_kw: float):
        """Reduces generation on net-exporting buses within a neighborhood by a specific total amount, prioritizing storage."""
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
            floor_gen_kw = load_on_bus
            final_gen_kw_for_bus = max(floor_gen_kw, new_target_gen_for_bus)
            total_reduction_for_bus = current_gen_on_bus - final_gen_kw_for_bus
            
            if total_reduction_for_bus <= 0: continue
            remaining_reduction = total_reduction_for_bus

            # --- Stage 1: Curtail active storage devices ---
            active_storage_gens = [
                device for device in self.storage_devices.values()
                if device['bus_name'] == bus_name and device['mode'] == 'generator' and device.get('active', True)
            ]
            for device in active_storage_gens:
                if remaining_reduction <= 0: break
                current_kw = device['actual_discharge_rate']
                curtailment = min(remaining_reduction, current_kw)
                device['actual_discharge_rate'] -= curtailment
                dss.Text.Command(f"edit Generator.{device['opendss_gen_name']} kW={device['actual_discharge_rate']}")
                remaining_reduction -= curtailment

            # --- Stage 2: Curtail regular generators if still needed ---
            if remaining_reduction > 0:
                regular_gens = [
                    gen_name for gen_name in self.generator_states
                    if self.generator_states[gen_name]['bus_name'] == bus_name and not gen_name.startswith('stor_gen_')
                ]
                total_reg_gen_power = sum(dss.Generators.kW() for gen_name in regular_gens if dss.Generators.Name(gen_name))
                if total_reg_gen_power > 0:
                    for gen_name in regular_gens:
                        if remaining_reduction <= 0: break
                        dss.Generators.Name(gen_name)
                        current_kw = dss.Generators.kW()
                        proportion = current_kw / total_reg_gen_power
                        curtailment = min(remaining_reduction * proportion, current_kw)
                        dss.Text.Command(f"edit Generator.{gen_name} kW={current_kw - curtailment}")
                        remaining_reduction -= curtailment

            # --- Stage 3: Update the master bus capacity tracking ---
            actual_reduction_amount = total_reduction_for_bus - remaining_reduction
            if actual_reduction_amount > 0:
                self.bus_capacities[bus_name]['gen_kw'] -= actual_reduction_amount

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
        num_dfps = len(self.dfps)

        for bus_name in all_bus_names:
            dss.Circuit.SetActiveBus(bus_name)
            nodes_on_bus = dss.Bus.Nodes()
            pu_voltages = dss.Bus.puVmagAngle()

            x_coord = dss.Bus.X()
            y_coord = dss.Bus.Y()

            caps = self.bus_capacities.get(bus_name, {'load_kw': 0, 'gen_kw': 0})
            total_load_kw = caps['load_kw']
            total_gen_kw = caps['gen_kw']
            net_power_kw = total_gen_kw - total_load_kw

            dfps_list = self.bus_dfps.setdefault(bus_name, [0] * num_dfps)
            if len(dfps_list) != num_dfps:
                dfps_list = (dfps_list + [0] * num_dfps)[:num_dfps]
                self.bus_dfps[bus_name] = dfps_list

            if nodes_on_bus:
                bus_data.append({
                    'Bus': bus_name,
                    'Coordinates': {'X': x_coord, 'Y': y_coord},
                    'DFPs': dfps_list,
                    'VMag_pu': pu_voltages[0], 'VAngle': pu_voltages[1],
                    'Load_kW': total_load_kw, 'Gen_kW': total_gen_kw, 'Net_Power_kW': net_power_kw
                })

        if not bus_data: return pd.DataFrame()

        buses_df = pd.DataFrame(bus_data)
        device_map = {bus: self.devices.get(bus, []) for bus in all_bus_names}
        
        storage_map = {bus: [] for bus in all_bus_names}
        for name, details in self.storage_devices.items():
            bus = details['bus_name']
            if bus in storage_map:
                storage_map[bus].append({
                    'device_name': name,
                    'mode': details['mode'],
                    'current_energy_kwh': round(details['current_energy_kwh'], 2),
                    'max_capacity_kwh': details['max_capacity_kwh'],
                    'build_charge_rate': details['build_charge_rate'],
                    'build_discharge_rate': details['build_discharge_rate'],
                    'actual_charge_rate': details.get('actual_charge_rate', 0),
                    'actual_discharge_rate': details.get('actual_discharge_rate', 0)
                })

        transformer_map = {}
        for bus in all_bus_names:
            names = self.bus_transformers.get(bus, [])
            transformer_map[bus] = [self.transformer_statuses.get(name) for name in names if self.transformer_statuses.get(name)]

        buses_df['Devices'] = buses_df['Bus'].map(device_map)
        buses_df['Transformers'] = buses_df['Bus'].map(transformer_map)
        buses_df['StorageDevices'] = buses_df['Bus'].map(storage_map)

        buses_df['Transformers'] = buses_df['Transformers'].apply(lambda d: d if isinstance(d, list) else [])
        buses_df['Devices'] = buses_df['Devices'].apply(lambda d: d if isinstance(d, list) else [])
        buses_df['StorageDevices'] = buses_df['StorageDevices'].apply(lambda d: d if isinstance(d, list) else [])

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
        gen_name = f"Gen_{bus_name_lower.replace('.', '_')}_{kw:.0f}kW"
        dss.Circuit.SetActiveBus(bus_name_lower)
        base_kv = dss.Bus.kVBase()
        if base_kv == 0: return

        conn, final_kv = (".1.2.3", base_kv) if phases == 3 else (f".{dss.Bus.Nodes()[0]}", base_kv / 1.732)
        dss.Text.Command(f'New Generator.{gen_name} Bus1={bus_name_lower}{conn} phases={phases} kV={final_kv:.4f} kW={kw} PF=1.0')

        if bus_name_lower not in self.bus_capacities:
            self.bus_capacities[bus_name_lower] = {'load_kw': 0, 'gen_kw': 0}
        self.bus_capacities[bus_name_lower]['gen_kw'] += kw

        self.generator_states[gen_name.lower()] = {
            'original_kw': kw,
            'bus_name': bus_name_lower,
        }

    def add_storage_device(self, bus_name: str, device_name: str, max_capacity_kwh: float, charge_rate_kw: float, discharge_rate_kw: float):
        """Adds a new storage device to the grid with separate charge/discharge rates."""
        primary_bus_lower = bus_name.lower()
        device_name_lower = device_name.lower().replace(' ', '_')

        neighborhood_id = next((nid for nid, buses in NEIGHBORHOOD_DATA.items() if primary_bus_lower in [b.lower() for b in buses]), None)
        if neighborhood_id is None:
            print(f"Error: Bus '{bus_name}' not found in any neighborhood.")
            return
        transformer_primary_bus = TRANSFORMER_DATA.get(neighborhood_id)
        if not transformer_primary_bus:
            print(f"Error: No transformer mapping for neighborhood {neighborhood_id}.")
            return
        secondary_bus = f"{transformer_primary_bus.lower()}_sec"

        load_name = f"stor_load_{device_name_lower}"
        gen_name = f"stor_gen_{device_name_lower}"

        self.storage_devices[device_name_lower] = {
            'bus_name': primary_bus_lower,
            'max_capacity_kwh': max_capacity_kwh,
            'current_energy_kwh': 0.0,
            'build_charge_rate': charge_rate_kw,
            'build_discharge_rate': discharge_rate_kw,
            'actual_charge_rate': charge_rate_kw, # Starts at build rate
            'actual_discharge_rate': 0, # Starts inactive
            'mode': 'load',
            'active': True,
            'last_update_time': time.time(),
            'opendss_load_name': load_name,
            'opendss_gen_name': gen_name,
        }

        dss.Text.Command(f"New Load.{load_name} Bus1={secondary_bus} phases=1 conn=wye kV=0.24 kW={charge_rate_kw} model=1")
        dss.Text.Command(f"New Generator.{gen_name} Bus1={secondary_bus} phases=1 kV=0.24 kW={discharge_rate_kw} PF=1.0 enabled=no")

        if primary_bus_lower not in self.bus_capacities:
            self.bus_capacities[primary_bus_lower] = {'load_kw': 0, 'gen_kw': 0}
        self.bus_capacities[primary_bus_lower]['load_kw'] += charge_rate_kw
        
        print(f"Storage device '{device_name}' added to bus '{bus_name}' in load mode.")

    def _disconnect_storage_device(self, device_name: str) -> dict:
        """NEW: Disconnects a storage device entirely from the simulation."""
        device_name_lower = device_name.lower().replace(' ', '_')
        device = self.storage_devices.get(device_name_lower)
        if not device:
            return {"status": "error", "message": f"Storage device '{device_name}' not found."}

        bus_name = device['bus_name']
        load_name = device['opendss_load_name']
        gen_name = device['opendss_gen_name']

        # Subtract its current contribution from bus capacities
        if device.get('active', True):
            if device['mode'] == 'load':
                if bus_name in self.bus_capacities and 'load_kw' in self.bus_capacities[bus_name]:
                    self.bus_capacities[bus_name]['load_kw'] -= device['actual_charge_rate']
            elif device['mode'] == 'generator':
                if bus_name in self.bus_capacities and 'gen_kw' in self.bus_capacities[bus_name]:
                    self.bus_capacities[bus_name]['gen_kw'] -= device['actual_discharge_rate']

        # Disable both OpenDSS elements associated with the storage device
        dss.Text.Command(f"disable Load.{load_name}")
        dss.Text.Command(f"disable Generator.{gen_name}")

        # Remove the device from the internal tracking dictionary
        del self.storage_devices[device_name_lower]

        message = f"Storage device '{device_name}' has been disconnected."
        print(message)
        return {"status": "success", "message": message}

    def toggle_storage_device(self, device_name: str, action: str = 'toggle') -> dict:
        """
        Toggles a storage device between load and generator modes, or disconnects it.
        'action' can be 'toggle' or 'disconnect'.
        """
        device_name_lower = device_name.lower().replace(' ', '_')

        if action.lower() == 'disconnect':
            return self._disconnect_storage_device(device_name)

        if action.lower() != 'toggle':
            return {"status": "error", "message": f"Invalid action '{action}'. Must be 'toggle' or 'disconnect'."}

        # --- Existing toggle logic proceeds from here ---
        device = self.storage_devices.get(device_name_lower)
        if not device:
            return {"status": "error", "message": f"Storage device '{device_name}' not found."}

        bus_name = device['bus_name']
        build_charge_kw = device['build_charge_rate']
        build_discharge_kw = device['build_discharge_rate']
        load_name = device['opendss_load_name']
        gen_name = device['opendss_gen_name']
        is_active = device.get('active', True)

        if device['mode'] == 'load':
            if device['current_energy_kwh'] <= 0:
                return {"status": "error", "message": f"Cannot switch to generator mode: Storage device '{device_name}' has no energy."}
            
            dss.Text.Command(f"edit Load.{load_name} enabled=no")
            if is_active:
                self.bus_capacities[bus_name]['load_kw'] -= device['actual_charge_rate']

            dss.Text.Command(f"edit Generator.{gen_name} enabled=yes kW={build_discharge_kw}")
            self.bus_capacities[bus_name]['gen_kw'] += build_discharge_kw
            
            device['mode'] = 'generator'
            device['active'] = True
            device['actual_charge_rate'] = 0
            device['actual_discharge_rate'] = build_discharge_kw
            message = f"Storage device '{device_name}' toggled to GENERATOR mode."

        elif device['mode'] == 'generator':
            dss.Text.Command(f"edit Generator.{gen_name} enabled=no")
            if is_active:
                self.bus_capacities[bus_name]['gen_kw'] -= device['actual_discharge_rate']

            dss.Text.Command(f"edit Load.{load_name} enabled=yes kW={build_charge_kw}")
            self.bus_capacities[bus_name]['load_kw'] += build_charge_kw

            device['mode'] = 'load'
            device['active'] = True
            device['actual_discharge_rate'] = 0
            device['actual_charge_rate'] = build_charge_kw
            message = f"Storage device '{device_name}' toggled to LOAD mode."
        
        device['last_update_time'] = time.time()
        return {"status": "success", "message": message}

    def subscribe_dfp(self, bus_name: str, dfp_name: str) -> dict:
        """Subscribes a bus to a DFP by its name."""
        bus_name_lower = bus_name.lower()
        all_buses = [b.lower() for b in dss.Circuit.AllBusNames()]
        if bus_name_lower not in all_buses:
            return {"status": "error", "message": f"Bus '{bus_name}' not found."}

        target_dfp = next((dfp for dfp in self.dfps if dfp['name'].lower() == dfp_name.lower()), None)
        if not target_dfp:
            return {"status": "error", "message": f"DFP with name '{dfp_name}' not found."}
        
        dfp_index = target_dfp['index']
        num_dfps = len(self.dfps)

        dfp_list = self.bus_dfps.setdefault(bus_name_lower, [])
        if len(dfp_list) < num_dfps:
            dfp_list.extend([0] * (num_dfps - len(dfp_list)))

        dfp_list[dfp_index - 1] = 1
        return {"status": "success"}

    def unsubscribe_dfp(self, bus_name: str, dfp_name: str) -> dict:
        """Unsubscribes a bus from a DFP by its name."""
        bus_name_lower = bus_name.lower()
        all_buses = [b.lower() for b in dss.Circuit.AllBusNames()]
        if bus_name_lower not in all_buses:
            return {"status": "error", "message": f"Bus '{bus_name}' not found."}

        target_dfp = next((dfp for dfp in self.dfps if dfp['name'].lower() == dfp_name.lower()), None)
        if not target_dfp:
            return {"status": "error", "message": f"DFP with name '{dfp_name}' not found."}

        dfp_index = target_dfp['index']
        num_dfps = len(self.dfps)

        dfp_list = self.bus_dfps.setdefault(bus_name_lower, [])
        if len(dfp_list) < num_dfps:
            dfp_list.extend([0] * (num_dfps - len(dfp_list)))

        if len(dfp_list) >= dfp_index:
            dfp_list[dfp_index - 1] = 0
        
        return {"status": "success"}

    def register_dfp(self, name: str, min_power_kw: float, target_pf: float):
        """Registers a new DFP. The index is determined by its position in the list."""
        dfp_index = len(self.dfps) + 1
        dfp_details = {
            "index": dfp_index,
            "name": name,
            "min_power_kw": min_power_kw,
            "target_pf": target_pf,
            "registered_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.dfps.append(dfp_details)
        print(f"DFP '{name}' (Index: {dfp_index}) registered successfully.")
        return dfp_details

    def update_dfp(self, name: str, new_min_power_kw: float, new_target_pf: float) -> dict:
        """NEW: Updates the parameters of an existing DFP identified by its name."""
        dfp_to_update = next((dfp for dfp in self.dfps if dfp['name'].lower() == name.lower()), None)

        if not dfp_to_update:
            return {"status": "error", "message": f"DFP with name '{name}' not found."}

        dfp_to_update['min_power_kw'] = new_min_power_kw
        dfp_to_update['target_pf'] = new_target_pf
        print(f"DFP '{name}' updated successfully.")
        return {"status": "success", "data": dfp_to_update}

    def delete_dfp(self, name: str) -> dict:
        """
        NEW: Deletes a DFP by its name and re-indexes all subsequent DFPs and bus subscriptions.
        """
        dfp_to_delete_index = -1
        for i, dfp in enumerate(self.dfps):
            if dfp['name'].lower() == name.lower():
                dfp_to_delete_index = i
                break

        if dfp_to_delete_index == -1:
            return {"status": "error", "message": f"DFP with name '{name}' not found."}

        self.dfps.pop(dfp_to_delete_index)
        print(f"DFP '{name}' removed from registry.")

        for i in range(dfp_to_delete_index, len(self.dfps)):
            self.dfps[i]['index'] -= 1

        for bus, subscriptions in self.bus_dfps.items():
            if len(subscriptions) > dfp_to_delete_index:
                subscriptions.pop(dfp_to_delete_index)
        
        print("All bus subscriptions have been re-mapped.")
        return {"status": "success"}

    def modify_high_wattage_devices_in_bus(self, bus_name: str, power_threshold_kw: float, reduction_factor: float) -> dict:
        """
        Reduces the load for all devices in a specific bus that are above a given power threshold.
        """
        bus_name_lower = bus_name.lower()
        devices_on_bus = self.devices.get(bus_name_lower, [])
        if not devices_on_bus:
            return {"status": "info", "message": f"No devices found on bus '{bus_name}'."}

        modified_count = 0
        total_reduction_kw = 0

        for device in list(devices_on_bus):
            if device.get('type') == 'storage': continue
            if device['kw'] > power_threshold_kw:
                original_kw = device['kw']
                new_kw = original_kw * reduction_factor
                reduction_amount = original_kw - new_kw

                load_name = f"dev_{device['device_name'].replace(' ', '_')}"
                dss.Text.Command(f"edit Load.{load_name} kW={new_kw}")
                
                device['kw'] = new_kw
                total_reduction_kw += reduction_amount
                modified_count += 1
        
        if total_reduction_kw > 0:
            if bus_name_lower in self.bus_capacities:
                self.bus_capacities[bus_name_lower]['load_kw'] -= total_reduction_kw

        if modified_count > 0:
            return {
                "status": "success", 
                "message": f"Modified {modified_count} devices on bus '{bus_name}'. Total load reduced by {total_reduction_kw:.2f} kW."
            }
        else:
            return {
                "status": "info",
                "message": f"No devices on bus '{bus_name}' exceeded the {power_threshold_kw} kW threshold."
            }


    def execute_dfp(self, dfp_name: str) -> dict:
        """
        Finds all buses subscribed to a DFP, executes its rules,
        and returns the participation status for each bus.
        """
        target_dfp = next((dfp for dfp in self.dfps if dfp['name'].lower() == dfp_name.lower()), None)
        if not target_dfp:
            return {"status": "error", "message": f"DFP with name '{dfp_name}' not found."}
        
        dfp_index = target_dfp['index']
        power_threshold_kw = target_dfp['min_power_kw']
        reduction_factor = target_dfp['target_pf']

        subscribed_buses = [
            bus_name for bus_name, subs in self.bus_dfps.items() 
            if len(subs) >= dfp_index and subs[dfp_index - 1] == 1
        ]

        if not subscribed_buses:
            return {"status": "info", "message": f"No buses are subscribed to DFP '{dfp_name}'."}

        log_summary = []
        participation_data = []
        
        for bus_name in subscribed_buses:
            did_participate = random.choice([True, False])
            participation_data.append({'bus_name': bus_name, 'participated': did_participate})
            
            if did_participate:
                result = self.modify_high_wattage_devices_in_bus(bus_name, power_threshold_kw, reduction_factor)
                log_summary.append(f"Bus '{bus_name}': {result['message']}")
            else:
                log_summary.append(f"Bus '{bus_name}': Chose not to participate")

        return {
            "status": "success",
            "message": f"Executed DFP '{dfp_name}' on {len(subscribed_buses)} bus(es).",
            "details": log_summary,
            "participation_data": participation_data
        }
    
    def get_power_flow_results(self) -> dict:
        """Returns key power flow results from the circuit."""
        total_p, _ = dss.Circuit.TotalPower()
        return {'converged': dss.Solution.Converged(), 'total_power_kW': total_p, 'total_losses_kW': dss.Circuit.Losses()[0]/1000}

    def get_system_capacity_info(self) -> dict:
        """
        Calculates the total original load and total transformer capacity of the system.
        """
        max_load_kw = sum(self.original_load_kws.values())

        max_power_kva = 0
        if dss.Transformers.Count() > 0:
            dss.Transformers.First()
            while True:
                max_power_kva += dss.Transformers.kVA()
                if not dss.Transformers.Next() > 0:
                    break
        
        return {
            "maximum_circuit_load_kW": max_load_kw,
            "maximum_circuit_power_kVA": max_power_kva
        }

import opendssdirect as dss
import pandas as pd

# Data mapping zip codes to a list of bus names.
NEIGHBORHOOD_DATA = {
    1: ['150', '150r', '149', '1', '2', '197', '3', '4', '5', '6', '7', '8'],
    2: ['9', '10', '11', '12', '14', '9r'],
    3: ['13', '15', '16', '17', '34', '52', '53', '152'],
    4: ['54', '55', '56', '57', '58', '59'],
    5: ['18', '19', '20', '21', '22', '23', '24', '135'],
    6: ['25r', '25', '26', '27', '28', '29', '30', '31', '32', '33', '250'],
    7: ['35', '36', '37', '38', '39', '40', '41'],
    8: ['42', '43', '44', '45', '46', '47', '48', '49', '50', '51', '151'],
    9: ['60', '61', '62', '63', '64', '65', '66', '61s', '610', '160r'],
    10: ['86', '87', '88', '89', '90', '91', '92', '93', '94_open', '95', '96'],
    11: ['76', '77', '78', '79', '80', '81', '82', '83', '84', '85'],
    12: ['67', '68', '69', '70', '71', '72', '73', '74', '75'],
    13: ['97', '98', '99', '100', '101', '102', '103', '104', '197', '450'],
    14: ['105', '106', '107', '108', '109', '110', '111', '112', '113', '114', '300_open']
}

class OpenDSSCircuit:
    """A class to interact with a persistent OpenDSS circuit object."""

    def __init__(self, dss_file: str):
        self.dss_file = dss_file or r"Test_Systems\IEEE_123_Bus-G\Master.dss"
        self._initialize_dss()

    def _initialize_dss(self):
        print("Initializing and compiling base circuit...")
        dss.Basic.ClearAll()
        dss.Text.Command(f'Compile "{self.dss_file}"')
        if dss.Circuit.NumBuses() == 0:
            raise FileNotFoundError(f"No buses found. Check DSS file: {self.dss_file}")

    def get_buses_with_loads(self) -> pd.DataFrame:
        """Gets all buses with voltage and correctly attributed load and generation information."""
        bus_data = []
        all_bus_names = [b.lower() for b in dss.Circuit.AllBusNames()]
        for bus_name in all_bus_names:
            dss.Circuit.SetActiveBus(bus_name)
            nodes_on_bus = dss.Bus.Nodes()
            pu_voltages = dss.Bus.puVmagAngle()
            for i, node in enumerate(nodes_on_bus):
                if (2 * i + 1) < len(pu_voltages):
                    v_mag_pu = pu_voltages[2 * i]
                    v_angle = pu_voltages[2 * i + 1]
                    bus_data.append({'Bus': bus_name, 'Node': node, 'VMag_pu': v_mag_pu, 'VAngle': v_angle})
        buses_df = pd.DataFrame(bus_data)

        # --- Definitive Fix for Load and Generation Aggregation ---
        
        load_kw, load_kvar = {}, {}
        gen_kw, gen_kvar = {}, {}

        # Aggregate loads per node
        if dss.Loads.Count() > 0:
            dss.Loads.First()
            while True:
                bus_name = dss.CktElement.BusNames()[0].split('.')[0].lower() # A Load has one terminal
                nodes = dss.CktElement.NodeOrder()
                num_nodes = len(nodes)
                if num_nodes > 0:
                    kw_per_node = dss.Loads.kW() / num_nodes
                    kvar_per_node = dss.Loads.kvar() / num_nodes
                    for node in nodes:
                        key = (bus_name, node)
                        load_kw[key] = load_kw.get(key, 0) + kw_per_node
                        load_kvar[key] = load_kvar.get(key, 0) + kvar_per_node
                if not dss.Loads.Next() > 0: break

        # Aggregate generators per node
        if dss.Generators.Count() > 0:
            dss.Generators.First()
            while True:
                bus_name = dss.CktElement.BusNames()[0].split('.')[0].lower() # A Generator has one terminal
                nodes = dss.CktElement.NodeOrder()
                num_nodes = len(nodes)
                powers = dss.CktElement.Powers()
                
                if num_nodes > 0 and len(powers) >= 2:
                    # Sum up all real and reactive powers for the element
                    total_kw = -1 * sum(powers[::2])
                    total_kvar = -1 * sum(powers[1::2])
                    # Distribute the total power among the nodes
                    kw_per_node = total_kw / num_nodes
                    kvar_per_node = total_kvar / num_nodes
                    for node in nodes:
                        key = (bus_name, node)
                        gen_kw[key] = gen_kw.get(key, 0) + kw_per_node
                        gen_kvar[key] = gen_kvar.get(key, 0) + kvar_per_node
                if not dss.Generators.Next() > 0: break
        
        # Map the aggregated data back to the main DataFrame
        buses_df['Load_kW'] = buses_df.apply(lambda row: load_kw.get((row['Bus'], row['Node']), 0), axis=1)
        buses_df['Load_kVAR'] = buses_df.apply(lambda row: load_kvar.get((row['Bus'], row['Node']), 0), axis=1)
        buses_df['Gen_kW'] = buses_df.apply(lambda row: gen_kw.get((row['Bus'], row['Node']), 0), axis=1)
        buses_df['Gen_kVAR'] = buses_df.apply(lambda row: gen_kvar.get((row['Bus'], row['Node']), 0), axis=1)

        return buses_df.fillna(0)

    def modify_loads_in_neighborhood(self, neighborhood_id: int, factor: float):
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
        """Adds or updates a generator on a specific bus, using different models for 1-ph and 3-ph."""
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
            final_kw = kw * 2 # Apply the "half-power" fix

        if gen_name_only in all_gen_names:
            # If it exists, update its kW property
            print(f"Generator '{gen_name_only}' already exists. Updating its kW setpoint.")
            dss.Text.Command(f"{full_dss_name}.kW={final_kw}")
        else:
            # If it does not exist, create it
            print(f"Adding new generator '{gen_name_only}'...")
            dss.Circuit.SetActiveBus(bus_name_lower)
            base_kv = dss.Bus.kVBase()

            # Defensive check to prevent crash if bus has no voltage base
            if base_kv == 0:
                print(f"ERROR: Bus '{bus_name_lower}' has a base voltage of 0. Cannot add generator.")
                return

            # Determine connection string and kV based on phase
            if phases == 3:
                conn = ".1.2.3"
                final_kv = base_kv
            else:
                node = dss.Bus.Nodes()[0]
                conn = f".{node}"
                final_kv = base_kv / 1.732
            
            dss.Text.Command(
                f'New {full_dss_name} '
                f'Bus1={bus_name_lower}{conn} phases={phases} '
                f'kV={final_kv:.4f} '
                f'kW={final_kw} {model_string}'
            )

    def solve_power_flow(self):
        dss.Text.Command("Set MaxControlIter=100")
        dss.Solution.Solve()

    def get_power_flow_results(self) -> dict:
        total_p, _ = dss.Circuit.TotalPower()
        return {'converged': dss.Solution.Converged(), 'total_power_kW': total_p, 'total_losses_kW': dss.Circuit.Losses()[0]/1000}
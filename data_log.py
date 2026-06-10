import pandas as pd
import matplotlib.pyplot as plt

file = "2025-05-16 10-35.csv"
dataframe = pd.read_csv(file,
                 header=0,
                 sep=",",
                 usecols=["Calculated boost (bar)",
                           "Calculated engine load value (%)",
                           "Calculated instant fuel consumption (MPG)",
                           "Engine coolant temperature (℉)",
                           "Engine RPM (rpm)",
                           "Fuel/Air commanded equivalence ratio ()",
                           "Instant engine power (based on fuel consumption) (hp)",
                           "Intake air temperature (℉)",
                           "Intake manifold absolute pressure (kPa)",
                           "MAF air flow rate (g/sec)",
                           "Power from MAF (hp)",
                           "Vehicle acceleration (g)",
                           "Vehicle speed (mph)"]
                )

def plot(parameters, labels):
        for i in range(len(parameters)):
                plt.subplot(8, 2, i + 1)
                plt.plot(parameters[i].index, parameters[i], label=labels[i])
                plt.title(f"{labels[i]} Over Time")

def show_info(df):
        rpm_label = "Engine RPM (rpm)"
        rpm = df[df[f"{rpm_label}"] > 0]
        speed_label = "Vehicle speed (mph)"
        speed = df[df[f"{speed_label}"] > 0]
        afr_label = "Fuel/Air commanded equivalence ratio ()"
        afr = df[df[f"{afr_label}"] > 0]
        boost_label = "Calculated boost (bar)"
        boost = df[df[f"{boost_label}"] > 0]
        hp_label = "Instant engine power (based on fuel consumption) (hp)"
        hp = df[df[f"{hp_label}"] > 0]
        maf_label = "MAF air flow rate (g/sec)"
        maf = df[df[f"{maf_label}"] > 0]
        coolant_temp_label = "Engine coolant temperature (℉)"
        coolant_temp = df[df[f"{coolant_temp_label}"] > 0]
        intake_temp_label = "Intake air temperature (℉)"
        intake_temp = df[df[f"{intake_temp_label}"] > 0]
        intake_pressure_label = "Intake manifold absolute pressure (kPa)"
        intake_pressure = df[df[f"{intake_pressure_label}"] > 0]
        acceleration_label = "Vehicle acceleration (g)"
        acceleration = df[df[f"{acceleration_label}"] > 0]
        
        
        parameters = [rpm, speed, afr, boost, hp, maf, coolant_temp, intake_temp, intake_pressure, acceleration]
        labels = [rpm_label, speed_label, afr_label, boost_label, hp_label, maf_label, coolant_temp_label, intake_temp_label, intake_pressure_label, acceleration_label]
        
        plt.figure(figsize=(20, 15))
        plot(parameters, labels)
        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
        bmw = dataframe.loc[2850:3400]
        show_info(bmw)

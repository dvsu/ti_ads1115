import sys
import json
from time import sleep
from ads1115 import ADS1115, PGA, I2CBus, I2CAddress


adc = ADS1115(bus=I2CBus.ONE,
              pga=PGA.FSR_6_144,
              address=I2CAddress.X48)

while True:
    try:
        # Example output
        # {
        #     "input_voltage": {
        #         "in0_in1": 4.68261,
        #         "in0_in3": 4.1965,
        #         "in1_in3": -0.5054,
        #         "in2_in3": 0.61341,
        #         "in0_gnd": 5.03286,
        #         "in1_gnd": 0.33044,
        #         "in2_gnd": 1.44925,
        #         "in3_gnd": 0.81636
        #     },
        #     "timestamp": 1627898911
        # }
        print(json.dumps(adc.get_measurement(), indent=2))
        sleep(2)

    except KeyboardInterrupt:
        sys.exit(1)

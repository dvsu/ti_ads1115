import sys
from time import sleep
from ads1115 import ADS1115, PGA, I2CBus, I2CAddress


ad = ADS1115(bus=I2CBus.ONE,
             pga=PGA.FSR_6_144,
             address=I2CAddress.X48)

while True:
    try:
        print(f"""IN0-GND: {ad.read_input_in0_gnd():.3f}V \
        IN1-GND: {ad.read_input_in1_gnd():.3f}V \
        IN2-GND: {ad.read_input_in2_gnd():.3f}V \
        IN3-GND: {ad.read_input_in3_gnd():.3f}V \
        """)
        sleep(1)

    except KeyboardInterrupt:
        sys.exit(1)

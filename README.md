# TI ADS1115

Driver for Texas Instruments TI ADS1115 analog-to-digital converter, written in Python

## How It Works

Once initialized, the input voltage measurement will be queued in `data`, in the background every 500ms. Then, `get_measurement()` method can be called to pull a datapoint from the queue. Each datapoint contains a timestamp, which can be used to identify the time when the specific measurement was taken. Please see example and output structure below.

## Example

Conditions:

- `Vcc` = 5V
- 4 analog inputs, `IN0`, `IN1`, `IN2`, and `IN3`
- Reference of measurement: `GND`
- Maximum voltage of analog input <= `Vcc`

```python
import sys
import json
from time import sleep
from ads1115 import ADS1115, PGA, I2CBus, I2CAddress


adc = ADS1115(bus=1,
              pga=PGA.FSR_6_144,
              address=I2CAddress.X48)

while True:
    try:
        print(json.dumps(adc.get_measurement(), indent=2))
        sleep(2)

    except KeyboardInterrupt:
        sys.exit(1)

```

## Output Structure

```json
{
  "input_voltage": {
    "in0_in1": 4.68261,
    "in0_in3": 4.1965,
    "in1_in3": -0.5054,
    "in2_in3": 0.61341,
    "in0_gnd": 5.03286,
    "in1_gnd": 0.33044,
    "in2_gnd": 1.44925,
    "in3_gnd": 0.81636
  },
  "timestamp": 1627898911
}
```

The `"input_voltage"` key consists of 8 key-value pairs. Key name is self-explanatory, i.e. measurement taken between 2 points. The value is the voltage of measurement in `Volt`. As the example of measurement is made between analog input `INx` and `GND`, then key-value pairs we are interested in are

- `"in0_gnd": 5.03286`
- `"in1_gnd": 0.33044`
- `"in2_gnd": 1.44925`
- `"in3_gnd": 0.81636`

These voltage were taken at `timestamp`, measured in seconds since the Unix epoch.

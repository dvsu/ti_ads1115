import sys
import smbus
import logging
import threading
from queue import Queue
from time import sleep
from datetime import datetime
from enum import Enum


class I2CAddress(Enum):
    X48 = 0x48  # ADDR - GND (default)
    X49 = 0x49  # ADDR - VDD
    X4A = 0x4A  # ADDR - SDA
    X4B = 0x4B  # ADDR - SCL


class PGA(Enum):
    FSR_6_144 = 0b000  # +-6.144V
    FSR_4_096 = 0b001  # +-4.096V
    FSR_2_048 = 0b010  # +-2.048V # default
    FSR_1_024 = 0b011  # +-1.024V
    FSR_0_512 = 0b100  # +-0.512V
    FSR_0_256_1 = 0b101  # +-0.256V
    FSR_0_256_2 = 0b110  # +-0.256V
    FSR_0_256_3 = 0b111  # +-0.256V


class OperatingMode(Enum):
    CONTINUOUS = 0b0
    SINGLE_SHOT = 0b1  # default


class DataRate(Enum):
    SPS_8 = 0b000
    SPS_16 = 0b001
    SPS_32 = 0b010
    SPS_64 = 0b011
    SPS_128 = 0b100  # default
    SPS_250 = 0b101
    SPS_475 = 0b110
    SPS_860 = 0b111


class ComparatorMode(Enum):
    TRADITIONAL = 0b0  # default
    WINDOW = 0b1


class ComparatorPolarity(Enum):
    ACTIVE_LOW = 0b0    # default
    ACTIVE_HIGH = 0b1


class LatchingComparator(Enum):
    NONLATCHING = 0b0    # default
    LATCHING = 0b1


class ComparatorQueue(Enum):
    AFTER_ONE_CONVERSION = 0b00
    AFTER_TWO_CONVERSIONS = 0b01
    AFTER_FOUR_CONVERSIONS = 0b10
    DISABLED = 0b11    # default


class _OperationalStatus(Enum):
    NONE = 0b0
    START = 0b1


class _Multiplexer(Enum):
    IN0_IN1 = 0b000  # AINP = AIN0 and AINN = AIN1
    IN0_IN3 = 0b001  # AINP = AIN0 and AINN = AIN3
    IN1_IN3 = 0b010  # AINP = AIN1 and AINN = AIN3
    IN2_IN3 = 0b011  # AINP = AIN2 and AINN = AIN3
    IN0_GND = 0b100  # AINP = AIN0 and AINN = GND
    IN1_GND = 0b101  # AINP = AIN1 and AINN = GND
    IN2_GND = 0b110  # AINP = AIN2 and AINN = GND
    IN3_GND = 0b111  # AINP = AIN3 and AINN = GND


class _PointerRegister(Enum):
    CONVERSION = 0b00
    CONFIG = 0b01
    LO_THRESH = 0b10
    HI_THRESH = 0b11


class ADS1115:

    dead_time = 0.01  # time gap between I2C write and read operations
    v_offset = 0.02  # residual voltage at input pin at no load condition, i.e. ideally zero
    sampling_period = 0.5  # polling period for analog input read

    def __init__(self, bus: int, pga: PGA, address: I2CAddress,
                 logger: str = None,
                 sampling: int = 5,
                 operating_mode: OperatingMode = OperatingMode.SINGLE_SHOT,
                 data_rate: DataRate = DataRate.SPS_475,
                 comparator_mode: ComparatorMode = ComparatorMode.TRADITIONAL,
                 comparator_polarity: ComparatorPolarity = ComparatorPolarity.ACTIVE_LOW,
                 latching_comparator: LatchingComparator = LatchingComparator.NONLATCHING,
                 comparator_queue: ComparatorQueue = ComparatorQueue.DISABLED):

        self.logger = None

        if logger:
            self.logger = logging.getLogger(logger)

        if not isinstance(bus, int):
            if self.logger:
                self.logger.error(
                    f"'bus' type mismatched. Given type '{type(bus).__name__}'. Expected type '{I2CBus.__name__}'")
            else:
                print(
                    f"'bus' type mismatched. Given type '{type(bus).__name__}'. Expected type '{I2CBus.__name__}'")

            sys.exit(1)

        if not isinstance(pga, PGA):
            if self.logger:
                self.logger.error(
                    f"'pga' type mismatched. Given type '{type(pga).__name__}'. Expected type '{PGA.__name__}'")
            else:
                print(
                    f"'pga' type mismatched. Given type '{type(pga).__name__}'. Expected type '{PGA.__name__}'")

            sys.exit(1)

        if not isinstance(address, I2CAddress):
            if self.logger:
                self.logger.error(
                    f"'address' type mismatched. Given type '{type(address).__name__}'. Expected type '{I2CAddress.__name__}'")
            else:
                print(
                    f"'address' type mismatched. Given type '{type(address).__name__}'. Expected type '{I2CAddress.__name__}'")

            sys.exit(1)

        self.bus = smbus.SMBus(bus)
        self.pga = pga.value
        self.address = address.value
        self.sampling = sampling
        self.operating_mode = operating_mode.value
        self.data_rate = data_rate.value
        self.comparator_mode = comparator_mode.value
        self.comparator_polarity = comparator_polarity.value
        self.latching_comparator = latching_comparator.value
        self.comparator_queue = comparator_queue.value
        self.__data = Queue(maxsize=20)

        if not self.is_detected():
            if self.logger:
                self.logger.error(
                    f"I2C address '0x{self.address:X}' is not detected on bus '{bus.value}'")
            else:
                print(
                    f"I2C address '0x{self.address:X}' is not detected on bus '{bus.value}'")
            sys.exit(1)

        self.config_registers = self.get_config_registers()

        if self.logger:
            self.logger.info("ADS1115 Initialization completed!")
        else:
            print("ADS1115 Initialization completed!")

        self._run()

    def is_detected(self) -> bool:
        for device in range(128):
            try:
                self.bus.read_byte(device)
                if device == self.address:
                    return True
            except:
                pass

        return False

    def _calculate_config_register(self, mux_config: int) -> list:

        config_reg_low = self.data_rate << 5 | \
            self.comparator_mode << 4 | \
            self.comparator_polarity << 3 | \
            self.latching_comparator << 2 | \
            self.comparator_queue

        return [_OperationalStatus.START.value << 7 |
                mux_config << 4 |
                self.pga << 1 |
                self.operating_mode,
                config_reg_low]

    def get_config_registers(self) -> dict:
        return {
            "in0_in1": self._calculate_config_register(_Multiplexer.IN0_IN1.value),
            "in0_in3": self._calculate_config_register(_Multiplexer.IN0_IN3.value),
            "in1_in3": self._calculate_config_register(_Multiplexer.IN1_IN3.value),
            "in2_in3": self._calculate_config_register(_Multiplexer.IN2_IN3.value),
            "in0_gnd": self._calculate_config_register(_Multiplexer.IN0_GND.value),
            "in1_gnd": self._calculate_config_register(_Multiplexer.IN1_GND.value),
            "in2_gnd": self._calculate_config_register(_Multiplexer.IN2_GND.value),
            "in3_gnd": self._calculate_config_register(_Multiplexer.IN3_GND.value)
        }

    def _read_analog_input(self, config_register: int) -> float:

        step_size = {
            0: 0.1875,
            1: 0.125,
            2: 0.0625,
            3: 0.03125,
            4: 0.015625,
            5: 0.0078125,
            6: 0.0078125,
            7: 0.0078125
        }

        total = 0

        for _ in range(self.sampling):
            self.bus.write_i2c_block_data(self.address,
                                          _PointerRegister.CONFIG.value,
                                          config_register)

            sleep(self.dead_time)

            data = self.bus.read_i2c_block_data(self.address,
                                                _PointerRegister.CONVERSION.value, 2)

            sleep(self.dead_time)

            # Byte-swap the 2-byte data to get adc value, then convert the data to voltage
            raw_adc = data[0] << 8 | data[1]

            if raw_adc > 32767:
                raw_adc -= 65536

            total += (raw_adc * step_size[self.pga] / 1000) - self.v_offset

        return total / self.sampling

    def read_input_in0_in1(self) -> float:
        return self._read_analog_input(self.config_registers["in0_in1"])

    def read_input_in0_in3(self) -> float:
        return self._read_analog_input(self.config_registers["in0_in3"])

    def read_input_in1_in3(self) -> float:
        return self._read_analog_input(self.config_registers["in1_in3"])

    def read_input_in2_in3(self) -> float:
        return self._read_analog_input(self.config_registers["in2_in3"])

    def read_input_in0_gnd(self) -> float:
        return self._read_analog_input(self.config_registers["in0_gnd"])

    def read_input_in1_gnd(self) -> float:
        return self._read_analog_input(self.config_registers["in1_gnd"])

    def read_input_in2_gnd(self) -> float:
        return self._read_analog_input(self.config_registers["in2_gnd"])

    def read_input_in3_gnd(self) -> float:
        return self._read_analog_input(self.config_registers["in3_gnd"])

    def _read_all_analog_inputs(self):
        while True:
            try:
                if self.__data.full():
                    self.__data.get()

                self.__data.put({
                    "input_voltage": {
                        "in0_in1": round(self.read_input_in0_in1(), 5),
                        "in0_in3": round(self.read_input_in0_in3(), 5),
                        "in1_in3": round(self.read_input_in1_in3(), 5),
                        "in2_in3": round(self.read_input_in2_in3(), 5),
                        "in0_gnd": round(self.read_input_in0_gnd(), 5),
                        "in1_gnd": round(self.read_input_in1_gnd(), 5),
                        "in2_gnd": round(self.read_input_in2_gnd(), 5),
                        "in3_gnd": round(self.read_input_in3_gnd(), 5)
                    },
                    "timestamp": int(datetime.now().timestamp())
                })

            except Exception as e:
                if self.logger:
                    self.logger.warning(f"{type(e).__name__}: {e}")
                else:
                    print(f"{type(e).__name__}: {e}")

            finally:
                sleep(self.sampling_period)

    def get_measurement(self) -> dict:
        if self.__data.empty():
            return {}

        return self.__data.get()

    def _run(self):
        threading.Thread(target=self._read_all_analog_inputs,
                         daemon=True).start()

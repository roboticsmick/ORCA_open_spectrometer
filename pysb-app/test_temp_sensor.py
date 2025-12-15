#!/usr/bin/env python3
"""
MCP9808 Temperature Sensor Test Script

This script tests the MCP9808 I2C temperature sensor and helps diagnose
connection issues.

Run on Raspberry Pi:
    python3 test_temp_sensor.py

Requirements:
    - I2C must be enabled (dtparam=i2c_arm=on in /boot/config.txt or /boot/firmware/config.txt)
    - User must be in 'i2c' group (groups $USER should show 'i2c')
    - python3-smbus installed (apt install python3-smbus)
"""

import sys

# MCP9808 Constants
MCP9808_I2CADDR_DEFAULT = 0x18
MCP9808_REG_AMBIENT_TEMP = 0x05
MCP9808_REG_MANUF_ID = 0x06
MCP9808_REG_DEVICE_ID = 0x07


def check_i2c_available():
    """Check if I2C bus is available."""
    print("\n" + "=" * 50)
    print("Step 1: Checking I2C Bus Availability")
    print("=" * 50)

    import os

    # Check for I2C device nodes
    i2c_buses = []
    for bus in [0, 1, 2]:
        path = f"/dev/i2c-{bus}"
        if os.path.exists(path):
            i2c_buses.append(bus)
            print(f"  [OK] {path} exists")
        else:
            print(f"  [--] {path} not found")

    if not i2c_buses:
        print("\n  [ERROR] No I2C bus found!")
        print("  Fix: Enable I2C in config:")
        print("    sudo raspi-config  (Interface Options -> I2C)")
        print("  Or manually add to /boot/firmware/config.txt:")
        print("    dtparam=i2c_arm=on")
        print("  Then reboot.")
        return None

    print(f"\n  Available I2C buses: {i2c_buses}")
    return i2c_buses[0] if 1 not in i2c_buses else 1  # Prefer bus 1


def check_i2c_permissions(bus_num):
    """Check user has permission to access I2C bus."""
    print("\n" + "=" * 50)
    print("Step 2: Checking I2C Permissions")
    print("=" * 50)

    import os
    import grp

    device_path = f"/dev/i2c-{bus_num}"

    # Check file permissions
    if os.access(device_path, os.R_OK | os.W_OK):
        print(f"  [OK] Read/write access to {device_path}")
        return True

    # Check if user is in i2c group
    try:
        i2c_gid = grp.getgrnam("i2c").gr_gid
        user_groups = os.getgroups()
        if i2c_gid in user_groups:
            print(f"  [OK] User is in 'i2c' group")
        else:
            print(f"  [ERROR] User is NOT in 'i2c' group")
            print(f"  Fix: sudo usermod -aG i2c $USER")
            print(f"  Then log out and back in (or reboot)")
    except KeyError:
        print("  [WARNING] 'i2c' group doesn't exist")

    print(f"\n  [ERROR] Cannot access {device_path}")
    print(f"  Quick fix: sudo chmod 666 {device_path}")
    print(f"  Or run this script with sudo: sudo python3 test_temp_sensor.py")
    return False


def scan_i2c_bus(bus_num):
    """Scan I2C bus for devices."""
    print("\n" + "=" * 50)
    print(f"Step 3: Scanning I2C Bus {bus_num} for Devices")
    print("=" * 50)

    try:
        import smbus2

        bus = smbus2.SMBus(bus_num)
    except ImportError:
        print("  [ERROR] smbus2 not installed!")
        print("  Fix: pip install smbus2")
        print("  Or: sudo apt install python3-smbus")
        return []
    except PermissionError:
        print(f"  [ERROR] Permission denied for /dev/i2c-{bus_num}")
        print("  Fix: Run with sudo or add user to i2c group")
        return []
    except Exception as e:
        print(f"  [ERROR] Cannot open I2C bus: {e}")
        return []

    found_devices = []
    print(f"  Scanning addresses 0x03 to 0x77...")

    for addr in range(0x03, 0x78):
        try:
            bus.read_byte(addr)
            found_devices.append(addr)
            device_name = ""
            if addr == 0x18:
                device_name = " <- MCP9808 (default)"
            elif addr == 0x19:
                device_name = " <- MCP9808 (A0=1)"
            elif addr == 0x68:
                device_name = " <- DS3231 RTC"
            elif addr == 0x3C or addr == 0x3D:
                device_name = " <- OLED Display"
            print(f"    [FOUND] 0x{addr:02X}{device_name}")
        except:
            pass

    bus.close()

    if not found_devices:
        print("  [WARNING] No I2C devices found!")
        print("  Check wiring:")
        print("    - SDA -> GPIO 2 (pin 3)")
        print("    - SCL -> GPIO 3 (pin 5)")
        print("    - VCC -> 3.3V (pin 1)")
        print("    - GND -> Ground (pin 6)")
    else:
        print(f"\n  Found {len(found_devices)} device(s): {[f'0x{a:02X}' for a in found_devices]}")

    return found_devices


def test_mcp9808(bus_num, address=MCP9808_I2CADDR_DEFAULT):
    """Test MCP9808 sensor communication."""
    print("\n" + "=" * 50)
    print(f"Step 4: Testing MCP9808 at Address 0x{address:02X}")
    print("=" * 50)

    try:
        import smbus2

        bus = smbus2.SMBus(bus_num)
    except Exception as e:
        print(f"  [ERROR] Cannot open I2C bus: {e}")
        return False

    # Read Manufacturer ID (should be 0x0054)
    try:
        data = bus.read_i2c_block_data(address, MCP9808_REG_MANUF_ID, 2)
        manuf_id = (data[0] << 8) | data[1]
        print(f"  Manufacturer ID: 0x{manuf_id:04X}", end="")
        if manuf_id == 0x0054:
            print(" [OK - Microchip]")
        else:
            print(f" [UNEXPECTED - expected 0x0054]")
    except Exception as e:
        print(f"  [ERROR] Cannot read Manufacturer ID: {e}")
        bus.close()
        return False

    # Read Device ID (should be 0x0400)
    try:
        data = bus.read_i2c_block_data(address, MCP9808_REG_DEVICE_ID, 2)
        device_id = (data[0] << 8) | data[1]
        print(f"  Device ID: 0x{device_id:04X}", end="")
        if device_id == 0x0400:
            print(" [OK - MCP9808]")
        else:
            print(f" [UNEXPECTED - expected 0x0400]")
    except Exception as e:
        print(f"  [ERROR] Cannot read Device ID: {e}")
        bus.close()
        return False

    # Read temperature
    try:
        data = bus.read_i2c_block_data(address, MCP9808_REG_AMBIENT_TEMP, 2)
        raw_temp = (data[0] << 8) | data[1]

        # Convert to Celsius
        temp_c = (raw_temp & 0x0FFF) / 16.0
        if raw_temp & 0x1000:
            temp_c -= 256.0

        print(f"\n  Raw temperature register: 0x{raw_temp:04X}")
        print(f"  Temperature: {temp_c:.2f}°C ({temp_c * 9/5 + 32:.2f}°F)")

        if -40 <= temp_c <= 125:
            print("  [OK] Temperature within sensor range (-40°C to +125°C)")
        else:
            print("  [WARNING] Temperature outside expected range")

    except Exception as e:
        print(f"  [ERROR] Cannot read temperature: {e}")
        bus.close()
        return False

    bus.close()
    return True


def continuous_reading(bus_num, address=MCP9808_I2CADDR_DEFAULT, interval=2.0):
    """Continuously read and display temperature."""
    print("\n" + "=" * 50)
    print("Step 5: Continuous Temperature Reading")
    print("=" * 50)
    print("Press Ctrl+C to stop\n")

    import smbus2
    import time

    bus = smbus2.SMBus(bus_num)

    try:
        count = 0
        while True:
            data = bus.read_i2c_block_data(address, MCP9808_REG_AMBIENT_TEMP, 2)
            raw_temp = (data[0] << 8) | data[1]
            temp_c = (raw_temp & 0x0FFF) / 16.0
            if raw_temp & 0x1000:
                temp_c -= 256.0

            count += 1
            print(f"  [{count:4d}] Temperature: {temp_c:6.2f}°C  ({temp_c * 9/5 + 32:6.2f}°F)")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n  Stopped by user")
    finally:
        bus.close()


def main():
    print("=" * 50)
    print("MCP9808 Temperature Sensor Diagnostic Test")
    print("=" * 50)

    # Step 1: Check I2C bus
    bus_num = check_i2c_available()
    if bus_num is None:
        sys.exit(1)

    # Step 2: Check permissions
    if not check_i2c_permissions(bus_num):
        print("\n[TIP] Try running with sudo: sudo python3 test_temp_sensor.py")
        # Continue anyway to try

    # Step 3: Scan bus
    devices = scan_i2c_bus(bus_num)

    # Check if MCP9808 found
    mcp9808_addr = None
    for addr in [0x18, 0x19, 0x1A, 0x1B, 0x1C, 0x1D, 0x1E, 0x1F]:  # Possible MCP9808 addresses
        if addr in devices:
            mcp9808_addr = addr
            break

    if mcp9808_addr is None:
        print("\n" + "=" * 50)
        print("MCP9808 NOT DETECTED")
        print("=" * 50)
        print("Check wiring:")
        print("  MCP9808 Pin  ->  Raspberry Pi Pin")
        print("  ------------------------------------")
        print("  VDD (power)  ->  3.3V (pin 1)")
        print("  GND (ground) ->  GND (pin 6)")
        print("  SDA (data)   ->  GPIO 2 / SDA (pin 3)")
        print("  SCL (clock)  ->  GPIO 3 / SCL (pin 5)")
        print("\nAddress pins (if present):")
        print("  A0, A1, A2   ->  Leave floating or connect to GND for 0x18")
        sys.exit(1)

    # Step 4: Test MCP9808
    if not test_mcp9808(bus_num, mcp9808_addr):
        sys.exit(1)

    # Step 5: Ask about continuous reading
    print("\n" + "=" * 50)
    print("SUCCESS! MCP9808 is working correctly.")
    print("=" * 50)

    try:
        response = input("\nStart continuous temperature reading? (y/N): ")
        if response.lower() == "y":
            continuous_reading(bus_num, mcp9808_addr)
    except EOFError:
        pass  # Running non-interactively

    print("\nTest complete.")


if __name__ == "__main__":
    main()

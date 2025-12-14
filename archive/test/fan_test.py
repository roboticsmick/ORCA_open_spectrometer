#!/usr/bin/env python3
"""
Simple DC Fan Enable Test Script for Raspberry Pi Zero 2W

Purpose:
    Test MOSFET-controlled fan circuit with simple on/off control.
    Designed for CTS FEX40-40-21 (tachometer wire not connected).

Hardware Configuration:
    - GPIO 4: MOSFET gate control (on/off switching)
    - Fan Red Wire: +5V through MOSFET
    - Fan Black Wire: Ground
    - Fan Yellow Wire: Not connected (leave disconnected)

Run Command:
    sudo python3 fan_test.py

Control Method:
    Simple digital on/off - fan runs at full speed when enabled.
    Most reliable method for thermal management applications.

Note: Requires RPi.GPIO library
    Install with: sudo apt-get install python3-rpi.gpio
"""

import RPi.GPIO as GPIO
import time
import sys

# Pin definitions
FAN_ENABLE_PIN = 4  # MOSFET gate control


def setup_gpio():
    """Initialize GPIO with safe defaults."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # Configure enable pin as output, start LOW (fan off)
    GPIO.setup(FAN_ENABLE_PIN, GPIO.OUT, initial=GPIO.LOW)

    print("GPIO initialized - fan off")


def test_fan_on_off():
    """Test basic fan enable/disable functionality."""
    try:
        setup_gpio()

        print("\n" + "=" * 50)
        print("Fan Circuit Test - Simple On/Off Control")
        print("=" * 50)

        # Turn fan ON
        print("\n[1] Turning fan ON...")
        GPIO.output(FAN_ENABLE_PIN, GPIO.HIGH)
        print("    GPIO 4 set HIGH - MOSFET enabled")
        print("    Fan should be running at full speed")
        print("    Listen for fan noise and check for airflow")

        print("\n    Running for 10 seconds...")
        for i in range(10):
            time.sleep(1)
            print(f"      {i+1}/10 seconds elapsed")

        # Turn fan OFF
        print("\n[2] Turning fan OFF...")
        GPIO.output(FAN_ENABLE_PIN, GPIO.LOW)
        print("    GPIO 4 set LOW - MOSFET disabled")
        print("    Fan should be stopped")

        time.sleep(3)

        # Cycle test
        print("\n[3] Rapid cycling test (3 cycles)...")
        for cycle in range(3):
            print(f"\n    Cycle {cycle+1}/3:")

            GPIO.output(FAN_ENABLE_PIN, GPIO.HIGH)
            print("      Fan ON")
            time.sleep(2)

            GPIO.output(FAN_ENABLE_PIN, GPIO.LOW)
            print("      Fan OFF")
            time.sleep(2)

        print("\n" + "=" * 50)
        print("Test Complete - Circuit Working Correctly")
        print("=" * 50)

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")

    except Exception as e:
        print(f"\nError during test: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Ensure fan is off
        GPIO.output(FAN_ENABLE_PIN, GPIO.LOW)
        GPIO.cleanup()
        print("\nGPIO cleaned up - fan disabled")


def test_extended_run():
    """Extended test for thermal verification."""
    try:
        setup_gpio()

        print("\n" + "=" * 50)
        print("Extended Fan Run Test")
        print("=" * 50)

        print("\nThis test runs the fan continuously.")
        print("Use this to verify cooling effectiveness on your spectrometer.")

        duration = input("\nEnter run duration in seconds (default 60): ")
        try:
            duration = int(duration) if duration else 60
        except ValueError:
            duration = 60

        print(f"\nRunning fan for {duration} seconds...")
        print("Press Ctrl+C to stop early")

        GPIO.output(FAN_ENABLE_PIN, GPIO.HIGH)
        print("Fan enabled")

        for i in range(duration):
            time.sleep(1)
            if (i + 1) % 10 == 0:
                print(f"  {i+1}/{duration} seconds elapsed")

        GPIO.output(FAN_ENABLE_PIN, GPIO.LOW)
        print("\nFan disabled - test complete")

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")

    except Exception as e:
        print(f"\nError during test: {e}")

    finally:
        GPIO.output(FAN_ENABLE_PIN, GPIO.LOW)
        GPIO.cleanup()
        print("GPIO cleaned up - fan disabled")


def main():
    """Main entry point with test selection."""
    print("=" * 50)
    print("Fan Circuit Test Utility")
    print("CTS FEX40-40-21 - Simple On/Off Control")
    print("=" * 50)

    print("\nWiring Check:")
    print("  Fan Red Wire    -> 5V through MOSFET drain")
    print("  Fan Black Wire  -> Ground")
    print("  Fan Yellow Wire -> NOT CONNECTED (leave disconnected)")
    print("  MOSFET Gate     -> GPIO 4")

    # Safety check
    response = input("\nIs fan properly connected? (y/n): ")
    if response.lower() != "y":
        print("Test cancelled")
        sys.exit(0)

    # Test selection
    print("\nTest Options:")
    print("  1. Basic on/off test (recommended for first test)")
    print("  2. Extended run test (for thermal verification)")

    choice = input("\nSelect test (1 or 2): ")

    if choice == "1":
        test_fan_on_off()
    elif choice == "2":
        test_extended_run()
    else:
        print("Invalid choice")
        sys.exit(1)


if __name__ == "__main__":
    main()

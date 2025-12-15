## @file network_info.py
#  @brief Background network information fetcher for WiFi SSID and IP address.
#
#  Runs a daemon thread that periodically queries network status using
#  system commands (iwgetid, hostname). Provides thread-safe access to
#  WiFi name and IP address for display in the menu system.

import subprocess
import threading
import time

import config
# No longer importing from main, which removes the circular dependency.

##
# @class NetworkInfo
# @brief Fetches and caches network information in a dedicated background thread.
# @details This class is responsible for obtaining the device's current Wi-Fi SSID
#          and IP address. It runs as a daemon thread, periodically updating the
#          information so that the main application can access it without blocking the UI.
class NetworkInfo:

    ##
    # @brief Initializes the NetworkInfo thread.
    # @param shutdown_flag A threading.Event to signal when the thread should terminate.
    def __init__(self, shutdown_flag):
        self._update_interval_s = config.NETWORK_UPDATE_INTERVAL_S
        self._wifi_name = "N/A"
        self._ip_address = "N/A"
        self._lock = threading.Lock()
        self._thread = None
        self.shutdown_flag = shutdown_flag

    ##
    # @brief Checks if a given network interface is currently up and running.
    # @param interface The name of the network interface (e.g., 'wlan0').
    # @return True if the interface is up, False otherwise.
    def _is_interface_up(self, interface='wlan0'):
        try:
            with open(f'/sys/class/net/{interface}/operstate') as f:
                status = f.read().strip()
            return status == 'up'
        except FileNotFoundError:
            return False

    ##
    # @brief Executes the `iwgetid` command to get the current Wi-Fi SSID.
    # @return The SSID string if connected, or "N/A" on failure.
    def _fetch_wifi_name(self):
        try:
            result = subprocess.run(['iwgetid', '-r'], capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "N/A"

    ##
    # @brief Executes the `hostname -I` command to get the device's IP address.
    # @return The first IP address in the list, or "N/A" on failure.
    def _fetch_ip_address(self):
        try:
            result = subprocess.run(['hostname', '-I'], capture_output=True, text=True, check=True)
            # Take the first IP address in the list
            return result.stdout.strip().split()[0]
        except (subprocess.CalledProcessError, FileNotFoundError, IndexError):
            return "N/A"

    ##
    # @brief The main loop for the background thread.
    # @details This loop runs until the injected `shutdown_flag` is set. It periodically
    #          checks the network status and updates the cached SSID and IP address.
    def _network_update_loop(self):
        while not self.shutdown_flag.is_set():
            wifi_name = "Disconnected"
            ip_address = "N/A"
            if self._is_interface_up():
                wifi_name = self._fetch_wifi_name()
                ip_address = self._fetch_ip_address()

            with self._lock:
                self._wifi_name = wifi_name
                self._ip_address = ip_address

            # Wait for the next update interval, checking the shutdown flag periodically
            for _ in range(int(self._update_interval_s * 10)):
                if self.shutdown_flag.is_set():
                    break
                time.sleep(0.1)

    ##
    # @brief Thread-safe method to get the cached Wi-Fi SSID.
    # @return The current Wi-Fi SSID as a string.
    def get_wifi_name(self):
        with self._lock:
            return self._wifi_name

    ##
    # @brief Thread-safe method to get the cached IP address.
    # @return The current IP address as a string.
    def get_ip_address(self):
        with self._lock:
            return self._ip_address

    ##
    # @brief Starts the background update thread.
    # @details If the thread has not already been started, it creates and starts it.
    def start(self):
        if self._thread is None:
            self._thread = threading.Thread(target=self._network_update_loop, daemon=True)
            self._thread.start()
            print("NetworkInfo thread started.")

    ##
    # @brief Stops the background update thread.
    # @details The thread's lifecycle is managed by the injected `shutdown_flag`.
    #          This method just waits briefly for the thread to join.
    def stop(self):
        print("NetworkInfo thread stopping...")
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2) # Wait briefly for it to finish

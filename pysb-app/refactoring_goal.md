# Refactoring Plan: PySB-App

## 1. Project Goal

The primary objective of this refactoring is to transform the original monolithic `main.py` script into a robust, maintainable, and scalable application. The new architecture will support future feature enhancements, improve stability, and be significantly easier for developers to understand and contribute to.

## 2. Core Architectural Principles

The refactoring process is guided by the following software engineering principles:

- **Separation of Concerns (SoC):** Logic is being strictly separated into distinct, single-responsibility modules. Hardware interaction, user interface components, and data management will not be mixed.

- **Multi-Threading for a Responsive UI:** All long-running or blocking tasks (e.g., hardware polling, data saving) are being moved into dedicated background threads. This ensures the main Pygame UI loop is never blocked, providing a smooth and responsive user experience.

- **Centralized Configuration:** All application-wide constants, pin numbers, and tuning parameters are stored in `config.py` to allow for easy modification without altering core application logic.

- **Code Reusability:** By encapsulating functionality into classes (e.g., `LeakSensor`, `NetworkInfo`), we create reusable components that can be instantiated and used wherever they are needed.

## 3. Refactoring Strategy & Implementation

### 3.1. Code Organization: New Directory Structure

The project has been reorganized from a single script into a structured directory format:

#### Draft plan outline

```
pysb-app/
├── main.py                 # Application entry point, orchestrator, and main UI loop.
├── config.py               # Centralized constants and configuration.
├── app_guide.md            # User-facing documentation.
│
├── hardware/               # Modules for direct interaction with physical hardware.
│   ├── leak_sensor.py
│   └── network_info.py
│
├── ui/                     # Modules related to the Pygame user interface.
│   ├── display_utils.py
│   ├── splash_screen.py
│   ├── terms_screen.py
│   └── menu_system.py
│
└── data/                   # (Future) Modules for data handling, saving, and processing.
```

### 3.2. Component-Based Design & Threading

Functionality is being broken down into independent components, many of which run in their own threads:

- **`LeakSensor` (`hardware/leak_sensor.py`):** Runs a background thread to poll the leak sensor GPIO pin. Communicates back to the main thread using a shared `threading.Event`.

- **`NetworkInfo` (`hardware/network_info.py`):** Runs a background thread to periodically check the Wi-Fi SSID and IP address. This prevents blocking network calls from freezing the UI. Data is accessed via thread-safe getter methods.

- **(Future) `SpectrometerController`:** Will manage all communication with the spectrometer hardware in its own thread, processing requests and putting results onto a queue.

- **(Future) `DataManager`:** Will run in a background thread to handle writing data to files, preventing UI stutters caused by slow I/O operations.

### 3.3. Dependency Management: Dependency Injection

To eliminate circular dependencies and create decoupled, testable components, we are using **Dependency Injection**. Instead of a module importing its dependencies directly, the dependencies are passed into its constructor.

- **Example:** The `main.py` module creates the `shutdown_flag` and `leak_detected_flag` events and "injects" them into the `LeakSensor` instance:

  ```python
  # in main.py
  shutdown_flag = threading.Event()
  leak_detected_flag = threading.Event()
  leak_sensor_inst = leak_sensor.LeakSensor(shutdown_flag, leak_detected_flag)
  ```

This makes `leak_sensor.py` a standalone component that is no longer dependent on `main.py`.

### 3.4. Code Documentation: Doxygen Standard

All new modules and classes are being commented using the **Doxygen** standard. This provides clear, consistent inline documentation and allows for the future generation of a complete technical guide for the codebase, which can then inform the user-facing `app_guide.md`.

## 4. Next Steps

The refactoring will proceed by applying these principles to the remaining functionality:

1.  Create the `SpectrometerController` class to manage spectrometer hardware interactions in a new thread.
2.  Create the `DataManager` class to handle all file I/O operations in a background thread.
3.  Create the `SpectrometerScreen` UI module to display live data from the spectrometer.
4.  Continue to add Doxygen comments to all new and refactored code.

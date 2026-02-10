"""Implementation of the Seabreeze Transport layer.

Some spectrometers can support different transports (usb, network, rs232, etc.)

"""

from __future__ import annotations

import importlib
import inspect
import ipaddress
import logging
import socket
import struct
import warnings
import weakref
from collections.abc import Iterable
from functools import partialmethod
from typing import TYPE_CHECKING
from typing import Any
from typing import Dict, Tuple, Optional

import usb.backend
import usb.core
import usb.util

from seabreeze.pyseabreeze.protocol import OBPProtocol
from seabreeze.pyseabreeze.types import PySeaBreezeProtocol
from seabreeze.pyseabreeze.types import PySeaBreezeTransport

if TYPE_CHECKING:
    from seabreeze.pyseabreeze.devices import EndPointMap


# encapsulate usb.core.USBError
class USBTransportError(Exception):
    def __init__(
        self, *args: Any, errno: int | None = None, error_code: int | None = None
    ) -> None:
        super().__init__(*args)
        self.errno = errno
        self.backend_error_code = error_code

    @classmethod
    def from_usberror(cls, err: usb.core.USBError) -> USBTransportError:
        return cls(str(err), errno=err.errno, error_code=err.backend_error_code)


class USBTransportDeviceInUse(Exception):
    pass


DeviceIdentity = Tuple[int, int, int, int]


# this can and should be opaque to pyseabreeze
class USBTransportHandle:
    def __init__(self, pyusb_device: usb.core.Device) -> None:
        """encapsulation for pyusb device classes

        Parameters
        ----------
        pyusb_device
        """
        self.pyusb_device: usb.core.Device = pyusb_device
        # noinspection PyUnresolvedReferences
        self.identity: DeviceIdentity = (
            pyusb_device.idVendor,
            pyusb_device.idProduct,
            pyusb_device.bus,
            pyusb_device.address,
        )
        self.pyusb_backend = get_name_from_pyusb_backend(pyusb_device.backend)
        self._interface_claimed = False

    def close(self) -> None:
        """Close the USB device handle properly.

        NOTE: We intentionally do NOT reset the device here. Reset is only done
        once at the start of open_device() to clear stale state. Resetting on
        close causes repeated USB resets when the transport is accessed multiple
        times (the original bug on Jetson Orin).
        """
        try:
            # Release interface first if claimed
            if self._interface_claimed:
                try:
                    usb.util.release_interface(self.pyusb_device, 0)
                    self._interface_claimed = False
                    logging.debug("Released USB interface 0")
                except usb.core.USBError:
                    pass
            # Dispose resources - this frees the libusb handle without resetting
            usb.util.dispose_resources(self.pyusb_device)
        except usb.core.USBError:
            logging.debug(
                "USBError while calling USBTransportHandle.close on {:04x}:{:04x}".format(
                    self.identity[0], self.identity[1]
                ),
                exc_info=True,
            )
        except Exception:
            # Catch any other errors during cleanup
            pass

    def __del__(self) -> None:
        if self.pyusb_backend == "libusb1":
            # have to check if .finalize() has been called
            # -> todo: maybe better to fix this in the api initialization of cseabreeze
            # -> todo: will probably have to check pyusb versions and only do this when necessary
            if not getattr(self.pyusb_device.backend, "_finalize_called", False):
                # if usb.core.Device.reset() gets called but the backend has been finalized already
                # (this happens only during interpreter shutdown)
                self.close()
        else:
            self.close()
        self.pyusb_device = None


class USBTransport(PySeaBreezeTransport[USBTransportHandle]):
    """implementation of the usb transport interface for spectrometers"""

    _required_init_kwargs = (
        "usb_vendor_id",
        "usb_product_id",
        "usb_endpoint_map",
        "usb_protocol",
    )
    vendor_product_ids: Dict[Tuple[int, int], str] = {}

    # add logging
    _log = logging.getLogger(__name__)

    def __init__(
        self,
        usb_vendor_id: int,
        usb_product_id: int,
        usb_endpoint_map: EndPointMap,
        usb_protocol: type[PySeaBreezeProtocol],
    ) -> None:
        super().__init__()
        self._vendor_id = usb_vendor_id
        self._product_id = usb_product_id
        self._endpoint_map = usb_endpoint_map
        self._protocol_cls = usb_protocol
        # internal settings
        self._default_read_size = {
            "low_speed": 64,
            "high_speed": 512,
            "high_speed_alt": 512,
        }
        self._read_endpoints = {
            "low_speed": "lowspeed_in",
            "high_speed": "highspeed_in",
            "high_speed_alt": "highspeed_in2",
        }
        if self._endpoint_map.lowspeed_in is not None:
            self._default_read_endpoint = "low_speed"
        else:
            self._default_read_endpoint = "high_speed"
        self._default_read_spectrum_endpoint = "high_speed"
        # internal state
        self._device: USBTransportHandle | None = None
        self._opened: bool | None = None
        self._protocol: PySeaBreezeProtocol | None = None

    def _clear_stale_claims_sysfs(self, pyusb_device: usb.core.Device) -> bool:
        """Clear stale USB claims using sysfs unbind/rebind (Jetson Orin safe).

        NOTE: This method is NOT called during normal operation. It is kept here
        for manual recovery scenarios where a stale claim from a crashed process
        is blocking device access. Calling this during normal open causes the
        device to physically disconnect and re-enumerate, leading to "Errno 19:
        No such device" errors.

        On Jetson Orin with tegra-xusb, USB reset causes device disconnection.
        This method uses kernel sysfs to unbind and rebind the device, which
        clears all userspace claims without the problematic USB reset.

        Returns True if successful, False otherwise.
        """
        import os
        import time
        import glob

        try:
            bus = pyusb_device.bus
            address = pyusb_device.address

            # Find the sysfs path for this device
            # USB devices are at /sys/bus/usb/devices/X-Y.Z where X is bus
            sysfs_pattern = f"/sys/bus/usb/devices/{bus}-*"

            device_path = None
            for path in glob.glob(sysfs_pattern):
                # Check if this path matches our device by reading devnum
                devnum_path = os.path.join(path, "devnum")
                if os.path.exists(devnum_path):
                    try:
                        with open(devnum_path, 'r') as f:
                            devnum = int(f.read().strip())
                            if devnum == address:
                                device_path = os.path.basename(path)
                                break
                    except (IOError, ValueError):
                        continue

            if not device_path:
                self._log.debug(f"Could not find sysfs path for bus={bus} addr={address}")
                return False

            unbind_path = "/sys/bus/usb/drivers/usb/unbind"
            bind_path = "/sys/bus/usb/drivers/usb/bind"

            # Check if we have write access
            if not os.access(unbind_path, os.W_OK):
                self._log.debug("No write access to sysfs USB unbind (need root)")
                return False

            self._log.info(f"Clearing stale claims via sysfs unbind/rebind: {device_path}")

            # Unbind the device
            try:
                with open(unbind_path, 'w') as f:
                    f.write(device_path)
                self._log.debug(f"Unbound {device_path}")
            except IOError as e:
                self._log.debug(f"Unbind failed (may already be unbound): {e}")

            # Wait for kernel to process
            time.sleep(0.5)

            # Rebind the device
            try:
                with open(bind_path, 'w') as f:
                    f.write(device_path)
                self._log.debug(f"Rebound {device_path}")
            except IOError as e:
                self._log.warning(f"Rebind failed: {e}")
                return False

            # Wait for device to re-enumerate
            time.sleep(1.0)

            self._log.info("Sysfs unbind/rebind complete")
            return True

        except Exception as e:
            self._log.debug(f"Sysfs claim clearing failed: {e}")
            return False

    def open_device(self, device: USBTransportHandle) -> None:
        if not isinstance(device, USBTransportHandle):
            raise TypeError("device needs to be a USBTransportHandle")
        self._device = device
        pyusb_device = self._device.pyusb_device
        import time

        # === STEP 1: Clear internal pyusb/libusb state ===
        # This frees any stale handles without bouncing the USB bus
        try:
            usb.util.dispose_resources(pyusb_device)
        except Exception:
            pass

        # === STEP 2: Detach kernel driver (required for user-space access) ===
        try:
            if pyusb_device.is_kernel_driver_active(0):
                self._log.debug("Detaching kernel driver from interface 0")
                pyusb_device.detach_kernel_driver(0)
        except NotImplementedError:
            pass  # unavailable on some systems/backends
        except usb.core.USBError as err:
            self._log.debug(f"Kernel driver detach failed (may be OK): {err}")

        # === STEP 3: Set configuration (only if necessary) ===
        # On Jetson Orin, calling set_configuration while interface is already
        # claimed causes the "interface 0 claimed" dmesg error and USB hangs.
        # We only call it if the device isn't already configured to config 1.
        try:
            # First, check if configuration is already set to 1
            # Most Linux systems do this automatically on plug
            cfg = pyusb_device.get_active_configuration()
            if cfg.bConfigurationValue != 1:
                self._log.debug("Device not configured to 1, setting configuration...")
                pyusb_device.set_configuration(1)
            else:
                self._log.debug("Device already configured to config 1, skipping set_configuration")
        except usb.core.USBError:
            # If get_active_configuration fails, the device is "unconfigured"
            try:
                self._log.debug("Device unconfigured, setting configuration 1...")
                pyusb_device.set_configuration(1)
            except usb.core.USBError as e:
                self._log.debug(f"Allowing set_config failure: {e}")

        # === STEP 4: Claim interface ===
        try:
            usb.util.claim_interface(pyusb_device, 0)
            self._device._interface_claimed = True
            self._log.debug("Successfully claimed USB interface 0")
        except usb.core.USBError as claim_err:
            self._log.error(f"Claim failed: {claim_err}")
            raise USBTransportDeviceInUse(
                f"Interface 0 is locked: {claim_err}. "
                "Try: 1) Kill any other python/seabreeze processes, 2) Unplug and replug the device"
            )

        self._opened = True

        # Configure the default_read_size according to pyusb info
        ep_max_packet_size = {}
        for intf in pyusb_device.get_active_configuration():
            for ep in intf.endpoints():
                ep_max_packet_size[ep.bEndpointAddress] = ep.wMaxPacketSize

        for mode_name, endpoint_map_name in self._read_endpoints.items():
            ep_int = getattr(self._endpoint_map, endpoint_map_name, None)
            if ep_int is None:
                continue
            try:
                max_size = ep_max_packet_size[ep_int]
            except KeyError:
                continue
            cur_size = self._default_read_size[mode_name]
            self._default_read_size[mode_name] = min(cur_size, max_size)

        # === STEP 5: Set generous default timeout ===
        # The default pyusb timeout (1000ms) is too short for spectrometers with
        # long integration times. Set a 10 second default - can be overridden later.
        try:
            pyusb_device.default_timeout = 10000  # 10 seconds
            self._log.debug("Set default USB timeout to 10000 ms")
        except Exception as err:
            self._log.debug(f"Could not set default timeout: {err}")

        # === STEP 6: Stabilization delay (critical for Ocean ST) ===
        # The Ocean ST needs time to wake up its OBP2 parser after configuration.
        # Without this delay, the first command (typically serial number query)
        # times out with Errno 110.
        time.sleep(0.5)
        self._log.debug("Device stabilization delay complete (500ms)")

        # This will initialize the communication protocol
        if self._opened:
            self._protocol = self._protocol_cls(self)

    @property
    def is_open(self) -> bool:
        return self._opened or False

    def close_device(self) -> None:
        # Release interface before closing
        if self._device is not None and hasattr(self._device, '_interface_claimed'):
            if self._device._interface_claimed:
                try:
                    usb.util.release_interface(self._device.pyusb_device, 0)
                    self._device._interface_claimed = False
                except usb.core.USBError:
                    pass

        if self._device is not None:
            self._device.close()
            self._device = None
        self._opened = False
        self._protocol = None

    def write(self, data: bytes, timeout_ms: int | None = None, **kwargs: Any) -> int:
        if self._device is None:
            raise RuntimeError("device not opened")
        if kwargs:
            warnings.warn(f"kwargs provided but ignored: {kwargs}")
        return self._device.pyusb_device.write(  # type: ignore
            self._endpoint_map.ep_out, data, timeout=timeout_ms
        )

    def read(
        self,
        size: int | None = None,
        timeout_ms: int | None = None,
        mode: str | None = None,
        **kwargs: Any,
    ) -> bytes:
        if self._device is None:
            raise RuntimeError("device not opened")
        mode = mode if mode is not None else self._default_read_endpoint
        endpoint = getattr(self._endpoint_map, self._read_endpoints[mode])
        if size is None:
            size = self._default_read_size[mode]
        if kwargs:
            warnings.warn(f"kwargs provided but ignored: {kwargs}")
        ret: bytes = self._device.pyusb_device.read(
            endpoint, size, timeout=timeout_ms
        ).tobytes()
        return ret

    @property
    def default_timeout_ms(self) -> int:
        if not self._device:
            raise RuntimeError("no protocol instance available")
        return self._device.pyusb_device.default_timeout  # type: ignore

    @default_timeout_ms.setter
    def default_timeout_ms(self, value: int) -> None:
        """Set the default USB timeout in milliseconds."""
        if not self._device:
            raise RuntimeError("no device available")
        self._device.pyusb_device.default_timeout = value
        self._log.debug(f"Set USB default_timeout to {value} ms")

    @property
    def _usb_device(self) -> usb.core.Device | None:
        """Provide access to underlying pyusb device for timeout configuration.

        This property exists to allow external code (like spectrometer_node.py)
        to configure USB timeouts for long integration times.
        """
        if self._device:
            return self._device.pyusb_device
        return None

    @property
    def protocol(self) -> PySeaBreezeProtocol:
        if self._protocol is None:
            raise RuntimeError("no protocol instance available")
        return self._protocol

    @classmethod
    def list_devices(cls, **kwargs: Any) -> Iterable[USBTransportHandle]:
        """list pyusb devices for all available spectrometers

        Note: this includes spectrometers that are currently opened in other
        processes on the machine.

        Yields
        ------
        devices : USBTransportHandle
            unique pyusb devices for each available spectrometer
        """
        # check if a specific pyusb backend is requested
        _pyusb_backend = kwargs.get("pyusb_backend", None)
        # get all matching devices
        try:
            pyusb_devices = usb.core.find(
                find_all=True,
                custom_match=lambda dev: (
                    (dev.idVendor, dev.idProduct) in cls.vendor_product_ids
                ),
                backend=get_pyusb_backend_from_name(name=_pyusb_backend),
            )
        except usb.core.NoBackendError:
            raise RuntimeError("No pyusb backend found")
        # encapsulate
        for pyusb_device in pyusb_devices:
            yield USBTransportHandle(pyusb_device)

    @classmethod
    def register_model(cls, model_name: str, **kwargs: Any) -> None:
        vendor_id = kwargs.get("usb_vendor_id")
        if not isinstance(vendor_id, int):
            raise TypeError(f"vendor_id {vendor_id:r} not an integer")
        product_id = kwargs.get("usb_product_id")
        if not isinstance(product_id, int):
            raise TypeError(f"product_id {product_id:r} not an integer")
        if (vendor_id, product_id) in cls.vendor_product_ids:
            raise ValueError(
                f"vendor_id:product_id {vendor_id:04x}:{product_id:04x} already in registry"
            )
        cls.vendor_product_ids[(vendor_id, product_id)] = model_name

    @classmethod
    def supported_model(cls, device: USBTransportHandle) -> str | None:
        """return supported model

        Parameters
        ----------
        device : USBTransportHandle
        """
        if not isinstance(device, USBTransportHandle):
            return None
        # noinspection PyUnresolvedReferences
        return cls.vendor_product_ids[
            (device.pyusb_device.idVendor, device.pyusb_device.idProduct)
        ]

    @classmethod
    def specialize(cls, model_name: str, **kwargs: Any) -> type[USBTransport]:
        assert set(kwargs) == set(cls._required_init_kwargs)
        # usb transport register automatically on registration
        cls.register_model(model_name, **kwargs)
        specialized_class = type(
            f"USBTransport{model_name}",
            (cls,),
            {"__init__": partialmethod(cls.__init__, **kwargs)},
        )
        return specialized_class

    @classmethod
    def initialize(cls, **_kwargs: Any) -> None:
        # NOTE: Original code called device.pyusb_device.reset() here, but this
        # causes constant USB resets on Jetson Orin. Skip reset during initialization.
        pass

    @classmethod
    def shutdown(cls, **_kwargs: Any) -> None:
        # dispose usb resources
        for device in cls.list_devices(**_kwargs):
            try:
                usb.util.dispose_resources(device.pyusb_device)
            except Exception as err:
                cls._log.debug(
                    "shutdown failed: {}('{}')".format(
                        err.__class__.__name__, getattr(err, "message", "no message")
                    )
                )


_pyusb_backend_instances: Dict[str, usb.backend.IBackend] = {}


def get_pyusb_backend_from_name(name: str) -> usb.backend.IBackend:
    """internal: allow requesting a specific pyusb backend for testing"""
    if name is None:
        # default is pick first that works: ('libusb1', 'libusb0', 'openusb')
        _backend = None
    else:
        try:
            _backend = _pyusb_backend_instances[name]
        except KeyError:
            try:
                m = importlib.import_module(f"usb.backend.{name}")
            except ImportError:
                raise RuntimeError(f"unknown pyusb backend: {name!r}")
            # noinspection PyUnresolvedReferences
            _backend = m.get_backend()
            # raise if a pyusb backend was requested but can't be loaded
            if _backend is None:
                raise RuntimeError(f"pyusb backend failed to load: {name!r}")
            _pyusb_backend_instances[name] = _backend
    return _backend


def get_name_from_pyusb_backend(backend: usb.backend.IBackend) -> str | None:
    """internal: return backend name from loaded backend"""
    module = inspect.getmodule(backend)
    if not module:
        return None
    return module.__name__.split(".")[-1]


#  ___ ____        _  _
# |_ _|  _ \__   _| || |
#  | || |_) \ \ / / || |_
#  | ||  __/ \ V /|__   _|
# |___|_|     \_/    |_|


# this can and should be opaque to pyseabreeze
class IPv4TransportHandle:
    def __init__(self, address: str, port: int) -> None:
        """encapsulation for IPv4 socket classes

        Parameters
        ----------

        """
        self.socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.identity: DeviceIdentity = (
            int(ipaddress.IPv4Address(address)),
            port,
            0,
            0,
        )
        # register callback to close socket on garbage collection
        self._finalizer = weakref.finalize(self, self.socket.close)

    def open(self) -> None:
        # create a new socket; if we closed it, it will have lost its file descriptor
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.connect(self.get_address())
        except OSError as e:
            raise RuntimeError(f"Could not connect to {self.get_address()}: {e}")

    def close(self) -> None:
        self._finalizer()

    @property
    def closed(self) -> bool:
        return not self._finalizer.alive

    def get_address(self) -> tuple[str, int]:
        """Return a touple consisting of the ip address and the port."""
        return (
            # IP address
            (str(ipaddress.IPv4Address(self.identity[0]))),
            # port
            self.identity[1],
        )


class IPv4Transport(PySeaBreezeTransport[IPv4TransportHandle]):
    """implementation of the IPv4 socket transport interface for spectrometers"""

    _required_init_kwargs = ("ipv4_protocol",)

    devices_ip_port: Dict[Tuple[str, int], str] = {}

    # add logging
    _log = logging.getLogger(__name__)

    def __init__(
        self,
        ipv4_protocol: type[PySeaBreezeProtocol],
    ) -> None:
        super().__init__()
        self._protocol_cls = ipv4_protocol
        # internal state
        self._device: IPv4TransportHandle | None = None
        self._opened: bool | None = None
        self._protocol: PySeaBreezeProtocol | None = None

    def open_device(self, device: IPv4TransportHandle) -> None:
        if not isinstance(device, IPv4TransportHandle):
            raise TypeError("device needs to be an IPv4TransportHandle")
        self._device = device
        self._device.open()
        self._opened = True

        # This will initialize the communication protocol
        if self._opened:
            self._protocol = self._protocol_cls(self)

    @property
    def is_open(self) -> bool:
        return self._opened or False

    def close_device(self) -> None:
        if self._device is not None:
            self._device.close()
            self._device = None
        self._opened = False
        self._protocol = None

    def write(self, data: bytes, timeout_ms: int | None = None, **kwargs: Any) -> int:
        if self._device is None:
            raise RuntimeError("device not opened")
        if kwargs:
            warnings.warn(f"kwargs provided but ignored: {kwargs}")
        if timeout_ms:
            self._device.socket.settimeout(timeout_ms / 1000.0)
        return self._device.socket.send(data)

    def read(
        self,
        size: int | None = None,
        timeout_ms: int | None = None,
        mode: str | None = None,
        **kwargs: Any,
    ) -> bytes:
        if self._device is None:
            raise RuntimeError("device not opened")
        if size is None:
            # use minimum packet size (no payload)
            size = 64
        if kwargs:
            warnings.warn(f"kwargs provided but ignored: {kwargs}")
        if timeout_ms:
            self._device.socket.settimeout(timeout_ms / 1000.0)
        data = bytearray(size)
        toread = size
        view = memoryview(data)
        while toread:
            nbytes = self._device.socket.recv_into(view, toread)
            view = view[nbytes:]
            toread -= nbytes
        return bytes(data)

    @property
    def default_timeout_ms(self) -> int:
        if not self._device:
            raise RuntimeError("no protocol instance available")
        timeout = self._device.socket.gettimeout()
        if not timeout:
            return 10000
        return int(timeout * 1000)

    @property
    def protocol(self) -> PySeaBreezeProtocol:
        if self._protocol is None:
            raise RuntimeError("no protocol instance available")
        return self._protocol

    @classmethod
    def list_devices(cls, **kwargs: Any) -> Iterable[IPv4TransportHandle]:
        """list IPv4 devices for all available spectrometers

        Note: this includes spectrometers that are currently opened in other
        processes on the machine.

        Yields
        ------
        devices : IPv4TransportHandle
            unique socket devices for each available spectrometer
        """
        # Use multicast to discover potential spectrometers. If no network
        # adapter was specified use INADDR_ANY: an appropriate interface is
        # chosen by the system (see ip(7)). This is usually the interface with
        # the highest metric.
        network_adapter = kwargs.get("network_adapter", None)
        # default values for multicast on HDX devices
        multicast_group = kwargs.get("multicast_group", "239.239.239.239")
        multicast_port = kwargs.get("multicast_port", 57357)
        # Create the datagram (UDP) socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # allow other sockets to bind this port too
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Set a timeout so the socket does not block
        # indefinitely when trying to receive data.
        sock.settimeout(kwargs.get("multicast_timeout", 1))
        sock.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_MULTICAST_IF,
            socket.inet_aton(network_adapter) if network_adapter else socket.INADDR_ANY,
        )
        mreq = struct.pack(
            "4sl" if not network_adapter else "4s4s",
            socket.inet_aton(multicast_group),
            (
                socket.INADDR_ANY
                if not network_adapter
                else socket.inet_aton(network_adapter)
            ),
        )
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        # prepare a message requesting all devices in the multicast group
        # to send their (USB) product id
        transport = IPv4Transport(OBPProtocol)
        protocol = OBPProtocol(transport)
        msg_type = 0xE01  # Product ID
        data = protocol.msgs[msg_type]()
        message = protocol._construct_outgoing_message(
            msg_type,
            data,
            request_ack=True,
        )
        sock.sendto(message, (multicast_group, multicast_port))
        while True:
            try:
                data = bytearray(90)
                nbytes, server = sock.recvfrom_into(data)
            except socket.timeout:
                break
            else:
                pid_raw = protocol._extract_message_data(data[:nbytes])
                pid = int(struct.unpack("<H", pid_raw)[0])
                # use known product ids of the USB transport to look up the model name
                vid = 0x2457  # Ocean vendor ID
                model = USBTransport.vendor_product_ids[(vid, pid)]
                try:
                    cls.register_model(
                        model_name=model,
                        ipv4_address=server[0],
                        ipv4_port=server[1],
                    )
                except ValueError:
                    # device already known
                    pass

        # connect to discovered and registered devices
        for address in cls.devices_ip_port:
            yield IPv4TransportHandle(*address)

    @classmethod
    def register_model(cls, model_name: str, **kwargs: Any) -> None:
        ip = kwargs.get("ipv4_address")
        if not isinstance(ip, str):
            raise TypeError(f"ip address {ip} not a string")
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            raise ValueError(f"ip address {ip} does not represent a valid IPv4 address")
        port = kwargs.get("ipv4_port")
        if not isinstance(port, int):
            raise TypeError(f"port {port} not an integer")
        if (ip, port) in cls.devices_ip_port:
            raise ValueError(f"ip address:port {ip}:{port} already in registry")
        cls.devices_ip_port[(ip, port)] = model_name

    @classmethod
    def supported_model(cls, device: IPv4TransportHandle) -> str | None:
        """return supported model

        Parameters
        ----------
        device : IPv4TransportHandle
        """
        if not isinstance(device, IPv4TransportHandle):
            return None
        return cls.devices_ip_port[device.get_address()]

    @classmethod
    def specialize(cls, model_name: str, **kwargs: Any) -> type[IPv4Transport]:
        # TODO check that this makes sense for the ipv4 transport
        assert set(kwargs) == set(cls._required_init_kwargs)
        # ipv4 transport register automatically on registration
        # cls.register_model(model_name, **kwargs)
        specialized_class = type(
            f"IPv4Transport{model_name}",
            (cls,),
            {"__init__": partialmethod(cls.__init__, **kwargs)},
        )
        return specialized_class

    @classmethod
    def initialize(cls, **_kwargs: Any) -> None:
        pass

    @classmethod
    def shutdown(cls, **_kwargs: Any) -> None:
        pass

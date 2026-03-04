import socket
import unittest

import zmq

from sglang.srt.utils import get_zmq_socket_on_host


def get_routable_ip_strings():
    """Correctly extracts IP strings from socket addrinfo."""
    ip_strings = []
    try:
        # Get address info for the local hostname
        # res = (family, type, proto, canonname, sockaddr)
        # sockaddr = (address, port) for IPv4 or (address, port, flow info, scope id) for IPv6
        addr_info = socket.getaddrinfo(socket.gethostname(), None)

        for res in addr_info:
            # res[4] is the sockaddr tuple. res[4][0] is the IP address string.
            ip_str: str = f"{res[4][0]}"

            # Filter out loopback, link-local (fe80), and duplicates
            if ip_str not in ("127.0.0.1", "::1", "0.0.0.0", "::"):
                if not ip_str.startswith("fe80") and ip_str not in ip_strings:
                    ip_strings.append(ip_str)
    except Exception:
        pass
    return ip_strings


class TestZmqUtils(unittest.TestCase):
    def setUp(self):
        # Create a fresh ZMQ context for each test
        self.context = zmq.Context()

    def tearDown(self):
        # Ensure context is terminated to clean up resources
        self.context.term()

    def test_get_socket_bind_success(self):
        """Test that the function successfully binds and returns a port > 0."""
        # Test cases: (name, host, socket_type)
        test_cases = [
            ("ipv4_loopback", "127.0.0.1", zmq.PULL),
            ("ipv4_any", "0.0.0.0", zmq.PUSH),
            ("ipv6_loopback", "::1", zmq.REP),
            ("default_none", None, zmq.REQ),
        ]
        host_ips = get_routable_ip_strings()
        if len(host_ips) != 0:
            test_cases.append(("host_ip", host_ips[0], zmq.PUSH))

        for name, host, s_type in test_cases:
            with self.subTest(case=name, host=host, type=s_type):
                try:
                    port, socket = get_zmq_socket_on_host(
                        self.context, socket_type=s_type, host=host
                    )

                    # Assertions
                    self.assertIsInstance(port, int, "Port should be an integer")
                    self.assertGreater(port, 0, "Port should be positive")
                    self.assertEqual(socket.socket_type, s_type)

                    # Verify socket is actually bound by checking the effective identity
                    self.assertIsNotNone(socket.getsockopt(zmq.IDENTITY))

                    socket.close()
                except zmq.ZMQError as e:
                    # Specific handling for IPv6 which might be disabled in some environments
                    if host == "::1" and "Protocol not supported" in str(e):
                        self.skipTest(f"IPv6 not supported on this host: {e}")
                    else:
                        self.fail(f"Failed on {name} with host {host}: {e}")


if __name__ == "__main__":
    unittest.main()

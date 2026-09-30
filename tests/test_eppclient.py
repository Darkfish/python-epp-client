import contextlib
import io
from pathlib import Path
import runpy
import socket
import ssl
import struct
import tempfile
import unittest
from unittest.mock import Mock, call, patch


SCRIPT = Path(__file__).resolve().parents[1] / 'eppclient.py'


def frame(payload):
    return struct.pack('>I', len(payload) + 4) + payload


class EppClientTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.xmlfile = Path(directory.name) / 'command.xml'
        self.xmlfile.write_text('<hello/>', encoding='utf-8')

        self.raw_socket = Mock()
        self.tls_socket = Mock()
        self.context = Mock()
        self.context.wrap_socket.return_value = self.tls_socket
        self.socket_factory = self.enterContext(patch(
            'socket.socket', return_value=self.raw_socket))
        self.context_factory = self.enterContext(patch(
            'ssl.create_default_context', return_value=self.context))
        self.sleep = self.enterContext(patch('time.sleep'))
        self.log = self.enterContext(patch('logging.info'))

    def receive(self, transport, *payloads, chunk_size=None):
        incoming = bytearray(b''.join(frame(payload) for payload in payloads))

        def recv(size):
            if not incoming:
                raise AssertionError('Client read beyond the supplied EPP frames')
            if chunk_size is not None:
                size = min(size, chunk_size)
            chunk = bytes(incoming[:size])
            del incoming[:size]
            return chunk

        transport.recv.side_effect = recv
        return incoming

    def run_client(self, *arguments):
        with patch('sys.argv', [str(SCRIPT), *map(str, arguments)]):
            # Run the CLI as-is: importing it would also parse arguments and connect.
            runpy.run_path(str(SCRIPT), run_name='__main__')

    def test_tls_defaults_and_ascii_command_framing(self):
        incoming = self.receive(self.tls_socket, b'<greeting/>', b'<response/>')

        self.run_client(self.xmlfile)

        self.socket_factory.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        self.raw_socket.settimeout.assert_called_once_with(301)
        self.raw_socket.connect.assert_called_once_with(('epp.qa.irs.net.nz', 700))
        self.context_factory.assert_called_once_with(
            cafile=None, purpose=ssl.Purpose.SERVER_AUTH)
        self.context.load_cert_chain.assert_called_once_with(certfile=None, keyfile=None)
        self.context.wrap_socket.assert_called_once_with(
            self.raw_socket, server_hostname='epp.qa.irs.net.nz')
        self.assertEqual(self.tls_socket.sendall.call_args_list, [
            call(b'\x00\x00\x00\x0e'), call(b'<hello/>\r\n')])
        self.raw_socket.sendall.assert_not_called()
        self.raw_socket.recv.assert_not_called()
        self.sleep.assert_not_called()
        self.assertFalse(incoming)
        self.log.assert_any_call('<greeting/>')
        self.log.assert_any_call('Response from server: \n<response/>')

    def test_custom_server_port_and_certificates(self):
        self.receive(self.tls_socket, b'<greeting/>', b'<response/>')

        self.run_client('--server', 'registry.example', '--port', '1700',
                        '--certificate', 'client.pem', '--private-key', 'key.pem',
                        '--ca-certificate', 'ca.pem', self.xmlfile)

        self.raw_socket.connect.assert_called_once_with(('registry.example', 1700))
        self.context_factory.assert_called_once_with(
            cafile='ca.pem', purpose=ssl.Purpose.SERVER_AUTH)
        self.context.load_cert_chain.assert_called_once_with(
            certfile='client.pem', keyfile='key.pem')
        self.context.wrap_socket.assert_called_once_with(
            self.raw_socket, server_hostname='registry.example')

    def test_plaintext_uses_raw_socket_without_tls(self):
        incoming = self.receive(self.raw_socket, b'<greeting/>', b'<response/>')

        self.run_client('--disable-ssl', self.xmlfile)

        self.context_factory.assert_not_called()
        self.assertEqual(self.raw_socket.sendall.call_args_list, [
            call(b'\x00\x00\x00\x0e'), call(b'<hello/>\r\n')])
        self.tls_socket.recv.assert_not_called()
        self.tls_socket.sendall.assert_not_called()
        self.assertFalse(incoming)

    def test_fragmented_headers_and_payloads_on_both_transports(self):
        for plaintext in (False, True):
            with self.subTest(plaintext=plaintext):
                transport = self.raw_socket if plaintext else self.tls_socket
                incoming = self.receive(
                    transport, b'<greeting/>', b'<response/>', chunk_size=1)

                self.run_client(*(['--disable-ssl'] if plaintext else []), self.xmlfile)

                self.assertFalse(incoming)
                self.assertEqual(transport.recv.call_args_list[:4], [
                    call(4), call(3), call(2), call(1)])
                self.log.assert_any_call('Response from server: \n<response/>')

    def test_multiple_commands_wait_before_each_send_and_read_each_response(self):
        second_file = self.xmlfile.with_name('second.xml')
        second_file.write_text('<logout/>', encoding='utf-8')
        incoming = self.receive(
            self.tls_socket, b'<greeting/>', b'<first/>', b'<second/>')
        events = Mock()
        events.attach_mock(self.sleep, 'sleep')
        events.attach_mock(self.tls_socket.sendall, 'sendall')
        events.attach_mock(self.tls_socket.recv, 'recv')

        self.run_client('--wait', '3', self.xmlfile, second_file)

        self.assertEqual(events.mock_calls, [
            call.recv(4), call.recv(11),
            call.sleep(3), call.sendall(b'\x00\x00\x00\x0e'), call.sendall(b'<hello/>\r\n'),
            call.recv(4), call.recv(8),
            call.sleep(3), call.sendall(b'\x00\x00\x00\x0f'), call.sendall(b'<logout/>\r\n'),
            call.recv(4), call.recv(9),
        ])
        self.assertFalse(incoming)

    def test_utf8_command_length_counts_bytes_on_both_transports(self):
        self.xmlfile.write_text('<name>māori</name>', encoding='utf-8')
        for plaintext in (False, True):
            with self.subTest(plaintext=plaintext):
                transport = self.raw_socket if plaintext else self.tls_socket
                self.receive(transport, b'<greeting/>', b'<response/>')

                self.run_client(*(['--disable-ssl'] if plaintext else []), self.xmlfile)

                self.assertEqual(transport.sendall.call_args_list, [
                    call(b'\x00\x00\x00\x19'),
                    call(b'<name>m\xc4\x81ori</name>\r\n'),
                ])
                transport.send.assert_not_called()
                self.log.assert_any_call('Sending XML (25 bytes):\n<name>māori</name>')

    def test_disconnect_during_header_or_payload_raises_on_both_transports(self):
        for plaintext in (False, True):
            for chunks in ([b''], [b'\x00\x00', b''],
                           [struct.pack('>I', 15), b'<greet', b'']):
                with self.subTest(plaintext=plaintext, chunks=chunks):
                    transport = self.raw_socket if plaintext else self.tls_socket
                    # A finite sequence also prevents a broken implementation hanging.
                    transport.recv.side_effect = chunks

                    with self.assertRaisesRegex(ConnectionError, 'Connection closed'):
                        self.run_client(*(['--disable-ssl'] if plaintext else []), self.xmlfile)

                    transport.sendall.assert_not_called()

    def test_zero_wait_does_not_sleep(self):
        self.receive(self.tls_socket, b'<greeting/>', b'<response/>')

        self.run_client('--wait', '0', self.xmlfile)

        self.sleep.assert_not_called()

    def test_invalid_arguments_exit_before_connecting(self):
        for arguments in ([], ['--port', 'invalid', self.xmlfile],
                          ['--wait', 'invalid', self.xmlfile]):
            with self.subTest(arguments=arguments), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    self.run_client(*arguments)
                self.assertEqual(error.exception.code, 2)
                self.socket_factory.assert_not_called()

    def test_missing_input_file_raises_without_sending(self):
        self.receive(self.tls_socket, b'<greeting/>')

        with self.assertRaises(FileNotFoundError):
            self.run_client(self.xmlfile.with_name('missing.xml'))

        self.tls_socket.sendall.assert_not_called()

    def test_greeting_timeout_propagates_without_sending(self):
        self.tls_socket.recv.side_effect = socket.timeout('timed out')

        with self.assertRaisesRegex(socket.timeout, 'timed out'):
            self.run_client(self.xmlfile)

        self.tls_socket.sendall.assert_not_called()

    def test_certificate_verification_failure_propagates(self):
        self.context.wrap_socket.side_effect = ssl.SSLCertVerificationError('untrusted')

        with self.assertRaises(ssl.SSLCertVerificationError):
            self.run_client(self.xmlfile)

        self.raw_socket.sendall.assert_not_called()
        self.tls_socket.sendall.assert_not_called()


if __name__ == '__main__':
    unittest.main()

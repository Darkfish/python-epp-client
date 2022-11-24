import os
import ssl
import time
import struct
import socket
import logging
import argparse

#: Log items
logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
                    level=logging.INFO)


#: Parse arguments
parser = argparse.ArgumentParser(
    description='Send prepared XML files to EPP server'
)
parser.add_argument(
    'xmlfiles',
    metavar='xmlfile',
    type=str,
    nargs='+',
    help='XML Input Files'
)
parser.add_argument(
    '--server',
    nargs='?',
    default='epp.qa.irs.net.nz',
    help='EPP server hostname or ip'
)
parser.add_argument(
    '--port',
    nargs='?',
    type=int,
    default=700,
    help='EPP server port'
)
parser.add_argument(
    '--certificate',
    nargs='?',
    default=None,
    help='client certificate file'
)
parser.add_argument(
    '--private-key',
    nargs='?',
    default=None,
    help='private key file'
)
parser.add_argument(
    '--ca-certificate',
    nargs='?',
    default=None,
    help='file with the bundle of CAs'
)
parser.add_argument(
    '--wait',
    nargs='?',
    type=int,
    default=None,
    help='Time to wait between commands'
)
parser.add_argument(
    '--disable-ssl',
    action='store_true',
    default=None,
    help='Disable SSL support (not RFC compliant)'
)
args = parser.parse_args()



class epp(object):
    def __init__(self):
        #: Set host
        self.host = args.server
        self.port = args.port

        #: Find size of C integers
        self.format_32 = self.format_32()

        #: Create connection to EPP server
        if args.disable_ssl:
            logging.info(' - Making plaintext connection to {0}:{1}'.format(
                self.host,
                self.port
            ))
        else:
            logging.info(' - Making SSL connection to {0}:{1}'.format(
                self.host,
                self.port
            ))
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(301)
        self.socket.connect((self.host, self.port))
        if not args.disable_ssl:
            context = ssl.create_default_context(
                cafile = args.ca_certificate,
                purpose = ssl.Purpose.SERVER_AUTH
            )
            context.load_cert_chain(
                certfile=args.certificate,
                keyfile=args.private_key
            )
            self.socket_ssl = context.wrap_socket(
                self.socket,
                server_hostname = self.host
            )

    def __del__(self):
        try:
            self.socket.close()
        except TypeError:
            """ Will occur when not properly connected """
            pass

    #: Uses basic EPP data structures from:
    #  - https://github.com/jochem/Python-EPP
    #  - http://www.bortzmeyer.org/4934.html
    def format_32(self):
        # Get the size of C integers. We need 32 bits unsigned.
        format_32 = ">I"
        if struct.calcsize(format_32) < 4:
            format_32 = ">L"
            if struct.calcsize(format_32) != 4:
                raise Exception("Cannot find a 32 bits integer")
        elif struct.calcsize(format_32) > 4:
            format_32 = ">H"
            if struct.calcsize(format_32) != 4:
                raise Exception("Cannot find a 32 bits integer")
        else:
            pass
        return format_32

    def int_from_net(self, data):
        return struct.unpack(self.format_32, data)[0]

    def int_to_net(self, value):
        return struct.pack(self.format_32, value)

    def read(self, schema_critical=True):
        logging.info('  - Trying to read 4-byte header from socket')
        length = self.read_until(4)
        if length:
            i = self.int_from_net(length)-4
            logging.info(
                '  - Found length header, trying to read {0} bytes'.format(i)
            )

            #: Return raw data
            return(self.read_until(i))

    def read_until(self, total_bytes):
        '''Buffer when self.socket[_ssl].recv (can't use MSG_WAITALL)'''
        buffer = bytes()
        while len(buffer) < total_bytes:
            i = total_bytes - len(buffer)
            if args.disable_ssl:
                buffer += self.socket.recv(i)
            else:
                buffer += self.socket_ssl.recv(i)
            logging.info(
                '  - Received {0}/{1} bytes'.format(
                    len(buffer),
                    total_bytes
                )
            )
        return(buffer)

    def write(self, xml):
        epp_as_string = xml
        # +4 for the length field itself (section 4 mandates that)
        # +2 for the CRLF at the end
        length = self.int_to_net(len(epp_as_string) + 4 + 2)
        logging.info(
            'Sending XML ({0} bytes):\n'.format(
                len(epp_as_string) + 4 + 2) + xml
        )
        if args.disable_ssl:
            self.socket.send(length)
            return self.socket.send((epp_as_string + "\r\n").encode())
        else:
            self.socket_ssl.send(length)
            return self.socket_ssl.send((epp_as_string + "\r\n").encode())

#: Connect to EPP server
client = epp()

#: Fetch greeting
logging.info('Trying to read EPP Greeting from server')
logging.info(client.read().decode())

for fname in args.xmlfiles:
    with open(fname, 'r') as f:
        if args.wait:
            time.sleep(args.wait)
        logging.info('Sending {0}'.format(fname))
        client.write(f.read())
        logging.info('Response from server: \n{0}'.format(client.read().decode()))

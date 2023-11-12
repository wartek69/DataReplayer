import logging
import re
import socket
import time
import argparse
from threading import Thread

class DataReplayer:
    def __init__(self, host, port, is_client_mode, delete_newline, is_hex):
        self.host = host
        self.port = port
        self.is_hex = is_hex
        self.is_client_mode = is_client_mode
        self.delete_newline = delete_newline
        self.conn = None
        self.msgs_send = 0
        if(self.is_client_mode):
            self.establish_client_connection()
        else:
            self.init_server_connection()

    def run(self, filename):
        # regex to delete everything between '$' and the '$'
        self.regex = re.compile(r'([$]).*?\1')
        self.open_file(filename)
        
    def init_server_connection(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as self.s:
            self.s.bind((self.host, self.port))
            logging.info('listening for connections on {}:{}...'.format(self.host, self.port))
            self.s.listen()
            self.conn, addr = self.s.accept()
            logging.info('connection accepted')

    def establish_client_connection(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((self.host, self.port))

    def open_file(self, filename):
        try:
            self.file = open(filename, 'r')
        except FileNotFoundError as e:
            logging.error(e)

    def receive_message(self):
        while True:
            if(self.is_client_mode):
                data = self.s.recv(10000)
            elif(self.conn is not None ):
                data = self.conn.recv(10000)

            logging.debug("received: {}".format(data))
            if(data == ""):
                time.sleep(0.1)

    def send_message(self, message):
        send_buffer = ""
        if self.is_hex:
            send_buffer = bytearray.fromhex(message)
        else:
            send_buffer = message.encode()

        if(self.is_client_mode):
            self.s.sendall(send_buffer)
        else:
            self.conn.sendall(send_buffer)
        self.msgs_send += 1
    
    def replay(self, timeout):
        i = 0
        for line in self.file:
            i += 1
            logging.debug(str(i) + ': ' + line)
            line = self.regex.sub("", line)
            logging.debug(str(i) + ': ' + line)
            if self.delete_newline:
                line = line.replace('\n', '')
            time.sleep(timeout)
            self.send_message(line)
        logging.debug('{} replay message sent'.format(i))
        if(not self.is_client_mode):
            self.s.close()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", help="port of the lidar", default=2112)
    parser.add_argument("-v", "--verbose", help="enable debug mode", action="store_true")
    parser.add_argument("--file", "-f", help = "rec file location", default='recordings/20190821122752SB_LIDAR.rec')
    parser.add_argument("--timeout", "-t", help = "interval between messages", default=0.001)
    parser.add_argument("--client", "-c", help= "use the replayer as a client, default server mode", action="store_true")
    parser.add_argument("--newline", "-n", help= "Deletes new lines from the parsed file", action="store_true")
    parser.add_argument("--ip", "-i", help = "Ip to connect to or use when in server mode", default='0.0.0.0')
    parser.add_argument("--hex", help = "Use when your recording file consists of a hex string", action="store_true")


    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s')
    else:
        logging.basicConfig(level=logging.INFO,
            format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s')

    return int(args.port), args.file, float(args.timeout), args.client, args.newline, args.ip, args.hex

if __name__ == '__main__':
    port, filename, timeout, is_client_mode, delete_newline, ip, is_hex = parse_args()
    replayer = DataReplayer(ip, port, is_client_mode, delete_newline, is_hex)
    thread = Thread(target = replayer.receive_message)
    thread.daemon = True
    thread.start()
    while True:
        replayer.run(filename)
        replayer.replay(timeout)
        time.sleep(timeout)
        logging.info('resending...')
        logging.info(f'msgs send: {replayer.msgs_send}')

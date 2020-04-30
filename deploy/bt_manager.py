import os
import serial
import re
from functools import partial
import time
import logging

logger = logging.getLogger(__name__)

level = os.getenv('APP_LOG_LEVEL', '10')
logger.setLevel(int(level))


def strip_extra_characters(str):
    str = re.sub('\d+\t', "", str)
    str = re.sub('[\r"0"]', "", str)
    return str


def generic_handler(cmd, err):
    pass


def str_to_bytes(my_str):
    return bytes(my_str, "ascii")


READ_DIR = b"at+dir \r\n"
RESET = b'atz \r\n'
FILE_CLOSE = b'at+fcl \r\n'
SB_VERSION = b"ati 33 \r\n"
SB_FIRMWARE = b"ati 3 \r\n"
SB_HEX = b"ati 13 \r\n"


class BTManager():
    def __enter__(self):
        return self

    def __init__(self, port):

        logger.info(("Running with port: {}".format(port)))
        self.sp = serial.Serial(port,
                                115200,
                                timeout=2,
                                parity=serial.PARITY_NONE,
                                rtscts=1)
        self.sp.send_break(duration=0.25)
        self.sp.readall()
        logger.info("port initialized")

    def __exit__(self, type, value, traceback):
        self.sp.close()

    def get_sb_version(self):
        res = self.write_bytes(SB_VERSION)
        self.sp.read_until(b"\r")
        return res

    def get_sb_hex(self):
        res = self.write_bytes(SB_HEX)
        self.sp.read_until(b"\r")
        return res

    def get_sb_firmware(self):
        res = self.write_bytes(SB_FIRMWARE)
        self.sp.read_until(b"\r")
        return res

    def write_str(self, cmd):
        return self.write_bytes(str_to_bytes(cmd))

    def write_bytes(self, bcmd):
        self.sp.write(bcmd)
        self.sp.flush()
        return self.sp.read_until(b'\r', 100)

    def send_single_cmd(self, cmd, meta, handler):
        cmd_line = cmd + ' ' + meta + '\r\n'
        logger.debug(("sending single command {}".format(repr(cmd_line))))
        self.write_str(cmd_line)
        if b'01\t' not in res:
            return (True, "")
        else:
            err_string = handler(cmd, res)
        return (False, err_string)

    def reset(self):
        return self.write_bytes(RESET)

    def read_dir(self):
        self.sp.write(READ_DIR)
        self.sp.flush()
        res = self.sp.read_until('00\r')
        logger.info("res {}".format(repr(res)))
        if b'\n01' in res:
            return (False, res)
        #read again
        self.sp.read_until(b"\r", 10)
        logger.debug(res)
        res_str = res.decode('utf-8')
        res = res_str.split('\n')
        res = list(map(strip_extra_characters, res))
        return (True, list([x for x in res if x != '']))

    def del_file(self, name):
        return self.send_single_cmd('at+del', '"{}"'.format(name),
                                    generic_handler)

    def load_file(self, name, file):
        logger.debug(("file to load {} with name {}".format(file, name)))
        try:
            with open(file, 'rb') as f:
                self.write_bytes(RESET)
                fowcmd = 'at+fow \"' + name + '\"\r\n'
                res = self.write_str(fowcmd)
                logger.info(("open file response: {}".format(repr(res))))
                if b'01\t' in res:
                    return False
                for block in iter(partial(f.read, 50), b''):
                    str_block = block.hex()
                    strblock = 'at+fwrh \"' + str_block + '\"\r\n'
                    logger.info(("write chunk {}".format(repr(str_block))))
                    res = self.write_str(strblock)
                    logger.info(("write chunk response {}".format(repr(res))))
                    if b'01\t' in res:
                        return False
                res = self.write_bytes(FILE_CLOSE)
                logger.debug(res)
                return res

        except IOError as e:
            logger.error(e)

    def at_command(self, cmd):
        logger.info(("at cmd:{}".format(cmd)))
        cmd = cmd + "\r\n"
        self.sp.write(str_to_bytes(cmd))
        self.sp.flush()
        time.sleep(0.4)
        size = self.sp.in_waiting
        logger.debug(("size reponse {}".format(size)))
        res = self.sp.read(size)
        logger.debug(("response raw:{}".format(repr(res))))
        return res.decode("utf-8")

    def start_app(self, cmd):
        logger.info(("starting app:{}".format(cmd)))
        cmd = 'at+run \"' + cmd + "\"\r\n"
        res = self.write_str(cmd)
        logger.info(("response raw:{}".format(repr(res))))


if __name__ == '__main__':
    port = os.getenv('BL654_PORT', '/dev/ttyUSB0')
    with BTManager(port) as bt:
        file_path = os.getenv('UWC_FILE', './mot.uwc')
        file_name = (file_path.split("/")[-1]).split(".")[-2]
        res, directory_list = bt.read_dir()
        logger.info("directory {}".format(directory_list))
        res = bt.write_bytes("ati 3 \r\n")
        logger.info("directory {}".format(directory_list))

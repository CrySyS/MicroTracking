import can  # http://skpang.co.uk/blog/archives/1220

# example lines
# 1483093132.049669        0380    000    8    30 bb 82 00 9d 53 00 81
# 1483093132.128087        0280    000    8    00 00 00 00 00 00 00 00
# 1483093132.130010        0180    000    6    64 a0 7f ff 44 00
# timestamp                arb_id  flag   dlc  data
# arb_id = arbitration_id
# flag = remote_frame|id_type|error_frame


class TraceFileReader:
    def __init__(self, file, debug=False):
        self.file_name = file
        self.debug = debug

    def read_line(self):
        cnt = 0
        error_counter = 0
        with open(self.file_name) as f:
            for line in f:
                cnt += 1
                try:
                    split_line = line.split(' ')
                    split_line = [x for x in split_line if x != '']

                    data = split_line[4:]
                    data = [int(x, 16) for x in data]

                    yield can.Message(timestamp=float(split_line[0]),
                                      is_remote_frame=bool(int(split_line[2][0])),
                                      is_extended_id=bool(int(split_line[2][1])),
                                      is_error_frame=bool(int(split_line[2][2])),
                                      arbitration_id=int(split_line[1], 16),
                                      dlc=int(split_line[3]),
                                      data=data)
                except (ValueError, IndexError):
                    #print("Error, unable to parse line #%d (skipping): '%s'" % (cnt, line))
                    error_counter = error_counter + 1
                    continue
        if self.debug:
            print("Number of read errors: %d " % (error_counter))

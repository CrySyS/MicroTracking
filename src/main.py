import sys
import math
import tracefilereader
from matplotlib import pyplot

debug = False


def init_car_type(car_t):

    if car_t == "CAR_1":
        if debug:
            print("CAR_1 selected")
        sp_id = int('0x410', 16)
        st_id = int('0x180', 16)
        return sp_id, st_id, can_speed_to_real_speed, can_steering_to_radius

    else:
        raise ValueError


def calculate_next_place(actual_x, actual_y, actual_direction, speed, radius, delta_time=1):

    if delta_time == 0 or speed == 0:
        return actual_x, actual_y, actual_direction

    delta_distance = speed * delta_time

    if radius:
        # for simplicity, assume that the vehicle is at the origo, then the center of turning is...
        # center_x = 0
        # center_y = -radius

        # delta_distance / circle_perimeter = delta_direction / 360
        # delta_distance / 2Rpi = delta_direction / 2pi
        # delta_direction = delta_distance / R
        delta_direction = -1 * delta_distance / radius

    else:  # not turning, radius=Inf
        delta_direction = 0

    next_direction = actual_direction + delta_direction

    delta_x = delta_distance * math.cos(next_direction)
    delta_y = delta_distance * math.sin(next_direction)

    next_x = actual_x + delta_x
    next_y = actual_y + delta_y

    if next_direction < 0:
        next_direction += 2 * math.pi
    if next_direction > 2 * math.pi:
        next_direction -= 2 * math.pi

    return next_x, next_y, next_direction


def print_plot(x, y):
    c = ['0.9', '0.7', '0.5', '0.3', '0.1']  # direction is from light(0,9) to dark(0.1)
    dx = x[0]
    x.reverse()
    dx -= x[0]
    dy = y[0]
    y.reverse()
    dy -= y[0]
    c.reverse()
    #pyplot.scatter(x, y, c=c)  # reversed plotting order to get nicer figure
    pyplot.plot(x, y, '-o', color='black',
         markersize=6, linewidth=2,
         markerfacecolor='white',
         markeredgecolor='gray',
         markeredgewidth=1)  # reversed plotting order to get nicer figure
    pyplot.plot(0, 0, '-p', color='red',
         markersize=6,
         markerfacecolor='white',
         markeredgecolor='red',
         markeredgewidth=1)
    #pyplot.arrow(x[0], y[0], dx, dy)
    pyplot.xlabel('X')
    pyplot.ylabel('Y')
    pyplot.title('Route from CAN messages\nStart: 0,0 red dot\nDirection: light->dark')
    pyplot.axis('equal')  # equal scale on x and y axis
    pyplot.savefig('../output/result.png')
    pyplot.show()


def can_speed_to_real_speed(data):  # speed in 2nd and 3rd bytes in two decimal precision (dkm/h)
    speed = int.from_bytes(data[1:3], 'big')
    speed = speed / 3.6 / 100  # speed converted to m/s

    '''
    real distance   measured distance   m/r     r/m
    30	            38,46	            1,282	0,780
    60	            78,66	            1,311	0,762
    90	            118,28	            1,314   0,761
    120	            157,56	            1,313	0,762
    150	            196,78	            1,312	0,762
    '''
    speed = speed * 0.762  # correction for too high speeds, seems to be working

    if debug:
        print('Speed: ', data, speed)
    return speed  # TODO forward and backward speed are the same now


def can_steering_to_radius(data):
    # steering position in 3rd and 4th bytes in two's complement
    # 0 center, right 65512-57712, left 0-7824
    # transformed to -7824 - 7824 range (total left -7824; total right 7824; center 0)
    # right turn -> positive radius; left turn -> negative radius
    # right turn, ~360 degree = 5736 -> diameter = 12,7 m radius = 6.35 m
    # steer 0 -> wheel pi/2=90; steer 5736 -> wheel 1.1688=66.96 => w= -7.009019694554718e-05 * S + pi/2
    # car length 2,7 m
    # if radius is very big (200 m), than assume no turning

    st_pos = int.from_bytes(data[2:4], 'big')
    if data[2] >= 2 ** 7:
        st_pos -= 2 ** 16
    st_pos *= -1
    wh_pos = -7.009019694554718e-05 * st_pos + math.pi/2  # in radian
    radius = 2.7 * math.tan(wh_pos)

    # if radius > 200 or radius < -200:
    #     radius = None

    if debug:
        print('Steering: ', data, st_pos, wh_pos, radius)
    return radius


if __name__ == "__main__":
    #if len(sys.argv) < 2:
    #    print("Usage: python3 canbasedtracker.py path_to_cantrace.csv (car_type)")
    #    sys.exit()

    if len(sys.argv) > 1:
        trace_file = sys.argv[1]
    else:
        trace_file = "../sample_trace/trace_1.log"

    # default car type if CAR_1
    if len(sys.argv) == 3:
        car_type = sys.argv[2]
    else:
        car_type = "CAR_1"

    if debug:
        print("Trace file: " + trace_file)
        print("Car type: " + car_type)

    speed_id, steering_pos_id, can_speed_to_real_speed, can_steering_to_radius = init_car_type(car_type)

    last_time = None
    last_display_time = 0
    display_periodicity = 1
    display_cnt = 0
    last_x = 0
    last_y = 0
    last_speed = 0
    last_direction = 0
    last_radius = None
    cnt = 0
    plot_x = []
    plot_y = []

    tr_reader = tracefilereader.TraceFileReader(trace_file, debug=debug)

    for msg in tr_reader.read_line():
        if msg.arbitration_id == speed_id or msg.arbitration_id == steering_pos_id:
            time = msg.timestamp
            if not last_time:
                last_time = time

            last_x, last_y, last_direction = calculate_next_place(
                last_x, last_y, last_direction, last_speed, last_radius, time - last_time
            )
            last_time = time
            if msg.arbitration_id == speed_id:
                last_speed = can_speed_to_real_speed(msg.data)
            elif msg.arbitration_id == steering_pos_id:
                last_radius = can_steering_to_radius(msg.data)

            if debug:
                if last_display_time + display_periodicity < last_time:
                    print("%d T: %f X: %f Y: %f S: %f D: %f"
                        % (display_cnt, last_time, last_x, last_y, last_speed, last_direction))
            else:
                if last_display_time + display_periodicity < last_time:
                    plot_x.append(last_x)
                    plot_y.append(last_y)
                    last_display_time = last_time
                    display_cnt += 1

            cnt += 1

    print_plot(plot_x, plot_y)

import sys
import math

debug = False


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
    wh_pos = -6.009019694554718e-05 * st_pos + math.pi/2  # in radian
    radius = 2.7 * math.tan(wh_pos)

    # if radius > 200 or radius < -200:
    #     radius = None

    if debug:
        print('Steering: ', data, st_pos, wh_pos, radius)
    return radius


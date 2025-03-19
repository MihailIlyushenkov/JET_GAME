import struct
import math

# str = b"PLAYAS 15\n"
# print(str)


# msg = struct.pack("<9sIiiifIfIIiiifIfIIiiifIfI", 
#                   str, 
#                   1, 2, 3, 4, 5.15, 6, 7.17, 8, 
#                   10, 20, 30, 40, 50.15, 60, 70.17, 80,
#                   11, 21, 31, 41, 51.15, 61, 71.17, 81)

# nmes = 3

# gotsrt = struct.unpack("<9s", msg[:9])
# msg = msg[9:]

# for i in range(nmes):
#     print(struct.unpack("IiiifIfI", msg[:32]))
#     msg = msg[32:]

# print(hex(0b10000000000000000))
# print(hex(0b01000000000000000))
# print(hex(0b00100000000000000))
# obj_index = 6555
# servdata = obj_index | 0b00100000000000000
# print(f"{bin(servdata)}")
# print(f"type: {bin(servdata & 0b10000000000000000)}, {bin(servdata & 0b01000000000000000)}, {bin(servdata & 0b00100000000000000)}")
# print(f"index:{servdata & 0b00011111111111111}")

# print(30*math.pi/180)
# print(math.pi/3)

PI = math.pi

def convertAngle(x): # (-PI; PI] -> [0, 2PI)
    return x if x >= 0 else (2*PI + x)

def getrange(cord1: tuple, cord2: tuple) -> float:
    return math.sqrt( (cord1[0] - cord2[0])**2 + (cord1[1] - cord2[1])**2)

def sub_tuple(a: tuple, b: tuple):
    if len(a) == len(b):
       return tuple(a[i] - b[i] for i in range(len(a)))
    else:
        raise IndexError("different sizes of objects")

def get_angle(x, y) -> float: #возвращает угол до точки (x, y), отсчитанный от оси x в диапазоне от 0 до 2PI 
    # if (x == 0):
    #     if y == 0:
    #         angle = 0
    #     elif y > 0:
    #         angle = PI/2
    #     else:
    #         angle = 3*PI/2
    # elif x > 0:
    #     angle = -math.atan(y/x)
    # else:
    #     if y >= 0:
    #         angle =  -PI + math.atan(y/(-x))
    #     if y < 0:
    #         angle = -math.atan(y/x) + PI
    angle = math.atan2(y, x)

    angle = convertAngle(angle)
    return angle

def sub_angle(a, b) -> float: #возрвращает кратчайший угло поворота от угла a до угла b
    if b == a:
        diff = 0
    elif b > a:
        if b - a <= PI:
            diff = b - a
        else:
            diff = -a - (2*PI - b)
    else: #b < a
        if a - b <= PI:
            diff = -(a - b)
        else:
            diff = b + (2*PI - a)
    return diff

my_x = 20
my_y = -150
tx = 480
ty = 0

x = tx - my_x
y = ty-my_y

print(x, y)
print(get_angle(x, y))

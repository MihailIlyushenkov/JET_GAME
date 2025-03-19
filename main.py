import pygame
import sys
import math
import asyncio
import struct

import pygame.draw_py

from data.player import player, ExtendedGroup, get_range, get_angle
from data.weapons import missle, armament, sub_angle
from data.interface import draw_edges

W = 1920
H = 1080
FPS = 60
PI = math.pi
SW = 0
SH = 0

frame = 0
mousex = 0
mousey = 0

pygame.init()
screen = pygame.display.set_mode((W, H))

SHOW_MAP = True
if SHOW_MAP:
    GLOBAL_MAP = pygame.image.load("data/assets/MAP.jpg")

#screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

clock = pygame.time.Clock()
all_weapons = {}
all_players = {}
game_objects = []

#обработка settings.txt
def makeweapon(data: list[str]) -> list[str, list]:
    #print(f"i got data: \n{data}")
    name = data[0]
    
    #scale = int(data[1])
    dim = [int(i) for i in data[1].split()]
    if len(dim) != 2:
        print("ERROR INVALID DIMENTION OF OBJECT")
    print(dim)
    meshnames = data[2].split()
    # mesh = [pygame.transform.scale(j, (j.get_width()/scale, j.get_height()/scale)) 
            # for j in [pygame.image.load(i) for i in meshnames]]

    mesh = [pygame.transform.scale(j, dim) 
            for j in [pygame.image.load(i) for i in meshnames]]


    settings = [(float(i) if '.' in i else int(i)) for i in data[3].split()]
    for j in [1,2,3,5]:
        settings[j] = settings[j]*FPS
    
    return [name, [mesh, settings]]

def makeplayer(data: list[str], team, all_weapons: dict) -> list[str, player]:
    #print(f"i got data: {data}")
    name = data[0]
    meshnames = data[1].split()
    dim = [int(i) for i in data[2].split()]
    if len(dim) != 2:
        print("ERROR INVALID DIMENTION OF OBJECT")
    print(dim)

    #scales = [int(i) for i in data[2].split()]

    mesh = []
    for i in range(len(meshnames)):
        image = pygame.image.load(meshnames[i])
        #mesh.append(pygame.transform.scale(image, 
        #                                   (image.get_width()/scales[i], image.get_height()/scales[i])))
        mesh.append(pygame.transform.scale(image, dim))
          

    start = [int(i) for i in data[3].split()]
    if data[4] != "None":
        weapon_list = [[i.split(':')[0], int(i.split(':')[1])] for i in data[4].split(',')]
        #print(weapon_list)
        arm = armament({i[0]: [i[1], *all_weapons[i[0]]] for i in weapon_list})
    else:
        arm = None
    
    settings = [(float(i) if '.' in i else int(i)) for i in data[5].split()]


    return [name, player(mesh, start, arm, team, settings)]

def updater(objects: list[player|missle], arguments: list):
    for i in range(min(len(objects), len(arguments))):
        objects[i].update(*arguments[i])

def drawer(objects: list[player|missle], arguments: list):
    for i in range(min(len(objects), len(arguments))):
        objects[i].draw(*arguments[i])

# def hitcheck(hittables: list[player], hitters: ExtendedGroup):
#     for i in hittables:
#         hitlist = list((filter(lambda x: x.team != i.team, pygame.sprite.spritecollide(i, hitters, False))))
#         if hitlist:
#             i.gethit()
#             for j in hitlist:
#                 j.gethit()
#     hitters.filterinactive()

try:        
    with open("data/settings.txt", "r") as f:
        data = f.readlines()
        
        data = list(filter(lambda x: x[0] != '#', data)) #удаляем комментарии
        data = [(i[:-1] if '\n' in i else i) for i in data] #отрезаем \n
        ws_index = data.index("$weapons$")
        weapon_count = int(data[ws_index + 1])

        batchstart = ws_index + 2 #индекс начала пакета данных (4 строки) описания вооружения в массиве

        for i in range(weapon_count):
            new_weapon = makeweapon(data[batchstart:batchstart + 4])
            all_weapons[new_weapon[0]] = new_weapon[1]
            batchstart += 4
        #print(all_weapons)

        pl_index = data.index("$players$")
        pl_count = int(data[pl_index + 1])
        batchstart = pl_index + 2


        for i in range(pl_count): #создаем пока что игрока с командой i, т.е. у всех созданных разные команды
            new_player = makeplayer(data[batchstart:batchstart + 6], i, all_weapons)
            all_players[new_player[0]] = new_player[1]
            batchstart += 6
            #print(f"INTERATION {i}")
        #print(all_players)

except FileNotFoundError:
    print("file 'settings.txt' or some of the mesh files not found, cant continue.")
    sys.exit()
except IndexError:
    print("settings file is corrupted")
    sys.exit()
else:
    pass

missiles = [*all_weapons.values()]
print("PRINTING MISSLES:::\n\n")
for i in missiles:
    print(i, "\n")

players = [*all_players.values()]
print(players)

#вспомогательные переменные для обработки ввода с клавиатуры
turn_left1 = False
turn_right1 = False
throttle_up1 = False
throttle_down1 = False

mouse = (0, 0)
offset = (0,0)

ONEWASUP = True
name = ""
index = 0

async def main():
    global name
    if len(sys.argv) < 3:
        print("Usage: %s <server> <user>" % (sys.argv[0]))
        sys.exit(1)
    server = sys.argv[1]
    username = sys.argv[2]
    name = username
    loop = asyncio.get_running_loop()
    end_of_game = loop.create_future()

    transport, protocol = await loop.create_datagram_endpoint(
            lambda: GameServerProtocol(end_of_game, username),
            remote_addr=(server, 9921))
    try:
        await end_of_game
    finally:
        transport.close()


turn_old = 777
thrust_old = 777

def draw_interface(surface: pygame.surface, owner_settings: list, targets: list):
    my_x, my_y, my_heading, my_rdr_mode, my_rdr_angle, my_rdr_range = owner_settings

    rscreen_H = rscreen_W = H/3
    top_x = W - rscreen_W
    top_y = H - rscreen_H
    pygame.draw.rect(surface, (0,0,0), 
                    (top_x, top_y - 30, rscreen_W, rscreen_H + 30))
    
    pygame.draw.rect(surface, (0,255,0), 
                    (top_x, top_y, rscreen_W, rscreen_H), 5)
    
    mode = ""
    if my_rdr_mode == 0:
        mode = "Off"
    elif my_rdr_mode == 1:
        mode = "SRC"
    elif my_rdr_mode == 2:
        mode = "TRC"
    else:
        mode = "mode Err"
    
    font = pygame.font.Font(None, 24)
    
    pygame.draw.rect(surface, (0,0,0), (0, 0, 250, 100))

    text = font.render(mode, True, (0, 255, 0))
    surface.blit(text, (top_x + rscreen_W/2 - 5, top_y - 20))

    text = font.render(f"{my_rdr_range}", True, (0,255,0))
    surface.blit(text, (top_x + rscreen_W - 60, top_y - 20))

    text = font.render("x, y, heading: {:.1f}, {:.1f}, {:.1f}".format(my_x, my_y, my_heading), True, (255, 255, 255))
    screen.blit(text, (10, 20))
    
    text = font.render("index: {:.1f}".format(index), True, (255, 255, 255))
    screen.blit(text, (10, 40))

    text = font.render("arr angle: {:.3f}".format(my_rdr_angle), True, (255, 255, 255))
    screen.blit(text, (10, 60))

    if mode == "SRC":
        pygame.draw.aaline(screen, 
                           (0, 255, 0), 
                           (W/2, H/2), 
                           (W/2 + my_rdr_range*math.cos((my_rdr_angle + my_heading) % (2*PI)), 
                                H/2 - my_rdr_range*math.sin((my_rdr_angle + my_heading) % (2*PI))),
                            1)

        pygame.draw.aaline(surface, (0,255,0), 
            (top_x + rscreen_W/2 - (my_rdr_angle/(PI/3))*(rscreen_W/2), top_y),
            (top_x + rscreen_W/2 - (my_rdr_angle/(PI/3))*(rscreen_W/2), top_y+rscreen_H), 1)
        
        for i in targets:
            tx, ty, theading, trmode = i
            # print(f"rdar processing target {tx, ty, theading, trmode}, my are {my_x, my_y, my_heading}")
            
            #print(f"angle to target ({my_x, my_y}, {tx, ty}):", get_angle(tx - my_x, ty-my_y))
            angle = sub_angle(get_angle(tx - my_x, ty-my_y), my_heading)
            #print("arr angle to target:", angle)

            rng = get_range((my_x, my_y), (tx, ty))
            cords = (top_x + rscreen_W/2 + angle/(PI/3)*(rscreen_W/2), top_y - (rng/my_rdr_range - 1)*rscreen_H)
            pygame.draw.circle(surface, (0, 255, 0), cords, 4)
            
            if (trmode == 1):
                draw_edges(surface, (255, 0, 0), cords, 20, 7)
    
    if mode == "TRC":
        for i in targets:
            tx, ty, theading, trmode = i
            if (trmode == 2):
                rng = get_range((my_x, my_y), (tx, ty))
                cords = (top_x + rscreen_W/2 - my_rdr_angle/(PI/3)*(rscreen_W/2), top_y + rscreen_H - (rng/my_rdr_range)*rscreen_H)
                pygame.draw.aaline(surface, (0,255,0), (cords[0], top_y + rscreen_H), cords, 1)
                pygame.draw.circle(surface, (0, 255, 0), cords, 4)

def game_step(transport, dt):
    global name, frame, turn_left1, turn_right1, throttle_up1, throttle_down1, thrust_old, turn_old, ONEWASUP

    launch = 0
    choose_weapon = 0
    choose_tar = 0
    lock = 0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sys.exit()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_a:
                turn_left1 = True
            if event.key == pygame.K_d:
                turn_right1 = True
            if event.key == pygame.K_LSHIFT:
                throttle_up1 = True
            if event.key == pygame.K_LCTRL:
                throttle_down1 = True
            if event.key == pygame.K_SPACE:
                launch = 1
            if event.key == pygame.K_TAB:
                pass
                #user.rdr.switch_fow()
            if event.key == pygame.K_CAPSLOCK:
                pass
                #user.rdr.switch_range()
            if event.key == pygame.K_BACKQUOTE:
                choose_weapon = 1
                #user.switch_weapon()
            if event.key == pygame.K_1 and ONEWASUP:
                ONEWASUP = False
                lock = 1
                #user.rdr.try_lock()
            
            if event.key == pygame.K_2:
                #user.rdr.choose_target()
                choose_tar = 1
            if event.key == pygame.K_EQUALS:
                pass
               # user.rdr.switch()
            
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_a:
                turn_left1 = False
            if event.key == pygame.K_d:
                turn_right1 = False
            if event.key == pygame.K_LSHIFT:
                throttle_up1 = False
            if event.key == pygame.K_LCTRL:
                throttle_down1 = False

            if event.key == pygame.K_1:
                ONEWASUP = True
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse = event.pos
    
    thrust = 0
    if (throttle_up1 + throttle_down1)%2:
        if throttle_up1: #and (self.thrust <= 99):
            thrust += 1
        elif throttle_down1: #and (self.thrust > 0): (эти проверки есть на сервере)
            thrust -= 1

    turn = turn_left1 - turn_right1
    

    if (thrust != thrust_old) or (turn != turn_old) or launch or choose_weapon or choose_tar or lock:
        message = f"CTRL {index} {thrust} {turn} {launch} {choose_weapon} {choose_tar} {lock}"
        print(message)
        transport.sendto(message.encode())
        
        thrust_old = thrust
        turn_old = turn


    frame = (frame + 1)%FPS

    ################DRAWING SECTION
    clock.tick(FPS)
    screen.fill((0,0,0))



    my_x, my_y, my_heading, my_rdr_mode, my_rdr_angle, my_rdr_range = dt
    my_x_client = my_x
    my_y_client = H - my_y
    user = all_players[name]
    found_rdr_targets = []

    #print(f"object attr: {x}, {y}, {heading}")
    # pygame.draw.circle(screen, (255, 255, 255), (0, H), 5)
    #pygame.draw.circle(screen, (255, 0, 0), (x, H -y), 15)
    #pygame.draw.aaline(screen, (255, 0, 0), (x, H -y), (x + 50*math.cos(heading), H -y - 50*math.sin(heading)))

    if SHOW_MAP: 
        screen.blit(GLOBAL_MAP, GLOBAL_MAP.get_rect(center = (-my_x_client, -my_y_client)))


    for i in game_objects:
        objnum, objtype, status, x, y, heading, rdr_mode, rdr_angle, rdr_range = i
        #print(f"processing object with parms: {i}")
        if objtype == "player":
            obj = all_players[f"user{objnum}"]
            cords = (x - my_x_client + W/2, H-y -my_y_client + H/2)
            obj.display(screen, heading, cords, status)
            
            #pygame.draw.circle(screen, (255, 0, 0), cords, 10)
            #pygame.draw.rect(screen, (255, 0, 0), (cords[0] - obj.rect.width/2, cords[1]-obj.rect.height/2, obj.rect.width, obj.rect.height), 4)
            pygame.draw.aaline(screen, (255, 0, 0), cords, (cords[0] + 50*math.cos(heading), cords[1] - 50*math.sin(heading)))
        if objtype == "missile":
            cords = (x - my_x_client + W/2, H-y -my_y_client + H/2)

            obj_surf = pygame.transform.rotate(missiles[objnum][0][0], heading*180/PI)
            screen.blit(obj_surf, obj_surf.get_rect(center = cords))

            pygame.draw.circle(screen, (0, 0, 255), cords, 10)
            pygame.draw.aaline(screen, (0, 0, 255), cords, (cords[0] + 100*math.cos(heading), cords[1] - 100*math.sin(heading)))
        
        if objtype == "radar_data" and objnum == index:
            found_rdr_targets.append([x, y, heading, rdr_mode])
    
    # font = pygame.font.Font(None, 24)
    # text = font.render("x, y, heading: {:.1f}, {:.1f}, {:.1f}".format(my_x, my_y, my_heading), True, (255, 255, 255))
    # screen.blit(text, (10, 10 + 40))
    # text = font.render("index: {:.1f}".format(index), True, (255, 255, 255))
    # screen.blit(text, (10, 10 + 60))

    draw_interface(screen, [my_x, my_y, my_heading, my_rdr_mode, my_rdr_angle, my_rdr_range], found_rdr_targets)

    pygame.display.update()
    ################

def decode_state(msg):
    # decoding header
    global game_objects
    magic, nobjects, tm = struct.unpack("<4sii", msg[:12])
    msg = msg[12:]

    # print(msg)
    # print("message[12:]: ", msg[12:])
    # print(magic, nobjects, tm)

    # print("Time %d objects %d" %(tm, nobjects))

    x = y = heading = 0
    my_x = my_y = my_heading = my_rdr_mode = my_rdr_angle = my_rdr_range = 0
    game_objects = []
    
    for i in range(nobjects):
        num, status, x, y, heading, rdr_mode, rdr_angle, rdr_range = struct.unpack("<IiiifIfI", msg[:32])
        heading = heading%(2*PI)
        #rdr_angle = -rdr_angle
        objtype = 'player' if (0b10000000000000000 & num) else 'missile' if (0b01000000000000000 & num) else 'radar_data' if (0b00100000000000000 & num) else 'unknown'
        objnum =  0b00011111111111111 & num


        game_objects.append([objnum, objtype, status, x, y, heading, rdr_mode, rdr_angle, rdr_range])
        
        if objnum == index and objtype == "player": #должно быть сравнение с собственным id'шником
            my_x, my_y, my_heading, my_rdr_mode, my_rdr_angle, my_rdr_range = x, y, heading, rdr_mode, rdr_angle, rdr_range
        
        
        #print("Object got: %s %d %d %d %d %f %d %f %d" % (objtype, objnum, status, x, y, heading, rdr_mode, rdr_angle, rdr_range))
        #print(f"num is {num}")
        msg = msg[32:]
    
    return (my_x, my_y, my_heading, my_rdr_mode, my_rdr_angle, my_rdr_range)
    

class GameServerProtocol:
    def __init__(self, end_of_game, username):
        self.transport = None
        self.username = username
        self.end_of_game = end_of_game

    def connection_made(self, transport):
        print("Connection made")
        self.transport = transport
        transport.sendto(('CONNECT %s\n' % self.username).encode())

    def datagram_received(self, data, peer):
        global index
        if data.startswith(b"PLAYAS"):
            print("OK, starting game")
            begin, b_index = data.split()
            index = int(b_index)
            print(index)
            
            
        elif data.startswith(b"NO VACANCY"):
            print("No such vacancy, please start with another username")
            self.end_of_game.set_result(True)
        elif data.startswith(b"STAT"):
            # state block got
            dt = decode_state(data)
            game_step(self.transport, dt)

    def connection_lost(self, exc):
        print("Connection lost: %s" % exc)
        self.end_of_game.set_result(True)


if __name__ == '__main__':
    asyncio.run(main())

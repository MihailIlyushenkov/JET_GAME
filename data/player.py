import pygame
import math
from data.weapons import *
from data.radar import *
from data.mygroup import ExtendedGroup

PI = math.pi

def sub_tuple(a: tuple, b: tuple):
    if len(a) == len(b):
       return tuple(a[i] - b[i] for i in range(len(a)))
    else:
        raise IndexError("different sizes of objects")

class player(pygame.sprite.Sprite):
    #settings = (best_pref_speed, thrust_coeff, turn_coeff)
    def __init__(self, mesh: list[pygame.Surface], start: tuple, weapons: armament, team: int, settings: tuple):
        pygame.sprite.Sprite.__init__(self)
        self.mesh = mesh
        self.image_ref = mesh[0]
        self.image = self.image_ref
        self.rect = self.image.get_rect(center = start)
        self.team = team

        self.center = list(start) #координаты
        self.angle = 0 #heading in radians
        self.speed = 0 #скорость
        self.thrust = 0 #тяга
        self.hit = False
        self.active = True
        self.time = 0
        
        self.locked = False

        self.weapons = weapons #armament class
        self.best_pref_speed, self.thrust_coeff, self.turn_coeff = settings #other parametrs
        if self.team == 0:
            self.rdr = radar(self, pygame.image.load("data/assets/radarbeam.png"), ((1000, 3000, 5000), (30, 45, 60), 1))
        else:
            self.rdr = None

    def update(self, *args):
        turn = args[0]
        throttle = args[1]
        all_objects = args[2]


        if self.hit:
            self.time += 1
            if self.time >= 300:
                self.active = False
            return None

        throttle_up, throttle_down = throttle
        if (throttle_up + throttle_down)%2:
            if throttle_up and (self.thrust <= 99):
                self.thrust += 1
            elif throttle_down and (self.thrust > 0):
                self.thrust -= 1
        
        self.speed = 10*self.thrust/100
        #обработка поворота
        turn_left, turn_right = turn

        #смещение
        #rect.move_ip не используем, т.к. координаты центра rect - int'ы, 
        #но нужен более точный подсчет в float для небольших углов self.angle
        self.center[0] +=  math.cos(self.angle)*self.speed
        self.center[1] += -math.sin(self.angle)*self.speed
        self.rect.center = self.center

        #поворот
        if (turn_left + turn_right)%2:
            self.angle = (self.angle + (turn_left - turn_right)*self.turn_coeff)%(2*PI)
            self.image = pygame.transform.rotate(self.image_ref, (self.angle * 180 / PI))
            self.rect = self.image.get_rect(center = self.center)
        
        if self.rdr:
            self.rdr.update(all_objects)
    
    def __repr__(self):
        #return f"cords: {self.rect.center}, thrust: {self.thrust}, speed: {self.speed}, angle: {self.angle}"
        return f"player with cords {self.rect.center}, mesh: {self.mesh}, settings: {self.best_pref_speed, self.thrust_coeff, self.turn_coeff}, armament: {self.weapons}"

    def shoot(self, target, proj_array: pygame.sprite.Group):
        missle = self.weapons.shoot(self, target)
        if missle != None: 
            proj_array.add(missle)
            print("LAUNCHED!!!!!!")

    def switch_weapon(self):
        self.weapons.switch_weapon()

    def illuminate(self, switch: bool):
        self.locked = switch

    def is_illuminated(self):
        return self.locked

    def gethit(self):
        self.hit = True
        self.time = 0
        self.image_ref = self.mesh[1]
        self.image = self.image_ref
        self.rect = self.image.get_rect(center = self.center)
        self.speed = 0

    def display(self, surface: pygame.surface, angle, position: tuple, status):
        mesh = 0
        if (status == 1):
            mesh = pygame.transform.rotate(self.mesh[0], angle*180/PI)
        elif(status == 2):
            mesh = pygame.transform.rotate(self.mesh[1], angle*180/PI)
        else:
            pygame.draw.circle(surface, (255, 255, 255), position, 15)
        
        if mesh:
            surface.blit(mesh, mesh.get_rect(center = position))

    def draw(self, surface: pygame.surface, offset = (0,0)):
        #print(self.rect.move(-offset[0], -offset[1]).center)
        if self.active: 
            #surface.blit(self.image, self.image.get_rect(center = (self.center[0]-offset[0], self.center[1]-offset[1])))
            surface.blit(self.image, self.image.get_rect(center = sub_tuple(self.center, offset)))
            pygame.draw.aaline(surface, (0,255,0), (self.center[0] - offset[0], self.center[1] - offset[1]), 
                                (self.center[0] + math.cos(self.angle)*150 - offset[0],
                                 self.center[1] - math.sin(self.angle)*150 - offset[1]))
            if self.rdr:
                self.rdr.draw(surface, offset)

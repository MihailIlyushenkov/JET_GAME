import pygame
import math
import time

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


class armament():
    def __init__(self, data: dict) -> None:
        self.types = list(data.keys())
        self.chosen_weapon = self.types[0]
        self.chosen_index = 0
        self.weapons_parameters = data #dictionary: missle_name: [ammo_count, [meshes], [weapon_init_parameters]]
        self.total = sum([i[0] for i in self.weapons_parameters.values()])

    def shoot(self, carrier, target):
        if hasattr(carrier, "angle") and hasattr(carrier, "speed") and hasattr(carrier, "center"):
            if hasattr(target, "center") or isinstance(target, (tuple, list)) or (target == None):
                if self.weapons_parameters[self.chosen_weapon][0] > 0:
                    self.weapons_parameters[self.chosen_weapon][0] -= 1
                    self.total -= 1
                    return missle(self.weapons_parameters[self.chosen_weapon][1],
                                    self.weapons_parameters[self.chosen_weapon][2], 
                                        carrier, target) #вернуть экземпляр класса missle
                else:
                    print("out of this missle type")
            else:
                raise TypeError("Invalid target -> cant spawn weapon")
        else:
            raise TypeError("Invalid weapon carrier -> cant spawn weapon")
    
    def switch_weapon(self):
        self.chosen_index = (self.chosen_index + 1)%len(self.types)
        self.chosen_weapon = self.types[self.chosen_index]

    def info(self):
        return self.chosen_weapon + f" {self.weapons_parameters[self.chosen_weapon][0]}/{self.total}"


    def __repr__(self) -> str:
        data = [[i, self.weapons_parameters[i][0]] for i in self.types]
        return f"{data}"


class missle(pygame.sprite.Sprite):
    def __init__(self, mesh: list[pygame.surface.Surface], settings: tuple, carrier, target = None):
        pygame.sprite.Sprite.__init__(self)
        self.mesh = mesh
        self.image_ref = mesh[0]
        self.image = pygame.transform.rotate(self.image_ref, carrier.angle)
        self.rect = self.image.get_rect(center = carrier.center)

        self.center = list(carrier.center) #координаты
        self.angle = carrier.angle #heading in radians
        self.speed = carrier.speed #скорость
        self.team = carrier.team #команда -> ракета не взаимодействует с объектами своей команды
        self.thrust = 0 #тяга
        
        self.mesh_index = 0
        self.time = 0 #lifetime in ticks (1 second = 1tick * FPS)
        self.hit = False
        self.active = True

        self.target = target
        self.turn_coeff, self.maxlifetime, self.enginedelay, self.booster_time, self.booster_force, self.sustainer_time, self.sustainer_force, self.drag_coeff, self.type = settings #other parametrs
        #в файле записаны длительности работы бустера и сустейнера -> но мы хотим получить значения концов их работы в отсчете от старта.
        self.booster_time += self.enginedelay
        self.sustainer_time += self.booster_time

        #print(self.turn_coeff, self.maxlifetime, self.enginedelay, self.booster_time, self.booster_force, self.sustainer_time, self.sustainer_force, self.drag_coeff)

    def move_to_point(self, cords: tuple):
        #поворот в поинт (для одного кадра)
        
        x = cords[0] - self.center[0]
        y = cords[1] - self.center[1]

        tar_angle = get_angle(x, y)
        cur_angle = self.angle 
        
        offset = 0
        diff = sub_angle(cur_angle, tar_angle)
        
        if diff == 0:
            offset = 0
        elif abs(diff) <= self.turn_coeff:
            offset = diff
        else:
            offset = self.turn_coeff if diff > 0 else -self.turn_coeff
        
        if offset != 0:
            self.angle = (self.angle + offset)%(PI*2)
            #self.image = pygame.transform.rotate(self.image_ref, (self.angle * 180 / PI))
            #self.rect = (self.image).get_rect(center = self.center)
    
    def navigate_to_target(self, target = None):
        if target == None:
            target = self.target
            if self.speed <= 0.3 or target == None:
                pass
            elif hasattr(target, "center") and hasattr(target, "speed") and hasattr(target, "angle"):
                appr_time_to_hit = getrange(self.center, target.center)/self.speed
                intersection_point = (target.center[0]
                                    + target.speed*math.cos(target.angle)*appr_time_to_hit,
                                    target.center[1]
                                    - target.speed*math.sin(target.angle)*appr_time_to_hit
                                    )
                self.move_to_point(intersection_point)
                #print("setting point")
                self.int_point = intersection_point
            elif isinstance(target, (tuple, list)):
                self.int_point = (target[0], target[1])
                self.move_to_point(self.int_point)
            else:
                raise AttributeError("object doesn't have center/speed/angle parametr")
        elif isinstance(target, (tuple, list)):
            self.int_point = (target[0], target[1])
            self.move_to_point(self.int_point)
        else:
            raise TypeError("cant navigate to this object")

    #def lock(self, target):
    #    self.target = target

    def gethit(self):
        self.hit = True
        self.active = False
    
    def illuminate(self, switch: bool):
        self.locked = switch

    def is_illuminated(self):
        return self.locked

    def update(self, *args):
        if self.hit:
            return None

        #рассчет ускорения и номера изображения
        if self.enginedelay < self.time <= self.booster_time:
            self.speed += self.booster_force - self.drag_coeff*(self.speed**2)
            self.mesh_index = 1
        elif self.booster_time < self.time < self.sustainer_time:
            self.speed += self.sustainer_force - self.drag_coeff*(self.speed**2)
            self.mesh_index = 2
        else:
            self.speed -= self.drag_coeff*(self.speed**2)
            self.mesh_index = 0

        
        self.image_ref = self.mesh[self.mesh_index]
        
        #доворот до цели
        if self.type == 2 or ((self.target != None) and self.target.is_illuminated()):
            self.navigate_to_target()

        self.time += 1

        self.center[0] +=  math.cos(self.angle)*self.speed
        self.center[1] += -math.sin(self.angle)*self.speed

        #image and rect update
        self.image = pygame.transform.rotate(self.image_ref, (self.angle * 180 / PI))
        self.rect = self.image.get_rect(center = self.center)
    
    def draw(self, surface: pygame.surface, *args): #if offset == None -> draws without offset

        offset = args[0]
        surface.blit(self.image, self.image.get_rect(center = sub_tuple(self.center, offset)))
        
        color = (0, 255, 0) if self.type == 1 else (0, 0, 255)

        if hasattr(self.target, "center") and self.target.is_illuminated():
            pygame.draw.aaline(surface, color, sub_tuple(self.center, offset), sub_tuple(self.target.center, offset))
        elif isinstance(self.target, (tuple, list)):
            pygame.draw.aaline(surface, color, sub_tuple(self.center, offset), sub_tuple((self.target[0], self.target[1]), offset))


        if hasattr(self, "int_point"):
            pygame.draw.circle(surface, (255,255,255), sub_tuple(self.int_point, offset), 5)
    
    def __repr__(self) -> str:
        return f"missle with center = {self.center}, angle = {self.angle}, speed = {self.speed}"

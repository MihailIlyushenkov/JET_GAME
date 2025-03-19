import pygame
import math
from data.weapons import get_angle, sub_angle, missle
from data.mygroup import ExtendedGroup

PI = math.pi

def sign(x):
    return 0 if x == 0 else (1 if x > 0 else -1)

def get_range(cords1: tuple, cords2: tuple):
    return math.sqrt((cords1[0] - cords2[0])**2 + (cords1[1] - cords2[1])**2)

def in_cone(cone_top, cone_global_angle, cone_hetigt, cone_angle, tcords):
    tx = tcords[0]
    ty = tcords[1]
    if get_range(cone_top, (tx, ty)) <= cone_hetigt:
        if abs(sub_angle(cone_global_angle, get_angle(tx - cone_top[0], ty-cone_top[1]))) <= (cone_angle):
            return True
        else: 
            #print(abs(sub_angle(cone_angle, get_angle(tx - cone_top[0], ty-cone_top[1])))*180/PI)
            #print(cone_angle)
            return False
    else: 
        return False

class radar(pygame.sprite.Sprite):
    def __init__(self, owner, array_image: pygame.surface.Surface, settings) -> None:
        if hasattr(owner, "center") and hasattr(owner, "angle"):
            pygame.sprite.Sprite.__init__(self)
            self.owner = owner
            self.image_ref = array_image
            self.image = self.image_ref

            self.array_angle = 0
            self.range_list, self.fow_list, self.scan_speed = settings
            self.on = True
            self.mode = "SRC" #can be SRC, LCK, TRC

            self.fow_list = tuple(i*PI/180 for i in self.fow_list)
            self.fow_index = 0
            self.fow = self.fow_list[0]
            self.gimbal_limit = max(self.fow_list)

            self.scan_speed = self.scan_speed*(2*PI)/180
            
            self.range = self.range_list[0]
            self.range_index = 0
            

            self.dir = 1

            self.found_obj = []
            self.found_obj_parm = []
            self.found_obj_old = []
            self.found_obj_parm_old = []

            self.target_to_lock = None

            self.locked = None

        else: 
            raise TypeError(f"object {owner} cant be owner of radar")
        


    def update(self, all_objects):
        self.center = self.owner.center

        if self.on == False:
            return
        
        if self.mode == "SRC":
            prob = self.array_angle + self.scan_speed*self.dir
                    
            if isinstance(all_objects[0], list) and isinstance(all_objects[1], ExtendedGroup):
                other_obj = [*list(filter(lambda x: x != self.owner, all_objects[0])), *all_objects[1]]

            if abs(prob) <= self.fow:
                self.array_angle = prob 
            else:
                self.dir = self.dir * (-1)
                self.array_angle = self.fow * sign(self.array_angle) + self.scan_speed*self.dir
                
                if not(self.target_to_lock in self.found_obj):
                    if self.found_obj == []:
                        self.target_to_lock = None
                    else:
                        self.target_to_lock = self.found_obj[0]
                    
                self.found_obj_old = self.found_obj
                self.found_obj_parm_old = self.found_obj_parm
                
                self.found_obj_parm = []
                self.found_obj = []
                
            

            found = list(filter(lambda x: x.active and in_cone(self.center, (self.owner.angle - self.array_angle )%(2*PI), 
                                                self.range, 2*PI/180, x.center), other_obj))
            for i in found:
                if not(i in self.found_obj):
                    self.found_obj.append(i)
                    self.found_obj_parm.append([get_range(self.center, i.center), 
                                            sub_angle(self.owner.angle, get_angle(i.center[0] - self.center[0], i.center[1]- self.center[1]))])
        elif self.mode == "TRC":
            self.array_angle = -sub_angle(self.owner.angle, get_angle(self.locked.center[0] - self.center[0], self.locked.center[1]- self.center[1]))
            if abs(self.array_angle) > self.gimbal_limit:
                self.mode = "SRC"
                self.array_angle = 0
                self.locked.illuminate(False)
                self.locked = None

    def switch_fow(self):
        self.fow_index = (self.fow_index + 1)%len(self.fow_list)
        self.fow = self.fow_list[self.fow_index]

        self.clear_search_data()

    def switch_range(self):
        self.range_index = (self.range_index + 1)%len(self.range_list)
        self.range = self.range_list[self.range_index]

        self.clear_search_data()
    
    def choose_target(self):
        if self.target_to_lock == None:
            if len(self.found_obj_old) != 0:
                self.target_to_lock = self.found_obj[0]
        else:
            if self.target_to_lock in self.found_obj_old:
                self.target_to_lock = self.found_obj_old[(self.found_obj_old.index(self.target_to_lock) + 1)%len(self.found_obj_old)]

    def try_lock(self):
        if self.mode == "SRC":
            if self.target_to_lock and in_cone(self.center, self.owner.angle, self.range, self.fow, self.target_to_lock.center):
                self.mode = "TRC"
                self.locked = self.target_to_lock
                self.locked.illuminate(True)
                self.array_angle = sub_angle(self.owner.angle, get_angle(self.locked.center[0] - self.center[0], self.locked.center[1]- self.center[1]))
            else:
                self.array_angle = 0

        elif self.mode == "TRC":
            self.mode = "SRC"
            self.locked.illuminate(False)
            self.locked = None
            self.array_angle = 0

        self.clear_search_data()
                    

    def get_mode(self):
        return (self.mode, self.range, self.fow, self.gimbal_limit, self.array_angle)
    
    def get_found(self):
        return [self.found_obj_old, self.found_obj_parm_old]

    def get_marked_for_lock(self):
        if self.target_to_lock:
            return [self.target_to_lock]
        return []
    
    def get_locked(self):
        return self.locked

    def get_locked_param(self):
        return [[ get_range(self.center, i.center),
                  sub_angle(self.owner.angle, get_angle(i.center[0] - self.center[0], i.center[1]- self.center[1]))
                ] for i in [self.locked]]

    def switch(self):
        if self.on and self.mode == "SRC":
            self.on = False
            self.clear_search_data()
            self.locked = None
        else:
            self.on = True

    def clear_search_data(self):
        self.target_to_lock = None
        self.found_obj = []
        self.found_obj_old = []
        self.found_obj_parm = []
        self.found_obj_parm_old = []

    def draw(self, surface: pygame.surface.Surface, offset):
        if self.on:

            x = self.center[0] - offset[0]
            y = self.center[1] - offset[1]
            
            #print(self.array_angle*180/PI)

            glob_angle = (self.array_angle - self.owner.angle)%(2*PI)
            rng = self.range if self.mode == "SRC" else get_range(self.center, self.locked.center)
            pygame.draw.aaline(surface, (0, 255, 0), (x,  y), (x + rng*math.cos(glob_angle), y + rng*math.sin(glob_angle)))

            for i in self.found_obj:
                if isinstance(i, missle):
                    pygame.draw.aaline(surface, (255,0,0), (x, y), (i.center[0] - offset[0], i.center[1] - offset[1]))
                else:
                    if i.team == 0:
                        pygame.draw.aaline(surface, (0,0,255), (x, y), (i.center[0] - offset[0], i.center[1] - offset[1]))
                    else:
                        pygame.draw.line(surface, (255,0,255), (x, y), (i.center[0] - offset[0], i.center[1] - offset[1]), 5)
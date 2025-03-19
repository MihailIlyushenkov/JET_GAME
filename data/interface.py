import pygame
import math
from data.player import player
from data.radar import radar
from data.mygroup import camera
from data.weapons import missle, armament

pygame.font.init()
PI = math.pi
SQRT2 = math.sqrt(2)

def draw_edges(surface: pygame.surface.Surface, color: tuple, center: tuple, sqsize, linesize):
    pygame.draw.aalines(surface, color, False, 
                        [(center[0] - SQRT2*sqsize/2, center[1] - SQRT2*sqsize/2 + linesize), 
                        (center[0] - SQRT2*sqsize/2, center[1] - SQRT2*sqsize/2), 
                        (center[0] - SQRT2*sqsize/2 + linesize, center[1] - SQRT2*sqsize/2)])
    
    pygame.draw.aalines(surface, color, False, 
                        [(center[0] + SQRT2*sqsize/2 - linesize, center[1] - SQRT2*sqsize/2), 
                        (center[0] + SQRT2*sqsize/2, center[1] - SQRT2*sqsize/2), 
                        (center[0] + SQRT2*sqsize/2, center[1] - SQRT2*sqsize/2 + linesize)])

    pygame.draw.aalines(surface, color, False, 
                        [(center[0] + SQRT2*sqsize/2 - linesize, center[1] + SQRT2*sqsize/2),
                        (center[0] + SQRT2*sqsize/2, center[1] + SQRT2*sqsize/2),
                        (center[0] + SQRT2*sqsize/2, center[1] + SQRT2*sqsize/2 - linesize)])
    
    pygame.draw.aalines(surface, color, False, 
                    [(center[0] - SQRT2*sqsize/2, center[1] + SQRT2*sqsize/2 - linesize),
                    (center[0] - SQRT2*sqsize/2, center[1] + SQRT2*sqsize/2),
                    (center[0] - SQRT2*sqsize/2 + linesize, center[1] + SQRT2*sqsize/2)]) 

class interface():
    def __init__(self, W, H, cam: camera):
        self.camera = cam
        self.W = W
        self.H = H
        self.font = pygame.font.Font(None, 24)

    def draw(self, surface: pygame.surface.Surface):
        data_object = self.camera.following

        if isinstance(data_object, (player, missle)):
            offset = self.camera.get_offset()
            center = data_object.center
            #line_conut = 0
            x0 = center[0] - offset[0] - self.W/2
            y0 = center[1] - offset[1] - self.H/2

            text = self.font.render("(x,y): ({:.1f},{:.1f})".format(data_object.center[0], data_object.center[1]), True, (255, 255, 255))
            surface.blit(text, (x0+10, y0+10))

            text = self.font.render("speed: {:.1f}".format(data_object.speed), True, (255, 255, 255))
            surface.blit(text, (x0+10, y0 +10 + 20))

            text = self.font.render("heading: {:.1f}".format(data_object.angle*180/PI), True, (255, 255, 255))
            surface.blit(text, (x0+10, y0 +10 + 40))

            if hasattr(data_object, "weapons"):
                if isinstance(data_object.weapons, armament):
                    text = self.font.render(data_object.weapons.info(), True, (255, 255, 255))
            else:
                text = self.font.render("no weapons", True, (255, 255, 255))
            surface.blit(text, (x0+10, y0 +10 + 60))


            if hasattr(data_object, "rdr"):
                if data_object.rdr:
                    rscreen_H = rscreen_W = self.H/3
                    top_x = x0 + self.W - rscreen_W
                    top_y = y0 + self.H - rscreen_H
                    pygame.draw.rect(surface, (0,255,0), 
                                    (top_x, top_y, rscreen_W, rscreen_H), 5)
                    mode, rng, fow, gim_limit, arrangle = data_object.rdr.get_mode()

                    text = self.font.render(mode, True, (0, 255, 0))
                    surface.blit(text, (top_x + rscreen_W/2 - 5, top_y - 20))

                    text = self.font.render(f"{rng}", True, (0,255,0))
                    surface.blit(text, (top_x + rscreen_W - 60, top_y - 20))
                    
                    if mode == "SRC":
                        text = self.font.render("{:.0f}".format(-fow*180/PI), True, (0,255,0))
                        surface.blit(text, (top_x + 10, top_y + 10))

                        text = self.font.render("{:.0f}".format(fow*180/PI), True, (0,255,0))
                        surface.blit(text, (top_x + rscreen_W - 30, top_y + 10))

                        pygame.draw.aaline(surface, (0,255,0), 
                                        (top_x + rscreen_W/2 + arrangle/fow*(rscreen_W/2), top_y),
                                            (top_x + rscreen_W/2 + arrangle/fow*(rscreen_W/2), top_y+rscreen_H),
                                        )
                        found_data = data_object.rdr.get_found()
                        
                        obj = found_data[0]
                        params = found_data[1]

                        #print(f"TARGETS: {obj}")
                        #print(f"PARAMS: {params}\n")

                        for i in params:
                            pygame.draw.circle(surface, (0, 255, 0), 
                                                (top_x - i[1]/fow*rscreen_W/2 + rscreen_W/2, top_y + (1 - i[0]/rng)*rscreen_H ), 5)

                        for i in data_object.rdr.get_marked_for_lock():
                            if i in obj:
                                iparams = params[obj.index(i)]
                                print(f"PARAMETERS = {iparams}\n")
                                center = (top_x - iparams[1]/fow*rscreen_W/2 + rscreen_W/2, top_y + (1 - iparams[0]/rng)*rscreen_H) 
                                draw_edges(surface, (255, 0, 0), center, 20, 7)
                    elif mode == "TRC":
                        text = self.font.render("{:.0f}".format(-gim_limit*180/PI), True, (0,255,0))
                        surface.blit(text, (top_x + 10, top_y + 10))

                        text = self.font.render("{:.0f}".format(gim_limit*180/PI), True, (0,255,0))
                        surface.blit(text, (top_x + rscreen_W - 30, top_y + 10))


                        params = data_object.rdr.get_locked_param()
                        for i in params:
                            if (i[0]/rng) < 1:
                                pygame.draw.circle(surface, (0, 255, 0), 
                                                    (top_x - i[1]/gim_limit*rscreen_W/2 + rscreen_W/2, top_y + (1 - i[0]/rng)*rscreen_H), 5)
                            
                            pygame.draw.aaline(surface, (0, 255, 0), 
                                               (top_x - i[1]/gim_limit*rscreen_W/2 + rscreen_W/2, top_y + max(1 - i[0]/rng, 0)*rscreen_H), ((top_x - i[1]/gim_limit*rscreen_W/2 + rscreen_W/2, top_y + rscreen_H)))


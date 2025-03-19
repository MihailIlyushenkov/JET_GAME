import pygame

class ExtendedGroup(pygame.sprite.Group):
    def draw(self, surface: pygame.surface, *args):
        for spr in self.sprites():
            spr.draw(surface, *args)
        a = pygame.sprite.Group()
    
    def filterinactive(self):
        badsprites = filter(lambda x: not((x.active)) if hasattr(x, "active") else False, self.sprites())
        self.remove(badsprites)

    def update(self, *args):
        for spr in self.sprites():
            spr.update(args)
    
    def __getitem__(self, index):
        return self.sprites()[index]
    
    def values(self):
        return self.sprites()


class camera():
    def __init__(self, tar_object, place: tuple):
        self.following = tar_object
        
        if hasattr(tar_object, "center"):
            self.obj_center = tar_object.center
        elif isinstance(tar_object, tuple):
            self.obj_center = tar_object
        else:
            raise TypeError(f"Cant follow object {self.following}")
        self.place_on_screen = place
    
    def get_offset(self):
        if hasattr(self.following, "center"):
            self.obj_center = self.following.center
        elif isinstance(self.following, (tuple, list)):
            self.obj_center = self.following 
        
        return (self.obj_center[0] - self.place_on_screen[0],self.obj_center[1] - self.place_on_screen[1])

    def change_following(self, tar_obj):
        self.following = tar_obj


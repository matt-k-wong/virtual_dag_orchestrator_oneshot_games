# game.py
import sys, subprocess, math, random, time

try:
    import pygame
except:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame-ce"])
    import pygame

pygame.init()
WIDTH, HEIGHT = 960, 540
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

def project(x, y, z):
    scale = 300 / (z + 0.1)
    return int(WIDTH//2 + x*scale), int(HEIGHT//2 + y*scale), scale

class Player:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.cooldown = 0

    def update(self, keys):
        speed = 0.05
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: self.x -= speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.x += speed
        if keys[pygame.K_UP] or keys[pygame.K_w]: self.y -= speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: self.y += speed
        self.x = max(-1, min(1, self.x))
        self.y = max(-1, min(1, self.y))
        if self.cooldown > 0: self.cooldown -= 1

    def shoot(self):
        if self.cooldown == 0:
            self.cooldown = 10
            return Bullet(self.x, self.y, 1)
        return None

    def draw(self):
        px, py, s = project(self.x, self.y, 1)
        pygame.draw.polygon(screen, (0,255,255),
            [(px,py-10),(px-5,py+10),(px+5,py+10)])

class Enemy:
    def __init__(self):
        self.x = random.uniform(-1,1)
        self.y = random.uniform(-1,1)
        self.z = random.uniform(5,10)

    def update(self, speed):
        self.z -= speed

    def draw(self):
        px, py, s = project(self.x, self.y, self.z)
        size = int(20*s/100)
        pygame.draw.rect(screen,(255,0,255),(px-size//2,py-size//2,size,size))

class Bullet:
    def __init__(self,x,y,z):
        self.x=x; self.y=y; self.z=z

    def update(self):
        self.z += 0.3

    def draw(self):
        px,py,s=project(self.x,self.y,self.z)
        pygame.draw.circle(screen,(255,255,0),(px,py),3)

class Particle:
    def __init__(self,x,y):
        self.x=x; self.y=y
        self.vx=random.uniform(-0.02,0.02)
        self.vy=random.uniform(-0.02,0.02)
        self.life=30

    def update(self):
        self.x+=self.vx
        self.y+=self.vy
        self.life-=1

    def draw(self):
        px,py,_=project(self.x,self.y,1)
        pygame.draw.circle(screen,(255,100,0),(px,py),2)

def reset():
    return Player(),[],[],[],0,0,False

player,enemies,bullets,particles,score,timer,gameover = reset()

while True:
    dt = clock.tick(60)/1000
    screen.fill((10,10,20))

    for e in pygame.event.get():
        if e.type==pygame.QUIT: pygame.quit(); sys.exit()
        if e.type==pygame.KEYDOWN:
            if e.key==pygame.K_ESCAPE: pygame.quit(); sys.exit()
            if e.key==pygame.K_r and gameover:
                player,enemies,bullets,particles,score,timer,gameover = reset()

    keys = pygame.key.get_pressed()

    if not gameover:
        player.update(keys)
        if keys[pygame.K_SPACE]:
            b=player.shoot()
            if b: bullets.append(b)

        timer += dt
        spawn_rate = min(2, 0.5 + timer*0.05)
        if random.random() < spawn_rate*dt:
            enemies.append(Enemy())

        for en in enemies[:]:
            en.update(0.05 + timer*0.01)
            if en.z < 0.5:
                gameover=True
            if abs(en.x-player.x)<0.1 and abs(en.y-player.y)<0.1 and en.z<1:
                gameover=True

        for b in bullets[:]:
            b.update()
            if b.z>10: bullets.remove(b)

        for en in enemies[:]:
            for b in bullets[:]:
                if abs(en.x-b.x)<0.1 and abs(en.y-b.y)<0.1 and abs(en.z-b.z)<0.5:
                    enemies.remove(en)
                    bullets.remove(b)
                    score+=100
                    for _ in range(10):
                        particles.append(Particle(en.x,en.y))
                    break

        for p in particles[:]:
            p.update()
            if p.life<=0: particles.remove(p)

    for en in enemies: en.draw()
    for b in bullets: b.draw()
    for p in particles: p.draw()
    player.draw()

    font = pygame.font.SysFont(None,30)
    txt = font.render(f"Score: {score}",True,(0,255,200))
    screen.blit(txt,(10,10))

    if gameover:
        t2 = font.render("GAME OVER - Press R",True,(255,50,50))
        screen.blit(t2,(WIDTH//2-120,HEIGHT//2))

    pygame.display.flip()

import pygame
import math
import random
import sys
import subprocess

# --- Auto-install bootstrap ---
def bootstrap():
    try:
        import pygame
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame-ce"])
        import pygame

bootstrap()

# --- Constants ---
WIDTH, HEIGHT = 1280, 720
FPS = 60
FOV = 400
MAX_SPEED = 50
ACCEL = 0.005
ROT_SPEED = 3.0
COLOR_BG = (10, 10, 25)
COLOR_CYAN = (0, 255, 255)
COLOR_MAGENTA = (255, 0, 255)
COLOR_LIME = (50, 255, 50)
COLOR_WHITE = (255, 255, 255)

class Camera:
    def __init__(self):
        self.pitch = 0.0
        self.roll = 0.0
        self.x = 0
        self.y = 0
        self.shake = 0

    def project(self, x, y, z):
        # Basic 3D -> 2D projection
        # Apply roll rotation
        rad_roll = math.radians(self.roll)
        rx = x * math.cos(rad_roll) - y * math.sin(rad_roll)
        ry = x * math.sin(rad_roll) + y * math.cos(rad_roll)

        # Apply pitch rotation
        rad_pitch = math.radians(self.pitch)
        # We only rotate around X axis for pitch
        ry = ry * math.cos(rad_pitch) - z * math.sin(rad_pitch)
        rz = ry * math.sin(rad_pitch) + z * math.cos(rad_pitch)
        
        # Recalculate ry after pitch
        ry = ry # simplified

        # Z-Culling
        if rz <= 1: 
            return None

        # Project to screen
        factor = FOV / rz
        sx = int(WIDTH // 2 + rx * factor)
        sy = int(HEIGHT // 2 + ry * factor)
        
        # Add shake
        if self.shake > 0:
            sx += random.randint(-self.shake, self.shake)
            sy += random.randint(-self.shake, self.shake)
            
        return sx, sy

class Entity:
    def __init__(self, x, y, z, size, color, is_gate=False):
        self.x = x
        self.y = y
        self.z = z
        self.size = size
        self.color = color
        self.is_gate = is_gate
        self.vertices = self._generate_vertices()

    def _generate_vertices(self):
        s = self.size / 2
        if self.is_gate:
            # Ring vertices
            verts = []
            for i in range(16):
                ang = math.radians(i * 22.5)
                verts.append((s * math.cos(ang), s * math.sin(ang), 0))
            return verts
        else:
            # Box vertices
            return [
                (-s, -s, -s), (s, -s, -s), (s, s, -s), (-s, s, -s),
                (-s, -s, s), (s, -s, s), (s, s, s), (-s, s, s)
            ]

    def update(self, speed):
        self.z -= speed

    def draw(self, screen, camera):
        # Project vertices
        projected = []
        for vx, vy, vz in self.vertices:
            p = camera.project(self.x + vx, self.y + vy, self.z + vz)
            if p: projected.append(p)
        
        if len(projected) < 2: return

        if self.is_gate:
            # Draw ring as a connected loop
            if len(projected) == 16:
                pygame.draw.polygon(screen, self.color, projected, 2)
        else:
            # Draw box wireframe
            # Edges for a cube
            edges = [
                (0,1), (1,2), (2,3), (3,0), # Back
                (4,5), (5,6), (6,7), (7,4), # Front
                (0,4), (1,5), (2,6), (3,7)  # Connectors
            ]
            for start, end in edges:
                if start < len(projected) and end < len(projected):
                    pygame.draw.line(screen, self.color, projected[start], projected[end], 2)

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("NEON VELOCITY: RIFT PILOT")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 24, bold=True)
        self.reset()

    def reset(self):
        self.camera = Camera()
        self.world_entities = []
        self.speed = 15.0
        self.distance = 0
        self.score = 0
        self.state = "MENU"
        self.spawn_timer = 0
        self.shake_timer = 0

    def spawn_object(self):
        # Randomly choose between Monolith and Gate
        is_gate = random.random() < 0.3
        x = random.uniform(-600, 600)
        y = random.uniform(-400, 400)
        size = random.uniform(80, 200)
        color = COLOR_LIME if is_gate else random.choice([COLOR_CYAN, COLOR_MAGENTA])
        self.world_entities.append(Entity(x, y, 3000, size, color, is_gate))

    def handle_input(self):
        keys = pygame.key.get_pressed()
        # Pitch
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.camera.pitch -= ROT_SPEED * 0.5
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.camera.pitch += ROT_SPEED * 0.5
        
        # Roll
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.camera.roll -= ROT_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.camera.roll += ROT_SPEED

        # Natural centering
        self.camera.pitch *= 0.95
        self.camera.roll *= 0.95

    def update(self):
        if self.state != "PLAYING":
            return

        self.speed += ACCEL
        self.distance += self.speed / 10
        
        # Spawn logic
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.spawn_object()
            self.spawn_timer = max(20, 60 - int(self.speed/2))

        # Update entities
        for e in self.world_entities[:]:
            e.update(self.speed)
            
            # Collision Detection
            if 0 < e.z < 50:
                # Calculate distance from player (0,0,0) relative to camera pitch/roll
                # For simplicity, we check if player is within the entity's bounds
                # Project player into world space or entity into player space
                dist_sq = (e.x)**2 + (e.y)**2
                # Approximate player position based on pitch/roll offset (simulated)
                # In a true sim, player moves. Here, the world moves.
                # We assume the player is at origin, but the "center" of the screen
                # is where the player is looking.
                
                # Simple collision: distance check
                if not e.is_gate:
                    if abs(e.x) < e.size/2 + 20 and abs(e.y) < e.size/2 + 20:
                        self.state = "GAMEOVER"
                        self.camera.shake = 20
                else:
                    if abs(e.x) < e.size and abs(e.y) < e.size:
                        self.score += 100
                        self.speed += 2 # Boost
                        self.camera.shake = 5

            if e.z < -100:
                self.world_entities.remove(e)

        if self.camera.shake > 0:
            self.camera.shake -= 1

    def draw_hud(self):
        # Speedometer
        speed_text = self.font.render(f"VELOCITY: {int(self.speed * 10)} KM/S", True, COLOR_CYAN)
        self.screen.blit(speed_text, (20, 20))
        
        # Distance/Score
        score_text = self.font.render(f"SCORE: {int(self.distance + self.score)}", True, COLOR_MAGENTA)
        self.screen.blit(score_text, (20, 50))
        
        # Crosshair
        cx, cy = WIDTH//2, HEIGHT//2
        pygame.draw.circle(self.screen, COLOR_WHITE, (cx, cy), 10, 1)
        pygame.draw.line(self.screen, COLOR_WHITE, (cx-20, cy), (cx+20, cy), 1)
        pygame.draw.line(self.screen, COLOR_WHITE, (cx, cy-20), (cx, cy+20), 1)

        # Speed lines
        for _ in range(5):
            start = (WIDTH//2, HEIGHT//2)
            angle = random.uniform(0, 2 * math.pi)
            length = random.uniform(100, 400) * (self.speed/15)
            end = (start[0] + math.cos(angle)*length, start[1] + math.sin(angle)*length)
            pygame.draw.line(self.screen, (40, 40, 80), start, end, 1)

    def draw(self):
        self.screen.fill(COLOR_BG)
        
        if self.state == "MENU":
            txt = self.font.render("NEON VELOCITY: RIFT PILOT", True, COLOR_CYAN)
            sub = self.font.render("PRESS ANY KEY TO START", True, COLOR_WHITE)
            self.screen.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2 - 20))
            self.screen.blit(sub, (WIDTH//2 - sub.get_width()//2, HEIGHT//2 + 20))
        
        elif self.state == "PLAYING" or self.state == "GAMEOVER":
            # Draw entities
            for e in self.world_entities:
                e.draw(self.screen, self.camera)
            
            self.draw_hud()
            
            if self.state == "GAMEOVER":
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                overlay.fill((255, 0, 0, 100))
                self.screen.blit(overlay, (0,0))
                txt = self.font.render("SYSTEM CRASHED", True, COLOR_WHITE)
                sub = self.font.render("PRESS SPACE TO REBOOT", True, COLOR_WHITE)
                self.screen.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2 - 20))
                self.screen.blit(sub, (WIDTH//2 - sub.get_width()//2, HEIGHT//2 + 20))

        pygame.display.flip()

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if self.state == "MENU":
                        self.state = "PLAYING"
                    if self.state == "GAMEOVER" and event.key == pygame.K_SPACE:
                        self.reset()
                        self.state = "PLAYING"

            self.handle_input()
            self.update()
            self.draw()
            self.clock.tick(FPS)

if __name__ == "__main__":
    game = Game()
    game.run()


from PIL import Image
import math
import numpy as np


class Vector:
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z

    def __add__(self, other):
        return Vector(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return Vector(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar):
        return Vector(self.x * scalar, self.y * scalar, self.z * scalar)

    def dot(self, other):
        return self.x*other.x + self.y*other.y + self.z*other.z

    def length(self):
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalize(self):
        l = self.length()
        if l == 0: return Vector(0, 0, 0)
        return self * (1.0 / l)

    def __repr__(self):
        return f"Vector3({self.x}, {self.y}, {self.z})"

class Material:
    def __init__(self, diffuse, specular, shininess):
        self.diffuse = diffuse
        self.specular = specular
        self.shininess = shininess


class Light:
    def __init__(self, position, color):
        self.position = position
        self.color = color


class Triangle:
    def __init__(self, v0, v1, v2, n0, n1, n2, material):
        self.v0, self.v1, self.v2 = v0, v1, v2
        self.n0, self.n1, self.n2 = n0, n1, n2
        self.material = material


def barycentric(p, a, b, c):
    denom = (b.y - c.y)*(a.x - c.x) + (c.x - b.x)*(a.y - c.y)
    if denom == 0:
        return -1, -1, -1
    w0 = ((b.y - c.y)*(p.x - c.x) + (c.x - b.x)*(p.y - c.y)) / denom
    w1 = ((c.y - a.y)*(p.x - c.x) + (a.x - c.x)*(p.y - c.y)) / denom
    w2 = 1 - w0 - w1
    return w0, w1, w2


class Renderer:
    def __init__(self, width, height, camera_pos, light):
        self.width = width
        self.height = height
        self.camera_pos = camera_pos
        self.light = light
        self.image = Image.new("RGB", (width, height))
        self.pixels = self.image.load()
        self.zbuffer = [[float('inf')] * width for _ in range(height)]

    def project(self, v):
        x = int((v.x + 1) * self.width / 2)
        y = int((1 - v.y) * self.height / 2)
        return Vector(x, y, v.z)

    def render_triangle(self, tri):
        p0 = self.project(tri.v0)
        p1 = self.project(tri.v1)
        p2 = self.project(tri.v2)

        min_x = max(min(p0.x, p1.x, p2.x), 0)
        max_x = min(max(p0.x, p1.x, p2.x), self.width - 1)
        min_y = max(min(p0.y, p1.y, p2.y), 0)
        max_y = min(max(p0.y, p1.y, p2.y), self.height - 1)

        for y in range(min_y, max_y+1):
            for x in range(min_x, max_x+1):
                w0, w1, w2 = barycentric(Vector(x, y, 0), p0, p1, p2)
                if w0 < 0 or w1 < 0 or w2 < 0:
                    continue

                z = tri.v0.z * w0 + tri.v1.z * w1 + tri.v2.z * w2
                if z > self.zbuffer[y][x]:
                    continue

                self.zbuffer[y][x] = z

                pos = tri.v0 * w0 + tri.v1 * w1 + tri.v2 * w2
                normal = (tri.n0 * w0 + tri.n1 * w1 + tri.n2 * w2).normalize()

                color = self.shade_pixel(pos, normal, tri.material)
                self.pixels[x, y] = (
                    int(color.x * 255),
                    int(color.y * 255),
                    int(color.z * 255)
                )

    def shade_pixel(self, pos, normal, material):
        to_light = (self.light.position - pos).normalize()
        to_view = (self.camera_pos - pos).normalize()

        diff = max(normal.dot(to_light), 0)
        diffuse = material.diffuse * diff

        halfway = (to_light + to_view).normalize()
        spec_angle = max(normal.dot(halfway), 0)
        spec = (spec_angle ** material.shininess)
        specular = material.specular * spec

        color = Vector(
            self.light.color.x * (diffuse.x + specular.x),
            self.light.color.y * (diffuse.y + specular.y),
            self.light.color.z * (diffuse.z + specular.z),
        )

        return Vector(
            min(max(color.x, 0), 1),
            min(max(color.y, 0), 1),
            min(max(color.z, 0), 1),
        )

def vec3_to_np(v):
    return np.array([v.x, v.y, v.z, 1.0])

def np_to_vec3(arr):
    return Vector(arr[0], arr[1], arr[2])

def translate(tx, ty, tz):
    return np.array([
        [1, 0, 0, tx],
        [0, 1, 0, ty],
        [0, 0, 1, tz],
        [0, 0, 0, 1]
    ])

def scale(sx, sy, sz):
    return np.array([
        [sx, 0,  0,  0],
        [0, sy,  0,  0],
        [0,  0, sz,  0],
        [0,  0,  0,  1]
    ])

def rotate_y(theta):
    c = math.cos(theta)
    s = math.sin(theta)
    return np.array([
        [ c, 0, s, 0],
        [ 0, 1, 0, 0],
        [-s, 0, c, 0],
        [ 0, 0, 0, 1]
    ])

def apply_transform(vec3, matrix):
    transformed = matrix @ vec3_to_np(vec3)
    return np_to_vec3(transformed)


if __name__ == "__main__":
    width, height = 400, 400
    camera_pos = Vector(0, 0, 3)
    light = Light(position=Vector(1, 1, 3), color=Vector(1, 1, 1))

    red_material = Material(diffuse=Vector(1, 0, 0), specular=Vector(1, 1, 1), shininess=32)

    base_tri = Triangle(
        Vector(-0.5, -0.5, 0),
        Vector(0.5, -0.5, 0),
        Vector(0, 0.5, 0),
        Vector(0, 0, 1),
        Vector(0, 0, 1),
        Vector(0, 0, 1),
        red_material
    )

    for frame in range(60):
        angle = frame * (2 * math.pi / 60)
        transform = translate(0, 0, 0) @ rotate_y(angle) @ scale(1, 1, 1)

        v0 = apply_transform(base_tri.v0, transform)
        v1 = apply_transform(base_tri.v1, transform)
        v2 = apply_transform(base_tri.v2, transform)
        n0 = apply_transform(base_tri.n0, transform)
        n1 = apply_transform(base_tri.n1, transform)
        n2 = apply_transform(base_tri.n2, transform)

        tri = Triangle(v0, v1, v2, n0.normalize(), n1.normalize(), n2.normalize(), red_material)

        renderer = Renderer(width, height, camera_pos, light)
        renderer.render_triangle(tri)

        filename = f"frames/frame_{frame:03d}.png"
        renderer.image.save(filename)
        print(f"Saved {filename}")

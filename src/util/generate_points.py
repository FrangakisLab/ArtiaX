from chimerax.geometry._geometry import closest_triangle_intercept
from chimerax.geometry import z_align
import numpy as np
import time

def generate_points_in_bbox(session, surface, radius=1, num_pts=100, method='poisson', n_candidates=30):
    if method not in ['poisson', 'uniform', 'regular grid']:
        return
    bbox = surface.bounds()
    xyz_min, xyz_max = bbox.xyz_min, bbox.xyz_max
    if method == 'poisson':
        coords = generate_poisson_disc_pts(radius, xyz_min, xyz_max, n_candidates)
    elif method == 'uniform':
        coords = generate_random_pts(num_pts, xyz_min, xyz_max)
    else:
        coords = generate_regular_grid_pts(num_pts, xyz_min, xyz_max)

    artia = session.ArtiaX
    artia.create_partlist(name=surface.name + " " + method + " particles")
    partlist = artia.partlists.child_models()[-1]
    from chimerax.geometry import translation
    for coord in coords:
        place = translation(coord)
        partlist.new_particle(place, [0, 0, 0], place)


def generate_points_in_surface(session, surface, radius=1, num_pts=100, method='poisson', n_candidates=30):
    if method not in ['poisson', 'uniform', 'regular grid']:
        return
    bbox = surface.bounds()
    xyz_min, xyz_max = bbox.xyz_min, bbox.xyz_max
    if method == 'poisson':
        coords = generate_poisson_disc_pts(radius, xyz_min, xyz_max, n_candidates)
    elif method == 'uniform':
        coords = generate_random_pts(num_pts, xyz_min, xyz_max)
    else:
        coords = generate_regular_grid_pts(num_pts, xyz_min, xyz_max)

    coords_in_surface = []
    for coord in coords:
        if is_point_in_surface(coord, surface.vertices, surface.triangles, xyz_min, xyz_max):
            coords_in_surface.append(coord)

    artia = session.ArtiaX
    artia.create_partlist(name=surface.name + " " + method + " particles inside")
    partlist = artia.partlists.child_models()[-1]
    from chimerax.geometry import translation
    for coord in coords_in_surface:
        place = translation(coord)
        partlist.new_particle(place, [0, 0, 0], place)


def generate_poisson_disc_pts(radius, xyz_min, xyz_max, n_candidates):
    from scipy.stats import qmc
    # The PoissonDisk generates points in a cube that then get scaled up to a rectangular prism. The radius refers to
    # a sphere in the cube, meaning that it will be scaled up to an ellipsoid. The user only enters a radius, so it
    # must be chosen which of the ellipsoids radii will be represented by the one the user has entered. Using the
    # following formula, the smallest ellipsoid radius is the one the user has entered.
    r = radius/min(xyz_max-xyz_min)
    engine = qmc.PoissonDisk(d=3, radius=r, ncandidates=n_candidates)
    samples = engine.fill_space()
    return samples * (xyz_max-xyz_min) + xyz_min


def generate_random_pts(num_total_pts, xyz_min, xyz_max):
    rng = np.random.default_rng()
    lens = xyz_max - xyz_min
    return np.array([[rng.random() * lens[0] + xyz_min[0], rng.random() * lens[1] + xyz_min[1], rng.random() * lens[2] + xyz_min[2]]
                    for i in range(num_total_pts)])


def generate_regular_grid_pts(num_total_pts, xyz_min, xyz_max):
    num_pts_per_axis = int(round(num_total_pts ** (1./3)))
    zz, yy, xx = np.meshgrid(np.linspace(xyz_min[2], xyz_max[2], num_pts_per_axis),
                             np.linspace(xyz_min[1], xyz_max[1], num_pts_per_axis),
                             np.linspace(xyz_min[0], xyz_max[0], num_pts_per_axis), indexing='ij')
    return np.stack((xx, yy, zz), axis=-1).reshape(num_pts_per_axis ** 3, 3)


def is_point_in_surface(point, vertices, triangles, xyz_min, xyz_max):
    closest_side = np.argmin(np.append(point-xyz_min, xyz_max-point))
    end = point.copy()
    end[closest_side % 3] = np.append(xyz_min, xyz_max)[closest_side]

    cti = closest_triangle_intercept
    fraction_of_distance, tnum = cti(vertices, triangles, point, end)

    dist_to_end = end - point
    start = point
    intercepts = 0
    margin = 1.001
    while fraction_of_distance is not None:
        intercepts += 1
        if intercepts > 1000:
            print("TOO MANY INTERSEPTS")
            return False
        start = start + fraction_of_distance*margin*dist_to_end
        dist_to_end = end - start
        fraction_of_distance, tnum = cti(vertices, triangles, start, end)
    return bool(intercepts % 2)


def generate_points_on_surface(session, surface, num_pts=100, radius=1, method='poisson'):
    if method not in ['poisson', 'uniform']:
        return

    if method == 'uniform':
        coords = uniform_on_surface(surface, num_pts)
    else:
        coords = poisson_on_surface(surface, radius)

    artia = session.ArtiaX
    artia.create_partlist(name="Particles on " + surface.name + " " + method)
    partlist = artia.partlists.child_models()[-1]
    from chimerax.geometry import translation
    for coord in coords:
        place = translation(coord)
        partlist.new_particle(place, [0, 0, 0], place)

    return partlist


def uniform_on_surface(surface, num_pts):
    verts, tris = surface.vertices, surface.triangles
    from chimerax.surface import surface_area
    tri_areas = [surface_area(verts, [tri]) for tri in tris]
    max_area = max(tri_areas)
    coords = np.zeros((num_pts, 3))
    for j in range(num_pts):
        while True:
            i = np.random.randint(0, len(tris))
            val = np.random.random()
            if val < tri_areas[i]/max_area:
                coords[j] = generate_point_on_tri(verts[tris[i]])
                break
    return coords


def generate_point_on_tri(verts):
    a, b = verts[1]-verts[0], verts[2]-verts[0]
    u1, u2 = np.random.random(), np.random.random()
    if u1 + u2 > 1:
        u1, u2 = 1 - u1, 1-u2
    return verts[0] + u1*a + u2*b


def poisson_on_surface(surface, radius):
    # Ugh hard... maybe https://sci-hub.ru/10.1109/TVCG.2012.34 or https://dl.acm.org/doi/pdf/10.1145/3233310 (try the latter one first)
    pass
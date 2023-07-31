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

    create_partlist_from_coords(session, surface.name + " " + method + " particles", coords)


def generate_points_in_surface(session, surface, radius=100, num_pts=100, method='poisson', n_candidates=30):
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

    create_partlist_from_coords(session, surface.name + " " + method + " particles inside", coords_in_surface)


def generate_poisson_disc_pts(radius, xyz_min, xyz_max, n_candidates):
    from scipy.stats import qmc
    # The PoissonDisk generates points in a cube that then get scaled up to a rectangular prism. The radius refers to
    # a sphere in the cube, meaning that it will be scaled up to an ellipsoid. The user only enters a radius, so it
    # must be chosen which of the ellipsoids radii will be represented by the one the user has entered. Using the
    # following formula, the smallest ellipsoid radius is the one the user has entered.

    r = float(radius)/min(xyz_max-xyz_min)
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


def create_partlist_from_coords(session, name, points, using_points=False):
    artia = session.ArtiaX
    artia.create_partlist(name=name)
    partlist = artia.partlists.child_models()[-1]
    from chimerax.geometry import translation
    if using_points:
        for point in points:
            place = translation(point.coord)
            partlist.new_particle(place, [0, 0, 0], point.rotation)
    else:
        coords = points
        for coord in coords:
            place = translation(coord)
            partlist.new_particle(place, [0, 0, 0], place)

    return partlist


class Point:
    def __init__(self, coord, rotation):
        self.coord = coord
        self.rotation = rotation


def generate_points_on_surface(session, surface, num_pts=100, radius=10, method='poisson', oV=10):
    if method not in ['poisson', 'uniform']:
        return

    if method == 'uniform':
        points = uniform_on_surface(surface, num_pts)
    else:
        points = poisson_on_surface(surface, radius, num_pts, oV)

    create_partlist_from_coords(session, "Particles on " + surface.name + " " + method, points, using_points=True)


def uniform_on_surface(surface, num_pts):
    # Using the unbiased sampling (version 2) from https://vcg.isti.cnr.it/Publications/2012/CCS12/TVCG-2011-07-0217.pdf
    verts, tris, norms = surface.vertices, surface.triangles, surface.normals
    from chimerax.surface import surface_area
    from chimerax.geometry import z_align
    tri_areas = [surface_area(verts, [tri]) for tri in tris]
    max_area = max(tri_areas)
    points = []
    for j in range(num_pts):
        while True:
            i = np.random.randint(0, len(tris))
            val = np.random.random()
            if val < tri_areas[i]/max_area:
                coord = generate_point_on_tri(verts[tris[i]])
                normal = norms[tris[i]].mean(0)
                rotation = z_align(coord, coord + normal).zero_translation().inverse()
                points.append(Point(coord, rotation))
                break
    return points


def generate_point_on_tri(verts):
    a, b = verts[1]-verts[0], verts[2]-verts[0]
    u1, u2 = np.random.random(), np.random.random()
    if u1 + u2 > 1:
        u1, u2 = 1 - u1, 1-u2
    return verts[0] + u1*a + u2*b


def poisson_on_surface(surface, radius, num_pts, oV=10):
    # Using the Constrained Sample-Based Poisson-Disk Sampling from https://vcg.isti.cnr.it/Publications/2012/CCS12/TVCG-2011-07-0217.pdf

    # Generate a pool of points using uniform sampling
    sample_pool = uniform_on_surface(surface, num_pts*oV)
    bounds = surface.bounds()
    xyz_min = bounds.xyz_min
    # Sort all the points into cells with side length r
    cells = fill_spacial_hash_table(xyz_min, radius, sample_pool)

    points = []
    while list(cells.values()):
        # Extracting a sample from the dict of potential points
        sample = list(cells.values())[0][0]
        index = np.array(list(cells.keys())[0])
        points.append(sample)
        # Remove all samples within r distance from the chosen sample
        remove_samples(sample, index, radius, cells)
    return points


def fill_spacial_hash_table(xyz_min, side_length, sample_pool):
    from collections import defaultdict
    cells = defaultdict(list)
    for sample in sample_pool:
        index = np.floor((sample.coord - xyz_min)/side_length).astype(int)
        cells[tuple(index)].append(sample)

    return cells


def remove_samples(sample, index, radius, cells):
    from itertools import product
    indices_to_check = [tuple(index + around) for around in product([-1, 0, 1], repeat=3)]
    indices_to_check = [index for index in indices_to_check if (np.asarray(index)>=[0,0,0]).all()]
    for index in indices_to_check:
        cells[index] = [point for point in cells[index] if np.linalg.norm(sample.coord - point.coord) > radius]
        if not cells[index]:
            del cells[index]


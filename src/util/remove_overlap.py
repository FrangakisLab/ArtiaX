from chimerax.geometry._geometry import closest_triangle_intercept
from chimerax.geometry import z_align
import numpy as np
import time

def remove_overlap(session, particles, pls, scms, bounds, method='distance', on_surface_particles=None, in_surface_particles=None, particles_to_keep_still=None, max_iterations=100, num_points=100, move_factor=1, rotate_to_normal=True):
    if method == 'distance':
        calculate_overlap = calculate_overlap_distance
    else:
        calculate_overlap = calculate_overlap_point_volume

    movements = get_movements(calculate_overlap, particles, scms, bounds, on_surface_particles, in_surface_particles, particles_to_keep_still, num_points, move_factor, rotate_to_normal)
    iteration = 0
    while not all(not movement.any() for movement in movements.values()):
        # move all the particles away from each other
        for p in particles:
            p.origin_coord = np.asarray(p.origin_coord) + movements[p]
        for pl in pls:
            pl.update_places()
        session.update_loop.draw_new_frame()
        movements = get_movements(calculate_overlap, particles, scms, bounds, on_surface_particles, in_surface_particles, particles_to_keep_still, num_points, move_factor, rotate_to_normal)
        iteration += 1
        if iteration > max_iterations:
            session.logger.warning("artiax remove overlap: {} iterations reached.".format(max_iterations))
            return


def get_movements(calculate_overlap, particles, scms, bounds, on_surface_particles, in_surface_particles, particles_to_keep_still, num_points, move_factor, rotate_to_normal):
    movements = calculate_overlap(particles, scms, bounds, particles_to_keep_still, num_points, move_factor)
    if on_surface_particles is not None:
        for ps, surface in on_surface_particles:
            movements = project_movements_to_surface(movements, ps, surface, bounds, rotate_to_normal)
    if in_surface_particles is not None:
        for ps, surface in in_surface_particles:
            movements = bound_movements_inside_surface(movements, ps, surface)
    return movements


def project_movements_to_surface(movements, particles, surface, bounds, rotate_to_normal=True):
    from chimerax.geometry._geometry import closest_triangle_intercept

    for p in particles:
        if not movements[p].any():
            continue
        search = np.asarray([0, 0, 1])
        f_up, t = closest_triangle_intercept(surface.vertices, surface.triangles, search + p.coord,
                                             - search + p.coord)
        if t is None:
            continue

        verts_on_plane = surface.vertices[surface.triangles[t]]
        normal = np.cross(verts_on_plane[1] - verts_on_plane[0], verts_on_plane[2] - verts_on_plane[0])
        normal = normal / np.linalg.norm(normal)

        new_pos = np.asarray(p.origin_coord) + movements[p]
        max_move = max(bounds[p].xyz_max - bounds[p].xyz_min)/2
        search = normal*max_move
        frac, closest_t_num = closest_triangle_intercept(surface.vertices, surface.triangles, new_pos + search,
                                                         new_pos - search)
        if frac is None:  # Put particle on same plane as defined by normal
            new_pos_plane_proj = new_pos - (np.dot(new_pos, normal) * normal)
            new_pos_on_plane = new_pos_plane_proj + (np.dot(verts_on_plane[0], normal) * normal)
            movements[p] = new_pos_on_plane - np.asarray(p.origin_coord)
        else:
            # Put particle on surface
            new_pos_on_surface = (new_pos + search - 2*search*frac)
            movements[p] = new_pos_on_surface - np.asarray(p.origin_coord)

            # Rotate particle along normal of current triangle
            if rotate_to_normal:
                verts_on_plane = surface.vertices[surface.triangles[t]]
                normal = np.cross(verts_on_plane[1] - verts_on_plane[0], verts_on_plane[2] - verts_on_plane[0])
                if normal.dot(surface.normals[surface.triangles[t]].mean(0)) < 0:  # Using vertex normals to find "out" direction
                    normal = -normal
                rotation_to_z = z_align(p.coord, p.coord + normal)
                rotation = rotation_to_z.zero_translation().inverse()
                p.rotation = rotation



    return movements


def bound_movements_inside_surface(movements, particles, surface, scms):
    from chimerax.geometry._geometry import find_close_points
    for p in particles:
        if not movements[p].any():
            continue
        scm = scms[p]
        p_verts = p.full_transform().transform_points(scm.vertices) + movements[p]
        close_points_indicies = find_close_points(p_verts, surface.vertices, 1)
        if not len(close_points_indicies[0]):
            continue
        all_close_points = np.vstack((p_verts[close_points_indicies[0]], surface[close_points_indicies[1]]))

        middle = all_close_points.mean(0)
        svd = np.linalg.svd(all_close_points - middle)
        normal = svd[2][2, :]
        normal = normal / np.linalg.norm(normal)

        p_to_middle = middle - np.array(p.coord)
        if normal.dot(p_to_middle) < 0:
            normal = -normal


def calculate_overlap_distance(particles, scms, bounds, particles_to_keep_still=None, not_used=None, also_not_used=None):
    from chimerax.geometry._geometry import find_close_points

    overlaps = {p: [] for p in particles}
    for i, p in enumerate(particles[:-1]):
        bounds_p = bounds[p]
        xyz_min_p, xyz_max_p = np.array(bounds_p.xyz_min + p.coord), np.array(bounds_p.xyz_max + p.coord)
        for j, other_p in enumerate(particles[i + 1:]):
            bounds_other_p = bounds[other_p]
            xyz_min_other_p, xyz_max_other_p = np.array(bounds_other_p.xyz_min + other_p.coord), np.array(
                bounds_other_p.xyz_max + other_p.coord)
            if (xyz_min_p <= xyz_max_other_p).all() and (xyz_max_p >= xyz_min_other_p).all():
                overlaps[p].append(other_p)
                overlaps[other_p].append(p)

    movements = {p: np.array([0,0,0], dtype=np.float64) for p in particles}
    number_of_overlaps = {p: 0 for p in particles}
    for i, p in enumerate(particles[:-1]):
        scm = scms[p]
        p_verts = p.full_transform().transform_points(scm.vertices)
        overlapping_particles = [other_p for other_p in overlaps[p] if other_p not in particles[:i]]
        for other_p in overlapping_particles:
            if particles_to_keep_still is not None and particles_to_keep_still[p] and particles_to_keep_still[other_p]:
                continue
            scm = scms[other_p]
            other_p_verts = other_p.full_transform().transform_points(scm.vertices)
            close_points_indicies = find_close_points(p_verts, other_p_verts, 1)
            if not len(close_points_indicies[0]):
                continue
            all_close_points = np.vstack((p_verts[close_points_indicies[0]], other_p_verts[close_points_indicies[1]]))

            middle = all_close_points.mean(0)
            svd = np.linalg.svd(all_close_points - middle)
            normal = svd[2][2, :]
            normal = normal/np.linalg.norm(normal)

            p_to_middle = middle - np.array(p.coord)
            if normal.dot(p_to_middle) < 0:
                normal = -normal

            # IF you need to speed something up, its this next function that is the bottleneck
            p_in_other_p_depth = find_depth_of_pts_from_plane(p_verts, middle, normal)
            other_p_in_p_depth = find_depth_of_pts_from_plane(other_p_verts, middle, -normal)

            movement_direction = -normal
            move_dist = (p_in_other_p_depth + other_p_in_p_depth)/2
            if particles_to_keep_still is None or (not particles_to_keep_still[p] and not particles_to_keep_still[other_p]):
                number_of_overlaps[p] += 1
                number_of_overlaps[other_p] += 1
                movements[p] += movement_direction * move_dist
                movements[other_p] -= movement_direction * move_dist
            elif particles_to_keep_still[p]:
                number_of_overlaps[other_p] += 1
                movements[other_p] -= movement_direction * move_dist*2
            else:
                number_of_overlaps[p] += 1
                movements[p] += movement_direction * move_dist*2

    for p in particles:
        if number_of_overlaps[p]:
            movements[p] = movements[p] / number_of_overlaps[p]
    return movements


def find_depth_of_pts_from_plane(pts, middle, normal):
    # Returns distance from the plane to the point furthest away from the plane on the side the normal points to.
    # Could maybe be faster?
    normal = np.asarray(normal)/np.linalg.norm(normal)
    pts = np.asarray(pts)
    offset = np.dot(normal, middle)
    pts_on_right_side = pts[np.dot(pts, normal) > offset]
    if len(pts_on_right_side):
        projected_to_normal = [normal * np.dot(normal, pt) for pt in pts_on_right_side]
        middle_projected_onto_normal = normal * np.dot(normal, middle)
        lengths = [np.linalg.norm(pt-middle_projected_onto_normal) for pt in projected_to_normal]
        return max(lengths)
    else:
        return 0


def calculate_overlap_point_volume(particles, scms, bounds, particles_to_keep_still=None, num_points=100, move_factor=0.33):
    # return a dictionary with the movement vector to add to all particles. particles is a list of all particles to calculate overlap for, scms and bounds are dicts with the particles as keys and scms/bounds as values.
    generate_pts = generate_poisson_disc_pts

    # Figure out which particles overlap each other and create an ordered list with the particles to generate points for
    overlaps = {p: [] for p in particles}
    overlaps_list = [[] for i in range(len(particles))]
    for i, p in enumerate(particles[:-1]):
        bounds_p = bounds[p]
        xyz_min_p, xyz_max_p = np.array(bounds_p.xyz_min + p.coord), np.array(bounds_p.xyz_max + p.coord)
        for j, other_p in enumerate(particles[i+1:]):
            bounds_other_p = bounds[other_p]
            xyz_min_other_p, xyz_max_other_p = np.array(bounds_other_p.xyz_min + other_p.coord), np.array(bounds_other_p.xyz_max + other_p.coord)
            if (xyz_min_p <= xyz_max_other_p).all() and (xyz_max_p >= xyz_min_other_p).all():
                overlaps[p].append(other_p)
                overlaps[other_p].append(p)
                overlaps_list[i].append(other_p)
                overlaps_list[j].append(p)

    ordered_particles = []
    while len(max(overlaps_list, key=len)):
        particle_most_overlaps_index = np.argmax(list(map(len, overlaps_list)))
        particle_most_overlaps = particles[particle_most_overlaps_index]
        ordered_particles.append(particle_most_overlaps)
        overlaps_list[particle_most_overlaps_index] = []
        overlaps_list = [[p for p in particle_list if p != particle_most_overlaps] for particle_list in overlaps_list]

    # Go through all particles that overlap and calculate the amount they overlap.
    movements = {p: np.array([0,0,0], dtype=np.float64) for p in particles}
    for i, p in enumerate(ordered_particles):
        bounds_p = bounds[p]
        bounds_size = bounds_p.size()
        bbox_vol = bounds_size[0] * bounds_size[1] * bounds_size[2]
        xyz_min, xyz_max = np.array(bounds_p.xyz_min + p.coord), np.array(bounds_p.xyz_max + p.coord)
        pts = generate_pts(num_points, xyz_min, xyz_max)
        scm = scms[p]
        p_verts = p.full_transform().transform_points(scm.vertices)

        pts_in_p1 = filter_points_inside(pts, p_verts, scm.triangles, xyz_min, xyz_max)

        overlapping_particles = [other_p for other_p in overlaps[p] if other_p not in ordered_particles[:i]]
        for other_p in overlapping_particles:
            if particles_to_keep_still is not None and particles_to_keep_still[p] and particles_to_keep_still[other_p]:
                continue
            scm = scms[other_p]
            p_verts = other_p.full_transform().transform_points(scm.vertices)

            pts_in_both = filter_points_inside(pts_in_p1, p_verts, scm.triangles, xyz_min, xyz_max)
            overlap_vol = bbox_vol * len(pts_in_both) / len(pts)

            movement_direction = np.asarray(p.coord) - other_p.coord
            movement_direction = movement_direction/np.linalg.norm(movement_direction)
            move_dist = (overlap_vol ** (1/3))*move_factor
            if particles_to_keep_still is None or (not particles_to_keep_still[p] and not particles_to_keep_still[other_p]):
                movements[p] += movement_direction * move_dist
                movements[other_p] -= movement_direction * move_dist
            elif particles_to_keep_still[p]:
                movements[other_p] -= movement_direction * move_dist * 2
            else:
                movements[p] += movement_direction * move_dist * 2
    return movements


def generate_poisson_disc_pts(num_total_pts, xyz_min, xyz_max):
    from scipy.stats import qmc
    radius = 1./int(round(num_total_pts ** (1./3)))
    #radius = 0.5/int(round(num_total_pts ** (1./3)))
    engine = qmc.PoissonDisk(d=3, radius=radius, ncandidates=10)  # 10 seems to be a good number... might have to look at that again
    samples = engine.fill_space()
    return samples * (xyz_max-xyz_min) + xyz_min


def is_point_in_surface(point, vertices, triangles, xyz_min, xyz_max):
    # NOT USED, but a nice example of how to find out if only one point is inside a surface
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


def filter_points_inside(points, vertices, triangles, xyz_min, xyz_max):
    cti = closest_triangle_intercept
    #rpt = repeat

    closest_sides = np.argmin(np.append(points - xyz_min, xyz_max - points, axis=1), axis=1)  # and allies and allies
    ends = points.copy()
    ends[range(ends.shape[0]), closest_sides % 3] = np.append(xyz_min, xyz_max)[closest_sides]

    intercepts = np.zeros(len(points), dtype=bool)
    margin = 1.001
    dists_to_end = ends - points
    for point, end, dist_to_end, i in zip(points, ends, dists_to_end, range(len(intercepts))):
        fraction_of_distance, tnum = cti(vertices, triangles, point, end)
        start = point
        intercept = 0
        while fraction_of_distance is not None:
            intercept += 1
            if intercept > 1000:
                print("TOO MANY INTERSEPTS")
                return False
            start = start + fraction_of_distance * margin * dist_to_end
            dist_to_end = end - start
            fraction_of_distance, tnum = cti(vertices, triangles, start, end)
        intercepts[i] = bool(intercept % 2)

    return points[intercepts]


##### TESTS/NOT USED #####
def project_movements_to_surface_plane(movements, particles, surface):
    from chimerax.geometry._geometry import closest_triangle_intercept

    for p in particles:
        f_up, tnum_up = closest_triangle_intercept(surface.vertices, surface.triangles, p.coord,
                                                   np.asarray([0, 0, 1]) + p.coord)
        f_down, tnum_down = closest_triangle_intercept(surface.vertices, surface.triangles, p.coord,
                                                       np.asarray([0, 0, -1]) + p.coord)
        ts = [tnum for tnum in [tnum_up, tnum_down] if tnum is not None]
        if len(ts) == 0:
            continue
        else:
            t = ts[0]  # Realized it probably doesnt matter which one to use if theyre both really close

        verts_on_plane = surface.vertices[surface.triangles[t]]
        normal = np.cross(verts_on_plane[1] - verts_on_plane[0], verts_on_plane[2] - verts_on_plane[0])
        normal = normal / np.linalg.norm(normal)

        new_pos = np.asarray(p.origin_coord) + movements[p]
        new_pos_plane_proj = new_pos - (np.dot(new_pos, normal) * normal)
        new_pos_on_plane = new_pos_plane_proj + (np.dot(verts_on_plane[0], normal) * normal)
        movements[p] = new_pos_on_plane - np.asarray(p.origin_coord)

    return movements


def calculate_overlap_in_particle_list(pl, num_total_pts, method='monte carlo'):
    import time
    ps = [pl.get_particle(cid) for cid in pl.particle_ids]
    scm = pl.collection_model.collections['surfaces']
    vertices, triangles = scm.vertices, scm.triangles

    # Kind of unnecessary but maybe small speedup
    surface_bounds = pl.display_model.get(0).surfaces[0].geometry_bounds()
    bounds_size = surface_bounds.size()
    bbox_vol = bounds_size[0] * bounds_size[1] * bounds_size[2]
    if method == 'monte carlo':
        generate_pts = generate_random_pts
    elif method == 'poisson':
        generate_pts = generate_poisson_disc_pts
    elif method == 'regular grid':
        generate_pts = generate_regular_grid_pts
    else:
        print("UNKNOWN METHOD")
        return

    for i, p in enumerate(ps[:-1]):
        # Generate points in the bounding box of p here
        t0 = time.time()
        xyz_min, xyz_max = np.array(surface_bounds.xyz_min + p.coord), np.array(surface_bounds.xyz_max + p.coord)
        pts = generate_pts(num_total_pts, xyz_min, xyz_max)
        p_verts = p.full_transform().transform_points(vertices)

        t1 = time.time()
        #pts_in_p1 = [pt for pt in pts if is_point_in_surface(pt, p_verts, triangles, xyz_min, xyz_max)]
        pts_in_p1 = filter_points_inside(pts, p_verts, triangles, xyz_min, xyz_max)  # a little bit faster
        print("ESTIMATED SIZE OF P: ", bbox_vol * len(pts_in_p1)/len(pts))
        t2 = time.time()
        print("NUM PTS IN P", len(pts_in_p1))
        for other_p in ps[i + 1:]:
            # Figure out which of those points are also in other_p
            p_verts = other_p.full_transform().transform_points(vertices)
            #pts_in_both = [pt for pt in pts_in_p1 if is_point_in_surface(pt, p_verts, triangles, xyz_min, xyz_max)]
            pts_in_both = filter_points_inside(pts_in_p1, p_verts, triangles, xyz_min, xyz_max)
            print("NUM PTS IN BOTH", len(pts_in_both))

            overlap_vol = bbox_vol * len(pts_in_both) / len(pts)
            print("OVERLAP BETWEEN: ", p, other_p, overlap_vol)
        t3 = time.time()
        print("Time taken to generate points: ", t1 - t0)
        print("Time taken to figure out the number of points in p1: ", t2 - t1)
        print("Time taken to figure out the number of points in all other particles: ", t3 - t2)
        print("Time taken in total: ", t3 - t0)


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

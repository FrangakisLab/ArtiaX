# General imports
import math

import numpy as np
from scipy.spatial import Delaunay
from collections import defaultdict

# ChimeraX imports
from chimerax.bild.bild import _BildFile
from chimerax.atomic import AtomicShapeDrawing
from chimerax.geometry import z_align

# ArtiaX imports
from .GeoModel import GeoModel


class Boundary(GeoModel):
    """
    An alpha surface boundary, computed using scipy Delaunay. Can be used to create concave shapes. Is
    created from the particle positions and alpha value. The alpha value is set between 0-1, with 0
    being only one tetrahedron, adn 1 being the convex hull of the particles. Can be used to reorient particles.
    """

    def __init__(self, name, session, particle_pos, alpha, particles=None, triangles=None, delete_tri_list=None):
        super().__init__(name, session)

        self.particles = particles
        """n-long list containing all particles used to define the sphere."""
        self.particle_pos = particle_pos
        """(n x 3) list containing all xyz positions of the particles."""

        if triangles is None:
            self.tri = get_triangles(particle_pos, alpha)
        else:
            self.tri = triangles
        """(n x 3 x 3) list of floats, where every row is a triangle with 3 points. The triangles that
        define the surface. If the triangles are not provided they get calculated."""

        self.alpha = alpha
        """Used to calculate the shape. Decides how many tetrahedrons get used in the shape."""

        if delete_tri_list is None:
            self.delete_tri_list = np.zeros((0,1), dtype=np.int32)
        else:
            self.delete_tri_list = delete_tri_list
        """List of ints, where each int is the index of a triangle to delete."""

        self.fitting_options = True

        self.update()
        session.logger.info("Created a boundary with {} vertices.".format(len(particle_pos)))

    def define_surface(self):
        """Could probably be done manually to improve performance."""
        b = _BildFile(self.session, 'dummy')

        for triangle in self.tri:
            b.polygon_command(
                ".polygon {} {} {} {} {} {} {} {} {}".format(*triangle[0], *triangle[1], *triangle[2]).split())

        d = AtomicShapeDrawing('shapes')
        d.add_shapes(b.shapes)

        return d.vertices, d.normals, d.triangles

    def update(self):
        vertices, normals, triangles = self.define_surface()
        self.set_geometry(vertices, normals, triangles)
        self.vertex_colors = np.full((len(vertices), 4), self.color)

    def recalc_and_update(self):
        """Recalculates the boundary, and resets the list of triangles to delete."""
        if self.particles is not None:
            for i, particle in enumerate(self.particles):
                self.particle_pos[i] = [particle.coord[0], particle.coord[1], particle.coord[2]]
        self.delete_tri_list = np.zeros((0,1), dtype=np.int32)
        self.tri = get_triangles(self.particle_pos, self.alpha)
        self.update()

    def change_alpha(self, alpha):
        if alpha != self.alpha and 0 <= alpha <= 1:
            self.alpha = alpha
            self.recalc_and_update()

    def reorient_particles_to_surface(self, particles, max_dist=None):
        """Reorients particles so that they point away from the surface. The particles that are in vertices
        get pointed towards the vertex average normal, and particles not in vertices point along the normal
        of the closest triangle. Ill be honest, this function is shit... its very hard to follow. Had to kinda throw it
        together in the end... Anyways it works by using the verts list, which is a list of all vertices, and
        vertex normals is a list with all normals for all the verts, with the index matching the verts.
        Tge vertex_normal_indices[i] contains how many normals are associated with vert[i]. """
        self.tri, verts, vertex_normals, vertex_normal_indices = get_triangles(self.particle_pos, self.alpha,
                                                                            calc_normals=True,
                                                                            delete_tri_list=self.delete_tri_list)

        if self.particles is not None:
            unaligned = [None] * len(particles)
            unaligned_index = 0
            for i, particle in enumerate(self.particles):
                if particle in particles:
                    curr_normals = np.zeros((0,3))
                    for j, vert in enumerate(verts):
                        if np.isclose(particle.coord, vert).all():
                            curr_normals = vertex_normals[j][:vertex_normal_indices[j]]
                            break
                    if len(curr_normals) > 0:
                        # Rotate to average normal
                        normal = np.add.reduce(curr_normals)
                        curr_pos = np.asarray(particle.coord)
                        rot = z_align(curr_pos, curr_pos + normal).zero_translation().inverse()
                        # Set rotation
                        particle.rotation = rot
                    else:
                        unaligned[unaligned_index] = particle
                        unaligned_index += 1
            # Add all particles that are not part of the boundary to the unaligned list:
            for particle in particles:
                if particle not in self.particles:
                    unaligned[unaligned_index] = particle
                    unaligned_index += 1
            unaligned = unaligned[:unaligned_index]
        else:
            unaligned = particles


        unaligned_coord = np.array([p.coord for p in unaligned])
        from chimerax.geometry._geometry import find_closest_points
        if max_dist is None:
            max_dist = max(self.bounds().xyz_max - self.bounds().xyz_min)
        unaligned_indices, aligned_indices, closest_indices = find_closest_points(unaligned_coord, verts, max_dist)
        for (unaligned_index, closest_index) in zip(unaligned_indices, closest_indices):
            curr_part = unaligned[unaligned_index]
            closest_pos = verts[closest_index]
            curr_pos = np.asarray(curr_part.coord)
            closest_to_current = curr_pos - np.asarray(closest_pos)
            closest_normals = vertex_normals[closest_index][:vertex_normal_indices[closest_index]]
            # Find normal most similar to the vector from the vertex to the particles
            orientation = closest_normals[
                np.argmax(np.array([np.dot(closest_to_current, normal) for normal in closest_normals]))]
            rot = z_align(curr_pos, curr_pos + orientation).zero_translation().inverse()
            # Set rotation
            curr_part.rotation = rot

        for particle_list in self.session.ArtiaX.partlists.child_models():
            particle_list.update_places()


        # for i, particle in enumerate(self.particles):
        #     if particle in particles:
        #         curr_normals = np.zeros((0, 3))
        #         for j, index_tri in enumerate(p_index_triangles):
        #             if i in index_tri:
        #                 curr_normals = np.append(curr_normals, [ordered_normals[j]], axis=0)
        #         if len(curr_normals) > 0:
        #             normals_dict[particle] = curr_normals
        #             # Rotate to average normal
        #             normal = np.add.reduce(curr_normals)
        #             curr_pos = np.asarray(particle.coord)
        #             rot = z_align(curr_pos, curr_pos + normal).zero_translation().inverse()
        #             # Set rotation
        #             particle.rotation = rot
        #             aligned[aligned_index] = particle
        #             aligned_index += 1
        #         else:
        #             unaligned[unaligned_index] = particle
        #             unaligned_index += 1
        # # Add all particles that are not part of the boundary to the unaligned list:
        # for particle in particles:
        #     if particle not in self.particles:
        #         unaligned[unaligned_index] = particle
        #         unaligned_index += 1
        #
        # aligned = aligned[:aligned_index]
        # unaligned = unaligned[:unaligned_index]
        # unaligned_coord = np.array([p.coord for p in unaligned])
        # aligned_coord = np.array([p.coord for p in aligned])
        # from chimerax.geometry._geometry import find_closest_points
        # max_dist = max(max(aligned_coord.flatten()), max(unaligned_coord.flatten()))
        # unaligned_indices, aligned_indices, closest_indices = find_closest_points(unaligned_coord, aligned_coord, max_dist)
        # for (unaligned_index, closest_index) in zip(unaligned_indices, closest_indices):
        #     curr_part = unaligned[unaligned_index]
        #     closest_part = aligned[closest_index]
        #     curr_pos = np.asarray(curr_part.coord)
        #     closest_to_current = curr_pos - np.asarray(closest_part.coord)
        #     closest_normals = normals_dict[closest_part]
        #     # Find normal most similar to the vector from the vertex to the particles
        #     orientation = closest_normals[
        #         np.argmax(np.array([np.dot(closest_to_current, normal) for normal in closest_normals]))]
        #     rot = z_align(curr_pos, curr_pos + orientation).zero_translation().inverse()
        #     # Set rotation
        #     curr_part.rotation = rot
        #
        # for particle_list in self.session.ArtiaX.partlists.child_models():
        #     particle_list.update_places()

    def remove_tetra(self, tri):
        self.delete_tri_list = np.append(self.delete_tri_list, tri)
        self.tri = get_triangles(self.particle_pos, self.alpha, delete_tri_list=self.delete_tri_list)
        self.update()

    def write_file(self, file_name):
        with open(file_name, 'wb') as file:
            np.savez(file, model_type="Boundary", particle_pos=self.particle_pos, alpha=self.alpha, triangles=self.tri,
                     delete_tri_list=self.delete_tri_list)


def get_triangles(particle_pos, alpha=0.7, calc_normals=False, delete_tri_list=None):
    """Creates the triangles that define the boundary. Gets kinda complicated with the addition of calculating normals
    and deleting tetras. Calculating normals is only done when reorienting particles. Deleting triangles works
    by doing the triangulation, figuring out which tetra the triangle belongs to, and recalculating the boundary
    without that tetra. This gets repeated for every tetra that is deleted. Can probably be speed up quite a lot,
    if there is a way to figure out what tetra the triangle belongs to without redoing the calculation every time.

    Parameters
    ----------
    particle_pos: (n x 3) list containing all xyz positions of the particles
    alpha: float between 0 and 1. 0 means only smallest tetra, 1 means convex hull.
    calc_normals: bool, if the normals should be calculated or not.
    delete_tri_list: list of ints with indices for every triangle that should be removed.

    Returns
    triangles: (n x 3 x 3) list of floats, where every row is a triangle with 3 points. The triangles that
        define the surface. If the triangles are not provided they get calculated.
    verts: (m, 3) list of floats with all vertices exactly once.
    vertex_normals: (m, 10, 3) list of floats, where every row contains all normals (up to ten) for the m:th
        vertex.
    vertex_normal_indices: (m,1) list with int, where every row says how many normals are used for that vertex.

    """
    tetra = Delaunay(particle_pos, furthest_site=False)
    """ Taken mostly from stack overflow: https://stackoverflow.com/a/58113037
    THANK YOU @Geun, this is pretty clever. """
    # Find radius of the circumsphere.
    # By definition, radius of the sphere fitting inside the tetrahedral needs
    # to be smaller than alpha value
    # http://mathworld.wolfram.com/Circumsphere.html
    tetrapos = np.take(particle_pos, tetra.simplices, axis=0)
    normsq = np.sum(tetrapos ** 2, axis=2)[:, :, None]
    ones = np.ones((tetrapos.shape[0], tetrapos.shape[1], 1))
    a = np.linalg.det(np.concatenate((tetrapos, ones), axis=2))
    Dx = np.linalg.det(np.concatenate((normsq, tetrapos[:, :, [1, 2]], ones), axis=2))
    Dy = -np.linalg.det(np.concatenate((normsq, tetrapos[:, :, [0, 2]], ones), axis=2))
    Dz = np.linalg.det(np.concatenate((normsq, tetrapos[:, :, [0, 1]], ones), axis=2))
    c = np.linalg.det(np.concatenate((normsq, tetrapos), axis=2))
    r = np.sqrt(Dx ** 2 + Dy ** 2 + Dz ** 2 - 4 * a * c) / (2 * np.abs(a))

    # Translate alpha value from 0-1 to shortest-longest
    sorted_r = np.sort(r)
    alpha = math.floor(alpha*len(r))
    if alpha == len(r):
        alpha -= 1
    alpha = sorted_r[alpha]

    # Find tetrahedrals
    tetras = tetra.simplices[r <= alpha, :]
    # triangles
    TriComb = np.array([(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)])
    triangles = tetras[:, TriComb].reshape(-1, 3)
    TrianglesDict = defaultdict(int)
    if calc_normals:
        # First delete triangle
        if delete_tri_list is not None and len(delete_tri_list) > 0:
            for delete_tri in delete_tri_list:
                # Calculate once to find the triangle that is to be removed
                for tri in triangles:
                    TrianglesDict[tuple(tri)] += 1
                new_index = 0
                for i, tri in enumerate(triangles):
                    if TrianglesDict[tuple(tri)] == 1:
                        if delete_tri == new_index:
                            delete_tri = i
                            break
                        new_index += 1
                # Now calculate again but remove the triangle
                for i, tetra_bools in enumerate(np.isin(tetras, triangles[delete_tri])):
                    if int(tetra_bools[0]) + int(tetra_bools[1]) + int(tetra_bools[2]) + int(tetra_bools[3]) == 3:
                        # Found tetra for triangle to delete
                        tetras = np.delete(tetras, i, axis=0)
                        break
                if len(tetras) > 0:
                    triangles = tetras[:, TriComb].reshape(-1, 3)
                    TrianglesDict = defaultdict(int)

        p_index_triangles = triangles
        ordered_normals = np.zeros((len(triangles), 3))
        triangles = np.array([particle_pos[np.asarray(tri)] for tri in triangles])
        TrianglesDict = defaultdict(int)
        # Remove triangles that occur twice, because they are within shapes, and calculate normals that point out
        for i, tri in enumerate(p_index_triangles):
            TrianglesDict[tuple(tri)] += 1

            if calc_normals and TrianglesDict[tuple(tri)] <= 1:
                tetra_index = i//4
                missing_vertex = 3 - (i % 4)
                missing_vertex_pos = particle_pos[tetras[tetra_index][missing_vertex]]
                tri_pos = triangles[i]
                normal = np.cross(tri_pos[1] - tri_pos[0], tri_pos[2] - tri_pos[0])
                to_unused = missing_vertex_pos - tri_pos[0]
                if np.dot(normal, to_unused) > 0:
                    normal = -normal
                normal = normal / np.linalg.norm(normal)
                ordered_normals[i] = normal

        verts = np.zeros((len(particle_pos), 3))
        max_norms = 10
        vert_normals = np.zeros((len(verts), max_norms, 3))
        vert_normal_indices = np.zeros((len(verts)), dtype=np.int32)
        added_vertices = np.zeros((0,1), dtype=np.int32)
        vertex_index = 0
        new_index = 0
        for i, tri in enumerate(p_index_triangles):
            if TrianglesDict[tuple(tri)] == 1:
                for tri_index in tri:
                    added_vertex = np.where(added_vertices==tri_index)[0]
                    if len(added_vertex) == 0:
                        added_vertices = np.append(added_vertices, tri_index)
                        verts[vertex_index] = particle_pos[tri_index]
                        vert_normals[vertex_index][0] = ordered_normals[i]
                        vert_normal_indices[vertex_index] = 1
                        vertex_index += 1
                    else:
                        vert_normals[added_vertex[0]][vert_normal_indices[added_vertex[0]]] = ordered_normals[i]
                        vert_normal_indices[added_vertex[0]] += 1
                        if vert_normal_indices[added_vertex[0]] == max_norms:
                            vert_normal_indices[added_vertex[0]] = max_norms - 1
                triangles[new_index] = particle_pos[tri]
                p_index_triangles[new_index] = tri
                ordered_normals[new_index] = ordered_normals[i]
                new_index += 1
        verts = verts[:vertex_index]
        triangles = triangles[:new_index]

        return triangles, verts, vert_normals, vert_normal_indices
    elif delete_tri_list is not None:
        for delete_tri in delete_tri_list:
            # Calculate once to find the triangle that is to be removed
            for tri in triangles:
                TrianglesDict[tuple(tri)] += 1
            new_index = 0
            for i, tri in enumerate(triangles):
                if TrianglesDict[tuple(tri)] == 1:
                    if delete_tri == new_index:
                        delete_tri = i
                        break
                    new_index += 1
            # Now calculate again but remove the triangle
            for i, tetra_bools in enumerate(np.isin(tetras, triangles[delete_tri])):
                if int(tetra_bools[0]) + int(tetra_bools[1]) + int(tetra_bools[2]) + int(tetra_bools[3]) == 3:
                    # Found tetra for triangle to delete
                    tetras = np.delete(tetras, i, axis=0)
                    break
            if len(tetras) > 0:
                triangles = tetras[:, TriComb].reshape(-1, 3)
                TrianglesDict = defaultdict(int)

        TrianglesDict = defaultdict(int)
        for tri in triangles:
            TrianglesDict[tuple(tri)] += 1
        triangles = np.array([particle_pos[np.asarray(tri)] for tri in TrianglesDict if TrianglesDict[tri] == 1])
        return triangles
    else:
        for tri in triangles:
            TrianglesDict[tuple(tri)] += 1
        triangles = np.array([particle_pos[np.asarray(tri)] for tri in TrianglesDict if TrianglesDict[tri] == 1])
        return triangles
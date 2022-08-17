# General imports
import math

import numpy as np
from scipy.spatial import Delaunay
from collections import defaultdict
from statistics import median

# ChimeraX imports
from chimerax.bild.bild import _BildFile
from chimerax.atomic import AtomicShapeDrawing
from chimerax.geometry import z_align

# ArtiaX imports
from .GeoModel import GeoModel


class Boundary(GeoModel):
    """Triangulated Plane"""

    def __init__(self, name, session, particle_pos, alpha, particles=None, triangles=None, delete_tri_list=None):
        super().__init__(name, session)

        self.particles = particles
        self.particle_pos = particle_pos

        if triangles is None:
            self.tri = get_triangles(particle_pos, alpha)
        else:
            self.tri = triangles

        self.p_index_triangles = None
        self.ordered_normals = None
        self.alpha = alpha

        if delete_tri_list is None:
            self.delete_tri_list = np.zeros((0,1), dtype=np.int32)
        else:
            self.delete_tri_list = delete_tri_list

        self.fitting_options = True

        self.update()
        session.logger.info("Created a boundary with {} vertices.".format(len(particle_pos)))

    def define_surface(self):
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

    def reorient_particles_to_surface(self, particles):
        if self.particles is None:
            return

        self.tri, self.p_index_triangles, self.ordered_normals = get_triangles(self.particle_pos, self.alpha,
                                                                               calc_normals=True)
        aligned = [None]*len(particles)
        aligned_index = 0
        unaligned = [None]*len(particles)
        unaligned_index = 0
        normals_dict = dict()
        for unaligned_index, particle in enumerate(self.particles):
            if particle in particles:
                curr_normals = np.zeros((0, 3))
                for j, index_tri in enumerate(self.p_index_triangles):
                    if unaligned_index in index_tri:
                        curr_normals = np.append(curr_normals, [self.ordered_normals[j]], axis=0)
                if len(curr_normals) > 0:
                    normals_dict[particle] = curr_normals
                    # Rotate to average normal
                    normal = np.add.reduce(curr_normals)
                    curr_pos = np.asarray(particle.coord)
                    rot = z_align(curr_pos, curr_pos + normal).zero_translation().inverse()
                    # Set rotation
                    particle.rotation = rot
                    aligned[aligned_index] = particle
                    aligned_index += 1
                else:
                    unaligned[unaligned_index] = particle
                    unaligned_index += 1

        aligned = aligned[:aligned_index]
        unaligned = unaligned[:unaligned_index]
        unaligned_coord = np.array([p.coord for p in unaligned])
        aligned_coord = np.array([p.coord for p in aligned])
        from chimerax.geometry._geometry import find_closest_points
        # TODO: change distance from 100 to something... more dynamic.
        unaligned_indices, aligned_indices, closest_indices = find_closest_points(unaligned_coord, aligned_coord, 100)
        for (unaligned_index, closest_index) in zip(unaligned_indices, closest_indices):
            curr_part = unaligned[unaligned_index]
            closest_part = aligned[closest_index]
            curr_pos = np.asarray(curr_part.coord)
            closest_to_current = curr_pos - np.asarray(closest_part.coord)
            closest_normals = normals_dict[closest_part]
            # Find normal most similar to the vector from the vertex to the particles
            orientation = closest_normals[
                np.argmax(np.array([np.dot(closest_to_current, normal) for normal in closest_normals]))]
            rot = z_align(curr_pos, curr_pos + orientation).zero_translation().inverse()
            # Set rotation
            curr_part.rotation = rot

        for particle_list in self.session.ArtiaX.partlists.child_models():
            particle_list.update_places()

    def remove_tetra(self, tri):
        self.delete_tri_list = np.append(self.delete_tri_list, tri)
        self.tri = get_triangles(self.particle_pos, self.alpha, delete_tri_list=self.delete_tri_list)
        self.update()

    def write_file(self, file_name):
        with open(file_name, 'wb') as file:
            np.savez(file, model_type="Boundary", particle_pos=self.particle_pos, alpha=self.alpha, triangles=self.tri,
                     delete_tri_list=self.delete_tri_list)


def get_triangles(particle_pos, alpha=0.7, calc_normals=False, delete_tri_list=None):
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
    if delete_tri_list is not None:
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
    elif calc_normals:
        p_index_triangles = triangles
        ordered_normals = np.zeros((len(triangles), 3))
        triangles = np.array([particle_pos[np.asarray(tri)] for tri in triangles])

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

        new_index = 0
        for i, tri in enumerate(p_index_triangles):
            if TrianglesDict[tuple(tri)] == 1:
                triangles[new_index] = particle_pos[tri]
                p_index_triangles[new_index] = tri
                ordered_normals[new_index] = ordered_normals[i]
                new_index += 1
        triangles = triangles[:new_index]
        p_index_triangles = p_index_triangles[:new_index]
        ordered_normals = ordered_normals[:new_index]

        return triangles, p_index_triangles, ordered_normals
    else:
        for tri in triangles:
            TrianglesDict[tuple(tri)] += 1
        triangles = np.array([particle_pos[np.asarray(tri)] for tri in TrianglesDict if TrianglesDict[tri] == 1])
        return triangles
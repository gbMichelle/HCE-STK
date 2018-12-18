from reclaimer.hek.defs.mod2 import mod2_def
from defs.amf import amf_def
from shared.model_functions import TrianglesToStrips
from shared.model_functions import CalcVertBiNormsAndTangents
import sys
import time
import math
mod2_ext = ".gbxmodel"
amf_ext = ".amf"

def amf_quat_to_gbx_quat(quat):
    return -quat[0], -quat[1], -quat[2], quat[3]

# Converts an AMF model into a GBX model.
def AmfToMod2(amf_model, do_output):
    gbx_model = mod2_def.build()
    target = gbx_model.data.tagdata
    source = amf_model.data
    
    target.base_map_u_scale = 1.0
    target.base_map_v_scale = 1.0
    
    node_translations = []
    
    t_nodes = target.nodes.STEPTREE
    s_nodes = source.nodes_header.STEPTREE
    if len(s_nodes) > 62:
        print("Warning, node count is over the max supported amount. Supported range: 1-62. Nodecount is: %d"
                % len(s_nodes))
    for s_node in s_nodes:
        t_nodes.append()
        t_node = t_nodes[-1]
        
        if len(s_node.name) > 31:
            t_node.name = s_node.name[0:31]
            print("Warning: The name of node #%d : %s is longer than 31 characters, got: %d" 
                  % (len(t_nodes), s_node.name, len(s_node.name)))
            print("Cutting it short to:", t_node.name)
        else:
            t_node.name = s_node.name
        
        t_node.next_sibling_node    = s_node.sibling_index
        t_node.first_child_node     = s_node.child_index
        t_node.parent_node          = s_node.parent_index
        t_node.translation.x        = s_node.position.x / 100
        t_node.translation.y        = s_node.position.y / 100
        t_node.translation.z        = s_node.position.z / 100
        t_node.rotation[:]          = amf_quat_to_gbx_quat(s_node.orientation)
        t_node.distance_from_parent = math.sqrt(t_node.translation[0]**2+t_node.translation[1]**2+t_node.translation[2]**2)
        
    
    t_markers = target.markers.STEPTREE
    s_markers = source.markers_header.STEPTREE
    for s_marker in s_markers:
        t_markers.append()
        t_marker = t_markers[-1]
        
        t_instances = t_marker.marker_instances.STEPTREE
        s_instances = s_marker.marker_instances.STEPTREE
        if len(s_marker.name) > 31:
            t_marker.name = s_marker.name[0:31]
            print("Warning: The name of node #%d : %s is longer than 31 characters, got: %d." 
                  % (len(t_markers), s_marker.name, len(s_marker.name)))
            print("Cutting it short to:", t_marker.name)
        else:
            t_marker.name = s_marker.name
        
        for s_instance in s_instances:
            t_instances.append()
            t_instances[-1][0:3] = s_instance[0:3]
            t_instances[-1].translation.x = s_instance.position.x / 100
            t_instances[-1].translation.y = s_instance.position.y / 100
            t_instances[-1].translation.z = s_instance.position.z / 100
            t_instances[-1].rotation[:] = amf_quat_to_gbx_quat(s_instance.orientation)
            
            
    t_regions = target.regions.STEPTREE
    s_regions = source.regions_header.STEPTREE
    t_geometries = target.geometries.STEPTREE
    if len(s_regions) > 8:
        print("Too many regions, max: 8, got: %s." % len(s_regions))
        
    for s_region in s_regions:
        t_regions.append()
        t_region = t_regions[-1]
        
        if len(s_region.name) > 31:
            t_region.name = s_region.name[0:31]
            print("Warning: The name of node #%d : %s is longer than 31 characters, got: %d." 
                  % (len(t_regions), s_region.name, len(s_region.name)))
            print("Cutting it short to:", t_region.name)
        else:
            t_region.name = s_region.name
        
        t_permutations = t_region.permutations.STEPTREE
        s_permutations = s_region.permutations_header.STEPTREE
        for s_permutation in s_permutations:
            t_permutations.append()
            t_permutation = t_permutations[-1]
            
            perm_name = s_permutation.name
            if t_region.name == "Instances":
                perm_name = perm_name.replace("%", "", 1)
            
            if len(perm_name) > 31:
                t_permutation.name = perm_name[0:31]
                print("Warning: The name of permutation #%d : %s in region: #%d : %s is longer than 31 characters, got: %d." 
                      % (len(t_permutations), perm_name, len(t_regions), s_region.name, len(perm_name)))
                print("Cutting it short to:", t_permutation.name)
            else:
                t_permutation.name = perm_name
            
            # set superlow-superhigh geometry block indices
            t_permutation[2:7] = [len(t_geometries)] * 5
            
            t_geometries.append()
            t_geometry = t_geometries[-1]
            
            t_parts = t_geometry.parts.STEPTREE
            #print(s_permutation.vertices_header)
            bounds = None
            if s_permutation.format_info.compression_format != 0:
                bounds     = s_permutation.vertices_header.bounds
            s_verts    = s_permutation.vertices_header.vertices.vertices
            s_tris     = s_permutation.faces_header.STEPTREE
            s_sections = s_permutation.sections_header.STEPTREE
            for s_section in s_sections:
                t_parts.append()
                t_part = t_parts[-1]
                
                t_part.shader_index = s_section.shader_index
                
                # Get all the triangles that use this shader
                used_vert_list = [False] * len(s_verts)
                triangles = []
                for i in range(s_section.starting_face, s_section.starting_face+s_section.face_count):
                    triangles.append(s_tris[i][:])
                    #triangles[-1].extend(s_tris[i][0:2])
                    #print(s_tris[i])
                    used_vert_list[triangles[-1][0]] = True
                    used_vert_list[triangles[-1][1]] = True
                    used_vert_list[triangles[-1][2]] = True
                
                # Get all vertices that are used by these triangles shader
                vert_translation_list = [0] * len(used_vert_list)
                verts = []
                for i in range(len(used_vert_list)):
                    if used_vert_list[i] == True:
                        verts.append(s_verts[i])
                        #print(s_verts[i])
                    vert_translation_list[i] = len(verts)-1
                #print(s_verts)
                ## Get all relevant info from each vert and add it to the GBX Model Part
                
                t_verts            = t_part.uncompressed_vertices.STEPTREE
                vertex_format      = s_permutation.format_info.vertex_format
                compression_format = s_permutation.format_info.compression_format
                for s_vert in verts:
                    t_verts.append()
                    t_vert = t_verts[-1]
                    
                    if compression_format == 0:
                        t_vert[0] = s_vert.data.position[0] / 100
                        t_vert[1] = s_vert.data.position[1] / 100
                        t_vert[2] = s_vert.data.position[2] / 100
                        t_vert[3:6] = s_vert.data.normal[0:3]
                        # binormals and tangents are calculated when all verts are added to the STEPTREE
                        t_vert.u = s_vert.data.u
                        t_vert.v = 1 - s_vert.data.v
                    else:
                        bounds = s_permutation.vertices_header.bounds
                        t_vert.position_x = ((s_vert.data.position.x / 32767) * (bounds.x.upper - bounds.x.lower) + bounds.x.lower) / 100
                        t_vert.position_y = ((s_vert.data.position.y / 32767) * (bounds.y.upper - bounds.y.lower) + bounds.y.lower) / 100
                        t_vert.position_z = ((s_vert.data.position.z / 32767) * (bounds.z.upper - bounds.z.lower) + bounds.z.lower) / 100
                        
                        t_vert.normal_i = s_vert.data.normal.i / 1023
                        t_vert.normal_j = s_vert.data.normal.j / 1023
                        t_vert.normal_k = s_vert.data.normal.k / 511
                        
                        t_vert.u = (s_vert.data.u / 32767) * (bounds.u.upper - bounds.u.lower) + bounds.u.lower
                        t_vert.v = 1 - ((s_vert.data.v / 32767) * (bounds.v.upper - bounds.v.lower) + bounds.v.lower)
                    
                    if vertex_format == 0:
                        t_vert.node_0_index = s_permutation.node_index
                        t_vert.node_0_weight = 1.0
                        
                    elif vertex_format == 1:
                        t_vert.node_0_index = s_vert.node_indices[0]
                        if s_vert.node_indices[1] != 255:
                            t_vert.node_1_index = s_vert.node_indices[1]
                            t_vert.node_0_weight = 0.5
                            t_vert.node_1_weight = 0.5
                        else:
                            t_vert.node_0_weight = 1.0
                            
                    elif vertex_format == 2:
                        index_count = 1
                        if   s_vert.node_indices[1] == 255: index_count = 1
                        elif s_vert.node_indices[2] == 255: index_count = 2
                        elif s_vert.node_indices[3] == 255: index_count = 3
                        else: index_count = 4
                        
                        # Put all the node indices and weights and put them in a neat list
                        available_verts = []
                        for i in range(0,index_count):
                            this_vert = []
                            this_vert.append(s_vert.node_indices[i])
                            this_vert.append(s_vert.node_weights[i])
                            available_verts.append(this_vert)
                            
                        vert_weights_to_collect = 1
                        if len(available_verts) > 1: vert_weights_to_collect = 2
                        
                        # Get the two highest weighted node indices and weights and apply them to the target vertex
                        for v in range(vert_weights_to_collect):
                            highest_weight       = 0.0
                            highest_weight_index = 0
                            highest_weight_ref   = 0
                            
                            for i in range(len(available_verts)):
                                if available_verts[i][1] > available_verts[i][1]:
                                    highest_weight = available_verts[i][1]
                                    highest_weight_index = available_verts[i][0]
                                    highest_weight_ref = i
                            
                            if v == 0:
                                t_vert.node_0_index = highest_weight_index
                                t_vert.node_0_weight = highest_weight
                            else:
                                t_vert.node_1_index = highest_weight_index
                                t_vert.node_1_weight = highest_weight
                            
                            available_verts.pop(highest_weight_ref)
                        
                        #Normalize vert weights so we end up with them totalling 1.0
                        total_weight = t_vert.node_0_weight + t_vert.node_1_weight
                        t_vert.node_0_weight /= total_weight
                        t_vert.node_1_weight /= total_weight
                        
                    
                ## Convert triangles to strips and add them to the GBX Model Part
                # Translate the triangle vert ids to match the correct verts in the Part
                for triangle in triangles:
                    triangle[0] = vert_translation_list[triangle[0]]
                    triangle[1] = vert_translation_list[triangle[1]]
                    triangle[2] = vert_translation_list[triangle[2]]
                
                # Calculate the Binormals and Tangents of each vert
                CalcVertBiNormsAndTangents(t_verts, triangles)
                
                triangle_strip = TrianglesToStrips(triangles)
                
                # The triangle strip needs to be divisible by 3
                needed_padding = (3 - len(triangle_strip) % 3) % 3
                
                # Any unused/padding slots in the triangles array need to have the number -1
                for i in range(needed_padding):
                    triangle_strip.append(-1)
                    
                # Write the strip to the array
                t_tris = t_part.triangles.STEPTREE
                for i in range(0, len(triangle_strip), 3):
                    t_tris.append()
                    t_tris[-1][:] = triangle_strip[i : i+3]

                # Calculate the centroid translation by averaging all vertices!
                t_part.centroid_translation[:] = [0.0,0.0,0.0]
                for v in t_verts:
                    for c in range(3):
                        #First 3 indices in a vertex are the translation.
                        t_part.centroid_translation[c] += v[c]
                for c in range(3):
                    t_part.centroid_translation[c] /= len(t_verts)
            
            
    t_shaders = target.shaders.STEPTREE
    s_shaders = source.shaders_header.STEPTREE
    shaders_already_exist = []
    for s_shader in s_shaders:
        t_shaders.append()
        t_shader = t_shaders[-1]
        t_shader.shader.filepath = s_shader.name
        for exists in shaders_already_exist:
            if exists[0][0] == s_shader.name:
                exists[0][1] += 1
        exists = [s_shader.name, 1]
        shaders_already_exist.append(exists)
        
    return gbx_model
    
#Only run this if the script is ran directly
if __name__ == '__main__':
    from argparse import ArgumentParser
    
    #Initialise startup arguments
    parser = ArgumentParser(description='Converter for AMF models to GBX models.')
    parser.add_argument('amf', metavar='amf', type=str,
                        help='The AMF file we want to convert to a GBX model.')
    parser.add_argument('output', metavar='output', type=str,
                        help='The GBX model we want to save to.')
    args = parser.parse_args()
    
    from shared.SharedFunctions import GetAbsFilepath
    amf_path = GetAbsFilepath(args.amf, amf_ext)

    print("\nLoading AMF model " + amf_path + "...", end='')
    sys.stdout.flush()
    amf = amf_def.build(filepath=(amf_path + amf_ext))
    print("done\n")
    print("Format version:", amf.data.version)
    sys.stdout.flush()

    gbx_model = AmfToMod2(amf, True)
    
    print("Saving GBX model tag...", end='')
    sys.stdout.flush()
    gbx_model.serialize(backup=True, temp=False, filepath=(args.output + mod2_ext))
    print("finished\n")

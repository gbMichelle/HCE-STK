from reclaimer.hek.defs.mod2 import mod2_def
from reclaimer.hek.defs.mod2 import part as part_desc
from supyr_struct.defs.block_def import BlockDef
part_def = BlockDef(part_desc, endian=">")
import copy
import math
mod2_ext = ".gbxmodel"

# Returns a list of indices for each shader. If there is more than one entry for the same shader
# the list entries corresponding to the duplicates will contain the index of the first occurrence.
def ListShaderIds(shaders_block):
    shaders = shaders_block.STEPTREE
    shader_count = shaders_block.size
    
    shader_ids = [0] * shader_count #preallocate list
    for i in range(shader_count):
        shader_ids[i] = i
        for j in range(i):
            if (shaders[i].shader.filepath == shaders[j].shader.filepath 
            and shaders[i].shader.tag_class == shaders[j].shader.tag_class):
                shader_ids[i] = j
                break

    return shader_ids

    
# Returns a condensed shader block and a list for use when translating 
# the shader indices in the tag to match the new block
def BuildCondensedShaderBlock(shaders_block):
    shaders = shaders_block.STEPTREE
    shader_ids = ListShaderIds(shaders_block)
    condensed_shader_ids = list(set(shader_ids))

    new_shaders = []
    for condensed_shader_id in condensed_shader_ids:
        new_shaders.append(shaders[condensed_shader_id])
    
    new_shader_ids = [0] * len(shader_ids)
    for i in range(len(shader_ids)):
        for j in range(len(condensed_shader_ids)):
            if (shader_ids[i] == condensed_shader_ids[j]):
                new_shader_ids[i] = j
                break
    
    return new_shaders, new_shader_ids

    
# Uses the translation_list to determine which old id corresponds to which new id.
# Edits the given geometries_block directly. 
def TranslateGeometryPartShaderIds(geometries_block, translation_list):
    geometries = geometries_block.STEPTREE
    
    for geometry in geometries:
        parts = geometry.parts.STEPTREE
        for part in parts:
            part.shader_index = translation_list[part.shader_index]
            
            
      
      
def TranslatePartNodeIds(part_steptree_entry, translation_list):
    verts = part_steptree_entry.uncompressed_vertices.STEPTREE
    
    for vert in verts:
        vert.node_0_index = translation_list[vert.node_0_index]
        vert.node_1_index = translation_list[vert.node_1_index]
        if (vert.node_1_weight == 0):
            vert.node_1_index = 0
    
    part_steptree_entry.compressed_vertices.STEPTREE.clear()


    
# Used for making the lists that are used to build new condensed geometries
def GroupGeometryPartsByShader(geometry, shaders_block):
    shader_count = len(shaders_block.STEPTREE)
    
    groups = []
    parts = geometry.parts.STEPTREE
    for i in range(shader_count):
        current_list = []
        for part in parts:
            if (part.shader_index == i):
                current_list.append(part)
                
        groups.append(current_list)
    
    return groups
    
    
    
    
def CombinePartsFromList(list):
    current_offset = 0
    
    shader_id = list[0].shader_index
    vert_counts = []
    centroids = []
    
    combined_verts = []
    triangle_strip_chain = []
    
    for i in range(len(list)):
        triangles = list[i].triangles.STEPTREE
        verts = list[i].uncompressed_vertices.STEPTREE
        centroid = list[i].centroid_translation
        
        current_strip = []
        # convert the 'triangles' to individual triangle strip points
        for triangle in triangles:
            if triangle.v0_index != -1:
                current_strip.append(triangle.v0_index+current_offset)
                if triangle.v1_index != -1:
                    current_strip.append(triangle.v1_index+current_offset)
                    if triangle.v2_index != -1:
                        current_strip.append(triangle.v2_index+current_offset)
        # if the number of triangles in this strip is uneven we need to copy the last vert
        if len(current_strip)%2 == 1 and i < len(list):
            current_strip.append(current_strip[len(current_strip)-1])
        # if the strip isn't the first copy the first vert to properly connect it to the one before
        if (i != 0):
            current_strip.insert(0, current_strip[0])
        # if the strip is the last strip don't add a copy of the last strip point
        if (i < len(list)):
            current_strip.append(current_strip[len(current_strip)-1])

        # add the current chain to the main chain
        triangle_strip_chain.extend(current_strip)
        # add the verts of this part to the combined set of verts
        combined_verts.extend(verts)
        # add the current vert count to the offset
        current_offset += len(verts)
        # save vert count for centroid averaging
        vert_counts.append(len(verts))
        # save centroid for averaging
        centroids.append(centroid)
    
    #create the new part we'll be writing to
    new_part = part_def.build()
    # set the right shader id
    new_part.shader_index = shader_id
    
    # get a weighted average of all centroids
    for centroid,vert_count in zip(centroids,vert_counts):
        new_part.centroid_translation.x += centroid.x * vert_count
        new_part.centroid_translation.y += centroid.y * vert_count
        new_part.centroid_translation.z += centroid.z * vert_count
    new_part.centroid_translation.x /= sum(vert_counts)
    new_part.centroid_translation.y /= sum(vert_counts)
    new_part.centroid_translation.z /= sum(vert_counts)
    
    new_part.uncompressed_vertices.STEPTREE[:] = combined_verts

    tris = new_part.triangles.STEPTREE
    for i in range(0, len(triangle_strip_chain), 3):
        tris.append()
        tris[len(tris)-1].v0_index = triangle_strip_chain[i]
        if (i+1 < len(triangle_strip_chain)):
            tris[len(tris)-1].v1_index = triangle_strip_chain[i+1]
            if (i+2 < len(triangle_strip_chain)):
                tris[len(tris)-1].v2_index = triangle_strip_chain[i+2]
    
    return new_part
    
    
    
    
def BuildPartList(groups):
    
    parts = []
    for group in groups:
        if (len(group) > 0):
            if (len(group) > 1):
                parts.append(CombinePartsFromList(group))
            else:
                parts.append(group[0])
            
    return parts
            
            
            
            
#########################################################################




def ModelCondenseShaders(model_tag):
    model = model_tag.data.tagdata

    new_shaders = BuildCondensedShaderBlock(model.shaders)
    model.shaders.STEPTREE[:] = new_shaders[0]
    
    TranslateGeometryPartShaderIds(model.geometries, new_shaders[1])
    
    
    

def ModelRemoveLocalNodes(model_tag):
    model = model_tag.data.tagdata
    geometries = model.geometries.STEPTREE
    
    for geometry in geometries:
        parts = geometry.parts.STEPTREE
        for part in parts:
            if (part.flags.ZONER):
                TranslatePartNodeIds(part, part.local_nodes)
                part.local_nodes.clear()
                part.flags.ZONER = False
                
    model.flags.parts_have_local_nodes = False

    
    
    
def ModelMergeGeometryPartsWithIdenticalShaderIds(model_tag):
    model = model_tag.data.tagdata
    geometries = model.geometries.STEPTREE
    shaders = model.shaders
    
    for geometry in geometries:
        geometry.parts.STEPTREE[:] = BuildPartList(GroupGeometryPartsByShader(geometry, shaders))

        
        

# Controls the calling of all the functions. Use this to ensure that all 
# required steps are done for the task you want executed.
def ModelOptimize(model_tag, do_output, condense_shaders, remove_local_nodes, condense_parts):
    model = model_tag.data.tagdata
    # setup
    if condense_parts:
        condense_shaders = True
        remove_local_nodes = True
    
    # actual execution
    if condense_shaders: 
        if do_output:
            print("Condensing shaders block...", end='')
            old_shaders_size = model.shaders.size
        ModelCondenseShaders(model_tag)
        if do_output:print("done", " - Reduced shader count from ", old_shaders_size, " to ", model.shaders.size, ".\n", sep='')
        
    if remove_local_nodes:
        if do_output:print("Removing Local Nodes...", end='')
        ModelRemoveLocalNodes(model_tag)
        if do_output:print("done\n")
    
    if condense_parts:
        if do_output:print("Condensing Geometry Parts...", end='')
        ModelMergeGeometryPartsWithIdenticalShaderIds(model_tag)
        if do_output:print("done\n")
        
    
    
    
#Only run this if the script is ran directly
if __name__ == '__main__':
    from argparse import ArgumentParser
    
    #Initialise startup arguments
    parser = ArgumentParser(description='Halo Gbxmodel optimizer. Made to optimize the model for render speed.')
    parser.add_argument('-s', '--remove-duplicate-shaders', dest='remove_shader_dupes', action='store_const',
                        const=True, default=False,
                        help='Removes duplicate shaders in the model tag without breaking indices.')
    parser.add_argument('-a', '--remove-local-nodes', dest='remove_local_nodes', action='store_const',
                        const=True, default=False,
                        help='Rereferences all local nodes to use absolute nodes.')
    parser.add_argument('-p', '--condense-geometry-parts', dest='condense_geometry_parts', action='store_const',
                        const=True, default=False,
                        help='For each geometry combines all parts that use the same shader. (Automatically enables --remove-duplicate-shaders and --remove-local-nodes)')
    parser.add_argument('model_tag', metavar='model_tag', type=str,
                        help='The tag we want to operate on.')
    args = parser.parse_args()
    
    from shared.SharedFunctions import GetAbsFilepath
    model_tag_path = GetAbsFilepath(args.model_tag, mod2_ext)

    print("\nLoading model " + model_tag_path + "...", end='')
    model_tag = mod2_def.build(filepath=(model_tag_path + mod2_ext))
    print("done\n")

    ModelOptimize(model_tag, True, args.remove_shader_dupes, args.remove_local_nodes, args.condense_geometry_parts)
    
    print("Saving model tag...", end='')
    model_tag.serialize(backup=True, temp=False)
    print("finished\n")

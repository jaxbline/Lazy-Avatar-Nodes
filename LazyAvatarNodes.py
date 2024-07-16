bl_info = {
    "name": "Lazy Avatar Nodes",
    "version": (1, 0, 3),
    "author": "Jax",
    "description": "Lazy way of setting up shaders for your VRCHAT avatar in blender",
}

import bpy

class MySettings(bpy.types.PropertyGroup):
    base_color_image: bpy.props.StringProperty(name="", subtype='FILE_PATH')
    normal_image: bpy.props.StringProperty(name="", subtype='FILE_PATH')
    metallic_smoothness_image: bpy.props.StringProperty(name="", subtype='FILE_PATH')
    emission_image: bpy.props.StringProperty(name="", subtype='FILE_PATH')
    emission_same_as_base: bpy.props.BoolProperty(name="Emission same as Base", default=False)
    strength: bpy.props.FloatProperty(name="Strength", default=1.0, min=0.0, max=100.0)
    use_packed_maps: bpy.props.BoolProperty(name="Use Packed Maps", default=False)
    roughness_image: bpy.props.StringProperty(name="", subtype='FILE_PATH')
    metallic_image: bpy.props.StringProperty(name="", subtype='FILE_PATH')
    emission_color: bpy.props.FloatVectorProperty(name="Emission Color", subtype='COLOR', default=(1.0, 1.0, 1.0), min=0.0, max=1.0)

    def clear_inputs(self):
        self.base_color_image = ""
        self.normal_image = ""
        self.metallic_smoothness_image = ""
        self.emission_image = ""
        self.emission_same_as_base = False
        self.strength = 1.0
        self.roughness_image = ""
        self.metallic_image = ""
        self.emission_color = (1.0, 1.0, 1.0)

class OpenImageOperator(bpy.types.Operator):
    bl_idname = "object.open_image"
    bl_label = "Open Image"

    filter_glob: bpy.props.StringProperty(default="*.png;*.jpg;*.jpeg;*.tga;*.bmp", options={'HIDDEN'})
    image_type: bpy.props.StringProperty()
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        settings = context.scene.my_settings

        if self.image_type == "BASE_COLOR":
            settings.base_color_image = self.filepath
        elif self.image_type == "METALLIC_SMOOTHNESS":
            settings.metallic_smoothness_image = self.filepath
        elif self.image_type == "NORMAL":
            settings.normal_image = self.filepath
        elif self.image_type == "EMISSION":
            settings.emission_image = self.filepath
        elif self.image_type == "ROUGHNESS":
            settings.roughness_image = self.filepath
        elif self.image_type == "METALLIC":
            settings.metallic_image = self.filepath

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class CreateTextureNodesOperator(bpy.types.Operator):
    bl_idname = "object.create_texture_nodes"
    bl_label = "Create Texture Nodes"

    def execute(self, context):
        settings = context.scene.my_settings

        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "No mesh object selected")
            return {'CANCELLED'}

        mat = obj.active_material
        if mat is None:
            mat = bpy.data.materials.new(name="Material")
            obj.active_material = mat

        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        nodes.clear()

        output_node = nodes.new(type='ShaderNodeOutputMaterial')
        output_node.location = (400, 0)

        principled_node = nodes.new(type='ShaderNodeBsdfPrincipled')
        principled_node.location = (0, 0)

        links.new(principled_node.outputs['BSDF'], output_node.inputs['Surface'])

        if settings.base_color_image:
            base_color_node = nodes.new(type='ShaderNodeTexImage')
            base_color_node.location = (-400, 200)
            try:
                base_color_node.image = bpy.data.images.load(settings.base_color_image)
                links.new(base_color_node.outputs['Color'], principled_node.inputs['Base Color'])
            except RuntimeError:
                self.report({'ERROR'}, f"Could not load image {settings.base_color_image}")

        if settings.use_packed_maps:
            if settings.metallic_smoothness_image:
                metallic_smoothness_node = nodes.new(type='ShaderNodeTexImage')
                metallic_smoothness_node.location = (-400, 0)
                try:
                    metallic_smoothness_node.image = bpy.data.images.load(settings.metallic_smoothness_image)
                    metallic_smoothness_node.image.colorspace_settings.name = 'Non-Color'

                    separate_color_node = nodes.new(type='ShaderNodeSeparateColor')
                    separate_color_node.location = (-200, 0)
                    separate_color_node.mode = 'RGB'
                    links.new(metallic_smoothness_node.outputs['Color'], separate_color_node.inputs['Color'])

                    invert_node = nodes.new(type='ShaderNodeInvert')
                    invert_node.location = (0, -100)
                    links.new(separate_color_node.outputs['Green'], invert_node.inputs['Color'])

                    links.new(separate_color_node.outputs['Red'], principled_node.inputs['Metallic'])
                    links.new(invert_node.outputs['Color'], principled_node.inputs['Roughness'])
                    links.new(metallic_smoothness_node.outputs['Alpha'], principled_node.inputs['Specular IOR Level'])
                except RuntimeError:
                    self.report({'ERROR'}, f"Could not load image {settings.metallic_smoothness_image}")
            else:
                principled_node.inputs['Roughness'].default_value = 1.0
                principled_node.inputs['Metallic'].default_value = 0.0
        else:
            if settings.metallic_image:
                metallic_node = nodes.new(type='ShaderNodeTexImage')
                metallic_node.location = (-400, 0)
                try:
                    metallic_node.image = bpy.data.images.load(settings.metallic_image)
                    metallic_node.image.colorspace_settings.name = 'Non-Color'
                    links.new(metallic_node.outputs['Color'], principled_node.inputs['Metallic'])
                except RuntimeError:
                    self.report({'ERROR'}, f"Could not load image {settings.metallic_image}")
            else:
                principled_node.inputs['Metallic'].default_value = 0.0

            if settings.roughness_image:
                roughness_node = nodes.new(type='ShaderNodeTexImage')
                roughness_node.location = (-400, -200)
                try:
                    roughness_node.image = bpy.data.images.load(settings.roughness_image)
                    roughness_node.image.colorspace_settings.name = 'Non-Color'
                    links.new(roughness_node.outputs['Color'], principled_node.inputs['Roughness'])
                except RuntimeError:
                    self.report({'ERROR'}, f"Could not load image {settings.roughness_image}")
            else:
                principled_node.inputs['Roughness'].default_value = 1.0

        if settings.normal_image:
            normal_map_node = nodes.new(type='ShaderNodeTexImage')
            normal_map_node.location = (-400, -400)
            try:
                normal_map_node.image = bpy.data.images.load(settings.normal_image)
                normal_map_node.image.colorspace_settings.name = 'Non-Color'

                normal_map_node2 = nodes.new(type='ShaderNodeNormalMap')
                normal_map_node2.location = (-200, -400)

                links.new(normal_map_node.outputs['Color'], normal_map_node2.inputs['Color'])
                links.new(normal_map_node2.outputs['Normal'], principled_node.inputs['Normal'])
            except RuntimeError:
                self.report({'ERROR'}, f"Could not load image {settings.normal_image}")

        if settings.emission_image:
            emission_node = nodes.new(type='ShaderNodeTexImage')
            emission_node.location = (-400, 400)
            try:
                emission_node.image = bpy.data.images.load(settings.emission_image)

                if settings.emission_same_as_base:
                    multiply_node = nodes.new(type='ShaderNodeMixRGB')
                    multiply_node.blend_type = 'MULTIPLY'
                    multiply_node.location = (-200, 400)
                    multiply_node.inputs['Fac'].default_value = 1.0

                    links.new(base_color_node.outputs['Color'], multiply_node.inputs['Color2'])
                    links.new(emission_node.outputs['Color'], multiply_node.inputs['Color1'])
                    links.new(multiply_node.outputs['Color'], principled_node.inputs['Emission Color'])
                else:
                    color_ramp_node = nodes.new(type='ShaderNodeValToRGB')
                    color_ramp_node.location = (-200, 400)
                    links.new(emission_node.outputs['Color'], color_ramp_node.inputs['Fac'])
                    color_ramp_node.color_ramp.elements[1].color = (*settings.emission_color, 1.0)
                    links.new(color_ramp_node.outputs['Color'], principled_node.inputs['Emission Color'])

                value_node = nodes.new(type='ShaderNodeValue')
                value_node.location = (-200, 600)
                value_node.outputs[0].default_value = settings.strength
                links.new(value_node.outputs[0], principled_node.inputs['Emission Strength'])
            except RuntimeError:
                self.report({'ERROR'}, f"Could not load image {settings.emission_image}")
        else:
            principled_node.inputs['Emission Strength'].default_value = 0.0

        settings.clear_inputs()  # Clear inputs after creating nodes, but preserve use_packed_maps

        return {'FINISHED'}

class VIEW3D_PT_import_images_panel(bpy.types.Panel):
    bl_label = "Lazy Avatar Nodes"
    bl_idname = "VIEW3D_PT_import_images_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Jax's Stuff"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.my_settings

        obj = context.active_object
        if obj and obj.active_material:
            material_name = obj.active_material.name
        else:
            material_name = "No material selected"

        layout.label(text=f"Selected Material: {material_name}")

        layout.operator("object.open_image", text="Base Color").image_type = "BASE_COLOR"
        layout.prop(settings, "base_color_image")

        layout.operator("object.open_image", text="Normal").image_type = "NORMAL"
        layout.prop(settings, "normal_image")

        layout.prop(settings, "use_packed_maps")

        if settings.use_packed_maps:
            layout.operator("object.open_image", text="Metallic/Smoothness").image_type = "METALLIC_SMOOTHNESS"
            layout.prop(settings, "metallic_smoothness_image")
        else:
            layout.operator("object.open_image", text="Metallic").image_type = "METALLIC"
            layout.prop(settings, "metallic_image")
            layout.operator("object.open_image", text="Roughness").image_type = "ROUGHNESS"
            layout.prop(settings, "roughness_image")

        layout.operator("object.open_image", text="Emission").image_type = "EMISSION"
        layout.prop(settings, "emission_image")

        layout.prop(settings, "emission_same_as_base", text="Emission same as Base")
        
        if not settings.emission_same_as_base:
            layout.prop(settings, "emission_color", text="Emission Color")
        
        layout.prop(settings, "strength", text="Strength")

        layout.operator("object.create_texture_nodes", text="Create Texture Nodes")

def register():
    bpy.utils.register_class(MySettings)
    bpy.types.Scene.my_settings = bpy.props.PointerProperty(type=MySettings)

    bpy.utils.register_class(OpenImageOperator)
    bpy.utils.register_class(CreateTextureNodesOperator)
    bpy.utils.register_class(VIEW3D_PT_import_images_panel)

def unregister():
    bpy.utils.unregister_class(MySettings)
    del bpy.types.Scene.my_settings

    bpy.utils.unregister_class(OpenImageOperator)
    bpy.utils.unregister_class(CreateTextureNodesOperator)
    bpy.utils.unregister_class(VIEW3D_PT_import_images_panel)

if __name__ == "__main__":
    register()
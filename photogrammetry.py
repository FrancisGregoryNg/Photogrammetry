import os
import subprocess
import shutil

# =============================================================================
#  Consecutively implement the following:
# 
#           [ O p e n M V G ]
#     - Image Listing
#     - Compute Features
#     - Computes Matches
#     - Incremental SfM or Global SfM
#     - Convert Output to OpenMVS Format
# 
#           [ O p e n M V S ]
#     - Densify Point Cloud
#     - Reconstruct Mesh
#     - Refine Mesh
#     - Texture Mesh
# 
#  (This script is based from ReleaseV1.3.Yellowtail.WindowsBinaries_VS2015.)
#
#
#                   [  I N S T R U C T I O N S  ]
#  Place each image dataset in separate folders inside "Photogrammetry_Input".
#  Edit the following "IMAGE_DATASETS" list to include the folder names
#  These datasets would be evaluated in consecutive order.
#
# =============================================================================
 
IMAGE_DATASETS = [
        "propeller_tacked",
##        "M01-580KV_Multistar-3508",
##        "M02-650KV_Multistar-3525",
##        "M03-750KV_AX-2810Q",
##        "M04-750KV_Multistar-Elite-2810",
##        "M05-2300KV_Gemfan-RT2205L",
##        "M06-2300KV_Quanum-MT2204",
##        "M07-2400KV_Multistar-V-Spec-1808",
##        "M08-2750KV_DYS-MR2205",
##        "P01-6X4",
##        "P02-6X5,5",
##        "P03-7X5",
##        "P04-7X6(3)",
##        "P05-8X4",
##        "P06-8X6(3)",
##        "P07-9X6",
##        "P08-10X6",
##        "P09-11X4,7",
##        "P10-11X7",
##        "P11-11X7(3)",
        ]

reconstruction_type = 'sequential'
#reconstruction_type = 'global'
#reconstruction_type = 'both'

OPENMVG_binaries = "OpenMVG"
OPENMVS_binaries = "OpenMVS"
camera_file_params = os.path.join(os.path.dirname(__file__), 
                                  "sensor_width_camera_database.txt")
main_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
input_eval_dir = os.path.join(main_dir, "2---Data", "Photogrammetry_Input")
output_eval_dir = os.path.join(main_dir, "2---Data", "Photogrammetry_Output")

class Photogrammetry:
    def __init__(self, current_set, reconstruction_type):
        self.current_set = current_set
        self.reconstruction_type = reconstruction_type
        self.matches_bin = None
        self.input_dir = os.path.join(input_eval_dir, 
                                      IMAGE_DATASETS[current_set])
        self.output_upper_dir = os.path.join(output_eval_dir, 
                                             IMAGE_DATASETS[current_set])
        self.output_dir = os.path.join(self.output_upper_dir, 
                                       self.reconstruction_type)
        self.matches_dir = os.path.join(self.output_dir, "[01]_Matches")
        self.pointCloud_dir = os.path.join(self.output_dir, "[02]_Point_Cloud")
        self.mesh_dir = os.path.join(self.output_dir, "[03]_Mesh")
        self.compiled_dir = os.path.join(output_eval_dir, "_Compiled")
        self.max_threads = "0" #for OpenMVS (0-all available cores)
        # Create the output folders if not present
        output_folders = [
            output_eval_dir,
            self.output_upper_dir,
            self.output_dir,
            self.matches_dir,
            self.pointCloud_dir,
            self.mesh_dir,
            self.compiled_dir]
        for folder in output_folders:
            if not os.path.exists(folder):
                os.mkdir(folder)

    def pipeline(self):
        self._OpenMVG_intrinsics_analysis()
        self._OpenMVG_compute_features()
        self._OpenMVG_compute_matches()
        self._OpenMVG_reconstruction()
        self._OpenMVG_convert_to_OpenMVS()
        self._OpenMVS_densify_point_cloud()
        self._OpenMVS_reconstruct_mesh()
        self._OpenMVS_refine_mesh()
        self._OpenMVS_texture_mesh()

    def _OpenMVG_intrinsics_analysis(self):
        self._state_current_set()
        print ("\n1. Intrinsics analysis")
        pIntrisics = subprocess.Popen(
            [os.path.join(OPENMVG_binaries, 
                          "openMVG_main_SfMInit_ImageListing"),  
            "-i", self.input_dir, 
            "-o", self.matches_dir, 
            "-d", camera_file_params, 
            "-c", "3"])
        pIntrisics.wait()

    def _OpenMVG_compute_features(self):
        self._state_current_set()
        print ("\n2. Compute features")
        pFeatures = subprocess.Popen(
            [os.path.join(OPENMVG_binaries, 
                          "openMVG_main_ComputeFeatures"),  
            "-i", os.path.join(self.matches_dir,"sfm_data.json"),
            "-o", self.matches_dir, 
            "-m", "SIFT", 
            "-f", "1",
            "-p", "NORMAL", # "NORMAL", "HIGH", "ULTRA"
            "-n", "5"])
        pFeatures.wait()

    def _OpenMVG_compute_matches(self):
        self._state_current_set()
        if self.reconstruction_type=='sequential':
            print ("\n3. Compute matches")
            pMatches = subprocess.Popen(
                [os.path.join(OPENMVG_binaries, 
                              "openMVG_main_ComputeMatches"),  
                "-i", os.path.join(self.matches_dir,"sfm_data.json"),
                "-o", self.matches_dir, 
                "-f", "1",
                "-n", "ANNL2",
                "-g", "f"])
            pMatches.wait()
            self.matches_bin = "matches.f.bin"

        if self.reconstruction_type=='global':
            print ("\n3. Compute matches (for the global SfM Pipeline)")
            pMatches = subprocess.Popen(
                [os.path.join(OPENMVG_binaries, 
                              "openMVG_main_ComputeMatches"),  
                "-i", os.path.join(self.matches_dir,"sfm_data.json"),
                "-o", self.matches_dir, 
                "-f", "1",
                "-g", "e"])
            pMatches.wait()
            self.matches_bin = "matches.e.bin"
            
    def _OpenMVG_reconstruction(self):
        self._state_current_set()
        if self.reconstruction_type=='sequential':
            print ("\n4. Do Incremental/Sequential reconstruction") 
            #To-do: set manually the initial pair to avoid the prompt question
            pRecons = subprocess.Popen(
                [os.path.join(OPENMVG_binaries, 
                              "openMVG_main_IncrementalSfM"),  
                "-i", os.path.join(self.matches_dir,"sfm_data.json"),
                "-m", self.matches_dir, 
                "-o", self.pointCloud_dir])
            pRecons.wait()
            
        if self.reconstruction_type=='global':
            print ("\n4. Do Global reconstruction")
            pRecons = subprocess.Popen(
                [os.path.join(OPENMVG_binaries, 
                              "openMVG_main_GlobalSfM"),  
                "-i", os.path.join(self.matches_dir,"sfm_data.json"),
                "-m", self.matches_dir, 
                "-o", self.pointCloud_dir])
            pRecons.wait()
            
    def _OpenMVG_robust_triangulation(self): #not necessary in pipeline
        self._state_current_set()
        print ("\n5. Structure from Known Poses (robust triangulation)")
        pRecons = subprocess.Popen(
            [os.path.join(OPENMVG_binaries, 
                          "openMVG_main_ComputeStructureFromKnownPoses"),  
            "-i", os.path.join(self.pointCloud_dir,"sfm_data.bin"), 
            "-m", self.matches_dir, 
            "-f", os.path.join(self.matches_dir, self.matches_bin), 
            "-o", os.path.join(self.pointCloud_dir,"robust.bin")])
        pRecons.wait()

    def _OpenMVG_colorize_structure(self): #not necessary in pipeline
        self._state_current_set()
        print ("\n6. Colorize Structure")
        pColor = subprocess.Popen(
            [os.path.join(OPENMVG_binaries, 
                          "openMVG_main_ComputeSfM_DataColor"),  
            "-i", os.path.join(self.pointCloud_dir,"sfm_data.bin"),
            "-o", os.path.join(self.pointCloud_dir,"colorized.ply")])
        pColor.wait()
        
        pColorRobust = subprocess.Popen(
            [os.path.join(OPENMVG_binaries, 
                          "openMVG_main_ComputeSfM_DataColor"),  
            "-i", os.path.join(self.pointCloud_dir,"robust.bin"),
            "-o", os.path.join(self.pointCloud_dir,"robust_colorized.ply")])
        pColorRobust.wait()

    def _OpenMVG_convert_to_OpenMVS(self):
        self._state_current_set()
        print ("\n7. Convert Output to OpenMVS Format")
        pConvertopenMVS = subprocess.Popen(
            [os.path.join(OPENMVG_binaries, 
                          "openMVG_main_openMVG2openMVS"),  
            "-i", os.path.join(self.pointCloud_dir,"sfm_data.bin"),
            "-o", os.path.join(self.mesh_dir, "scene.mvs"),
            "-d", os.path.join(self.mesh_dir, "scene_undistorted_images"),
            "-n", "5"])
        pConvertopenMVS.wait()

    def _OpenMVS_densify_point_cloud(self):
        self._state_current_set()  
        print ("\n8. Densify Point Cloud")
        pDense = subprocess.Popen(
            [os.path.join(OPENMVS_binaries, "DensifyPointCloud"), 
            "-i", os.path.join(self.mesh_dir,"scene.mvs"),
            "-w", self.mesh_dir,
            #"--resolution-level", "2", #originally 1
                #times to scale down images before point cloud computation
            "--min-resolution", "640", #images not scaled below this resolution
            "--number-views", "4", 
                #number of views used for depth-map estimation
                #(0-all neighbor views available)
            "--number-views-fuse", "3",
                #minimum number of images that agree with an estimate during
                #fusion to consider it an inlier
            "--estimate-colors", "1", 
                #estimate the colors for the dense point cloud
            "--estimate-normals", "0",
                #estimate the normals for the dense point cloud
            "--sample-mesh", "0",
                #uniformly samples points on a mesh (0-disabled, 
                #<0 - number of points, >0 - sample density per square unit)
                #Note: The above was taken as is from the options of the
                #executable. The meaning of the parameter values are unclear.
            "--max-threads", self.max_threads])
        pDense.wait()

    def _OpenMVS_reconstruct_mesh(self):
        self._state_current_set()
        print ("\n9. Reconstruct Mesh")
        pReconsMesh = subprocess.Popen(
            [os.path.join(OPENMVS_binaries, "ReconstructMesh"),  
            "scene_dense.mvs",
            "-w", self.mesh_dir,
            "--min-point-distance", "2.5",
                #minimum pixel distance between the projection of two 3D points
                #to consider them different while triangulating (0-disabled)
            "--constant-weight", "1",
                #all views have weights 1 instead of the available weight
            "--free-space-support", "0",
                #exploits free-space support to reconstruct weakly-represented 
                #surfaces
            "--thickness-factor", "1",
                #multiplier for the minimum thickness in visibility weighting
            "--quality-factor", "1",
                #multiplier for the quality weight considered during graph-cut
            "--decimate", "1", #decimation factor from 0 to 1 (1-disabled)
            "--remove-spurious", "20", 
                #factor to remove faces with long edges or isolated components 
                #(0-disabled)
            "--remove-spikes", "1",
                #flag controlling the removal of spike faces
            "--close-holes", "30", 
                #try to close small holes in reconstructed surface (0-disabled)
            "--smooth", "2", 
                #iterations to smooth reconstructed surface (0-disabled)
            "--max-threads", self.max_threads])
        pReconsMesh.wait()

    def _OpenMVS_refine_mesh(self):
        self._state_current_set()
        print ("\n10. Refine Mesh")
        pRefine = subprocess.Popen(
            [os.path.join(OPENMVS_binaries, "RefineMesh"),  
            "scene_dense_mesh.mvs",
            "-w", self.mesh_dir,
            "--export-type", "ply",            
            #"--resolution-level", "2", #originally 0
                #times to scale down images before mesh refinement
            "--min-resolution", "640", #images not scaled below this resolution
            "--max-views", "8", #maximum neighbor images for refining the mesh
            "--decimate", "0", 
                #decimation factor from 0 to 1 applied to input surface
                #(0-auto, 1-disabled)
            "--close-holes", "30",
                #try to close small holes in input surface (0-disabled)
            "--ensure-edge-size", "1",
                #ensure edge size and improve vertex valence of input surface
                #(0-disabled, 1-auto, 2-force)
            "--max-face-area", "64",
                #maximum face area projected in any pair of images that is not
                #subdivided (0-disabled)
            "--scales", "3",
                #iterations to run mesh optimization on multi-scale images
            "--scale-step", "0.5",
                #image scale factor used at each mesh optimization step
            "--reduce-memory", "1", #recompute data to reduce memory needed
            "--alternate-pair", "0",
                #refine mesh using an image pair alternatively as reference
                #(9-both, 1-alternate, 2-only left, 3-only right)
            "--regularity-weight", "0.200000003",
                #scalar regularity weight to balance between photo-consistency
                #and regularization terms during mesh optimization
            "--rigidity-elasticity-ratio", "0.899999976",
                #scalar ratio used to compute the regularity gradient as a
                #combination of rigidity and elasticity
            "--gradient-step", "45.0499992",
                #gradient step to be used instead (0-auto)
            "--planar-vertex-ratio", "0",
                #threshold used to remove vertices on planar patches
            "--use-cuda", "1", #refine mesh using CUDA
            "--max-threads", self.max_threads,
            "-o", (IMAGE_DATASETS[self.current_set] + "_" + 
                   self.reconstruction_type + "_untextured")])
        pRefine.wait()
        self._compile_to_folder("_untextured.ply")

    def _OpenMVS_texture_mesh(self):
        self._state_current_set()    
        print ("\n11. Texture Mesh")
        pTexture = subprocess.Popen(
            [os.path.join(OPENMVS_binaries, "TextureMesh"),  
            IMAGE_DATASETS[self.current_set] + "_" + self.reconstruction_type 
                + "_untextured.mvs",
            "-w", self.mesh_dir,
            "--export-type", "ply",
            "--max-threads", self.max_threads,
            "-o", (IMAGE_DATASETS[self.current_set] + "_" + 
                   self.reconstruction_type + "_textured")])
        pTexture.wait()
        self._compile_to_folder("_textured.ply")
        self._compile_to_folder("_textured.png")

    def _state_current_set(self):
        print("\n\n\t\t\tCurrent dataset: " + IMAGE_DATASETS[self.current_set]) 

    def _compile_to_folder(self, file_appendage):
        source = os.path.join(self.mesh_dir, IMAGE_DATASETS[self.current_set] + 
                              "_" + self.reconstruction_type + file_appendage)
        output = os.path.join(output_eval_dir, "_Compiled", 
                              IMAGE_DATASETS[self.current_set] + "_" + 
                              self.reconstruction_type + file_appendage)
        shutil.copy2(source, output)
             
if reconstruction_type == 'sequential' or reconstruction_type == 'both':
    for dataset in range(len(IMAGE_DATASETS)):
        current_run = Photogrammetry(dataset, 'sequential')
        try:
            current_run.pipeline()
        except:
            pass

if reconstruction_type == 'global' or reconstruction_type == 'both':
    for dataset in range(len(IMAGE_DATASETS)):
        current_run = Photogrammetry(dataset, 'global')
        try:
            current_run.pipeline()
        except:
            pass

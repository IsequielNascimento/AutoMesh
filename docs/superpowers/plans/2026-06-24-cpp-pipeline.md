# C++ Pipeline Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Dockerized Python-based AutoMesh pipeline with a high-performance, lightweight C++ native pipeline, reducing image size to under 200MB, removing GUI/X11 dependencies, and ensuring final GLB output with correct vertex colors.

**Architecture:** A sequential C++ binary pipeline. Step 1 cleans points and estimates normals (`automesh-preproc` using LASlib + nanoflann + Eigen). Step 2 is Kazhdan's `PoissonReconstruction`. Step 3 is headless `InstantMeshes`. Step 4 is `automesh-colortransfer` (using nanoflann + tinygltf) which interpolates colors from Step 1 and writes the final `.glb` model directly.

**Tech Stack:** C++, CMake, LASlib (LAStools), nanoflann, Eigen 3, tinygltf, happly (header-only PLY parser), Docker multi-stage.

## Global Constraints

- CMake minimum version: 3.15
- C++ Standard: C++17
- Target directory for custom C++ code: `src/`
- Output GLB path: `/pipeline/output/resultado_final.glb`
- Docker runtime base image: `ubuntu:22.04` (clean runtime phase)

---

### Task 1: Project Build Setup and Dependency Management

**Files:**
- Create: `CMakeLists.txt`
- Create: `src/CMakeLists.txt`
- Modify: `.gitignore`

**Interfaces:**
- Produces: CMake build system configured to automatically pull and compile header-only dependencies (`nanoflann`, `Eigen`, `tinygltf`, `happly`).

- [ ] **Step 1: Write the root CMakeLists.txt**
  Create [CMakeLists.txt](file:///e:/Programming%20Stuff/AutoMesh/CMakeLists.txt) to declare the project, download external header-only libraries, and add the `src` subdirectory.
  ```cmake
  cmake_minimum_required(VERSION 3.15)
  project(AutoMesh CXX)

  set(CMAKE_CXX_STANDARD 17)
  set(CMAKE_CXX_STANDARD_REQUIRED ON)

  include(FetchContent)

  # nanoflann
  FetchContent_Declare(
    nanoflann
    GIT_REPOSITORY https://github.com/jlblancoc/nanoflann.git
    GIT_TAG v1.5.0
  )
  FetchContent_MakeAvailable(nanoflann)

  # Eigen
  FetchContent_Declare(
    eigen
    GIT_REPOSITORY https://gitlab.com/libeigen/eigen.git
    GIT_TAG 3.4.0
  )
  FetchContent_MakeAvailable(eigen)

  # tinygltf
  FetchContent_Declare(
    tinygltf
    GIT_REPOSITORY https://github.com/syoyo/tinygltf.git
    GIT_TAG release
  )
  FetchContent_MakeAvailable(tinygltf)

  # happly
  FetchContent_Declare(
    happly
    GIT_REPOSITORY https://github.com/Alrecenk/happly.git
    GIT_TAG master
  )
  FetchContent_MakeAvailable(happly)

  add_subdirectory(src)
  ```

- [ ] **Step 2: Create the src subdirectory CMakeLists.txt**
  Create [src/CMakeLists.txt](file:///e:/Programming%20Stuff/AutoMesh/src/CMakeLists.txt) to define targets for `automesh-preproc` and `automesh-colortransfer`.
  ```cmake
  # Targets will be defined here as sources are implemented
  ```

- [ ] **Step 3: Update .gitignore**
  Modify [.gitignore](file:///e:/Programming%20Stuff/AutoMesh/.gitignore) to ensure build directories are ignored.
  ```
  /build/
  /bin/
  ```

- [ ] **Step 4: Verify CMake Configuration**
  Create a temporary `build` folder and run cmake to check that downloads complete.
  Run: `mkdir build; cd build; cmake ..`
  Expected: Downloads for nanoflann, eigen, tinygltf, and happly finish successfully and configuration finishes.

- [ ] **Step 5: Commit build setup**
  Run: `git add CMakeLists.txt src/CMakeLists.txt .gitignore; git commit -m "build: setup CMake build system and dependencies"`

---

### Task 2: Implement `automesh-preproc` (Step 1 C++)

**Files:**
- Create: `src/preproc/main.cpp`
- Modify: `src/CMakeLists.txt`

**Interfaces:**
- Produces: Executable `automesh-preproc` that reads `.laz`, filters outliers, subsamples space, estimates normals, and writes a `.ply` point cloud.

- [ ] **Step 1: Write `src/preproc/main.cpp`**
  Create [src/preproc/main.cpp](file:///e:/Programming%20Stuff/AutoMesh/src/preproc/main.cpp) with the full C++ logic utilizing `LASlib`, `nanoflann`, `Eigen`, and `happly`.
  ```cpp
  #include <iostream>
  #include <vector>
  #include <unordered_map>
  #include <algorithm>
  #include <cmath>
  #include <fstream>
  #include <Eigen/Dense>
  #include <nanoflann.hpp>
  #include "happly.h"

  // LASlib includes (installed system-wide in builder phase)
  #include <lasreader.hpp>

  struct Point {
      double x, y, z;
      unsigned char r, g, b;
      double nx, ny, nz;
      long long grid_key[3];
  };

  struct PointCloud {
      std::vector<Point> pts;
      inline size_t kdtree_get_point_count() const { return pts.size(); }
      inline double kdtree_get_pt(const size_t idx, const size_t dim) const {
          if (dim == 0) return pts[idx].x;
          else if (dim == 1) return pts[idx].y;
          return pts[idx].z;
      }
      template <class BBOX>
      bool kdtree_get_bbox(BBOX&) const { return false; }
  };

  int main(int argc, char* argv[]) {
      if (argc < 6) {
          std::cerr << "Usage: " << argv[0] << " <input.laz> <output.ply> <spatial_subsample> <sor_neighbors> <sor_std>\n";
          return 1;
      }

      std::string input_path = argv[1];
      std::string output_path = argv[2];
      double spatial_subsample = std::stod(argv[3]);
      int sor_neighbors = std::stoi(argv[4]);
      double sor_std = std::stod(argv[5]);

      std::cout << "[*] Loading LAZ file: " << input_path << std::endl;
      LASreadOpener lasreadopener;
      lasreadopener.set_file_name(input_path.c_str());
      LASreader* lasreader = lasreadopener.open();
      if (!lasreader) {
          std::cerr << "Error opening file: " << input_path << std::endl;
          return 1;
      }

      std::vector<Point> raw_points;
      while (lasreader->read_point()) {
          Point p;
          p.x = lasreader->point.get_x();
          p.y = lasreader->point.get_y();
          p.z = lasreader->point.get_z();
          if (lasreader->point.have_rgb) {
              p.r = static_cast<unsigned char>(lasreader->point.get_rgb()[0] >> 8);
              p.g = static_cast<unsigned char>(lasreader->point.get_rgb()[1] >> 8);
              p.b = static_cast<unsigned char>(lasreader->point.get_rgb()[2] >> 8);
          } else {
              p.r = 255; p.g = 255; p.b = 255;
          }
          p.nx = p.ny = p.nz = 0.0;
          raw_points.push_back(p);
      }
      lasreader->close();
      delete lasreader;

      std::cout << "[*] Loaded " << raw_points.size() << " points." << std::endl;

      // 1. Voxel Downsampling
      std::cout << "[*] Applying voxel downsampling..." << std::endl;
      std::vector<Point> downsampled_points;
      if (spatial_subsample > 0.0) {
          struct KeyHash {
              std::size_t operator()(const std::array<long long, 3>& key) const {
                  return std::hash<long long>()(key[0]) ^ 
                         (std::hash<long long>()(key[1]) << 1) ^ 
                         (std::hash<long long>()(key[2]) << 2);
              }
          };
          std::unordered_map<std::array<long long, 3>, Point, KeyHash> voxel_grid;
          for (const auto& p : raw_points) {
              long long kx = static_cast<long long>(std::floor(p.x / spatial_subsample));
              long long ky = static_cast<long long>(std::floor(p.y / spatial_subsample));
              long long kz = static_cast<long long>(std::floor(p.z / spatial_subsample));
              std::array<long long, 3> key = {kx, ky, kz};
              if (voxel_grid.find(key) == voxel_grid.end()) {
                  voxel_grid[key] = p;
              }
          }
          for (const auto& pair : voxel_grid) {
              downsampled_points.push_back(pair.second);
          }
      } else {
          downsampled_points = raw_points;
      }
      std::cout << "[*] Points after downsampling: " << downsampled_points.size() << std::endl;

      // Build initial PointCloud struct for KD-Tree
      PointCloud cloud;
      cloud.pts = downsampled_points;

      using my_kd_tree_t = nanoflann::KDTreeSingleIndexAdaptor<
          nanoflann::L2_Simple_Adaptor<double, PointCloud>,
          PointCloud, 3>;

      my_kd_tree_t index(3, cloud, nanoflann::KDTreeSingleIndexAdaptorParams(10));
      index.buildIndex();

      // 2. SOR Outlier Removal
      std::cout << "[*] Applying SOR filter..." << std::endl;
      std::vector<double> avg_distances(cloud.pts.size());
      double global_mean = 0.0;
      for (size_t i = 0; i < cloud.pts.size(); ++i) {
          double query_pt[3] = { cloud.pts[i].x, cloud.pts[i].y, cloud.pts[i].z };
          std::vector<size_t> ret_index(sor_neighbors);
          std::vector<double> out_dist_sqr(sor_neighbors);
          index.knnSearch(&query_pt[0], sor_neighbors, &ret_index[0], &out_dist_sqr[0]);

          double sum_dist = 0.0;
          for (int j = 1; j < sor_neighbors; ++j) { // skip neighbor 0 (itself)
              sum_dist += std::sqrt(out_dist_sqr[j]);
          }
          avg_distances[i] = sum_dist / (sor_neighbors - 1);
          global_mean += avg_distances[i];
      }
      global_mean /= cloud.pts.size();

      double sq_sum = 0.0;
      for (double d : avg_distances) sq_sum += (d - global_mean) * (d - global_mean);
      double global_std = std::sqrt(sq_sum / cloud.pts.size());

      std::vector<Point> clean_points;
      double sor_threshold = global_mean + sor_std * global_std;
      for (size_t i = 0; i < cloud.pts.size(); ++i) {
          if (avg_distances[i] <= sor_threshold) {
              clean_points.push_back(cloud.pts[i]);
          }
      }
      std::cout << "[*] Points after SOR filter: " << clean_points.size() << std::endl;

      // Rebuild tree on clean points
      cloud.pts = clean_points;
      my_kd_tree_t clean_index(3, cloud, nanoflann::KDTreeSingleIndexAdaptorParams(10));
      clean_index.buildIndex();

      // 3. Normal Estimation
      std::cout << "[*] Estimating normals..." << std::endl;
      const int k_normals = 10;
      for (size_t i = 0; i < cloud.pts.size(); ++i) {
          double query_pt[3] = { cloud.pts[i].x, cloud.pts[i].y, cloud.pts[i].z };
          std::vector<size_t> ret_index(k_normals);
          std::vector<double> out_dist_sqr(k_normals);
          clean_index.knnSearch(&query_pt[0], k_normals, &ret_index[0], &out_dist_sqr[0]);

          // Compute Centroid
          Eigen::Vector3d centroid(0.0, 0.0, 0.0);
          for (int j = 0; j < k_normals; ++j) {
              const auto& p = cloud.pts[ret_index[j]];
              centroid += Eigen::Vector3d(p.x, p.y, p.z);
          }
          centroid /= k_normals;

          // Covariance Matrix
          Eigen::Matrix3d cov = Eigen::Matrix3d::Zero();
          for (int j = 0; j < k_normals; ++j) {
              const auto& p = cloud.pts[ret_index[j]];
              Eigen::Vector3d d = Eigen::Vector3d(p.x, p.y, p.z) - centroid;
              cov += d * d.transpose();
          }

          // Smallest Eigenvector
          Eigen::SelfAdjointEigenSolver<Eigen::Matrix3d> solver(cov);
          Eigen::Vector3d normal = solver.eigenvectors().col(0);
          normal.normalize();

          // Orient towards viewer (assumed looking down -Z or local positive Z)
          if (normal.z() < 0.0) {
              normal = -normal;
          }

          cloud.pts[i].nx = normal.x();
          cloud.pts[i].ny = normal.y();
          cloud.pts[i].nz = normal.z();
      }

      // Write PLY using happly
      std::cout << "[*] Writing PLY to: " << output_path << std::endl;
      happly::PLYData ply_data;
      std::vector<std::array<double, 3>> positions;
      std::vector<std::array<double, 3>> normals;
      std::vector<std::array<unsigned char, 3>> colors;

      for (const auto& p : cloud.pts) {
          positions.push_back({p.x, p.y, p.z});
          normals.push_back({p.nx, p.ny, p.nz});
          colors.push_back({p.r, p.g, p.b});
      }

      ply_data.addVertexPositions(positions);
      ply_data.addVertexNormals(normals);
      ply_data.addVertexColors(colors);
      ply_data.write(output_path, happly::DataFormat::Binary);

      std::cout << "[*] Preprocessing completed successfully." << std::endl;
      return 0;
  }
  ```

- [ ] **Step 2: Define build target in `src/CMakeLists.txt`**
  Modify [src/CMakeLists.txt](file:///e:/Programming%20Stuff/AutoMesh/src/CMakeLists.txt) to build the `automesh-preproc` binary, linking with `LAS` (requires `LAS` library, which will be found via find_library or direct compiler flags in Docker phase).
  ```cmake
  add_executable(automesh-preproc preproc/main.cpp)
  target_link_libraries(automesh-preproc las nanoflann::nanoflann Eigen3::Eigen happly)
  ```

- [ ] **Step 3: Create a mock compilation script for local verification**
  Since building LASlib locally requires its sources, write a small shell script to build target step-by-step or skip until Docker. We will test during Docker build.

- [ ] **Step 4: Commit `automesh-preproc` code**
  Run: `git add src/preproc/main.cpp src/CMakeLists.txt; git commit -m "feat: implement C++ point cloud preprocessor"`

---

### Task 3: Implement `automesh-colortransfer` and GLB Exporter (Step 4 C++)

**Files:**
- Create: `src/colortransfer/main.cpp`
- Modify: `src/CMakeLists.txt`

**Interfaces:**
- Consumes: Outlier-removed PLY `passo1_nuvem.ply` (with colors) and decimate PLY `passo3_lowpoly.ply` (without colors).
- Produces: Executable `automesh-colortransfer` which produces the final `/pipeline/output/resultado_final.glb` file.

- [ ] **Step 1: Write `src/colortransfer/main.cpp`**
  Create [src/colortransfer/main.cpp](file:///e:/Programming%20Stuff/AutoMesh/src/colortransfer/main.cpp). This handles loading target PLY, building KD-tree on source PLY, interpolating colors via Inverse Distance Weighting, and exporting GLB via tinygltf.
  ```cpp
  #include <iostream>
  #include <vector>
  #include <array>
  #include <cmath>
  #include <limits>
  #include <nanoflann.hpp>
  #include "happly.h"

  #define TINYGLTF_IMPLEMENTATION
  #define STB_IMAGE_IMPLEMENTATION
  #define STB_IMAGE_WRITE_IMPLEMENTATION
  #include "tiny_gltf.h"

  struct PointCloud {
      std::vector<std::array<double, 3>> pts;
      std::vector<std::array<unsigned char, 3>> colors;

      inline size_t kdtree_get_point_count() const { return pts.size(); }
      inline double kdtree_get_pt(const size_t idx, const size_t dim) const {
          return pts[idx][dim];
      }
      template <class BBOX>
      bool kdtree_get_bbox(BBOX&) const { return false; }
  };

  int main(int argc, char* argv[]) {
      if (argc < 4) {
          std::cerr << "Usage: " << argv[0] << " <source_cloud.ply> <target_mesh.ply> <output.glb>\n";
          return 1;
      }

      std::string source_path = argv[1];
      std::string target_path = argv[2];
      std::string output_path = argv[3];

      std::cout << "[*] Loading source cloud: " << source_path << std::endl;
      happly::PLYData source_ply(source_path);
      PointCloud source_cloud;
      source_cloud.pts = source_ply.getVertexPositions();
      try {
          source_cloud.colors = source_ply.getVertexColors();
      } catch (...) {
          std::cerr << "[!] Error: Source cloud has no vertex colors." << std::endl;
          return 1;
      }

      std::cout << "[*] Loading target mesh: " << target_path << std::endl;
      happly::PLYData target_ply(target_path);
      std::vector<std::array<double, 3>> target_positions = target_ply.getVertexPositions();
      std::vector<std::vector<size_t>> target_faces = target_ply.getFaceIndices();
      std::vector<std::array<double, 3>> target_normals;
      try {
          target_normals = target_ply.getVertexNormals();
      } catch (...) {
          std::cout << "[*] Normal estimation missing in target. Generating empty normals..." << std::endl;
          target_normals.resize(target_positions.size(), {0.0, 0.0, 1.0});
      }

      // Build KD-tree on Source Cloud
      using my_kd_tree_t = nanoflann::KDTreeSingleIndexAdaptor<
          nanoflann::L2_Simple_Adaptor<double, PointCloud>,
          PointCloud, 3>;

      my_kd_tree_t index(3, source_cloud, nanoflann::KDTreeSingleIndexAdaptorParams(10));
      index.buildIndex();

      // Interpolate Colors
      std::cout << "[*] Interpolating colors for target vertices..." << std::endl;
      std::vector<std::array<unsigned char, 3>> target_colors(target_positions.size());
      const int N_NEIGHBORS = 3;

      for (size_t i = 0; i < target_positions.size(); ++i) {
          double query_pt[3] = { target_positions[i][0], target_positions[i][1], target_positions[i][2] };
          std::vector<size_t> ret_index(N_NEIGHBORS);
          std::vector<double> out_dist_sqr(N_NEIGHBORS);
          index.knnSearch(&query_pt[0], N_NEIGHBORS, &ret_index[0], &out_dist_sqr[0]);

          double sum_weight = 0.0;
          double r_sum = 0.0, g_sum = 0.0, b_sum = 0.0;

          for (int j = 0; j < N_NEIGHBORS; ++j) {
              double d = std::sqrt(out_dist_sqr[j]);
              double weight = 1.0 / (d + 1e-6);
              sum_weight += weight;
              r_sum += source_cloud.colors[ret_index[j]][0] * weight;
              g_sum += source_cloud.colors[ret_index[j]][1] * weight;
              b_sum += source_cloud.colors[ret_index[j]][2] * weight;
          }

          target_colors[i][0] = static_cast<unsigned char>(std::round(r_sum / sum_weight));
          target_colors[i][1] = static_cast<unsigned char>(std::round(g_sum / sum_weight));
          target_colors[i][2] = static_cast<unsigned char>(std::round(b_sum / sum_weight));
      }

      // Export GLB using tinygltf
      std::cout << "[*] Formatting mesh to GLB..." << std::endl;
      tinygltf::Model model;
      tinygltf::Asset asset;
      asset.version = "2.0";
      asset.generator = "AutoMesh-C++";
      model.asset = asset;

      // Pack buffers
      std::vector<unsigned char> buffer_data;

      // 1. Positions (float32)
      size_t pos_offset = buffer_data.size();
      for (const auto& pos : target_positions) {
          float p[3] = { static_cast<float>(pos[0]), static_cast<float>(pos[1]), static_cast<float>(pos[2]) };
          buffer_data.insert(buffer_data.end(), reinterpret_cast<unsigned char*>(p), reinterpret_cast<unsigned char*>(p) + sizeof(p));
      }

      // 2. Normals (float32)
      size_t norm_offset = buffer_data.size();
      for (const auto& norm : target_normals) {
          float n[3] = { static_cast<float>(norm[0]), static_cast<float>(norm[1]), static_cast<float>(norm[2]) };
          buffer_data.insert(buffer_data.end(), reinterpret_cast<unsigned char*>(n), reinterpret_cast<unsigned char*>(n) + sizeof(n));
      }

      // 3. Colors (float32, 0.0 - 1.0, 3 floats per vertex as RGB)
      size_t color_offset = buffer_data.size();
      for (const auto& col : target_colors) {
          float c[3] = { col[0] / 255.0f, col[1] / 255.0f, col[2] / 255.0f };
          buffer_data.insert(buffer_data.end(), reinterpret_cast<unsigned char*>(c), reinterpret_cast<unsigned char*>(c) + sizeof(c));
      }

      // 4. Indices (uint32)
      size_t index_offset = buffer_data.size();
      for (const auto& face : target_faces) {
          if (face.size() >= 3) {
              unsigned int idx0 = static_cast<unsigned int>(face[0]);
              unsigned int idx1 = static_cast<unsigned int>(face[1]);
              unsigned int idx2 = static_cast<unsigned int>(face[2]);
              buffer_data.insert(buffer_data.end(), reinterpret_cast<unsigned char*>(&idx0), reinterpret_cast<unsigned char*>(&idx0) + sizeof(idx0));
              buffer_data.insert(buffer_data.end(), reinterpret_cast<unsigned char*>(&idx1), reinterpret_cast<unsigned char*>(&idx1) + sizeof(idx1));
              buffer_data.insert(buffer_data.end(), reinterpret_cast<unsigned char*>(&idx2), reinterpret_cast<unsigned char*>(&idx2) + sizeof(idx2));
          }
      }

      tinygltf::Buffer buffer;
      buffer.data = std::move(buffer_data);
      model.buffers.push_back(std::move(buffer));

      // BufferViews
      tinygltf::BufferView pos_bv;
      pos_bv.buffer = 0; pos_bv.byteOffset = pos_offset;
      pos_bv.byteLength = target_positions.size() * 12;
      pos_bv.target = TINYGLTF_TARGET_ARRAY_BUFFER;
      model.bufferViews.push_back(pos_bv);

      tinygltf::BufferView norm_bv;
      norm_bv.buffer = 0; norm_bv.byteOffset = norm_offset;
      norm_bv.byteLength = target_normals.size() * 12;
      norm_bv.target = TINYGLTF_TARGET_ARRAY_BUFFER;
      model.bufferViews.push_back(norm_bv);

      tinygltf::BufferView col_bv;
      col_bv.buffer = 0; col_bv.byteOffset = color_offset;
      col_bv.byteLength = target_colors.size() * 12;
      col_bv.target = TINYGLTF_TARGET_ARRAY_BUFFER;
      model.bufferViews.push_back(col_bv);

      tinygltf::BufferView idx_bv;
      idx_bv.buffer = 0; idx_bv.byteOffset = index_offset;
      size_t num_indices = 0;
      for (const auto& f : target_faces) if (f.size() >= 3) num_indices += 3;
      idx_bv.byteLength = num_indices * 4;
      idx_bv.target = TINYGLTF_ELEMENT_ARRAY_BUFFER;
      model.bufferViews.push_back(idx_bv);

      // Accessors
      tinygltf::Accessor pos_acc;
      pos_acc.bufferView = 0; pos_acc.componentType = TINYGLTF_COMPONENT_TYPE_FLOAT;
      pos_acc.count = target_positions.size(); pos_acc.type = TINYGLTF_TYPE_VEC3;
      model.accessors.push_back(pos_acc);

      tinygltf::Accessor norm_acc;
      norm_acc.bufferView = 1; norm_acc.componentType = TINYGLTF_COMPONENT_TYPE_FLOAT;
      norm_acc.count = target_normals.size(); norm_acc.type = TINYGLTF_TYPE_VEC3;
      model.accessors.push_back(norm_acc);

      tinygltf::Accessor col_acc;
      col_acc.bufferView = 2; col_acc.componentType = TINYGLTF_COMPONENT_TYPE_FLOAT;
      col_acc.count = target_colors.size(); col_acc.type = TINYGLTF_TYPE_VEC3;
      model.accessors.push_back(col_acc);

      tinygltf::Accessor idx_acc;
      idx_acc.bufferView = 3; idx_acc.componentType = TINYGLTF_COMPONENT_TYPE_UNSIGNED_INT;
      idx_acc.count = num_indices; idx_acc.type = TINYGLTF_TYPE_SCALAR;
      model.accessors.push_back(idx_acc);

      // Material
      tinygltf::Material material;
      material.name = "VertexColoredMaterial";
      material.pbrMetallicRoughness.roughnessFactor = 0.8;
      material.pbrMetallicRoughness.metallicFactor = 0.1;
      model.materials.push_back(material);

      // Primitive
      tinygltf::Primitive primitive;
      primitive.attributes["POSITION"] = 0;
      primitive.attributes["NORMAL"] = 1;
      primitive.attributes["COLOR_0"] = 2;
      primitive.indices = 3;
      primitive.material = 0;
      primitive.mode = TINYGLTF_MODE_TRIANGLES;

      tinygltf::Mesh mesh;
      mesh.name = "LowPolyMesh";
      mesh.primitives.push_back(primitive);
      model.meshes.push_back(mesh);

      tinygltf::Node node;
      node.mesh = 0;
      model.nodes.push_back(node);

      tinygltf::Scene scene;
      scene.nodes.push_back(0);
      model.scenes.push_back(scene);
      model.defaultScene = 0;

      std::cout << "[*] Saving GLB to: " << output_path << std::endl;
      tinygltf::TinyGLTF gltf_writer;
      if (!gltf_writer.WriteGltfSceneToFile(&model, output_path, true, true, true, true)) {
          std::cerr << "[!] Error writing GLB file." << std::endl;
          return 1;
      }

      std::cout << "[*] GLB export completed successfully." << std::endl;
      return 0;
  }
  ```

- [ ] **Step 2: Define build target in `src/CMakeLists.txt`**
  Modify [src/CMakeLists.txt](file:///e:/Programming%20Stuff/AutoMesh/src/CMakeLists.txt) to build the `automesh-colortransfer` binary.
  ```cmake
  # Append this to src/CMakeLists.txt
  add_executable(automesh-colortransfer colortransfer/main.cpp)
  target_link_libraries(automesh-colortransfer nanoflann::nanoflann tinygltf happly)
  ```

- [ ] **Step 3: Commit `automesh-colortransfer` code**
  Run: `git add src/colortransfer/main.cpp src/CMakeLists.txt; git commit -m "feat: implement C++ color transfer and GLB exporter"`

---

### Task 4: Docker Setup and Integration

**Files:**
- Create: `Dockerfile.new` (temporarily, to preserve original during validation)
- Create: `entrypoint.sh.new`
- Modify: `docker-compose.yml`

**Interfaces:**
- Consumes: Environment variables (`INPUT_FILE`, `TARGET_VERTICES`, `POISSON_DEPTH`, `SOR_NEIGHBORS`, `SOR_STD`, `SPATIAL_SUBSAMPLE`)
- Produces: Docker image that executes the native binaries, generating the output `.glb` in the target volume.

- [ ] **Step 1: Write `Dockerfile.new`**
  Create [Dockerfile.new](file:///e:/Programming%20Stuff/AutoMesh/Dockerfile.new) containing the multi-stage build.
  ```dockerfile
  # --- Phase 1: Builder ---
  FROM ubuntu:22.04 AS builder

  ENV DEBIAN_FRONTEND=noninteractive
  RUN apt-get update && apt-get install -y \
      build-essential \
      cmake \
      git \
      wget \
      unzip \
      libpng-dev \
      zlib1g-dev \
      && rm -rf /var/lib/apt/lists/*

  # 1. Compile LASlib (LAStools)
  WORKDIR /build-libs
  RUN git clone https://github.com/LAStools/LAStools.git \
      && cd LAStools/LASlib \
      && mkdir build && cd build \
      && cmake .. -DCMAKE_BUILD_TYPE=Release \
      && make -j$(nproc) \
      && make install

  # 2. Compile PoissonReconstruction (Kazhdan)
  WORKDIR /build-libs
  RUN git clone https://github.com/mkazhdan/PoissonReconstruction.git \
      && cd PoissonReconstruction \
      && make -j$(nproc) \
      && cp Bin/Linux/PoissonReconstruction /usr/local/bin/

  # 3. Compile Instant Meshes (Headless)
  WORKDIR /build-libs
  RUN git clone --recursive https://github.com/wjakob/instant-meshes.git \
      && cd instant-meshes \
      && mkdir build && cd build \
      && cmake .. -DINSTANT_MESHES_CLI=ON \
      && make -j$(nproc) \
      && cp InstantMeshes /usr/local/bin/

  # 4. Compile our custom C++ Pipeline Tools
  WORKDIR /app
  COPY CMakeLists.txt ./
  COPY src/ ./src/
  RUN mkdir build && cd build \
      && cmake .. -DCMAKE_BUILD_TYPE=Release \
      && make -j$(nproc)

  # --- Phase 2: Runtime ---
  FROM ubuntu:22.04

  ENV DEBIAN_FRONTEND=noninteractive
  RUN apt-get update && apt-get install -y \
      libpng16-16 \
      libgomp1 \
      && rm -rf /var/lib/apt/lists/*

  # Copy compiled executables from builder
  COPY --from=builder /usr/local/bin/PoissonReconstruction /usr/local/bin/
  COPY --from=builder /usr/local/bin/InstantMeshes /usr/local/bin/
  COPY --from=builder /app/build/src/automesh-preproc /usr/local/bin/
  COPY --from=builder /app/build/src/automesh-colortransfer /usr/local/bin/

  # Script
  WORKDIR /pipeline
  COPY entrypoint.sh.new ./entrypoint.sh
  RUN chmod +x ./entrypoint.sh

  VOLUME ["/pipeline/input", "/pipeline/output"]

  ENTRYPOINT ["/pipeline/entrypoint.sh"]
  ```

- [ ] **Step 2: Write `entrypoint.sh.new`**
  Create [entrypoint.sh.new](file:///e:/Programming%20Stuff/AutoMesh/entrypoint.sh.new) to orchestrate calls to the compiled executables.
  ```bash
  #!/bin/bash
  set -e

  log() { echo -e "\033[0;34m[INFO]\033[0m $1"; }
  success() { echo -e "\033[0;32m[OK]\033[0m   $1"; }
  error() { echo -e "\033[0;31m[ERRO]\033[0m $1"; exit 1; }

  INPUT_DIR="/pipeline/input"
  OUTPUT_DIR="/pipeline/output"

  TARGET_VERTICES="${TARGET_VERTICES:-80000}"
  POISSON_DEPTH="${POISSON_DEPTH:-10}"
  SOR_NEIGHBORS="${SOR_NEIGHBORS:-20}"
  SOR_STD="${SOR_STD:-1.5}"
  SPATIAL_SUBSAMPLE="${SPATIAL_SUBSAMPLE:-0.5}"

  # Detect input
  if [ -z "$INPUT_FILE" ]; then
      INPUT_LAZ=$(find "$INPUT_DIR" -maxdepth 1 -name "*.laz" | head -1)
      [ -z "$INPUT_LAZ" ] && error "Nenhum .laz encontrado em $INPUT_DIR"
  else
      INPUT_LAZ="${INPUT_DIR}/${INPUT_FILE}"
      [ ! -f "$INPUT_LAZ" ] && error "Arquivo nao encontrado: $INPUT_LAZ"
  fi

  OUTPUT_GLB="${OUTPUT_DIR}/resultado_final.glb"

  log "Entrada           : $INPUT_LAZ"
  log "Saida GLB         : $OUTPUT_GLB"
  log "Target vertices   : $TARGET_VERTICES"
  log "Poisson depth     : $POISSON_DEPTH"

  # 1. Preprocess
  log "Executando automesh-preproc..."
  automesh-preproc "$INPUT_LAZ" "/tmp/passo1_nuvem.ply" "$SPATIAL_SUBSAMPLE" "$SOR_NEIGHBORS" "$SOR_STD"

  # 2. Poisson
  log "Executando PoissonReconstruction..."
  PoissonReconstruction --in "/tmp/passo1_nuvem.ply" --out "/tmp/passo2_highpoly.ply" --depth "$POISSON_DEPTH" --threads $(nproc)

  # 3. Retopology
  log "Executando InstantMeshes..."
  InstantMeshes -o "/tmp/passo3_lowpoly.ply" -v "$TARGET_VERTICES" "/tmp/passo2_highpoly.ply"

  # 4. Color transfer & GLB export
  log "Executando automesh-colortransfer..."
  automesh-colortransfer "/tmp/passo1_nuvem.ply" "/tmp/passo3_lowpoly.ply" "$OUTPUT_GLB"

  success "PIPELINE FINALIZADO COM SUCESSO! Arquivo salvo em: $OUTPUT_GLB"
  ls -lh "$OUTPUT_GLB"
  ```

- [ ] **Step 3: Modify `docker-compose.yml` to target new files**
  Edit [docker-compose.yml](file:///e:/Programming%20Stuff/AutoMesh/docker-compose.yml).
  ```yaml
  # Replace lines 3-5 with:
  #     build:
  #       context: .
  #       dockerfile: Dockerfile.new
  ```

- [ ] **Step 4: Commit integration files**
  Run: `git add Dockerfile.new entrypoint.sh.new docker-compose.yml; git commit -m "feat: add docker files and build configuration for C++ pipeline"`

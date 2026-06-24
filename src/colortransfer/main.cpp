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
